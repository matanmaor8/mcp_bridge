from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from models import BuilderResult, ReviewerResult

IGNORE_DIRS = {
    ".git",
    ".codex",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "tmp",
}
IGNORE_SUFFIXES = {".pyc", ".pyo"}
TASK_FILE_NAME = ".bridge_codex_task.txt"


@dataclass
class CodexAvailability:
    command: str
    available: bool
    reason: str
    resolved_path: str = ""


@dataclass
class CodexExecutionResult:
    changed_files: list[str]
    tests_passed: bool
    rolled_back: bool = False
    diff_summary: str = ""
    test_output: str = ""
    backup_dir: str = ""
    output: str = ""


def detect_codex_command(command: str) -> CodexAvailability:
    resolved = shutil.which(command)
    if resolved:
        return CodexAvailability(command=command, available=True, reason="command found", resolved_path=resolved)
    return CodexAvailability(command=command, available=False, reason=f"command not found: {command}")


def _clean_text(text: str) -> str:
    return (
        text.replace("Iâ€™m", "I'm")
        .replace("â€™", "'")
        .replace("â€œ", '"')
        .replace("â€\x9d", '"')
        .replace("â€“", "-")
        .replace("\r\n", "\n")
        .strip()
    )


class CodexRepoExecutor:
    def __init__(self, repo_root: str | Path, codex_command: str) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.codex_command = codex_command or os.getenv("CODEX_COMMAND", "codex")
        self.codex_timeout_seconds = int(os.getenv("CODEX_TIMEOUT_SECONDS", "240"))
        self.test_timeout_seconds = int(os.getenv("TEST_TIMEOUT_SECONDS", "120"))
        self.node_exe = os.getenv("NODE_EXE", "").strip()
        self.task_file = self.repo_root / TASK_FILE_NAME

    def _build_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.node_exe:
            node_dir = str(Path(self.node_exe).parent)
            existing_path = env.get("PATH", "")
            if node_dir and node_dir not in existing_path:
                env["PATH"] = node_dir + os.pathsep + existing_path
        return env

    def _iter_files(self) -> Iterable[Path]:
        for path in self.repo_root.rglob("*"):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(self.repo_root).parts
            if any(part in IGNORE_DIRS for part in rel_parts):
                continue
            if path.suffix.lower() in IGNORE_SUFFIXES:
                continue
            if path.name == TASK_FILE_NAME:
                continue
            yield path

    def _snapshot_state(self) -> dict[str, str]:
        state: dict[str, str] = {}
        for path in self._iter_files():
            rel = path.relative_to(self.repo_root).as_posix()
            try:
                state[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
        return state

    def _detect_test_command(self) -> list[str] | None:
        override = os.getenv("TEST_COMMAND", "").strip()
        if override:
            return shlex.split(override, posix=os.name != "nt")
        if (
            (self.repo_root / "pytest.ini").exists()
            or (self.repo_root / "pyproject.toml").exists()
            or list(self.repo_root.glob("tests/test_*.py"))
        ):
            return ["python", "-m", "pytest", "-q", "--ignore=tmp"]
        if (self.repo_root / "package.json").exists():
            return ["npm", "test", "--", "--runInBand"]
        return None

    def _run_tests(self) -> tuple[bool, str]:
        command = self._detect_test_command()
        if not command:
            return True, "No test command detected; treating validation as pass."
        try:
            proc = subprocess.run(
                command,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
                timeout=self.test_timeout_seconds,
                env=self._build_env(),
            )
            output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
            return proc.returncode == 0, output
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            output = (stdout + "\n" + stderr).strip()
            return False, f"Test command timed out after {self.test_timeout_seconds}s.\n{output}"

    def _git_diff(self) -> str:
        if not (self.repo_root / ".git").exists():
            return ""
        proc = subprocess.run(
            ["git", "diff", "--", "."],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            env=self._build_env(),
        )
        return ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()

    def _write_task_file(self, task: str) -> None:
        self.task_file.write_text(task + "\n", encoding="utf-8")

    def _remove_task_file(self) -> None:
        try:
            if self.task_file.exists():
                self.task_file.unlink()
        except OSError:
            pass

    def _run_codex(self) -> str:
        availability = detect_codex_command(self.codex_command)
        if not availability.available:
            return availability.reason

        prompt = (
            f"Read the full task from {TASK_FILE_NAME} in the repository root and execute it exactly as written. "
            "Return your full response as normal text."
        )
        command = [self.codex_command, "exec", "--full-auto", "--color", "never", "--skip-git-repo-check", prompt]
        if os.name == "nt":
            command = ["cmd", "/c", *command]
        proc = subprocess.run(
            command,
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=self.codex_timeout_seconds,
            env=self._build_env(),
        )
        return _clean_text(((proc.stdout or "") + "\n" + (proc.stderr or "")).strip())

    def execute_task(self, task: str) -> CodexExecutionResult:
        before = self._snapshot_state()
        self._write_task_file(task)
        try:
            codex_output = self._run_codex()
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            self._remove_task_file()
            return CodexExecutionResult(
                changed_files=[],
                tests_passed=False,
                diff_summary="",
                test_output="",
                output=f"Codex timed out after {self.codex_timeout_seconds}s.\n{(stdout + chr(10) + stderr).strip()}",
            )
        finally:
            self._remove_task_file()

        after = self._snapshot_state()
        changed_files = sorted(
            [rel for rel, digest in after.items() if before.get(rel) != digest]
            + [rel for rel in before.keys() - after.keys()]
        )
        changed_files = [p for p in changed_files if p != TASK_FILE_NAME]
        diff_summary = self._git_diff()
        if not diff_summary:
            diff_summary = (
                "Changed files:\n" + "\n".join(f"- {rel}" for rel in changed_files)
                if changed_files
                else "No file changes detected."
            )
        tests_passed, test_output = self._run_tests()
        return CodexExecutionResult(
            changed_files=changed_files,
            tests_passed=tests_passed,
            diff_summary=diff_summary,
            test_output=test_output,
            output=codex_output,
        )


class CodexAgentClient:
    def __init__(self, codex_command: str, repo_path: str) -> None:
        self.codex_command = codex_command or os.getenv("CODEX_COMMAND", "codex")
        self.repo_path = repo_path

    def run_builder(self, task: str, manager_instruction: str) -> BuilderResult:
        return BuilderResult(
            summary=f"Codex will execute the task directly in the repository: {task}",
            proposed_changes=["Codex direct repository execution"],
            checks_run=["post-run validation"],
            risks=[],
        )

    def run_reviewer(self, task: str, builder_result: BuilderResult, execution_context: str = "") -> ReviewerResult:
        tests_passed = "TESTS_PASSED=True" in execution_context
        no_changes = "CHANGED_FILES=[]" in execution_context or "No file changes detected." in execution_context
        if tests_passed and not no_changes:
            return ReviewerResult(
                verdict="APPROVE",
                summary="Codex applied changes and validation passed.",
                issues=[],
                next_actions=[],
            )
        if tests_passed and no_changes:
            return ReviewerResult(
                verdict="BLOCK",
                summary="Codex completed without making any file changes.",
                issues=["No modified files were detected in the repository."],
                next_actions=["Retry with a more explicit task that names the exact file or content to write."],
            )
        return ReviewerResult(
            verdict="REVISE",
            summary="Codex completed but validation did not pass.",
            issues=[execution_context.strip() or "Validation context missing."],
            next_actions=["Inspect the diff and test output, then retry with a more targeted task."],
        )
