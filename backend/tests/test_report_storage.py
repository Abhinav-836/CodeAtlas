"""Reports live in the database: they survive restarts, can be shared read-only, and moved between browsers."""
import json
from pathlib import Path

from conftest import Browser
from test_api import run_analysis


def test_reports_are_in_the_database_not_on_disk(browser):
    _, res = run_analysis(browser)
    rid = res["report_id"]
    assert not Path(f"storage/reports/{rid}.json").exists()

    from app.services import report_store

    row = report_store.get_row(rid)
    assert row is not None and row.secrets_found >= 1 and row.total_lines > 0
    listed = browser.get("/api/reports").json()["reports"]
    assert [r["id"] for r in listed] == [rid]
    assert listed[0]["secrets_found"] == row.secrets_found and listed[0]["size_bytes"] > 0


def test_reports_survive_a_restart(client, browser):
    _, res = run_analysis(browser)
    rid = res["report_id"]
    # Simulate a new server process: drop the store's connection pool and the task queue's memory.
    from app.services import report_store

    report_store.reset_engine()
    r = browser.get(f"/api/reports/{rid}")
    assert r.status_code == 200 and r.json()["report_id"] == rid
    assert browser.get(f"/api/reports/{rid}", params={"format": "pdf"}).content[:4] == b"%PDF"


def test_old_report_files_are_imported(client, browser):
    from app.core.owner import OWNER_KEY, hash_token
    from app.services import report_store

    owner = hash_token(browser.headers["X-Owner-Token"])
    folder = Path("storage/legacy-reports")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "legacy_report_1.json").write_text(json.dumps({
        "analysis_id": "legacy_report_1", "path": "old-repo", OWNER_KEY: owner,
        "metrics": {"total_lines": 42}, "security": {"secrets_found": 2},
    }))
    (folder / "broken.json").write_text("{not json")
    assert report_store.import_files(str(folder)) == 1
    assert report_store.import_files(str(folder)) == 0  # already there
    listed = {r["id"]: r for r in browser.get("/api/reports").json()["reports"]}
    assert listed["legacy_report_1"]["total_lines"] == 42


def test_share_link_is_read_only_and_revocable(client, browser, other_browser):
    _, res = run_analysis(browser)
    rid = res["report_id"]

    # Only the owner can share
    assert other_browser.post(f"/api/reports/{rid}/share").status_code == 404
    r = browser.post(f"/api/reports/{rid}/share")
    assert r.status_code == 200
    share = r.json()["share_token"]

    # Anyone with the link can view and download, without an owner token
    view = client.get(f"/api/shared/{share}")
    assert view.status_code == 200
    body = view.json()
    assert body["report_id"] == rid and body["shared_view"] is True and "_owner" not in body
    assert client.get(f"/api/shared/{share}", params={"format": "pdf", "download": True}).content[:4] == b"%PDF"
    assert browser.get("/api/reports").json()["reports"][0]["shared"] is True

    # …but the link gives no owner rights
    assert other_browser.delete(f"/api/reports/{rid}").status_code == 404

    # A new link replaces the old one; turning sharing off kills it
    second = browser.post(f"/api/reports/{rid}/share").json()["share_token"]
    assert client.get(f"/api/shared/{share}").status_code == 404
    assert browser.delete(f"/api/reports/{rid}/share").status_code == 200
    assert client.get(f"/api/shared/{second}").status_code == 404
    assert client.get("/api/shared/not-a-real-token-at-all-xx").status_code == 404
    assert client.get("/api/shared/x").status_code == 404


def test_move_reports_to_another_device(client):
    laptop, phone = Browser(client), Browser(client)
    _, res = run_analysis(laptop)
    rid = res["report_id"]
    assert phone.get("/api/reports").json()["reports"] == []

    # The laptop moves its reports to the phone's key…
    bad = laptop.post("/api/reports/transfer", json={"to_key": "nope"})
    assert bad.status_code == 400
    r = laptop.post("/api/reports/transfer", json={"to_key": phone.headers["X-Owner-Token"]})
    assert r.status_code == 200 and r.json()["moved"] == 1

    # …and from then on the phone's key owns them (the laptop switches to that key too).
    assert [x["id"] for x in phone.get("/api/reports").json()["reports"]] == [rid]
    assert phone.get(f"/api/reports/{rid}").status_code == 200
    assert laptop.get(f"/api/reports/{rid}").status_code == 404
    laptop.headers = dict(phone.headers)
    assert laptop.get(f"/api/reports/{rid}").status_code == 200


def test_database_url_normalisation():
    from app.core.config import Settings
    from app.services.report_store import sync_url

    s = Settings()
    for raw in (
        "postgres://u:p@ep-x.neon.tech/db?sslmode=require",
        "postgresql://u:p@ep-x.neon.tech/db?sslmode=require&channel_binding=require",
        "postgresql+asyncpg://u:p@h/db",
    ):
        s.DATABASE_URL = raw
        assert s.database_url.startswith("postgresql+psycopg://u:p@"), s.database_url
    s.DATABASE_URL = "sqlite:///./x.db"
    assert s.database_url == "sqlite+aiosqlite:///./x.db"
    assert sync_url(s.database_url) == "sqlite:///./x.db"
