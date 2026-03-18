from __future__ import annotations

import difflib
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from models import ExecutionResult


SAFE_TASKS = {
    "Improve logging in the sample repo and add tests": "logging_and_tests",
    "Improve logging in the sample repo": "logging_only",
}


class RepoExecutor:
    def __init__(self, repo_root: Path, allow_edit_paths: tuple[str, ...]) -> None:
        self.repo_root = repo_root
        self.allow_edit_paths = allow_edit_paths
        self.backup_root = repo_root / ".orchestrator_backups"
        self.backup_root.mkdir(exist_ok=True)

    def _ensure_allowed(self, relative_path: str) -> Path:
        if not any(relative_path == prefix or relative_path.startswith(prefix + "/") for prefix in self.allow_edit_paths):
            raise RuntimeError(f"Editing blocked outside allowlist: {relative_path}")
        return self.repo_root / relative_path

    def _snapshot(self, targets: Iterable[str]) -> Path:
        import time

        backup_dir = self.backup_root / f"backup_{int(time.time() * 1000)}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for rel in targets:
            src = self.repo_root / rel
            dst = backup_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                shutil.copy2(src, dst)
        return backup_dir

    def _restore(self, backup_dir: Path, targets: Iterable[str]) -> None:
        for rel in targets:
            dst = self.repo_root / rel
            src = backup_dir / rel
            if src.exists():
                shutil.copy2(src, dst)

    def _read(self, relative_path: str) -> str:
        return self._ensure_allowed(relative_path).read_text(encoding="utf-8")

    def _write(self, relative_path: str, content: str) -> None:
        path = self._ensure_allowed(relative_path)
        path.write_text(content, encoding="utf-8", newline="\n")

    def _edit_service_logging(self) -> str:
        rel = "app/service.py"
        before = self._read(rel)
        target = '    logger.info("processing %s", name)\n'
        if target in before:
            return rel
        marker = "def process_name(name: str) -> str:\n"
        if marker not in before:
            raise RuntimeError("Expected process_name function was not found.")
        after = before.replace(marker, marker + target, 1)
        self._write(rel, after)
        return rel

    def _edit_test(self) -> str:
        rel = "tests/test_service.py"
        before = self._read(rel)
        test_block = (
            "\n\n"
            "def test_process_name_returns_expected_prefix() -> None:\n"
            '    assert process_name("Matan") == "processing Matan"\n'
        )
        if "test_process_name_returns_expected_prefix" in before:
            return rel
        self._write(rel, before.rstrip() + test_block + "\n")
        return rel

    def _diff_for(self, rel: str, old: str, new: str) -> str:
        return "".join(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            )
        )

    def execute_task(self, task: str) -> ExecutionResult:
        mode = SAFE_TASKS.get(task)
        if mode is None:
            return ExecutionResult([], "Unsupported repo task.", False, "Task unsupported.", False, "")

        targets = ["app/service.py"]
        if mode == "logging_and_tests":
            targets.append("tests/test_service.py")

        originals = {rel: self._read(rel) for rel in targets}
        backup_dir = self._snapshot(targets)
        changed_files: list[str] = []
        rolled_back = False

        try:
            changed_files.append(self._edit_service_logging())
            if mode == "logging_and_tests":
                changed_files.append(self._edit_test())

            tests = subprocess.run(
                ["python", "-m", "pytest", "-q"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
            tests_passed = tests.returncode == 0
            if not tests_passed:
                self._restore(backup_dir, targets)
                rolled_back = True

            effective_files = sorted(set(changed_files))
            diff_parts = []
            for rel in effective_files:
                current = self._read(rel)
                baseline = originals.get(rel, "")
                if current != baseline:
                    diff_parts.append(self._diff_for(rel, baseline, current))
            diff_summary = "\n".join(diff_parts) if diff_parts else "No effective file diffs."
            return ExecutionResult(
                changed_files=effective_files,
                diff_summary=diff_summary,
                tests_passed=tests_passed,
                test_output=(tests.stdout + "\n" + tests.stderr).strip(),
                rolled_back=rolled_back,
                backup_dir=str(backup_dir),
            )
        except Exception as exc:  # pragma: no cover - safety path
            self._restore(backup_dir, targets)
            return ExecutionResult([], f"Execution failed: {exc}", False, str(exc), True, str(backup_dir))
