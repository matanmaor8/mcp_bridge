from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class BuilderResult:
    summary: str
    proposed_changes: List[str]
    checks_run: List[str]
    risks: List[str]


@dataclass
class ReviewerResult:
    verdict: str
    summary: str
    issues: List[str]
    next_actions: List[str]


@dataclass
class ExecutionResult:
    changed_files: List[str]
    diff_summary: str
    tests_passed: bool
    test_output: str
    rolled_back: bool
    backup_dir: str


@dataclass
class RoundRecord:
    round_index: int
    manager_instruction: str
    builder_result: BuilderResult
    reviewer_result: ReviewerResult
    execution_result: ExecutionResult | None = None


@dataclass
class RunState:
    task: str
    rounds: List[RoundRecord] = field(default_factory=list)
    final_status: str = "INCOMPLETE"
    final_summary: str = ""
