import os
import json
import importlib
import sys
from pathlib import Path

import pytest

def import_config_in_tmp(tmp_path: Path, secrets=None):
    """Create minimal secrets.json and import modules.config from tmp dir."""
    if secrets is None:
        secrets = {
            "SNIPEIT_API_URL": "https://example.com/api",
            "SNIPEIT_API_KEY": "test-key",
            "DATTO_API_KEY": "datto-key",
            "DATTO_API_SECRET": "datto-secret",
        }
    (tmp_path / "secrets.json").write_text(json.dumps(secrets))
    (tmp_path / "user_id_cache.json").write_text(json.dumps({"alice@example.com": 123}))
    # Note: asset_cache_path points to the same filename in current implementation.

    # Ensure clean import state
    sys.modules.pop("modules.config", None)
    sys.modules.pop("modules.logging", None)

    # Change CWD to tmp and import
    os.chdir(tmp_path)
    cfg = importlib.import_module("modules.config")
    importlib.reload(cfg)
    return cfg


def test_setup_global_vars_loads_secrets(tmp_path: Path):
    """Test that setup_global_vars correctly loads secrets and caches."""
    cfg = import_config_in_tmp(tmp_path)
    g = cfg.setup_global_vars()
    assert "api_url" in g and g["api_url"].startswith("https://")
    assert "headers" in g and g["headers"]["Authorization"].endswith("test-key")
    # user cache loaded from user_id_cache.json
    assert g["user_cache"].get("alice@example.com") == 123


@pytest.mark.parametrize(
    "platform,expected_suffix",
    [
        ("win32", Path("venv") / "Scripts" / "python.exe"),
        ("linux", Path("venv") / "bin" / "python"),
        ("linux2", Path("venv") / "bin" / "python"),
        ("darwin", None),
        ("unsupported", None),
    ],
)
def test_get_venv_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, expected_suffix: Path):
    """Test getting the path to the Python executable in the virtual environment based on platform."""
    cfg = import_config_in_tmp(tmp_path)
    monkeypatch.setattr(sys, "platform", platform)
    script_path = Path("/repo/license_scripts/adobe.py")
    if expected_suffix is None:
        with pytest.raises(OSError):
            cfg.get_venv_path(script_path)
    else:
        result = cfg.get_venv_path(script_path)
        assert isinstance(result, Path)
        assert str(result).endswith(str(expected_suffix))


@pytest.mark.parametrize(
    "platform,expected",
    [
        ("win32", "pwsh.exe"),
        ("linux", "pwsh"),
        ("linux2", "pwsh"),
        ("darwin", None),
        ("unsupported", None),
    ],
)
def test_get_pwsh_executable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, expected: str):
    """Test getting the PowerShell executable path based on platform."""
    cfg = import_config_in_tmp(tmp_path)
    monkeypatch.setattr(sys, "platform", platform)
    if expected is None:
        with pytest.raises(OSError):
            cfg.get_pwsh_executable()
    else:
        result = cfg.get_pwsh_executable()
        assert result == expected


def test_get_assignments_file_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test providing a valid assignments file."""
    cfg = import_config_in_tmp(tmp_path)
    file = tmp_path / "assignments.csv"
    file.write_text("email\nalice@example.com\n")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    monkeypatch.setattr("builtins.input", lambda _='': str(file))
    path = cfg.get_assignments_file("assignments")
    assert path == str(file)


def test_get_assignments_file_missing_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that providing a missing file raises a FileNotFoundError."""
    cfg = import_config_in_tmp(tmp_path)
    missing = tmp_path / "missing.csv"
    monkeypatch.setattr("builtins.input", lambda _='': str(missing))
    with pytest.raises(FileNotFoundError):
        cfg.get_assignments_file("assignments")


def test_get_assignments_file_invalid_ext_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that providing a file with an invalid extension raises a ValueError."""
    cfg = import_config_in_tmp(tmp_path)
    bad = tmp_path / "file.json"
    bad.write_text("{}")
    monkeypatch.setattr("builtins.input", lambda _='': str(bad))
    with pytest.raises(ValueError):
        cfg.get_assignments_file("assignments")


def test_load_script_config_license_vendor(tmp_path: Path):
    """Test loading config for a license script vendor."""
    cfg = import_config_in_tmp(tmp_path)
    app_config = {
        "company_domain": "@a.ca",
        "license": {
            "solidprofessor": {
                "LICENSE_ID": 60
            }
        },
        "assets": {
            "update_monitors": {
                "some_asset_config": True
            }
        }
    }
    (tmp_path / "app_config.json").write_text(json.dumps(app_config))
    script_path = Path("/repo/license_scripts/solidprofessor.py")
    result = cfg.load_script_config(script_path)
    assert result["LICENSE_ID"] == 60
    assert result["company_domain"] == "@a.ca"
    assert "some_asset_config" not in result


def test_get_datto_credentials(tmp_path: Path):
    """Test retrieving Datto API credentials from secrets.json."""
    secrets = {
        "SNIPEIT_API_URL": "https://example.com/api",
        "SNIPEIT_API_KEY": "test-key",
        "DATTO_API_KEY": "abc",
        "DATTO_API_SECRET": "xyz",
    }
    cfg = import_config_in_tmp(tmp_path, secrets=secrets)
    key, secret = cfg.get_datto_credentials()
    assert key == "abc" and secret == "xyz"


def test_get_datto_credentials_invalid_json(tmp_path: Path):
    cfg = import_config_in_tmp(tmp_path)
    (tmp_path / "secrets.json").write_text("{'invalid_json'}")
    with pytest.raises(ValueError):
        cfg.get_datto_credentials()


def test_get_api_path(tmp_path: Path):
    """Test getting the expected API path for a given script."""
    cfg = import_config_in_tmp(tmp_path)
    script_path = Path("/repo/license_scripts/adobe.py")
    api_path = cfg.get_api_path(script_path)
    assert api_path.endswith("/api/api_adobe.py")