from pathlib import Path
import argparse, hashlib, json, math

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(outdir):
    import openseespy
    import openseespy.opensees as ops

    outdir=outdir.resolve()
    outdir.mkdir(parents=True,exist_ok=True)
    inp=outdir/"opensees_truss_input.json"
    res=outdir/"opensees_truss_results.json"
    contract={
        "nodes":{"1":[0,0],"2":[4,0],"3":[2,3]},
        "elements":{"1":[1,3],"2":[2,3]},
        "E":210000.0,"A":1000.0,"load":[0.0,-100000.0]
    }
    inp.write_text(json.dumps(contract,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    ops.wipe()
    ops.model("basic","-ndm",2,"-ndf",2)
    ops.node(1,0.0,0.0);ops.node(2,4.0,0.0);ops.node(3,2.0,3.0)
    ops.fix(1,1,1);ops.fix(2,1,1)
    ops.uniaxialMaterial("Elastic",1,210000.0)
    ops.element("truss",1,1,3,1000.0,1)
    ops.element("truss",2,2,3,1000.0,1)
    ops.timeSeries("Linear",1);ops.pattern("Plain",1,1)
    ops.load(3,0.0,-100000.0)
    ops.system("BandGeneral");ops.numberer("RCM");ops.constraints("Plain")
    ops.integrator("LoadControl",1.0);ops.algorithm("Linear");ops.analysis("Static")
    code=int(ops.analyze(1))
    if code!=0:
        raise RuntimeError(f"OpenSees analysis failed with code {code}")
    ops.reactions()
    disp=[float(x) for x in ops.nodeDisp(3)]
    r1=[float(x) for x in ops.nodeReaction(1)]
    r2=[float(x) for x in ops.nodeReaction(2)]
    if not disp[1] < 0:
        raise RuntimeError(f"Expected downward displacement, received {disp}")
    vr=r1[1]+r2[1]
    if not math.isclose(vr,100000.0,rel_tol=1e-8,abs_tol=1e-4):
        raise RuntimeError(f"Support reactions do not balance load: {vr}")
    result={"node_3_displacement":disp,"node_1_reaction":r1,
            "node_2_reaction":r2,"vertical_reaction_sum":vr}
    res.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    evidence={
        "schema_version":"phoenix.opensees-acceptance/5.5.0",
        "status":"ACCEPTED","engine_id":"opensees",
        "version":str(ops.version()),
        "package_version":str(getattr(openseespy,"__version__","")),
        "analysis":"linear_static_2d_truss","analysis_code":code,
        "acceptance_basis":"REAL_OPENSEES_LINEAR_STATIC_ARTIFACT",
        "results":result,
        "artifacts":[
            {"path":inp.name,"size_bytes":inp.stat().st_size,"sha256":sha(inp)},
            {"path":res.name,"size_bytes":res.stat().st_size,"sha256":sha(res)}
        ],
        "simulated":False,
        "professional_review_required":True
    }
    (outdir/"opensees_engine_acceptance.json").write_text(
        json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8"
    )
    ops.wipe()
    return evidence

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
    print(json.dumps(run(Path(a.output)),indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
