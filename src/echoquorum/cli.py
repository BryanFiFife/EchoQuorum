from __future__ import annotations
import argparse, json, sys
from .core import EchoQuorumError, assess, load_case, canonical_digest

def main(argv=None) -> int:
    p=argparse.ArgumentParser(prog="echoquorum",description="Independence-aware quorum checks for AI agent swarms")
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("assess",help="assess quorum from a JSON vote manifest")
    a.add_argument("manifest"); a.add_argument("--choice"); a.add_argument("--json",action="store_true")
    d=sub.add_parser("digest",help="print canonical manifest digest"); d.add_argument("manifest")
    ns=p.parse_args(argv)
    try:
        case=load_case(ns.manifest)
        if ns.cmd=="digest": print(canonical_digest(case)); return 0
        result=assess(case,ns.choice)
        if ns.json: print(json.dumps(result.to_dict(),indent=2,sort_keys=True))
        else:
            print(f"decision={result.decision_id} choice={result.choice}")
            print(f"raw_votes={result.raw_votes} independent_groups={result.independent_groups} threshold={result.threshold}")
            print("QUORUM PASS" if result.quorum_met else "QUORUM FAIL")
            for i,g in enumerate(result.groups,1): print(f"  group {i}: {', '.join(g)}")
            for w in result.warnings: print(f"  warning: {w}")
        return 0 if result.quorum_met else 2
    except EchoQuorumError as e:
        print(f"echoquorum: {e}",file=sys.stderr); return 3
if __name__=="__main__": raise SystemExit(main())
