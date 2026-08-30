# EchoQuorum

[![CI](https://github.com/BryanFiFife/EchoQuorum/actions/workflows/ci.yml/badge.svg)](https://github.com/BryanFiFife/EchoQuorum/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/runtime%20dependencies-0-success)
![License](https://img.shields.io/badge/license-MIT-blue)
![Mode](https://img.shields.io/badge/enforcement-deterministic-informational)
![Agentic AI](https://img.shields.io/badge/agentic%20AI-swarm%20safety-8A2BE2)

**Five agents agreeing is not the same thing as five independent votes.**

EchoQuorum is a zero-runtime-dependency verifier for AI-agent councils, swarms and ensemble workflows. It detects shared upstream provenance and calculates an **effective independent quorum** instead of blindly counting agent IDs.

## The future failure mode

As agent systems scale horizontally, operators will increasingly use “multiple agents agreed” as a confidence signal. That signal is weak when those agents share the same model family, provider, prompt, evidence or tool path. Correlated agents can produce the appearance of consensus without independent evidence. EchoQuorum turns that hidden correlation into a machine-checkable gate.

## What it does

- Ingests a JSON vote manifest.
- Compares model family, provider, prompt digest, evidence hashes and tool lineage.
- Builds an explainable correlation graph.
- Collapses correlated voters into provenance groups.
- Fails quorum when the number of independent groups is below the required threshold.
- Treats missing lineage conservatively.
- Emits deterministic JSON suitable for CI or an agent runtime.

## Quick start

```bash
git clone https://github.com/BryanFiFife/EchoQuorum.git
cd EchoQuorum
PYTHONPATH=src python -m echoquorum.cli assess examples/correlated.json
```

Expected result: three raw `approve` votes collapse to two independent provenance groups, so a threshold of three fails. Exit code `2` means “well-formed assessment, quorum not met”; malformed input exits `3`.

## Manifest

```json
{
  "decision_id": "deploy-production",
  "threshold": 3,
  "correlation_cutoff": 0.70,
  "votes": [
    {
      "agent_id": "planner-a",
      "choice": "approve",
      "model_family": "family-a",
      "provider": "provider-a",
      "prompt_hash": "sha256:...",
      "evidence": ["sha256:source-1"],
      "tools": ["mcp:deploy"]
    }
  ]
}
```

## Correlation heuristic

The v0.1 score is intentionally boring and inspectable: same model family `0.25`, same provider `0.10`, same prompt digest `0.20`, evidence Jaccard overlap up to `0.35`, tool overlap up to `0.10`. At or above the configured cutoff, the two voters share an edge. Connected voters form one effective provenance group.

This is **not** a claim that two different model families are truly independent. It is a practical, deterministic lower-bound check using provenance you can actually log. See `docs/THREAT_MODEL.md`.

## Why not an LLM judge?

A model judging whether other models are independent introduces the same hidden-correlation problem into the safety gate. EchoQuorum keeps the allow/deny path deterministic, offline and replayable.

## Integration pattern

```python
from echoquorum import assess
result = assess(manifest, choice="approve")
if not result.quorum_met:
    raise RuntimeError("independent quorum not met")
```

## Quality gates

```bash
python -m compileall -q src tests
PYTHONPATH=src python -m unittest discover -s tests -v
```

The repository ships adversarial tests for duplicate identities, missing lineage, correlated evidence, malformed thresholds, deterministic grouping and CLI exit semantics.

## Scope

EchoQuorum complements identity, provenance, governance and debate frameworks. It does not verify the truth of evidence, detect all collusion, authenticate provenance by itself, or guarantee a correct decision. Its job is one thing: **do not call correlated votes an independent quorum.**

## Security

Read `SECURITY.md` and `docs/THREAT_MODEL.md` before using this as an enforcement gate. Provenance must be collected by a trusted runtime rather than self-asserted by the voting agents.

## License

MIT.
