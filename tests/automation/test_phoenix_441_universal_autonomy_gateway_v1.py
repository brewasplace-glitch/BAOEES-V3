import dataclasses, json, tempfile, time, unittest
from pathlib import Path

from phoenix.autonomy import (
    GatewayAuditLog,
    MutationIntent,
    PolicyDecisionLog,
    UniversalAutonomyGateway,
)

ROOT=Path(__file__).resolve().parents[2]

def gateway(td=None):
    decision_log=None
    audit=None
    if td is not None:
        decision_log=PolicyDecisionLog(Path(td)/"decision.jsonl")
        audit=GatewayAuditLog(Path(td)/"gateway.jsonl")
    return UniversalAutonomyGateway.from_repo(ROOT,decision_log=decision_log,audit_log=audit)

def low_intent(path="docs/automation/autonomous_generated/x.md"):
    return MutationIntent(
        engine_id="autonomy.low_risk_executor",
        action="documentation.update",
        risk="LOW",
        domain="documentation",
        paths=(path,),
        gates=("clean_synced","verified_backup","open_source_review","risk_low","allowlisted_path","audit_log"),
    )

class TestUniversalGateway(unittest.TestCase):
    def test_contract_active_and_fail_closed(self):
        g=gateway()
        self.assertTrue(g.gateway_policy["enabled"])
        self.assertTrue(g.gateway_policy["fail_closed"])
        self.assertEqual(g.gateway_policy["future_engine_default"],"DENY_UNREGISTERED")

    def test_north_star_covers_all_current_and_future_engines(self):
        m=gateway().decision_engine.north_star["machine_contract"]
        self.assertTrue(m["universal_gateway_required_for_all_current_and_future_engines"])
        self.assertEqual(m["future_engine_default_if_unregistered"],"DENY")
        self.assertTrue(m["mutation_permit_required"])

    def test_unregistered_future_engine_denied(self):
        g=gateway()
        with self.assertRaises(PermissionError):
            g.authorize(MutationIntent(
                engine_id="future.engine.never.seen",
                action="documentation.update",
                risk="LOW",
                domain="documentation",
                paths=("docs/automation/autonomous_generated/future.md",),
                gates=("clean_synced","verified_backup","open_source_review","risk_low","allowlisted_path","audit_log"),
            ))

    def test_registered_executor_gets_bound_permit(self):
        g=gateway()
        p=g.authorize(low_intent())
        self.assertEqual(p.engine_id,"autonomy.low_risk_executor")
        self.assertEqual(p.action,"documentation.update")
        self.assertEqual(p.paths,("docs/automation/autonomous_generated/x.md",))
        self.assertEqual(p.policy_bundle_sha256,g.decision_engine.bundle_sha256)

    def test_permit_consumes_once(self):
        g=gateway()
        p=g.authorize(low_intent())
        g.consume(p,engine_id=p.engine_id,action=p.action,paths=p.paths)
        with self.assertRaises(PermissionError):
            g.consume(p,engine_id=p.engine_id,action=p.action,paths=p.paths)

    def test_permit_wrong_engine_denied(self):
        g=gateway()
        p=g.authorize(low_intent())
        with self.assertRaises(PermissionError):
            g.consume(p,engine_id="autonomy.mainline_promoter",action=p.action,paths=p.paths)

    def test_permit_wrong_action_denied(self):
        g=gateway()
        p=g.authorize(low_intent())
        with self.assertRaises(PermissionError):
            g.consume(p,engine_id=p.engine_id,action="evidence.generate",paths=p.paths)

    def test_permit_wrong_path_denied(self):
        g=gateway()
        p=g.authorize(low_intent())
        with self.assertRaises(PermissionError):
            g.consume(
                p,
                engine_id=p.engine_id,
                action=p.action,
                paths=("docs/automation/autonomous_generated/other.md",),
            )

    def test_tampered_fingerprint_denied(self):
        g=gateway()
        p=g.authorize(low_intent())
        bad=dataclasses.replace(p,fingerprint="0"*64)
        with self.assertRaises(PermissionError):
            g.consume(bad,engine_id=bad.engine_id,action=bad.action,paths=bad.paths)

    def test_foreign_gateway_permit_denied(self):
        g1=gateway()
        g2=gateway()
        p=g1.authorize(low_intent())
        with self.assertRaises(PermissionError):
            g2.consume(p,engine_id=p.engine_id,action=p.action,paths=p.paths)

    def test_executor_registry_path_escape_denied(self):
        g=gateway()
        with self.assertRaises(PermissionError):
            g.authorize(low_intent("phoenix/unsafe.py"))

    def test_executor_registry_action_escape_denied(self):
        g=gateway()
        with self.assertRaises(PermissionError):
            g.authorize(MutationIntent(
                engine_id="autonomy.low_risk_executor",
                action="source.modify",
                risk="LOW",
                domain="software",
                paths=("docs/automation/autonomous_generated/x.md",),
                gates=(),
            ))

    def test_engine_registry_all_mutators_require_gateway(self):
        g=gateway()
        for e in g.engine_registry["engines"]:
            if e.get("mutation_capable"):
                self.assertTrue(e.get("gateway_required"))
                self.assertTrue(e.get("allowed_actions"))
                self.assertTrue(e.get("allowed_domains"))

    def test_future_engine_manifest_without_gateway_denied(self):
        g=gateway()
        with self.assertRaises(PermissionError):
            g.assert_future_engine_admission({
                "engine_id":"future.example",
                "mutation_capable":True,
                "gateway_required":False,
                "allowed_actions":["documentation.update"],
                "allowed_domains":["documentation"],
                "allowed_path_roots":["docs/automation/autonomous_generated/"],
            })

    def test_future_engine_manifest_not_registered_denied(self):
        g=gateway()
        with self.assertRaises(PermissionError):
            g.assert_future_engine_admission({
                "engine_id":"future.example",
                "mutation_capable":True,
                "gateway_required":True,
                "allowed_actions":["documentation.update"],
                "allowed_domains":["documentation"],
                "allowed_path_roots":["docs/automation/autonomous_generated/"],
            })

    def test_policy_bundle_covers_registry_and_gateway_policy(self):
        files=gateway().decision_engine.bundle_manifest["files"]
        self.assertIn("engine_registry_v1.json",files)
        self.assertIn("universal_gateway_policy_v1.json",files)
        self.assertIn("future_engine_admission_contract_v1.json",files)
        self.assertTrue(all(v.get("required") for v in files.values()))

    def test_gateway_audit_issue_and_consume(self):
        with tempfile.TemporaryDirectory() as td:
            g=gateway(td)
            p=g.authorize(low_intent())
            g.consume(p,engine_id=p.engine_id,action=p.action,paths=p.paths)
            rows=(Path(td)/"gateway.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows),2)
            self.assertEqual(json.loads(rows[0])["event_type"],"PERMIT_ISSUED")
            self.assertEqual(json.loads(rows[1])["event_type"],"PERMIT_CONSUMED")

    def test_decision_log_records_engine_actor(self):
        with tempfile.TemporaryDirectory() as td:
            g=gateway(td)
            g.authorize(low_intent())
            row=json.loads((Path(td)/"decision.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["request"]["actor"],"autonomy.low_risk_executor")

    def test_gateway_schemas_are_draft_2020_12(self):
        cfg=ROOT/"configs/phoenix"
        for name in ("universal_gateway_policy_v1.schema.json","engine_registry_v1.schema.json"):
            d=json.loads((cfg/name).read_text(encoding="utf-8"))
            self.assertEqual(d["$schema"],"https://json-schema.org/draft/2020-12/schema")

if __name__=="__main__":
    unittest.main()
