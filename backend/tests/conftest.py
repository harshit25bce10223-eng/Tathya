from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import Item, User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


def database_available() -> bool:
    import socket

    from app.core.config import settings as _settings

    # Fast TCP pre-check: psycopg can hang for minutes when nothing listens
    # on localhost (IPv6 blackhole), so never reach for it blindly.
    try:
        host = _settings.DATABASE_URL.hosts()[0]
        with socket.create_connection((host["host"], host["port"]), timeout=2):
            return True
    except (OSError, ValueError, IndexError):
        return False


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session | None]:
    if not database_available():
        # Deterministic (no-DB) tests still run; DB tests skip themselves.
        yield None
        return
    try:
        engine.connect().close()
    except Exception:  # noqa: BLE001
        yield None
        return
    if not (engine.url.database or "").startswith("tathya_audit_test_"):
        pytest.fail("Database tests require an isolated database. Run scripts/run_isolated_backend_tests.py.")
    with Session(engine) as session:
        init_db(session)
        yield session
        from app.core.jobs import drain_jobs
        drain_jobs()
        session.rollback()
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
