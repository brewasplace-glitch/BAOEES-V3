from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from phoenix.autonomy.project_stability_design_basis_input_evidence_qualification_r9_5_1 import build_project_stability_design_basis_input_evidence_qualification
CHECKS=["ALTERNATE_LOAD_PATH_EVIDENCE","DIAPHRAGM_CONTINUITY","GLOBAL_BUCKLING_FACTOR","LOAD_PATH_CONTINUITY","SECOND_ORDER_AMPLIFICATION","SOFT_STOREY_STIFFNESS_RATIO","STOREY_STABILITY_INDEX","TORSIONAL_DRIFT_RATIO","WEAK_STOREY_STRENGTH_RATIO"]

def base_template():
    criteria={"ALTERNATE_LOAD_PATH_EVIDENCE":{"minimum_residual_capacity_proxy_ratio":None},"DIAPHRAGM_CONTINUITY":{},"GLOBAL_BUCKLING_FACTOR":{"minimum_critical_load_factor":None},"LOAD_PATH_CONTINUITY":{},"SECOND_ORDER_AMPLIFICATION":{"max_amplification_factor":None},"SOFT_STOREY_STIFFNESS_RATIO":{"minimum_ratio":None},"STOREY_STABILITY_INDEX":{"max_stability_index":None},"TORSIONAL_DRIFT_RATIO":{"max_torsional_drift_ratio":None},"WEAK_STOREY_STRENGTH_RATIO":{"minimum_ratio":None}}
    checks={c:{"applicability":None,"methodology_accepted":False,"methodology_acceptance_reference":None,"primary_source_record_id":None,"supporting_source_record_ids":[],"acceptance_criteria":criteria[c],"criteria_traceability":{},"evidence_reference":f"R9.3:{c}"} for c in CHECKS}
    return {"schema_version":"phoenix.r9-5-project-stability-design-basis-required-input/1.0","r9_5_project_stability_design_basis_decision":{"decision_id":"P-STABILITY-DESIGN-BASIS-DECISION","jurisdictional_basis":{"project_jurisdiction":"Suriname / Paramaribo","engineering_design_methodology":"Eurocode 2 based","current_2026_surinaame_legal_status":"NOT_EXTERNALLY_VERIFIED","eurocode_2_legal_adoption":"NOT_ESTABLISHED_BY_UPLOADED_PRIMARY_SOURCES"},"seismic_applicability":{"status":None,"reference_type":None,"reference":None,"source_record_id":None,"professional_scope_reviewed":False,"scope_review_reference":None},"source_records":{"EXAMPLE_PROJECT_POLICY_RECORD":{"reference_type":"PROJECT_ENGINEERING_POLICY","reference":None}},"checks":checks}}

def blocked_r95():
    reg={}
    for c in CHECKS:
        m=["explicit_applicability_decision","methodology_accepted","primary_source_record_id"]
        support=[]
        if c=="GLOBAL_BUCKLING_FACTOR":
            m.append("minimum_critical_load_factor"); support=[{"status":"AVAILABLE","source_id":"SR-SUR-BB1-1956-001","rule_id":"SUR-BB1-A27-BUCKLING","source_pointer":"Bouwbesluit no. 1, Article 27","support_scope":"CHECK_APPLICABILITY_ONLY","exact_v8_6_acceptance_limit_available":False}]
        if c in {"SOFT_STOREY_STIFFNESS_RATIO","TORSIONAL_DRIFT_RATIO","WEAK_STOREY_STRENGTH_RATIO"}: m.append("explicit_seismic_applicability_decision")
        if c=="WEAK_STOREY_STRENGTH_RATIO": m += ["explicit_candidate_screening_proxy_acceptance","screening_proxy_review_reference","minimum_ratio"]
        if c=="ALTERNATE_LOAD_PATH_EVIDENCE": m += ["independent_engineering_evidence_reference","independent_review_reference","independent_review_status_REVIEWED","independently_verified_alternate_path","minimum_residual_capacity_proxy_ratio"]
        reg[c]={"state":"DECISION_OR_SOURCE_INPUT_REQUIRED","missing_requirements":m,"available_surinaame_primary_support":support,"decision_snapshot":{}}
    return {"status":"BLOCKED","summary":{"r9_3_technical_evidence_count":9},"decision_register":reg,"required_input_template":base_template(),"source_states":{}}

