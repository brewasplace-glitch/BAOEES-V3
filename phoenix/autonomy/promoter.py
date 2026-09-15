from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json, os, subprocess, tempfile, uuid

def _norm(path:str)->str:
    return path.replace("\\","/").lstrip("./")

@dataclass(frozen=True)
class LowRiskMainlinePromotionPolicy:
    enabled:bool
    mode:str
    main_branch:str
    candidate_branch_prefix:str
    max_commits_ahead:int
    allowed_status_codes:tuple[str,...]
    allowed_roots:tuple[str,...]
    allowed_extensions:tuple[str,...]
    max_files:int
    max_file_bytes:int
    max_total_bytes:int
    require_backup_receipt:bool
    require_bundle_verified:bool
    require_snapshot_verified:bool
    promotion_engine:str
    delete_candidate_after_success:bool
    allowed_governance_side_effect_paths:tuple[str,...]
    max_governance_files:int
    max_governance_file_bytes:int
    max_governance_total_bytes:int

    @classmethod
    def from_json(cls,path:Path):
        d=json.loads(Path(path).read_text(encoding="utf-8-sig"))
        return cls(
            bool(d["enabled"]),
            str(d["mode"]),
            str(d["main_branch"]),
            str(d["candidate_branch_prefix"]),
            int(d["max_commits_ahead"]),
            tuple(d["allowed_status_codes"]),
            tuple(d["allowed_roots"]),
            tuple(d["allowed_extensions"]),
            int(d["max_files"]),
            int(d["max_file_bytes"]),
            int(d["max_total_bytes"]),
            bool(d["require_backup_receipt"]),
            bool(d["require_bundle_verified"]),
            bool(d["require_snapshot_verified"]),
            str(d["promotion_engine"]),
            bool(d["delete_candidate_after_success"]),
            tuple(d.get("allowed_governance_side_effect_paths",())),
            int(d.get("max_governance_files",0)),
            int(d.get("max_governance_file_bytes",0)),
            int(d.get("max_governance_total_bytes",0)),
        )

