from pathlib import Path


def test_windows_build_workflow_contract() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    workflow = repository_root / ".github" / "workflows" / "build-windows.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "runs-on: windows-latest" in text
    assert "actions/checkout@v6" in text
    assert "actions/setup-python@v6" in text
    assert 'python-version: "3.12"' in text
    assert "Set-Location lohnmail-pywebview-test" in text
    assert ".\\BUILD-WINDOWS.ps1" in text
    assert "release\\LohnMail\\App\\LohnMail.exe" in text
    assert "*-exe-update.zip" in text
    assert "*-exe-update.json" in text
    assert "actions/upload-artifact@v4" in text
    assert "if-no-files-found: error" in text
