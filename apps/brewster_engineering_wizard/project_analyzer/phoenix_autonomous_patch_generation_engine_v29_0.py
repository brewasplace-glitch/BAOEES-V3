from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import datetime
from pathlib import Path

NAME="Phoenix Autonomous Patch Generation Engine"
VER="v29.0"

def root():
    p=Path.cwd().resolve()
    for x in [p,*p.parents]:
        if (x/".git").exists(): return x
    raise RuntimeError("PROJECT-PHOENIX root niet gevonden.")

ROOT=root()
CFG=ROOT/"configs/phoenix"
PROPOSALS=ROOT/"outputs/development/v28_0/development_proposals_v28_0.json"
PATCH_PLAN=ROOT/"outputs/development/v28_0/development_patch_plan_v28_0.json"
OUT=ROOT/"outputs/runtime/v29_0"
PATCHES=ROOT/"outputs/patches/v29_0"

class PatchEngine:
    def __init__(self):
        self.policy=self.read(CFG/"patch_generation_policy_v29_0.json")
        self.registry=self.read(CFG/"patch_template_registry_v29_0.json")

    def self_test(self):
        checks={
            "policy_exists":bool(self.policy),
            "registry_exists":bool(self.registry),
            "proposals_exist":PROPOSALS.exists(),
            "patch_plan_exists":PATCH_PLAN.exists(),
            "python_supported":sys.version_info>=(3,10)
        }
        return self.save(OUT/"patch_generation_self_test_v29_0.json",{
            "engine":NAME,"version":VER,"checks":checks,
            "status":"PASS" if all(checks.values()) else "FAIL"
        })

    def analyze(self):
        proposals=self.read(PROPOSALS).get("proposals",[])
        plans=self.read(PATCH_PLAN).get("patches",[])
        pids={x["proposal_id"] for x in proposals}
        qids={x["patch_id"] for x in plans}
        findings={
            "proposal_count":len(proposals),
            "patch_plan_count":len(plans),
            "matching_ids":sorted(pids&qids),
            "missing_patch_plans":sorted(pids-qids),
            "orphan_patch_plans":sorted(qids-pids)
        }
        status="PASS" if not findings["missing_patch_plans"] and not findings["orphan_patch_plans"] else "FAIL"
        return self.save(OUT/"patch_generation_analysis_v29_0.json",{
            "engine":NAME,"version":VER,"findings":findings,"status":status
        })

    def manifest(self):
        proposals=self.read(PROPOSALS).get("proposals",[])
        rows=[]
        for proposal in proposals:
            template=self.template_for(proposal["action"])
            row={
                "patch_id":proposal["proposal_id"],
                "target_id":proposal["target_id"],
                "action":proposal["action"],
                "target_path":proposal.get("path",""),
                "template_id":template["template_id"],
                "allowed_operations":template["allowed_operations"],
                "required_tests":template["required_tests"],
                "requires_go":True,
                "apply_mode":"DRY_RUN"
            }
            row["fingerprint"]=self.fingerprint(row)
            rows.append(row)
        return self.save(PATCHES/"patch_manifest_v29_0.json",{
            "engine":NAME,"version":VER,"manifests":rows,
            "automatic_application":False,"status":"PASS"
        })

    def test_matrix(self):
        manifest=self.manifest()
        rows=[]
        for item in manifest["manifests"]:
            for test_type in item["required_tests"]:
                rows.append({
                    "patch_id":item["patch_id"],
                    "target_id":item["target_id"],
                    "test_type":test_type,
                    "required":True,
                    "status":"PLANNED"
                })
        return self.save(PATCHES/"patch_test_matrix_v29_0.json",{
            "engine":NAME,"version":VER,"tests":rows,"status":"PASS"
        })

    def bundle_plan(self):
        manifest=self.manifest()
        tests=self.test_matrix()
        bundle={
            "bundle_id":"PROJECT-PHOENIX-v29.0-PATCH-BUNDLE",
            "patch_count":len(manifest["manifests"]),
            "test_count":len(tests["tests"]),
            "application_mode":"DRY_RUN",
            "requires_go_before_apply":True,
            "automatic_source_changes":False
        }
        bundle["fingerprint"]=self.fingerprint(bundle)
        return self.save(PATCHES/"patch_bundle_plan_v29_0.json",{
            "engine":NAME,"version":VER,"bundle":bundle,"status":"PASS"
        })

    def application_plan(self):
        manifest=self.manifest()
        steps=[]
        for i,item in enumerate(manifest["manifests"],1):
            steps.append({
                "sequence":i,
                "patch_id":item["patch_id"],
                "target_id":item["target_id"],
                "steps":[
                    "verify_clean_repository","create_backup","render_patch_in_temp",
                    "validate_expected_paths","run_syntax_tests","run_unit_tests",
                    "run_regression_tests","require_explicit_go","apply_patch",
                    "verify_working_tree"
                ],
                "status":"PLANNED",
                "automatic_apply":False
            })
        return self.save(PATCHES/"patch_application_plan_v29_0.json",{
            "engine":NAME,"version":VER,"steps":steps,
            "safe_to_apply_without_go":False,"status":"PASS"
        })

    def summary(self):
        a=self.analyze();m=self.manifest();t=self.test_matrix();b=self.bundle_plan();p=self.application_plan()
        return self.save(OUT/"patch_generation_summary_v29_0.json",{
            "engine":NAME,"version":VER,
            "analysis_status":a["status"],
            "patch_count":len(m["manifests"]),
            "test_count":len(t["tests"]),
            "bundle_fingerprint":b["bundle"]["fingerprint"],
            "application_step_count":len(p["steps"]),
            "automatic_source_changes":False,
            "safe_to_apply_without_go":False,
            "status":"PASS" if a["status"]=="PASS" else "FAIL"
        })

    def template_for(self,action):
        for template in self.registry["templates"]:
            if template["action"]==action:return template
        return self.registry["default_template"]

    def fingerprint(self,data):
        raw=json.dumps(data,sort_keys=True,ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def read(self,path):
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def save(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True)
        data["generated_at"]=datetime.now().isoformat(timespec="seconds")
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8-sig")
        data["output_path"]=str(path)
        return data

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("cmd",choices=["self-test","analyze","manifest","test-matrix","bundle-plan","application-plan","summary"])
    args=ap.parse_args()
    e=PatchEngine()
    fn={
        "self-test":e.self_test,
        "analyze":e.analyze,
        "manifest":e.manifest,
        "test-matrix":e.test_matrix,
        "bundle-plan":e.bundle_plan,
        "application-plan":e.application_plan,
        "summary":e.summary
    }[args.cmd]
    result=fn()
    print(json.dumps(result,ensure_ascii=True,indent=2))
    if result.get("status")!="PASS": raise SystemExit(1)

if __name__=="__main__":main()
