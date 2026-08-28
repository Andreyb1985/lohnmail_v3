from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from threading import RLock
import time


class WorkflowSessionStore:
    """Persist resumable workflow state independently for every company."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()

    def _read(self) -> dict[str, dict]:
        if not self.path.is_file():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def load(self, company_id: str) -> dict:
        with self._lock:
            value = self._read().get(str(company_id or ""), {})
            return value if isinstance(value, dict) else {}

    def _write(self, data: dict[str, dict]) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                delete=False,
            ) as temporary:
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)

            for attempt in range(6):
                try:
                    os.replace(temporary_path, self.path)
                    temporary_path = None
                    return True
                except PermissionError:
                    if attempt == 5:
                        return False
                    time.sleep(0.05 * (attempt + 1))
                except OSError:
                    return False
            return False
        except OSError:
            return False
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def save(self, company_id: str, state: dict) -> None:
        company_id = str(company_id or "").strip()
        if not company_id:
            return
        with self._lock:
            data = self._read()
            data[company_id] = state
            self._write(data)

    def delete(self, company_id: str) -> None:
        company_id = str(company_id or "").strip()
        if not company_id:
            return
        with self._lock:
            data = self._read()
            if company_id not in data:
                return
            data.pop(company_id, None)
            self._write(data)
