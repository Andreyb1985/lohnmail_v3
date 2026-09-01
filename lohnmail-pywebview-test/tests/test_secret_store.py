from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.config import build_default_settings, load_settings, save_settings


class FakeSecretStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def set(self, secret_id: str, value: str) -> None:
        self.values[secret_id] = value

    def get(self, secret_id: str) -> str:
        return self.values.get(secret_id, "")

    def delete(self, secret_id: str) -> None:
        self.values.pop(secret_id, None)


def test_global_and_company_passwords_are_not_written_to_settings_json():
    with TemporaryDirectory() as temporary_directory:
        settings_path = Path(temporary_directory) / "settings.json"
        store = FakeSecretStore()
        settings = build_default_settings()
        settings["smtp"]["password"] = "global-secret"
        settings["companies"] = [
            {
                "id": "alpha",
                "name": "Alpha",
                "mail_settings": {"scope": "custom", "smtp": {"password": "company-secret"}},
            }
        ]
        settings["selected_company_id"] = "alpha"

        with patch("core.config.SETTINGS_PATH", settings_path), patch(
            "core.config._secret_store", return_value=store
        ):
            save_settings(settings)
            on_disk = json.loads(settings_path.read_text(encoding="utf-8"))
            loaded = load_settings()

        assert "password" not in on_disk["smtp"]
        assert "password" not in on_disk["companies"][0]["mail_settings"]["smtp"]
        assert store.values["smtp:global"] == "global-secret"
        assert store.values["smtp:company:alpha"] == "company-secret"
        assert loaded["smtp"]["password"] == "global-secret"
        assert loaded["companies"][0]["mail_settings"]["smtp"]["password"] == "company-secret"


def test_existing_plaintext_password_is_migrated_before_json_is_rewritten():
    with TemporaryDirectory() as temporary_directory:
        settings_path = Path(temporary_directory) / "settings.json"
        settings_path.write_text(
            json.dumps({"smtp": {"password": "legacy-secret"}}), encoding="utf-8"
        )
        store = FakeSecretStore()

        with patch("core.config.SETTINGS_PATH", settings_path), patch(
            "core.config._secret_store", return_value=store
        ):
            loaded = load_settings()
            on_disk = json.loads(settings_path.read_text(encoding="utf-8"))

        assert store.values["smtp:global"] == "legacy-secret"
        assert loaded["smtp"]["password"] == "legacy-secret"
        assert "password" not in on_disk["smtp"]
