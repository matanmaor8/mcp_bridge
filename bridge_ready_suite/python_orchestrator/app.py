from __future__ import annotations

import argparse

from rich.console import Console
from rich.panel import Panel

from config import Settings
from llm_client import MockAgentClient, OpenAIAgentClient
from orchestrator import Orchestrator
from codex_adapter import CodexAgentClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--mode", choices=["mock", "openai", "repo", "codex"], default="mock")
    parser.add_argument("--repo", default="")
    args = parser.parse_args()

    settings = Settings.from_env()

    if args.mode in {"mock", "repo"}:
        client = MockAgentClient()
    elif args.mode == "openai":
        client = OpenAIAgentClient(settings.openai_api_key, settings.openai_model)
    elif args.mode == "codex":
        client = CodexAgentClient(codex_command=settings.codex_command, repo_path=args.repo or "")
    else:
        raise ValueError(f"Unsupported mode: {args.mode}")

    orchestrator = Orchestrator(client, settings.max_rounds, settings.allow_edit_paths, settings.codex_command)
    state = orchestrator.run(task=args.task, mode=args.mode, repo_path=args.repo or None)

    console = Console()
    console.print(Panel.fit(f"Final status: {state.final_status}", title="Run result"))
    console.print(f"Summary: {state.final_summary}")

    if state.rounds and state.rounds[-1].execution_result:
        execution = state.rounds[-1].execution_result
        output = getattr(execution, "output", "").strip()
        diff_summary = getattr(execution, "diff_summary", "").strip()
        test_output = getattr(execution, "test_output", "").strip()

        if output:
            console.print(Panel(output, title="Codex output"))

        console.print("Changed files:")
        if execution.changed_files:
            for rel in execution.changed_files:
                console.print(f"- {rel}")
        else:
            console.print("- none")

        console.print(f"Tests passed: {execution.tests_passed}")

        if diff_summary:
            console.print(Panel(diff_summary, title="Diff summary"))
        if test_output:
            console.print(Panel(test_output, title="Test output"))
        if execution.rolled_back:
            console.print("Rollback: yes")


if __name__ == "__main__":
    main()
