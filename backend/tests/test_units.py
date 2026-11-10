"""Unit tests for pieces that don't need the server."""
import pytest

from app.api.routes.upload import _extract_github_info
from app.core.owner import hash_token, same_owner
from app.workers.analyze_task import _calculate_overall_risk_score, _get_risk_level


@pytest.mark.parametrize(
    "url,repo,branch",
    [
        ("https://github.com/octo/hello", "hello", None),
        ("https://github.com/octo/hello.git", "hello", None),
        ("https://github.com/octo/hello/tree/develop", "hello", "develop"),
        ("git@github.com:octo/hello.git", "hello", None),
        ("gh repo clone octo/hello", "hello", None),
        # The form's own example format, without https://
        ("github.com/octo/hello", "hello", None),
        ("www.github.com/octo/hello", "hello", None),
        ("GitHub.com/octo/hello/tree/develop", "hello", "develop"),
        ("octo/hello", "hello", None),
    ],
)
def test_github_url_parsing(url, repo, branch):
    info = _extract_github_info(url)
    assert info["repo_name"] == repo
    assert info["repo_url"] == "https://github.com/octo/hello.git"
    assert info.get("branch") == branch


def test_owner_hash_and_comparison():
    assert hash_token("a" * 40) == hash_token("a" * 40)
    assert same_owner(hash_token("a" * 40), hash_token("a" * 40))
    assert not same_owner(None, hash_token("a" * 40))      # unowned data belongs to nobody
    assert not same_owner(hash_token("a" * 40), hash_token("b" * 40))


def _result(by_risk=None, secrets=0, vulns=None, avg_complexity=0, files=10):
    return {
        "security": {
            "secrets_found": secrets,
            "secrets_summary": {"by_risk": by_risk or {}},
            "by_severity": vulns or {},
        },
        "complexity": {"avg_complexity_score": avg_complexity},
        "summary": {"total_files": files},
    }


def test_risk_score_weights_secrets_by_severity():
    assert _get_risk_level(_calculate_overall_risk_score(_result())) == "none"
    one_critical = _calculate_overall_risk_score(_result({"critical": 1}, secrets=1))
    assert _get_risk_level(one_critical) == "high"
    one_low = _calculate_overall_risk_score(_result({"low": 1}, secrets=1))
    assert _get_risk_level(one_low) == "low"
    worst = _calculate_overall_risk_score(
        _result({"critical": 5}, secrets=5, vulns={"critical": 3, "high": 4}, avg_complexity=60, files=2000)
    )
    assert worst == 100 and _get_risk_level(worst) == "critical"


def test_secret_masking_never_reveals_most_of_a_secret():
    from app.services.security.secrets_scanner import _mask_secret
    assert _mask_secret("short") == "***"
    # A short password keeps only 2 characters (it used to show "Admi*_123")
    assert _mask_secret("Admin_123") == "Ad********"
    key = "sk_live_" + "x" * 24 + "9f3a"
    masked = _mask_secret(key)
    assert masked.startswith("sk_l") and masked.endswith("9f3a") and "x" not in masked
