from pathlib import Path
import shutil

from llm_client import MockAgentClient
from orchestrator import Orchestrator
from config import project_root


def test_repo_mode_is_idempotent(tmp_path: Path) -> None:
    src = project_root() / "sample_repo_template"
    dst = tmp_path / "repo"
    shutil.copytree(src, dst)

    orch = Orchestrator(MockAgentClient(), 2, ("app", "tests"))
    first = orch.run("Improve logging in the sample repo and add tests", mode="repo", repo_path=str(dst))
    second = orch.run("Improve logging in the sample repo and add tests", mode="repo", repo_path=str(dst))

    service_text = (dst / "app" / "service.py").read_text(encoding="utf-8")
    assert service_text.count('logger.info("processing %s", name)') == 1
    assert first.final_status == "APPROVED"
    assert second.final_status == "APPROVED"
