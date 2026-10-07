"""Append every loop event to a JSONL file in runs/, one run per file."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class RunLogger:
    def __init__(self, runs_dir: str | Path = "runs", label: str | None = None):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        self.run_id = f"{stamp}-{label or uuid.uuid4().hex[:6]}"
        self.path = Path(runs_dir) / f"{self.run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: dict) -> None:
        record = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "run_id": self.run_id, **event}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
