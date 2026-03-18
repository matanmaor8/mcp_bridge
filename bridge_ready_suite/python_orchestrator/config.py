from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    max_rounds: int
    codex_command: str
    auto_approve_safe: bool
    allow_edit_paths: tuple[str, ...]

    @staticmethod
    def from_env() -> "Settings":
        allow_paths_raw = os.getenv("ALLOW_EDIT_PATHS", "app,tests")
        allow_paths = tuple(p.strip() for p in allow_paths_raw.split(",") if p.strip())
        return Settings(
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5").strip(),
            max_rounds=int(os.getenv("MAX_ROUNDS", "4")),
            codex_command=os.getenv("CODEX_COMMAND", "codex").strip(),
            auto_approve_safe=os.getenv("AUTO_APPROVE_SAFE", "true").lower() == "true",
            allow_edit_paths=allow_paths,
        )


def project_root() -> Path:
    return Path(__file__).resolve().parent
