import os
import json
import importlib
import sys
from pathlib import Path

import pytest


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text="", ok=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        # If ok is not provided, infer from status_code
        self.ok = (status_code < 400) if ok is None else ok

    def json(self):
        return self._json_data


def import_licenses_in_tmp(tmp_path: Path, secrets=None):
    """Prepare tmp workspace and import modules.licenses with controlled config."""
    if secrets is None:
        secrets = {
            "SNIPEIT_API_URL": "https://example.com/api",
            "SNIPEIT_API_KEY": "test-key",
        }

    # Minimal files used by modules.config/setup_global_vars
    (tmp_path / "secrets.json").write_text(json.dumps(secrets))
    (tmp_path / "user_id_cache.json").write_text(json.dumps({}))
    (tmp_path / "asset_id_cache.json").write_text(json.dumps({}))

    # Ensure clean import state
    for m in ("modules.licenses", "modules.users", "modules.config", "modules.logging"):
        sys.modules.pop(m, None)

    # Switch to temp cwd so config reads local secrets/caches
    os.chdir(tmp_path)
    mod = importlib.import_module("modules.licenses")
    importlib.reload(mod)
    return mod


def test_get_license_info_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test successful retrieval of license info."""
    licenses = import_licenses_in_tmp(tmp_path)

    def fake_get(url, headers=None):
        assert url == "https://example.com/api/licenses/123"
        return DummyResp(200, {"name": "Test License"})

    monkeypatch.setattr(licenses.requests, "get", fake_get)

    assert licenses._get_license_info(123) is True


def test_get_license_info_exception_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that exceptions during license info retrieval cause exit."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses.requests, "get", lambda *a, **k: (_ for _ in ()).throw(Exception("boom")))
    with pytest.raises(SystemExit):
        licenses._get_license_info(1)


def test_get_license_seats_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test successful retrieval of license seats."""
    licenses = import_licenses_in_tmp(tmp_path)

    def fake_get(url, headers=None):
        assert url == "https://example.com/api/licenses/5/seats"
        return DummyResp(200, {"rows": [{"id": 1}, {"id": 2}]})

    monkeypatch.setattr(licenses.requests, "get", fake_get)
    rows = licenses._get_license_seats(5)
    assert isinstance(rows, list) and len(rows) == 2


def test_get_license_seats_error_status_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that a >399 status code returns None for license seats."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses.requests, "get", lambda *a, **k: DummyResp(500, text="server"))
    assert licenses._get_license_seats(9) is None


def test_get_license_seat_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test counting the number of license seats."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses, "_get_license_seats", lambda _id: [{"id": 1}, {"id": 2}, {"id": 3}])
    assert licenses.get_license_seat_count(42) == 3


