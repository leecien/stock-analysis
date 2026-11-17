"""狀態（state）與輸出（public）JSON 檔案存取。

state/   ：每次執行之間要保留的資料（看過的新聞、關鍵字統計、預測紀錄、花費）
public/  ：給手機 App 讀取的結果（latest.json、history.json）
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, state_dir: Path, out_dir: Path):
        self.state_dir = Path(state_dir)
        self.out_dir = Path(out_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default

    @staticmethod
    def _write(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"), default=str)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)

    def load_state(self, name: str, default: Any = None) -> Any:
        return self._read(self.state_dir / f"{name}.json", {} if default is None else default)

    def save_state(self, name: str, data: Any) -> None:
        self._write(self.state_dir / f"{name}.json", data)

    def load_output(self, name: str, default: Any = None) -> Any:
        return self._read(self.out_dir / f"{name}.json", {} if default is None else default)

    def save_output(self, name: str, data: Any) -> None:
        self._write(self.out_dir / f"{name}.json", data)