class T(unittest.TestCase):
    def setUp(self): self.policy=ROOT/'configs/phoenix/structural/project_stability_design_basis_input_evidence_qualification_policy_r9_5_1.json'
    def runx(self,r=None): return build_project_stability_design_basis_input_evidence_qualification(project_id='P',r95_result=r or blocked_r95(),policy_path=self.policy)
    def test_01(self): self.assertEqual(self.runx()['status'],'BLOCKED')
    def test_02(self): self.assertEqual(self.runx()['summary']['technical_analysis_required_count'],0)
    def test_03(self): self.assertIsNotNone(self.runx()['prefilled_project_input'])
    def test_04(self): self.assertEqual(len(self.runx()['evidence_requirement_matrix']),9)
    def test_05(self): self.assertEqual(self.runx()['summary']['consolidated_input_package_count'],5)
    def test_06(self):
        r=self.runx(); rec=r['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['source_records']; self.assertFalse(any(k.startswith('EXAMPLE_') for k in rec))
    def test_07(self):
        rec=self.runx()['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['source_records']; self.assertIn('SURINAME_BOUWBESLUIT_A26_STRENGTH',rec)
    def test_08(self):
        rec=self.runx()['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['source_records']; self.assertEqual(rec['SURINAME_BOUWBESLUIT_A27_BUCKLING']['source_pointer'],'Bouwbesluit no. 1, Article 27')
    def test_09(self):
        c=self.runx()['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['checks']['GLOBAL_BUCKLING_FACTOR']; self.assertIn('SURINAME_BOUWBESLUIT_A27_BUCKLING',c['supporting_source_record_ids'])
    def test_10(self):
        c=self.runx()['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['checks']['GLOBAL_BUCKLING_FACTOR']; self.assertIsNone(c['acceptance_criteria']['minimum_critical_load_factor'])
    def test_11(self):
        s=self.runx()['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['seismic_applicability']; self.assertIsNone(s['status'])
    def test_12(self):
        rec=self.runx()['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['source_records']; self.assertFalse(rec['PROJECT_STABILITY_POLICY_REQUIRED']['project_policy_approved'])
    def test_13(self):
        rec=self.runx()['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['source_records']; self.assertFalse(rec['LICENSED_STABILITY_SOURCE_REQUIRED']['licensed_use_confirmed'])
    def test_14(self): self.assertFalse(self.runx()['safety']['background_ai_source_as_normative_input'])
    def test_15(self): self.assertFalse(self.runx()['safety']['automatic_seismic_applicability_decision'])
    def test_16(self): self.assertFalse(self.runx()['safety']['automatic_project_policy_approval'])
    def test_17(self): self.assertFalse(self.runx()['safety']['not_applicable_auto_waives_v8_6'])
    def test_18(self): self.assertEqual(self.runx()['safety']['production_release'],'LOCKED')
    def test_19(self):
        r=blocked_r95(); r['decision_register']['DIAPHRAGM_CONTINUITY']['decision_snapshot']={'applicability':'APPLICABLE','methodology_accepted':True}; o=self.runx(r); c=o['prefilled_project_input']['r9_5_project_stability_design_basis_decision']['checks']['DIAPHRAGM_CONTINUITY']; self.assertTrue(c['methodology_accepted'])
    def test_20(self): self.assertEqual(self.runx({'status':'PASSED'})['status'],'PASSED')
    def test_21(self):
        r=blocked_r95(); r['required_input_template']={}; self.assertEqual(self.runx(r)['blockers'][0]['reason'],'R9_5_1_REQUIRED_TEMPLATE_MISSING')
if __name__=='__main__': unittest.main()
