from __future__ import annotations

import json
from typing import Protocol

from models import BuilderResult, ReviewerResult
from prompts import BUILDER_SYSTEM_PROMPT, REVIEWER_SYSTEM_PROMPT


class AgentClient(Protocol):
    def run_builder(self, task: str, manager_instruction: str) -> BuilderResult:
        ...

    def run_reviewer(self, task: str, builder_result: BuilderResult, execution_context: str = "") -> ReviewerResult:
        ...


class MockAgentClient:
    def run_builder(self, task: str, manager_instruction: str) -> BuilderResult:
        lower = task.lower()
        proposed = []
        checks = ["manual review"]
        risks: list[str] = []
        if "logging" in lower:
            proposed.append("app/service.py: Add structured logging to service.process_name")
        if "test" in lower:
            proposed.append("tests/test_service.py: Add test that validates process_name output")
            checks.append("pytest -q")
        if not proposed:
            risks.append("Task is not mapped to a safe known edit.")
        return BuilderResult(
            summary=f"Planned safe repo changes for task: {task}",
            proposed_changes=proposed,
            checks_run=checks,
            risks=risks,
        )

    def run_reviewer(self, task: str, builder_result: BuilderResult, execution_context: str = "") -> ReviewerResult:
        if not builder_result.proposed_changes:
            return ReviewerResult(
                verdict="BLOCK",
                summary="Task is not supported by the safe demo builder.",
                issues=["No mapped change available."],
                next_actions=["Use a supported sample task or switch to codex mode."],
            )
        if "TESTS_PASSED=True" in execution_context or not execution_context:
            return ReviewerResult(
                verdict="APPROVE",
                summary="The changes are concrete and validation passed.",
                issues=[],
                next_actions=[],
            )
        return ReviewerResult(
            verdict="REVISE",
            summary="Validation failed or was incomplete.",
            issues=[execution_context.strip() or "Validation context missing."],
            next_actions=["Inspect diff and fix failing tests before retrying."],
        )


class OpenAIAgentClient:
    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def _response_text(self, response) -> str:
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text
        return str(response)

    def run_builder(self, task: str, manager_instruction: str) -> BuilderResult:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": BUILDER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Task:\n{task}\n\nManager instruction:\n{manager_instruction}"},
            ],
        )
        return BuilderResult(**json.loads(self._response_text(response)))

    def run_reviewer(self, task: str, builder_result: BuilderResult, execution_context: str = "") -> ReviewerResult:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Task:\n{task}\n\n"
                        f"Builder result:\n{json.dumps(builder_result.__dict__, ensure_ascii=False)}\n\n"
                        f"Execution context:\n{execution_context}"
                    ),
                },
            ],
        )
        return ReviewerResult(**json.loads(self._response_text(response)))
