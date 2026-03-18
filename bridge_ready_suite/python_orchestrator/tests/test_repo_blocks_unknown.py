from pathlib import Path
import shutil

from llm_client import MockAgentClient
from orchestrator import Orchestrator
from config import project_root


def test_unknown_repo_task_is_blocked(tmp_path: Path) -> None:
    src = project_root() / "sample_repo_template"
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)

    orch = Orchestrator(MockAgentClient(), 2, ("app", "tests"))
    state = orch.run("Delete everything", mode="repo", repo_path=str(dst))
    assert state.final_status == "BLOCKED"