class LowRiskMainlinePromoter:
    def __init__(self,repo_root:Path,policy:LowRiskMainlinePromotionPolicy,runtime_root:Path|None=None):
        self.repo_root=Path(repo_root).resolve()
        self.policy=policy
        local=Path(os.environ.get("LOCALAPPDATA",tempfile.gettempdir()))
        self.runtime_root=Path(
            runtime_root or (local/"PROJECT-PHOENIX"/"autonomy"/"mainline_promotion")
        )

    def git(self,*args:str,check=True)->str:
        cp=subprocess.run(
            ["git","-c","core.longpaths=true","-C",str(self.repo_root),*args],
            text=True,
            encoding="utf-8",
            errors="strict",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if check and cp.returncode:
            raise RuntimeError(f"git {' '.join(args)} failed: {cp.stdout.rstrip()}")
        return cp.stdout.rstrip("\r\n")

    def _receipt(self,path:Path,expected:str)->dict:
        if self.policy.require_backup_receipt and not Path(path).is_file():
            raise RuntimeError("verified backup receipt required")
        d=json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if d.get("status")!="PASS" or d.get("baseline")!=expected:
            raise RuntimeError("backup receipt invalid or baseline mismatch")
        if self.policy.require_bundle_verified and d.get("bundle_verified") is not True:
            raise RuntimeError("backup bundle verification missing")
        if self.policy.require_snapshot_verified and d.get("snapshot_verified") is not True:
            raise RuntimeError("backup snapshot verification missing")
        if not Path(str(d.get("bundle_path",""))).is_file():
            raise RuntimeError("backup bundle file missing")
        if not Path(str(d.get("snapshot_path",""))).is_dir():
            raise RuntimeError("backup snapshot directory missing")
        return d

    def _status(self):
        return tuple(
            x for x in
            self.git("status","--porcelain=v1","--untracked-files=all").splitlines()
            if x
        )

    def _worktree(self,branch):
        current={}
        blocks=[]
        for line in self.git("worktree","list","--porcelain").splitlines()+[""]:
            if not line:
                if current:
                    blocks.append(current)
                    current={}
                continue
            if line.startswith("worktree "):
                current["path"]=line[9:]
            elif line.startswith("branch refs/heads/"):
                current["branch"]=line[18:]
        for block in blocks:
            if block.get("branch")==branch and block.get("path"):
                return Path(block["path"])
        return None

    def _validate_jsonl(self,text:str,rel:str)->None:
        for line_number,line in enumerate(text.splitlines(),1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"invalid governance JSONL {rel} line {line_number}: {exc}"
                ) from exc

    def _paths(self,expected,candidate):
        lines=self.git("diff","--name-status",f"{expected}..{candidate}").splitlines()
        if not lines:
            raise RuntimeError("candidate has no changed paths")

        allowed_status=set(self.policy.allowed_status_codes)
        allowed_ext={x.lower() for x in self.policy.allowed_extensions}
        governance_allow={
            _norm(x).lower() for x in self.policy.allowed_governance_side_effect_paths
        }

        primary=[]
        governance=[]
        primary_total=0
        governance_total=0
        all_paths=[]

        for line in lines:
            parts=line.split("\t")
            if len(parts)<2:
                raise RuntimeError(f"invalid diff status: {line}")

            status=parts[0]
            if status not in allowed_status:
                raise RuntimeError(f"candidate status {status} not allowed")

            rel=_norm(parts[-1])
            low=rel.lower()
            size=int(self.git("cat-file","-s",f"{candidate}:{rel}"))

            if low in governance_allow:
                governance.append(rel)
                governance_total+=size
                if len(governance)>self.policy.max_governance_files:
                    raise RuntimeError("too many governance side-effect files")
                if size>self.policy.max_governance_file_bytes:
                    raise RuntimeError(f"governance side-effect file too large: {rel}")
                if governance_total>self.policy.max_governance_total_bytes:
                    raise RuntimeError("governance side-effect payload too large")

                suffix=Path(rel).suffix.lower()
                content=None
                if suffix in {".json",".jsonl"}:
                    content=self.git("show",f"{candidate}:{rel}")
                if suffix==".json":
                    json.loads(content)
                elif suffix==".jsonl":
                    self._validate_jsonl(content,rel)
            else:
                if not any(
                    low.startswith(_norm(root).lower())
                    for root in self.policy.allowed_roots
                ):
                    raise RuntimeError(
                        f"candidate path outside LOW-risk roots/governance allowlist: {rel}"
                    )
                if Path(rel).suffix.lower() not in allowed_ext:
                    raise RuntimeError(f"candidate extension not allowed: {rel}")

                primary.append(rel)
                primary_total+=size

                if len(primary)>self.policy.max_files:
                    raise RuntimeError("candidate primary file count invalid")
                if size>self.policy.max_file_bytes:
                    raise RuntimeError(f"candidate primary file too large: {rel}")
                if primary_total>self.policy.max_total_bytes:
                    raise RuntimeError("candidate primary payload too large")

                if Path(rel).suffix.lower()==".json":
                    json.loads(self.git("show",f"{candidate}:{rel}"))

            all_paths.append(rel)

        if not primary:
            raise RuntimeError("candidate contains no primary LOW-risk mutation")

        self.git("diff","--check",f"{expected}..{candidate}","--",*all_paths)
        return tuple(primary),tuple(governance)

    def promote(self,candidate_branch:str,expected_head:str,backup_receipt:Path)->dict:
        eid="PROMOTE-"+uuid.uuid4().hex[:12].upper()
        report_dir=self.runtime_root/eid
        report_dir.mkdir(parents=True,exist_ok=True)

        if (
            not self.policy.enabled
            or self.policy.mode!="backup_gated_fast_forward_only"
            or self.policy.promotion_engine!="git_merge_ff_only"
        ):
            raise RuntimeError("promotion policy disabled or invalid")

        if not candidate_branch.startswith(self.policy.candidate_branch_prefix):
            raise RuntimeError("candidate prefix not allowed")
        if self.git("branch","--show-current").strip()!=self.policy.main_branch:
            raise RuntimeError("main branch mismatch")
        if self._status():
            raise RuntimeError("main worktree must be clean")

        self.git("fetch","origin",self.policy.main_branch)
        head=self.git("rev-parse","HEAD").strip()
        origin=self.git("rev-parse",f"origin/{self.policy.main_branch}").strip()
        if head!=expected_head or origin!=expected_head:
            raise RuntimeError("main/origin baseline mismatch")

        receipt=self._receipt(Path(backup_receipt),expected_head)

        candidate=self.git("rev-parse",candidate_branch).strip()
        parent=self.git("rev-parse",f"{candidate_branch}^").strip()
        ahead=int(self.git("rev-list","--count",f"{expected_head}..{candidate_branch}"))

        if (
            ahead!=1
            or ahead>self.policy.max_commits_ahead
            or parent!=expected_head
        ):
            raise RuntimeError("candidate must be exactly one direct commit ahead")

        if self.git("merge-base",expected_head,candidate_branch).strip()!=expected_head:
            raise RuntimeError("candidate cannot fast-forward")

        subject=self.git("show","-s","--format=%s",candidate_branch).strip()
        if not subject.startswith("chore(autonomy): low-risk candidate LOW-"):
            raise RuntimeError("candidate provenance marker missing")

        primary_paths,governance_paths=self._paths(expected_head,candidate_branch)

        self.git("fetch","origin",self.policy.main_branch)
        if self.git("rev-parse",f"origin/{self.policy.main_branch}").strip()!=expected_head:
            raise RuntimeError("REMOTE_RACE_GUARD: origin changed")
        if self._status():
            raise RuntimeError("main became dirty")

        self.git("merge","--ff-only",candidate_branch)

        promoted=self.git("rev-parse","HEAD").strip()
        if promoted!=candidate or self._status():
            raise RuntimeError("fast-forward verification failed")

        self.git("push","origin",self.policy.main_branch)
        self.git("fetch","origin",self.policy.main_branch)
        if self.git("rev-parse",f"origin/{self.policy.main_branch}").strip()!=candidate:
            raise RuntimeError("remote verification failed")

        cleaned=False
        worktree=self._worktree(candidate_branch)
        if self.policy.delete_candidate_after_success:
            if worktree is not None:
                self.git("worktree","remove","--force",str(worktree))
            self.git("branch","-d",candidate_branch)
            cleaned=True

        result={
            "schema":"PHOENIX_LOW_RISK_MAINLINE_PROMOTION_REPORT_V1",
            "status":"PASS",
            "execution_id":eid,
            "baseline":expected_head,
            "promoted_commit":candidate,
            "candidate_branch":candidate_branch,
            "main_branch":self.policy.main_branch,
            "paths":list(primary_paths),
            "governance_side_effect_paths":list(governance_paths),
            "governance_side_effects_validated":True,
            "backup_receipt":str(backup_receipt),
            "backup_bundle_sha256":receipt.get("bundle_sha256"),
            "promotion_engine":"git merge --ff-only",
            "push_mode":"normal_non_force",
            "mainline_promoted":True,
            "candidate_cleaned":cleaned,
            "medium_high_critical":"BLOCKED",
        }
        (report_dir/"promotion_report.json").write_text(
            json.dumps(result,indent=2,ensure_ascii=False),
            encoding="utf-8",newline="\n"
        )
        return result
