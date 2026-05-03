import os
import json
import importlib
import sys
import requests
from pathlib import Path

import pytest


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


def import_users_in_tmp(tmp_path: Path, secrets=None, initial_cache=None):
    """Prepare a temp workspace and import modules.users with controlled config."""
    if secrets is None:
        secrets = {
            "SNIPEIT_API_URL": "https://example.com/api",
            "SNIPEIT_API_KEY": "test-key",
        }
    if initial_cache is None:
        initial_cache = {"alice@example.com": 1}

    # Minimal files used by modules.config/setup_global_vars
    (tmp_path / "secrets.json").write_text(json.dumps(secrets))
    (tmp_path / "user_id_cache.json").write_text(json.dumps(initial_cache))
    (tmp_path / "asset_id_cache.json").write_text(json.dumps({}))

    # Ensure clean import state
    sys.modules.pop("modules.users", None)
    sys.modules.pop("modules.config", None)
    sys.modules.pop("modules.logging", None)

    # Switch to temp cwd so config reads local secrets/caches
    os.chdir(tmp_path)
    users_mod = importlib.import_module("modules.users")
    importlib.reload(users_mod)
    return users_mod


def test_user_mail_to_id_list_uses_cache_and_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Cached email returns immediately; missing email fetched via API and cached."""
    users_mod = import_users_in_tmp(
        tmp_path,
        initial_cache={"alice@example.com": 10},
    )

    def fake_get(url, headers=None):
        assert url == "https://example.com/api/users?email=bob@example.com"
        return DummyResp(200, {"rows": [{"id": 20}]})

    monkeypatch.setattr(users_mod.requests, "get", fake_get)

    result = users_mod.user_mail_to_id_list(["alice@example.com", "bob@example.com"])
    assert result == [10, 20]

    # cache file must include bob now
    cache_path = tmp_path / "user_id_cache.json"
    data = json.loads(cache_path.read_text())
    assert data["bob@example.com"] == 20


def test_get_user_email_by_id_from_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """If ID is present in cache values, returns email without API call."""
    users_mod = import_users_in_tmp(
        tmp_path,
        initial_cache={"charlie@example.com": 30},
    )

    def fail_get(*args, **kwargs):
        raise AssertionError("requests.get should not be called when email is in cache")

    monkeypatch.setattr(users_mod.requests, "get", fail_get)

    email = users_mod.get_user_email_by_id(30)
    assert email == "charlie@example.com"


def test_get_user_email_by_id_uses_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """If ID not in cache, fetch via API."""
    users_mod = import_users_in_tmp(tmp_path, initial_cache={})

    def fake_get(url, headers=None):
        assert url == "https://example.com/api/users/77"
        return DummyResp(200, {"email": "dan@example.com"})

    monkeypatch.setattr(users_mod.requests, "get", fake_get)

    email = users_mod.get_user_email_by_id(77)
    assert email == "dan@example.com"


def test_user_mail_to_id_dict_maps_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that user_mail_to_id_dict returns a complete mapping of emails to IDs."""
    users_mod = import_users_in_tmp(tmp_path, initial_cache={"eve@example.com": 50})

    def fake_get(url, headers=None):
        assert url == "https://example.com/api/users?email=frank@example.com"
        return DummyResp(200, {"rows": [{"id": 60}]})

    monkeypatch.setattr(users_mod.requests, "get", fake_get)

    mapping = users_mod.user_mail_to_id_dict(["eve@example.com", "frank@example.com"])
    assert mapping == {"eve@example.com": 50, "frank@example.com": 60}

    # frank must be in cache now
    cache_path = tmp_path / "user_id_cache.json"
    data = json.loads(cache_path.read_text())
    assert data["frank@example.com"] == 60


def test_user_mail_notes_to_id_notes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that user_mail_notes_to_id_notes correctly maps email-note pairs to ID-note pairs."""
    users_mod = import_users_in_tmp(tmp_path, initial_cache={"greg@example.com": 70})

    def fake_get(url, headers=None):
        assert url == "https://example.com/api/users?email=helen@example.com"
        return DummyResp(200, {"rows": [{"id": 80}]})

    monkeypatch.setattr(users_mod.requests, "get", fake_get)

    input_pairs = [("greg@example.com", "note A"), ("helen@example.com", "note B")]
    result = users_mod.user_mail_notes_to_id_notes(input_pairs)
    assert result == [(70, "note A"), (80, "note B")]


def test_fetch_user_id_api_error_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """API error leads to SystemExit from the helper."""
    users_mod = import_users_in_tmp(tmp_path, initial_cache={})

    def fake_get(url, headers=None):
        assert url == "https://example.com/api/users?email=bad@example.com"
        return DummyResp(500, {"error": "server"}, text="server error")

    monkeypatch.setattr(users_mod.requests, "get", fake_get)

    with pytest.raises(SystemExit):
        users_mod._fetch_user_id_from_api("bad@example.com")


def test_get_user_email_by_id_api_error_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """API error leads to SystemExit from get_user_email_by_id."""
    users_mod = import_users_in_tmp(tmp_path, initial_cache={})

    def fake_get(url, headers=None):
        assert url == "https://example.com/api/users/999"
        return DummyResp(404, {"error": "not found"}, text="not found")

    monkeypatch.setattr(users_mod.requests, "get", fake_get)

    with pytest.raises(SystemExit):
        users_mod.get_user_email_by_id(999)


def test_get_user_email_by_id_fails_gracefully(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """If API call fails (e.g., network error), logs critical and exits."""
    users_mod = import_users_in_tmp(tmp_path, initial_cache={})

    def fake_get(url, headers=None):
        raise requests.exceptions.ConnectionError("Network failure")

    monkeypatch.setattr(users_mod.requests, "get", fake_get)

    with pytest.raises(SystemExit):
        users_mod.get_user_email_by_id(1230)