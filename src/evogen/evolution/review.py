from __future__ import annotations

import compileall
import re
from pathlib import Path

from evogen.core.enums import Severity
from evogen.core.ids import new_id
from evogen.core.models import CandidateManifest, ReviewFinding, ReviewReport


class PythonCandidateReviewer:
    """Static adversarial checks for generated Python candidate code."""

    def review(
        self,
        candidate: CandidateManifest,
        *,
        forbidden_literals: list[str] | None = None,
    ) -> ReviewReport:
        root = Path(candidate.workspace_path)
        files: list[Path] = []
        unsafe_paths: list[str] = []
        resolved_root = root.resolve()
        for relative in sorted(candidate.workspace_file_digests):
            candidate_path = Path(relative)
            full = (root / candidate_path).resolve()
            if (
                candidate_path.is_absolute()
                or ".." in candidate_path.parts
                or resolved_root not in full.parents
            ):
                unsafe_paths.append(relative)
            else:
                files.append(root / candidate_path)
        findings: list[ReviewFinding] = []
        checks: dict[str, bool] = {}

        checks["workspace_exists"] = root.exists()
        if not root.exists():
            findings.append(
                ReviewFinding(
                    severity=Severity.CRITICAL,
                    code="workspace_missing",
                    message=f"Candidate workspace does not exist: {root}",
                )
            )
            return ReviewReport(
                review_id=new_id("review"),
                candidate_id=candidate.candidate_id,
                passed=False,
                checks=checks,
                findings=findings,
            )

        checks["workspace_files_present"] = bool(files) and all(path.is_file() for path in files)
        checks["workspace_paths_safe"] = not unsafe_paths
        if unsafe_paths:
            findings.append(
                ReviewFinding(
                    severity=Severity.CRITICAL,
                    code="unsafe_workspace_path",
                    message=f"Candidate workspace declares unsafe paths: {unsafe_paths!r}",
                )
            )
        if not checks["workspace_files_present"]:
            findings.append(
                ReviewFinding(
                    severity=Severity.HIGH,
                    code="missing_workspace_file",
                    message="One or more declared workspace files are absent.",
                )
            )

        compile_root = root / "plugins"
        checks["python_compiles"] = compileall.compile_dir(
            compile_root,
            quiet=1,
            force=True,
        )
        if not checks["python_compiles"]:
            findings.append(
                ReviewFinding(
                    severity=Severity.CRITICAL,
                    code="python_compile_failed",
                    message="Generated capability plugin did not compile.",
                )
            )

        forbidden = [literal for literal in (forbidden_literals or []) if literal]
        shortcut_found = False
        suspicious_patterns = [
            re.compile(r"scenario[_-]?id", re.IGNORECASE),
            re.compile(r"if\s+.*target.*==", re.IGNORECASE),
        ]
        for path in files:
            if not path.exists() or path.suffix != ".py":
                continue
            text = path.read_text(encoding="utf-8")
            for literal in forbidden:
                if literal in text:
                    shortcut_found = True
                    findings.append(
                        ReviewFinding(
                            severity=Severity.HIGH,
                            code="revealing_literal_embedded",
                            message=f"Candidate embeds forbidden revealing literal {literal!r}.",
                            file=str(path.relative_to(root)),
                        )
                    )
            for pattern in suspicious_patterns:
                if pattern.search(text):
                    findings.append(
                        ReviewFinding(
                            severity=Severity.MEDIUM,
                            code="shortcut_pattern_review",
                            message=(
                                "Candidate contains a pattern that may specialize behavior to a "
                                "scenario or target; manual or model review is required."
                            ),
                            file=str(path.relative_to(root)),
                        )
                    )
        checks["no_revealing_literals"] = not shortcut_found

        changed_scope_ok = all(
            Path(relative).parts and Path(relative).parts[0] == "plugins"
            for relative in candidate.workspace_file_digests
        )
        checks["change_scope_limited"] = changed_scope_ok
        if not changed_scope_ok:
            findings.append(
                ReviewFinding(
                    severity=Severity.HIGH,
                    code="change_scope_broadened",
                    message="Reference candidate changed files outside the plugin boundary.",
                )
            )

        blocking = {Severity.CRITICAL, Severity.HIGH}
        passed = all(checks.values()) and not any(
            finding.severity in blocking for finding in findings
        )
        return ReviewReport(
            review_id=new_id("review"),
            candidate_id=candidate.candidate_id,
            passed=passed,
            checks=checks,
            findings=findings,
            reviewed_files=[str(path.relative_to(root)) for path in files if path.exists()],
        )
