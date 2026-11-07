"""End-to-end API tests: upload a ZIP, analyse it, read results and reports."""
import io
import json
import time
import zipfile

from conftest import SAMPLE_PROJECT, make_zip


def run_analysis(browser, files=None):
    up = browser.upload(files)
    assert up.status_code == 200, up.text
    r = browser.post("/api/analyze", params={"path": up.json()["extracted_to"]})
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]
    for _ in range(120):
        status = browser.get(f"/api/analyze/status/{task_id}").json()
        if status["status"] not in ("queued", "running"):
            break
        time.sleep(0.25)
    assert status["status"] == "completed", status
    res = browser.get(f"/api/analyze/results/{task_id}")
    assert res.status_code == 200, res.text
    return task_id, res.json()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ("healthy", "ok", "degraded")


def test_owner_token_is_required(client):
    assert client.get("/api/reports").status_code == 401
    bad = client.get("/api/reports", headers={"X-Owner-Token": "short"})
    assert bad.status_code == 401


def test_upload_rejects_non_zip_and_path_traversal(browser):
    r = browser.post("/api/upload/zip", files={"file": ("notes.txt", b"hi", "text/plain")})
    assert r.status_code == 400

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("../../evil.py", "print('pwned')")
    r = browser.post("/api/upload/zip", files={"file": ("evil.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 400 and "traversal" in r.json()["detail"].lower()


def test_cannot_analyze_paths_outside_uploads(browser):
    for path in ("/", "/etc", "storage/uploads", "storage/uploads/../.."):
        r = browser.post("/api/analyze", params={"path": path})
        assert r.status_code in (403, 404), (path, r.status_code)


def test_full_analysis(browser):
    _, res = run_analysis(browser)

    assert res["status"] == "completed"
    # node_modules is skipped: 6 real files, not 7
    assert res["summary"]["total_files"] == 6
    langs = res["languages"]["detected_languages"]
    assert "Python" in langs and "JavaScript" in langs
    assert res["languages"]["primary_language"] == "Python"

    # The hard-coded key is found, reported with its line, and masked
    sec = res["security"]
    assert sec["secrets_found"] == 1
    secret = sec["secrets"][0]
    assert secret["file"].endswith("app/main.py") and secret["line"] == 4
    assert "1234567890abcdefghijklmnop" not in json.dumps(res)

    # A committed live credential must make the repo at least "high" risk
    assert res["overall_risk_level"] in ("high", "critical"), res["overall_risk_score"]

    # The server's own directory layout never leaks into results
    assert "storage/uploads" not in json.dumps(res)
    assert "_owner" not in res
    assert res["report_id"]


def test_clean_project_is_low_risk(browser):
    clean = {k: v for k, v in SAMPLE_PROJECT.items() if k != "app/main.py"}
    clean["app/main.py"] = "from app.utils import add\n\nprint(add(1, 2))\n"
    _, res = run_analysis(browser, clean)
    assert res["security"]["secrets_found"] == 0
    assert res["overall_risk_level"] in ("none", "low")


def test_other_people_cannot_see_your_work(browser, other_browser):
    up = browser.upload().json()
    # Someone else can't analyse your upload
    r = other_browser.post("/api/analyze", params={"path": up["extracted_to"]})
    assert r.status_code == 404

    task_id, res = run_analysis(browser)
    report_id = res["report_id"]
    for url in (
        f"/api/analyze/status/{task_id}",
        f"/api/analyze/results/{task_id}",
        f"/api/reports/{report_id}",
    ):
        assert other_browser.get(url).status_code == 404, url
    assert other_browser.delete(f"/api/reports/{report_id}").status_code == 404
    listed = [r["id"] for r in other_browser.get("/api/reports").json()["reports"]]
    assert report_id not in listed


def test_reports_list_get_and_delete(browser):
    _, res = run_analysis(browser)
    report_id = res["report_id"]

    listed = browser.get("/api/reports").json()["reports"]
    row = next(r for r in listed if r["id"] == report_id)
    assert row["secrets_found"] == 1 and row["files_analyzed"] == 6

    full = browser.get(f"/api/reports/{report_id}")
    assert full.status_code == 200 and "_owner" not in full.text

    r = browser.delete(f"/api/reports/{report_id}")
    assert r.status_code == 200 and r.json()["deleted"] is True
    assert browser.get(f"/api/reports/{report_id}").status_code == 404


def test_unknown_task_is_404(browser):
    assert browser.get("/api/analyze/status/does-not-exist").status_code == 404
    assert browser.get("/api/analyze/results/does-not-exist").status_code == 404
