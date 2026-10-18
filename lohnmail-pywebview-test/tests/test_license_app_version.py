from core.license_manager import LicenseManager
from ui_web import version


def test_license_requests_use_current_release_version(monkeypatch):
    monkeypatch.setattr(version, 'APP_VERSION', '2.1.5')
    assert LicenseManager.app_version() == 'v2.1.5'