def test_remove_duplicate_license_seats_unassigns_extras(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that duplicate license seats are unassigned correctly."""
    licenses = import_licenses_in_tmp(tmp_path)
    calls = []

    def fake_unassign(license_id, seat_id, user_id, note):
        calls.append((license_id, seat_id, user_id, note))

    monkeypatch.setattr(licenses, "_unassign_license_seat", fake_unassign)
    current = [
        {"id": 101, "assigned_user": {"id": 5}},
        {"id": 102, "assigned_user": {"id": 5}},
        {"id": 103, "assigned_user": {"id": 6}},
        {"id": 104, "assigned_user": None},
    ]
    licenses._remove_duplicate_license_seats(7, current)
    # Only the second seat for user 5 should be unassigned
    assert calls == [(7, 102, 5, "Unassigned duplicate by script")]


def test_unassign_license_seat_put_called(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that unassigning a license seat makes the correct PUT request."""
    licenses = import_licenses_in_tmp(tmp_path)
    # Patch get_user_email_by_id in the module
    monkeypatch.setattr(licenses, "get_user_email_by_id", lambda uid: "x@example.com")

    seen = {}

    def fake_put(url, json=None, headers=None):
        seen["url"] = url
        seen["json"] = json
        return DummyResp(200, {})

    monkeypatch.setattr(licenses.requests, "put", fake_put)
    licenses._unassign_license_seat(3, 55, 42, "Reason")
    assert seen["url"] == "https://example.com/api/licenses/3/seats/55"
    assert seen["json"]["assigned_to"] is None and seen["json"]["asset_id"] is None
    assert seen["json"]["notes"] == "Reason"


def test_unassign_license_seat_handles_non_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that unassigning a license seat handles non-200 responses gracefully."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses, "get_user_email_by_id", lambda uid: "x@example.com")
    monkeypatch.setattr(licenses.requests, "put", lambda *a, **k: DummyResp(400, {}, "bad"))
    # Should not raise
    licenses._unassign_license_seat(1, 2, 3, "note")


def test_assign_license_seat_put_called_with_and_without_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that assigning a license seat makes the correct PUT request with and without a note."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses, "get_user_email_by_id", lambda uid: "y@example.com")
    calls = []

    def fake_put(url, json=None, headers=None):
        calls.append((url, json))
        return DummyResp(200, {})

    monkeypatch.setattr(licenses.requests, "put", fake_put)
    licenses._assign_license_seat(8, 99, 77)
    licenses._assign_license_seat(8, 100, 78, note="Hello")

    assert calls[0][0] == "https://example.com/api/licenses/8/seats/99"
    assert calls[0][1] == {"assigned_to": 77}
    assert calls[1][0] == "https://example.com/api/licenses/8/seats/100"
    assert calls[1][1] == {"assigned_to": 78, "notes": "Hello"}


def test_set_license_seat_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test setting the license seat count."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses.requests, "patch", lambda *a, **k: DummyResp(200, {}))
    assert licenses._set_license_seat_count(5, 12) is True
    monkeypatch.setattr(licenses.requests, "patch", lambda *a, **k: DummyResp(500, {}, "err"))
    assert licenses._set_license_seat_count(5, 12) is False


def test_assign_license_seats_notes_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test the flow of assigning license seats with notes."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses, "_get_license_info", lambda _id: True)

    # Sequence of seats: initial, after-duplicates, after-set-count
    seq = [
        [
            {"id": 1, "assigned_user": {"id": 10}},
            {"id": 2, "assigned_user": None},
        ],
        [
            {"id": 1, "assigned_user": {"id": 10}},
            {"id": 2, "assigned_user": None},
        ],
        [
            {"id": 1, "assigned_user": None},
            {"id": 2, "assigned_user": None},
        ],
    ]

    def get_seats(_id):
        return seq.pop(0)

    monkeypatch.setattr(licenses, "_get_license_seats", get_seats)

    unassigned = []
    assigned = []
    monkeypatch.setattr(licenses, "_remove_duplicate_license_seats", lambda *_: None)
    monkeypatch.setattr(licenses, "_unassign_license_seat", lambda lic, seat, uid, note: unassigned.append((seat, uid, note)))
    monkeypatch.setattr(licenses, "_set_license_seat_count", lambda *_: True)
    monkeypatch.setattr(licenses, "_assign_license_seat", lambda lic, seat, uid, note=None: assigned.append((seat, uid, note)))

    # We want to unassign user 10 and assign user 20 with note
    licenses.assign_license_seats_notes(license_id=99, user_ids_and_notes=[(20, "N")], seat_count=1)

    # Unassigned one seat for user 10
    assert any(u[1] == 10 for u in unassigned)
    # Assigned one open seat to user 20 with note
    assert assigned == [(1, 20, "N")] or assigned == [(2, 20, "N")]


def test_assign_license_seats_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test the flow of assigning license seats without notes."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses, "_get_license_info", lambda _id: True)

    seq = [
        [{"id": 1, "assigned_user": {"id": 10}}, {"id": 2, "assigned_user": None}],
        [{"id": 1, "assigned_user": {"id": 10}}, {"id": 2, "assigned_user": None}],
        [{"id": 1, "assigned_user": None}, {"id": 2, "assigned_user": None}],
    ]
    monkeypatch.setattr(licenses, "_get_license_seats", lambda _id: seq.pop(0))
    monkeypatch.setattr(licenses, "_remove_duplicate_license_seats", lambda *_: None)
    monkeypatch.setattr(licenses, "_set_license_seat_count", lambda *_: True)

    assigned = []
    monkeypatch.setattr(licenses, "_unassign_license_seat", lambda lic, seat, uid, note: None)
    monkeypatch.setattr(licenses, "_assign_license_seat", lambda lic, seat, uid: assigned.append((seat, uid)))

    licenses.assign_license_seats(license_id=9, user_ids=[20], seat_count=1)
    assert assigned and assigned[0][1] == 20


def test_get_license_note_success_and_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test getting license note successfully and handling errors."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses.requests, "get", lambda *a, **k: DummyResp(200, {"notes": "hello"}))
    assert licenses._get_license_note(1) == "hello"
    monkeypatch.setattr(licenses.requests, "get", lambda *a, **k: DummyResp(404, {}, "nope"))
    assert licenses._get_license_note(1) is False


def test_update_license_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that updating a license note returns True on success and False on failure."""
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses.requests, "patch", lambda *a, **k: DummyResp(200, {}))
    assert licenses.update_license_notes(1, "n") is True
    monkeypatch.setattr(licenses.requests, "patch", lambda *a, **k: DummyResp(500, {}, "err"))
    assert licenses.update_license_notes(1, "n") is False


def test_update_license_note_non_company_users_builds_and_updates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that updating license note for non-company users builds and updates the note correctly."""
    licenses = import_licenses_in_tmp(tmp_path)
    # Existing note with old external section
    current_note = "Some base note\n#External Users:\n-\tOld User - old@example.com"
    monkeypatch.setattr(licenses, "_get_license_note", lambda _id: current_note)

    captured = {}
    def fake_update(_id, note):
        captured["note"] = note
        return True

    monkeypatch.setattr(licenses, "update_license_notes", fake_update)

    users = [{"name": "Alice", "email": "alice@ext.com"}, {"name": "Bob", "email": "bob@ext.com"}]
    ok = licenses.update_license_note_non_company_users(60, users)
    assert ok is True
    assert captured["note"].startswith("Some base note")
    assert "#External Users:" in captured["note"]
    assert "-\tAlice - alice@ext.com" in captured["note"]
    assert "-\tBob - bob@ext.com" in captured["note"]


def test_update_license_note_non_company_users_no_existing_note(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that updating license note for non-company users works when there is no existing note."""
    licenses = import_licenses_in_tmp(tmp_path)
    # No existing note
    monkeypatch.setattr(licenses, "_get_license_note", lambda _id: "")

    captured = {}
    def fake_update(_id, note):
        captured["note"] = note
        return True

    monkeypatch.setattr(licenses, "update_license_notes", fake_update)

    users = [{"name": "Charlie", "email": "charlie@ext.com"}]
    ok = licenses.update_license_note_non_company_users(60, users)
    assert ok is True
    assert "#External Users:" in captured["note"]
    assert "-\tCharlie - charlie@ext.com" in captured["note"]


def test_update_license_note_non_company_users_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test that updating license note for non-company users is idempotent and does not update if unchanged."""
    licenses = import_licenses_in_tmp(tmp_path)
    existing = "#External Users:\n-\tAlice - alice@ext.com"
    # Already matches what would be generated
    monkeypatch.setattr(licenses, "_get_license_note", lambda _id: existing)
    # If update is called, fail test
    monkeypatch.setattr(licenses, "update_license_notes", lambda *_: (_ for _ in ()).throw(AssertionError("should not update")))
    users = [{"name": "Alice", "email": "alice@ext.com"}]
    assert licenses.update_license_note_non_company_users(1, users) is True


def test_get_licenses_with_params(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Test getting licenses with query parameters."""
    licenses = import_licenses_in_tmp(tmp_path)

    seen = {}
    def fake_get(url, headers=None):
        seen["url"] = url
        return DummyResp(200, {"rows": []})

    monkeypatch.setattr(licenses.requests, "get", fake_get)
    res = licenses.get_licenses({"limit": 50, "offset": 10})
    assert res == {"rows": []}
    assert seen["url"] in (
        "https://example.com/api/licenses?limit=50&offset=10",
        "https://example.com/api/licenses?offset=10&limit=50",
    )


def test_update_license_notes_returns_true_false(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    licenses = import_licenses_in_tmp(tmp_path)
    monkeypatch.setattr(licenses.requests, "patch", lambda *a, **k: DummyResp(200, {}, ok=True))
    assert licenses.update_license_notes(5, "n") is True
    monkeypatch.setattr(licenses.requests, "patch", lambda *a, **k: DummyResp(500, {}, ok=False))
    assert licenses.update_license_notes(5, "n") is False