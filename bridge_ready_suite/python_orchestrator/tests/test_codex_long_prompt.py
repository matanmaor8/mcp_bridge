from __future__ import annotations

import os
from pathlib import Path

from codex_adapter import CodexRepoExecutor


def test_codex_long_prompt_uses_task_file(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docs").mkdir()
    (repo / "tests").mkdir()
    (repo / "tests" / "test_dummy.py").write_text("def test_dummy():\n    assert True\n", encoding="utf-8")

    fake_codex = tmp_path / "fake_codex.py"
    fake_codex.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        "import sys\n"
        "task = Path('.bridge_codex_task.txt').read_text(encoding='utf-8')\n"
        "Path('docs/generated.md').write_text(task[:200], encoding='utf-8')\n"
        "print('Created docs/generated.md from task file.')\n",
        encoding="utf-8",
    )
    fake_codex.chmod(0o755)

    monkeypatch.setenv("TEST_COMMAND", "python -m pytest -q")
    executor = CodexRepoExecutor(repo, str(fake_codex))

    long_task = "Create docs/generated.md with exactly this content:\n\n" + ("LONG-CONTENT-1234567890\n" * 2000)
    result = executor.execute_task(long_task)

    assert result.tests_passed is True
    assert "docs/generated.md" in result.changed_files
    assert (repo / "docs" / "generated.md").exists()
    written = (repo / "docs" / "generated.md").read_text(encoding="utf-8")
    assert "LONG-CONTENT-1234567890" in written
    assert "Created docs/generated.md" in result.output
