"""
Test setup: run the app from a throwaway working directory (storage/, the
SQLite file and reports all live there), with AI turned off so no LLM is
needed.
"""
import io
import os
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

_work = tempfile.mkdtemp(prefix="codeatlas-test-")
os.chdir(_work)
os.environ.update(
    {
        "DEBUG": "false",
        # Set TEST_DATABASE_URL to an empty Postgres database to run against Postgres.
        "DATABASE_URL": os.environ.get("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{_work}/test.db",
        "OLLAMA_BASE_URL": "http://127.0.0.1:9",  # nothing listens here
        "LLM_TIMEOUT": "1",
        "ENABLE_AI_INSIGHTS": "false",
    }
)

from fastapi.testclient import TestClient  # noqa: E402

SAMPLE_PROJECT = {
    "app/main.py": (
        "import os\n"
        "from app.utils import add\n\n"
        "API_KEY = 'sk-live-1234567890abcdefghijklmnop'\n\n"
        "def handler(items):\n"
        "    total = 0\n"
        "    for i in items:\n"
        "        if i > 10:\n"
        "            if i % 2 == 0:\n"
        "                total += add(i, 1)\n"
        "            else:\n"
        "                total -= 1\n"
        "        elif i < 0:\n"
        "            total += 2\n"
        "    return total\n"
    ),
    "app/utils.py": "def add(a, b):\n    return a + b\n",
    "app/__init__.py": "",
    "web/index.js": "export function greet(name) {\n  return `Hello ${name}`;\n}\n",
    "README.md": "# Sample\n",
    "requirements.txt": "fastapi==0.110.0\n",
    "node_modules/junk/index.js": "module.exports = 1;\n",  # must be ignored
}


def make_zip(files=None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, body in (files or SAMPLE_PROJECT).items():
            z.writestr(f"sample-project/{name}", body)
    return buf.getvalue()


def token() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex[:8]  # 40 url-safe chars


@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app

    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:  # runs startup/shutdown (DB init, task queue)
        yield c


class Browser:
    """One visitor: their own owner token, like a browser's localStorage."""

    def __init__(self, client):
        self.client = client
        self.headers = {"X-Owner-Token": token()}

    def get(self, url, **kw):
        return self.client.get(url, headers=self.headers, **kw)

    def post(self, url, **kw):
        return self.client.post(url, headers=self.headers, **kw)

    def delete(self, url, **kw):
        return self.client.delete(url, headers=self.headers, **kw)

    def upload(self, files=None, name="sample-project.zip"):
        return self.post(
            "/api/upload/zip",
            files={"file": (name, make_zip(files), "application/zip")},
        )


@pytest.fixture
def browser(client):
    return Browser(client)


@pytest.fixture
def other_browser(client):
    return Browser(client)
