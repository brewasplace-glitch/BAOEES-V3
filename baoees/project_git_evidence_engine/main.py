import json
import subprocess
from datetime import datetime
from pathlib import Path


class ProjectGitEvidenceEngine:

    def __init__(self):
        self.git_evidence_result = {}

    def create_git_evidence(
        self,
        project_result=None,
        storage_result=None,
        audit_result=None,
        checksum_result=None,
        repo_root="."
    ):
        project_result = project_result or {}
        storage_result = storage_result or {}
        audit_result = audit_result or {}
        checksum_result = checksum_result or {}

        repo_root = Path(repo_root)

        folder_structure = storage_result.get("folder_structure", {})
        project_output_dir = Path(
            storage_result.get(
                "project_output_dir",
                "outputs/projects/unknown_project"
            )
        )

        runtime_logs_dir = Path(
            folder_structure.get(
                "runtime_logs",
                project_output_dir / "08_runtime_logs"
            )
        )

        runtime_logs_dir.mkdir(parents=True, exist_ok=True)

        project_id = storage_result.get("project_id", "unknown_project")
        project_name = project_result.get("project_name", "Onbekend project")

        git_evidence_file = runtime_logs_dir / f"{project_id}_git_evidence.json"

        git_data = self.collect_git_data(repo_root=repo_root)

        evidence_data = {
            "engine": "ProjectGitEvidenceEngine",
            "version": "1.0",
            "status": "PROJECT_GIT_EVIDENCE_OPGESLAGEN",
            "calculation_level": "Git versie- en codebewijs per projectrun",
            "project_id": project_id,
            "project_name": project_name,
            "project_output_dir": str(project_output_dir),
            "baoees_version": "BAOEES V3.x",
            "software_name": "BREWSTER-ENGINEERING-WIZARD",
            "repo_root": str(repo_root.resolve()),
            "git": git_data,
            "audit_status": audit_result.get("status", "ONBEKEND"),
            "checksum_status": checksum_result.get("status", "ONBEKEND"),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze Project Version / Git Evidence Engine v1.0 legt de Git-branch, "
                "commit hash, remote URL en werkmapstatus vast. Hiermee kan later worden "
                "aangetoond met welke codeversie projectoutput is gegenereerd."
            )
        }

        git_evidence_file_result = self.write_json_file(
            file_path=git_evidence_file,
            data=evidence_data
        )

        self.git_evidence_result = {
            "engine": "ProjectGitEvidenceEngine",
            "version": "1.0",
            "status": "PROJECT_GIT_EVIDENCE_OPGESLAGEN",
            "calculation_level": "project version / Git evidence export",
            "project_id": project_id,
            "project_name": project_name,
            "runtime_logs_dir": str(runtime_logs_dir),
            "git_evidence_file": git_evidence_file_result,
            "git_branch": git_data.get("branch", "ONBEKEND"),
            "git_commit_hash": git_data.get("commit_hash", "ONBEKEND"),
            "git_commit_short_hash": git_data.get("commit_short_hash", "ONBEKEND"),
            "git_is_clean": git_data.get("is_clean", False),
            "git_status_text": git_data.get("status_text", ""),
            "warnings": self.build_warnings(git_evidence_file_result, git_data),
            "recommendation": self.build_recommendation(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "disclaimer": (
                "Deze engine maakt een eerste Git evidence bestand. Latere versies kunnen "
                "automatisch GitHub release tags, semantic versioning, buildnummer, gebruikersnaam "
                "en digitale ondertekening toevoegen."
            )
        }

        return self.git_evidence_result

    def collect_git_data(self, repo_root):
        return {
            "branch": self.run_git_command(["git", "branch", "--show-current"], repo_root),
            "commit_hash": self.run_git_command(["git", "rev-parse", "HEAD"], repo_root),
            "commit_short_hash": self.run_git_command(["git", "rev-parse", "--short", "HEAD"], repo_root),
            "commit_date": self.run_git_command(["git", "log", "-1", "--format=%cI"], repo_root),
            "commit_subject": self.run_git_command(["git", "log", "-1", "--format=%s"], repo_root),
            "remote_origin_url": self.run_git_command(["git", "config", "--get", "remote.origin.url"], repo_root),
            "status_text": self.run_git_command(["git", "status", "--short"], repo_root),
            "status_full": self.run_git_command(["git", "status"], repo_root),
            "is_clean": self.is_working_tree_clean(repo_root),
            "evidence_timestamp": datetime.now().isoformat(timespec="seconds")
        }

    def run_git_command(self, command, repo_root):
        try:
            completed = subprocess.run(
                command,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False
            )

            output = completed.stdout.strip()
            error = completed.stderr.strip()

            if completed.returncode != 0:
                if error:
                    return f"FOUT: {error}"
                return "FOUT: Git command mislukt"

            return output

        except Exception as error:
            return f"FOUT: {error}"

    def is_working_tree_clean(self, repo_root):
        status_text = self.run_git_command(
            ["git", "status", "--short"],
            repo_root
        )

        if str(status_text).startswith("FOUT:"):
            return False

        return status_text.strip() == ""

    def write_json_file(self, file_path, data):
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2, ensure_ascii=False)

            return {
                "path": str(file_path),
                "status": "OPGESLAGEN",
                "exists": file_path.exists(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }

        except Exception as error:
            return {
                "path": str(file_path),
                "status": "FOUT",
                "exists": False,
                "size_bytes": 0,
                "error": str(error)
            }

    def build_warnings(self, git_evidence_file_result, git_data):
        warnings = []

        if git_evidence_file_result.get("status") != "OPGESLAGEN":
            warnings.append("Git evidence bestand is niet opgeslagen.")

        if str(git_data.get("commit_hash", "")).startswith("FOUT:"):
            warnings.append("Git commit hash kon niet worden bepaald.")

        if str(git_data.get("branch", "")).startswith("FOUT:"):
            warnings.append("Git branch kon niet worden bepaald.")

        if not git_data.get("is_clean", False):
            warnings.append(
                "Git working tree was niet schoon op het moment van evidence-generatie."
            )

        if not warnings:
            warnings.append("Geen kritieke Git evidence-waarschuwingen.")

        return warnings

    def build_recommendation(self):
        return {
            "status": "PROJECT_GIT_EVIDENCE_ADVIES",
            "advice": (
                "Gebruik deze engine als codeversie-bewijslaag. De volgende stap is koppeling "
                "aan audit trail, checksum manifest, HTML-dashboard en finale ZIP."
            ),
            "next_steps": [
                "ProjectGitEvidenceEngine koppelen aan BAOEES Core",
                "git evidence opnemen in ZIP-export",
                "git evidence opnemen in audit trail",
                "git evidence tonen in HTML-dashboard",
                "GitHub release tag toevoegen",
                "BAOEES semantische versie toevoegen",
                "buildnummer toevoegen",
                "digitale ondertekening toevoegen"
            ]
        }

    def get_git_evidence_result(self):
        return self.git_evidence_result

    def run(self):
        print("Project Version / Git Evidence Engine actief")