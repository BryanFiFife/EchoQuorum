import json, tempfile, unittest
from pathlib import Path
from echoquorum.core import EchoQuorumError, assess, canonical_digest, pair_correlation
from echoquorum.cli import main

def vote(i,choice="approve",model=None,provider=None,prompt=None,evidence=None,tools=None):
    return {"agent_id":i,"choice":choice,"model_family":model or f"model-{i}","provider":provider or f"provider-{i}","prompt_hash":prompt or f"p-{i}","evidence":evidence or [f"src-{i}"],"tools":tools or [f"tool-{i}"]}

def case(votes,threshold=3,cutoff=.7):
    return {"decision_id":"d1","threshold":threshold,"correlation_cutoff":cutoff,"votes":votes}

class Tests(unittest.TestCase):
    def test_independent_pass(self): self.assertTrue(assess(case([vote("a"),vote("b"),vote("c")])).quorum_met)
    def test_correlated_collapse(self):
        vs=[vote(x,model="same",provider="same",prompt="same",evidence=["same"],tools=["same"]) for x in "abc"]
        r=assess(case(vs)); self.assertFalse(r.quorum_met); self.assertEqual(r.independent_groups,1)
    def test_two_groups(self):
        a=vote("a",model="m",provider="p",prompt="x",evidence=["e"]); b=vote("b",model="m",provider="p",prompt="x",evidence=["e"]); c=vote("c")
        r=assess(case([a,b,c],threshold=2)); self.assertTrue(r.quorum_met); self.assertEqual(r.independent_groups,2)
    def test_choices_counted_separately(self):
        r=assess(case([vote("a","yes"),vote("b","no"),vote("c","no")],threshold=2),"no"); self.assertTrue(r.quorum_met)
    def test_default_choice_tiebreak(self):
        r=assess(case([vote("a","z"),vote("b","a")],threshold=1)); self.assertEqual(r.choice,"a")
    def test_duplicate_agent(self):
        with self.assertRaises(EchoQuorumError): assess(case([vote("a"),vote("a")],1))
    def test_bad_threshold(self):
        with self.assertRaises(EchoQuorumError): assess(case([vote("a")],0))
    def test_bad_cutoff(self):
        with self.assertRaises(EchoQuorumError): assess(case([vote("a")],1,1.1))
    def test_bad_evidence_type(self):
        v=vote("a"); v["evidence"]="x"
        with self.assertRaises(EchoQuorumError): assess(case([v],1))
    def test_unknown_lineage_correlates(self):
        a={"agent_id":"a","choice":"yes","evidence":[],"tools":[]}; b={"agent_id":"b","choice":"yes","evidence":[],"tools":[]}
        r=assess(case([a,b],2)); self.assertFalse(r.quorum_met); self.assertEqual(r.independent_groups,1)
    def test_one_unknown_warns(self):
        a={"agent_id":"a","choice":"yes","evidence":[],"tools":[]}; b=vote("b","yes")
        r=assess(case([a,b],1)); self.assertTrue(r.warnings)
    def test_pair_correlation_exact(self):
        a={"model_family":"m","provider":"p","prompt_hash":"h","evidence":frozenset(["e"]),"tools":frozenset(["t"])}
        s,reasons=pair_correlation(a,a); self.assertAlmostEqual(s,1.0); self.assertGreaterEqual(len(reasons),5)
    def test_evidence_partial(self):
        a={"model_family":"a","provider":"a","prompt_hash":"a","evidence":frozenset(["1","2"]),"tools":frozenset()}
        b={"model_family":"b","provider":"b","prompt_hash":"b","evidence":frozenset(["2","3"]),"tools":frozenset()}
        s,_=pair_correlation(a,b); self.assertAlmostEqual(s,0.35/3)
    def test_digest_stable_key_order(self):
        c=case([vote("a")],1); d1=canonical_digest(c); c2=json.loads(json.dumps(c,sort_keys=True)); self.assertEqual(d1,canonical_digest(c2))
    def test_digest_changes(self):
        c=case([vote("a")],1); d=canonical_digest(c); c["votes"][0]["choice"]="no"; self.assertNotEqual(d,canonical_digest(c))
    def test_groups_deterministic(self):
        vs=[vote(x,model="m",provider="p",prompt="h",evidence=["e"],tools=["t"]) for x in ["c","a","b"]]
        self.assertEqual(assess(case(vs,1)).groups,(("a","b","c"),))
    def test_cli_pass_and_fail(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.json"; p.write_text(json.dumps(case([vote("a")],1)))
            self.assertEqual(main(["assess",str(p)]),0); self.assertEqual(main(["assess",str(p),"--choice","missing"]),2)
    def test_cli_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.json"; p.write_text("not json"); self.assertEqual(main(["assess",str(p)]),3)
    def test_boolean_threshold_rejected(self):
        c=case([vote("a")],1); c["threshold"]=True
        with self.assertRaises(EchoQuorumError): assess(c)
    def test_no_votes_rejected(self):
        with self.assertRaises(EchoQuorumError): assess({"decision_id":"x","threshold":1,"votes":[]})

if __name__=='__main__': unittest.main()
