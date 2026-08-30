from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

REQUIRED_LINEAGE_FIELDS = ("model_family", "provider", "prompt_hash")

class EchoQuorumError(ValueError):
    pass


def _norm_str(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EchoQuorumError("expected non-empty string")
    return value.strip()


def _norm_set(value: Any, field: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list):
        raise EchoQuorumError(f"{field} must be a list of strings")
    out = []
    for item in value:
        out.append(_norm_str(item))
    return frozenset(out)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _lineage_completeness(vote: dict[str, Any]) -> float:
    present = sum(bool(vote.get(k)) for k in REQUIRED_LINEAGE_FIELDS)
    present += int(bool(vote.get("evidence")))
    present += int(bool(vote.get("tools")))
    return present / 5.0


def pair_correlation(a: dict[str, Any], b: dict[str, Any]) -> tuple[float, list[str]]:
    """Return deterministic correlation estimate and reasons.

    This is intentionally a provenance correlation heuristic, not a semantic
    similarity model. It asks whether two votes plausibly share upstream causes.
    """
    score = 0.0
    reasons: list[str] = []
    if a.get("model_family") and a.get("model_family") == b.get("model_family"):
        score += 0.25; reasons.append("same model_family")
    if a.get("provider") and a.get("provider") == b.get("provider"):
        score += 0.10; reasons.append("same provider")
    if a.get("prompt_hash") and a.get("prompt_hash") == b.get("prompt_hash"):
        score += 0.20; reasons.append("same prompt_hash")
    ev = _jaccard(a["evidence"], b["evidence"])
    if ev:
        score += 0.35 * ev; reasons.append(f"evidence overlap={ev:.3f}")
    tools = _jaccard(a["tools"], b["tools"])
    if tools:
        score += 0.10 * tools; reasons.append(f"tool overlap={tools:.3f}")

    ca, cb = _lineage_completeness(a), _lineage_completeness(b)
    if ca < 0.4 and cb < 0.4:
        score = max(score, 0.80)
        reasons.append("both votes have insufficient lineage")
    elif ca < 0.4 or cb < 0.4:
        score = max(score, 0.55)
        reasons.append("one vote has insufficient lineage")
    return min(score, 1.0), reasons


class _DSU:
    def __init__(self, items: Iterable[str]):
        self.parent = {x: x for x in items}
    def find(self, x: str) -> str:
        p = self.parent[x]
        if p != x:
            self.parent[x] = self.find(p)
        return self.parent[x]
    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


@dataclass(frozen=True)
class Assessment:
    decision_id: str
    choice: str
    raw_votes: int
    independent_groups: int
    threshold: int
    quorum_met: bool
    groups: tuple[tuple[str, ...], ...]
    edges: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["groups"] = [list(g) for g in self.groups]
        d["edges"] = list(self.edges)
        d["warnings"] = list(self.warnings)
        return d


def _normalize_case(case: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(case, dict):
        raise EchoQuorumError("case must be a JSON object")
    decision_id = _norm_str(case.get("decision_id"))
    threshold = case.get("threshold")
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1:
        raise EchoQuorumError("threshold must be an integer >= 1")
    cutoff = case.get("correlation_cutoff", 0.70)
    if not isinstance(cutoff, (int, float)) or isinstance(cutoff, bool) or not 0 <= float(cutoff) <= 1:
        raise EchoQuorumError("correlation_cutoff must be between 0 and 1")
    votes_in = case.get("votes")
    if not isinstance(votes_in, list) or not votes_in:
        raise EchoQuorumError("votes must be a non-empty list")
    seen: set[str] = set(); votes=[]
    for raw in votes_in:
        if not isinstance(raw, dict):
            raise EchoQuorumError("each vote must be an object")
        aid = _norm_str(raw.get("agent_id"))
        if aid in seen:
            raise EchoQuorumError(f"duplicate agent_id: {aid}")
        seen.add(aid)
        choice = _norm_str(raw.get("choice"))
        vote = {
            "agent_id": aid,
            "choice": choice,
            "model_family": str(raw.get("model_family", "")).strip(),
            "provider": str(raw.get("provider", "")).strip(),
            "prompt_hash": str(raw.get("prompt_hash", "")).strip(),
            "evidence": _norm_set(raw.get("evidence"), "evidence"),
            "tools": _norm_set(raw.get("tools"), "tools"),
        }
        votes.append(vote)
    return {"decision_id": decision_id, "threshold": threshold, "correlation_cutoff": float(cutoff), "votes": votes}


def assess(case: dict[str, Any], choice: str | None = None) -> Assessment:
    c = _normalize_case(case)
    if choice is None:
        counts: dict[str, int] = {}
        for v in c["votes"]:
            counts[v["choice"]] = counts.get(v["choice"], 0) + 1
        choice = sorted(counts, key=lambda x: (-counts[x], x))[0]
    choice = _norm_str(choice)
    votes = [v for v in c["votes"] if v["choice"] == choice]
    ids = [v["agent_id"] for v in votes]
    dsu = _DSU(ids)
    edges=[]
    for i, a in enumerate(votes):
        for b in votes[i+1:]:
            score, reasons = pair_correlation(a,b)
            if score >= c["correlation_cutoff"]:
                dsu.union(a["agent_id"], b["agent_id"])
                edges.append({"a": a["agent_id"], "b": b["agent_id"], "score": round(score,6), "reasons": reasons})
    groups_map: dict[str, list[str]] = {}
    for aid in ids:
        groups_map.setdefault(dsu.find(aid), []).append(aid)
    groups = tuple(sorted((tuple(sorted(v)) for v in groups_map.values()), key=lambda g: g[0]))
    warnings=[]
    for v in votes:
        if _lineage_completeness(v) < 0.6:
            warnings.append(f"{v['agent_id']}: incomplete lineage reduces confidence in independence")
    return Assessment(
        decision_id=c["decision_id"], choice=choice, raw_votes=len(votes),
        independent_groups=len(groups), threshold=c["threshold"],
        quorum_met=len(groups) >= c["threshold"], groups=groups,
        edges=tuple(sorted(edges,key=lambda e:(e["a"],e["b"]))), warnings=tuple(sorted(warnings)))


def load_case(path: str | Path) -> dict[str, Any]:
    try:
        data=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise EchoQuorumError(str(e)) from e
    if not isinstance(data,dict):
        raise EchoQuorumError("top-level JSON must be an object")
    return data


def canonical_digest(case: dict[str, Any]) -> str:
    c=_normalize_case(case)
    serial={**c,"votes":[{**v,"evidence":sorted(v["evidence"]),"tools":sorted(v["tools"])} for v in c["votes"]]}
    return sha256(json.dumps(serial,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
