from __future__ import annotations
import hashlib, json
from pathlib import Path

class PhoenixReleaseFramework:
    VERSION="1.0.0"

    def fingerprint(self,manifest):
        raw=json.dumps(manifest.to_dict(),sort_keys=True,separators=(",",":")).encode()
        return hashlib.sha256(raw).hexdigest()

    def build_plan(self,repository,manifest):
        root=Path(repository)
        groups={"track":[],"ignore":[],"clean":[]}
        missing=[]
        for artifact in manifest.artifacts:
            groups[artifact.policy].append(artifact.path)
            if artifact.required and artifact.policy!="clean" and not (root/artifact.path).exists():
                missing.append(artifact.path)
        return {
            "release_id":manifest.id,
            "track":groups["track"],"ignore":groups["ignore"],"clean":groups["clean"],
            "missing_required":missing,"ready":not missing,
            "fingerprint_sha256":self.fingerprint(manifest),
        }

    def verify_hashes(self,repository,manifest):
        root=Path(repository); results=[]
        for artifact in manifest.artifacts:
            path=root/artifact.path
            if artifact.sha256 and path.is_file():
                actual=self.hash_file(path)
                results.append({"path":artifact.path,"expected":artifact.sha256.lower(),
                                "actual":actual,"matches":actual==artifact.sha256.lower()})
        return results

    def rollback_journal(self,manifest,base_commit,output):
        data={"schema_version":"phoenix.release-rollback/1.0",
              "release_id":manifest.id,"version":manifest.version,
              "base_commit":base_commit,
              "track":[a.path for a in manifest.artifacts if a.policy=="track"],
              "clean":[a.path for a in manifest.artifacts if a.policy=="clean"],
              "manifest_fingerprint_sha256":self.fingerprint(manifest)}
        path=Path(output); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return path

    @staticmethod
    def hash_file(path):
        h=hashlib.sha256()
        with Path(path).open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
        return h.hexdigest()
