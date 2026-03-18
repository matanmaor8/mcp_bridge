from __future__ import annotations

from pathlib import Path

from logging_utils import persist_run
from models import ReviewerResult, RoundRecord, RunState
from repo_tools import RepoExecutor
from codex_adapter import CodexRepoExecutor


class Orchestrator:
    def __init__(self, agent_client, max_rounds: int, allow_edit_paths: tuple[str, ...], codex_command: str = 'codex') -> None:
        self.agent_client = agent_client
        self.max_rounds = max_rounds
        self.allow_edit_paths = allow_edit_paths
        self.codex_command = codex_command

    def _manager_instruction(self, task: str, round_index: int, prior_review: ReviewerResult | None) -> str:
        if round_index == 1:
            return f'Perform one focused pass on task: {task}'
        if prior_review and prior_review.verdict == 'REVISE':
            return 'Retry with a narrower edit and prioritize passing tests.'
        return f'Continue carefully on task: {task}'

    def _repo_context(self, execution_result) -> str:
        return (
            f'TESTS_PASSED={execution_result.tests_passed}\n'
            f'ROLLED_BACK={execution_result.rolled_back}\n'
            f'CHANGED_FILES={execution_result.changed_files}\n'
            f'DIFF=\n{execution_result.diff_summary}\n'
            f'TEST_OUTPUT=\n{execution_result.test_output}'
        )

    def run(self, task: str, mode: str = 'mock', repo_path: str | None = None) -> RunState:
        state = RunState(task=task)
        prior_review = None
        rounds = 1 if mode == 'codex' else self.max_rounds

        for round_index in range(1, rounds + 1):
            instruction = self._manager_instruction(task, round_index, prior_review)
            builder_result = self.agent_client.run_builder(task, instruction)
            execution_result = None
            review_context = ''

            if mode in {'repo', 'codex'}:
                if not repo_path:
                    raise RuntimeError('repo_path is required for repo and codex modes')
                repo_root = Path(repo_path).resolve()
                executor = RepoExecutor(repo_root, self.allow_edit_paths) if mode == 'repo' else CodexRepoExecutor(repo_root, self.codex_command)
                execution_result = executor.execute_task(task)
                review_context = self._repo_context(execution_result)

            reviewer_result = self.agent_client.run_reviewer(task, builder_result, review_context)
            state.rounds.append(
                RoundRecord(
                    round_index=round_index,
                    manager_instruction=instruction,
                    builder_result=builder_result,
                    reviewer_result=reviewer_result,
                    execution_result=execution_result,
                )
            )
            prior_review = reviewer_result

            if reviewer_result.verdict in {'APPROVE', 'BLOCK'}:
                state.final_status = 'APPROVED' if reviewer_result.verdict == 'APPROVE' else 'BLOCKED'
                state.final_summary = reviewer_result.summary
                persist_run(state)
                return state

        state.final_status = 'MAX_ROUNDS_REACHED'
        state.final_summary = 'Stopped after reaching max rounds without approval.'
        persist_run(state)
        return state
