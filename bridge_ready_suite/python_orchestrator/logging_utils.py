from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from models import RunState


def persist_run(state: RunState) -> Path:
    runs_dir = Path("runs")
    runs_dir.mkdir(exist_ok=True)
    path = runs_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(asdict(state), indent=2, ensure_ascii=False), encoding="utf-8")
    return path
