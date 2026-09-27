import os
import sys
from pathlib import Path

TEST_DB_PATH = Path(__file__).resolve().parent / "test_okdriver.db"

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["ENABLE_ANALYTICS_SIMULATOR"] = "false"
os.environ["ENABLE_HEARTBEAT_SERVICE"] = "false"
os.environ["REDIS_URL"] = ""
os.environ["JWT_SECRET_KEY"] = "test-secret-key-do-not-use-in-production"
os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "Bh7ZMJqGb8PiTrt3RleIkq1LC_BoKbiaWfdv_fR4p5g="
os.environ["DEFAULT_ADMIN_PASSWORD"] = "Admin@12345"
os.environ["DEFAULT_OPERATOR_PASSWORD"] = "Operator@12345"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(scope="session")
def admin_token(client):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "Admin@12345"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def operator_token(client):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "operator", "password": "Operator@12345"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def operator_headers(operator_token):
    return {"Authorization": f"Bearer {operator_token}"}
