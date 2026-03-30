from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from threading import Thread
from time import sleep
import sys

import pytest
from httpx import ASGITransport, AsyncClient
from psycopg import connect
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import deps as api_deps
from app.api.routes import jobs as job_routes
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.tasks import job_tasks

TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/csv_job_platform_test"


def _ensure_test_database() -> None:
    database_url = make_url(TEST_DATABASE_URL)
    admin_url = database_url.set(database="postgres")
    psycopg_admin_url = admin_url.render_as_string(hide_password=False).replace(
        "postgresql+psycopg",
        "postgresql",
    )

    with connect(psycopg_admin_url, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (database_url.database,),
            )
            if cursor.fetchone() is None:
                cursor.execute(f'CREATE DATABASE "{database_url.database}"')


_ensure_test_database()
engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Iterator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class MockCeleryDelay:
    def __init__(self) -> None:
        self.queued_job_ids: list[int] = []

    def delay(self, job_id: int) -> None:
        self.queued_job_ids.append(job_id)

    def run_next(self) -> int:
        job_id = self.queued_job_ids.pop(0)
        job_tasks.process_job(job_id)
        return job_id

    def run_next_async(self, pause_seconds: float = 0.05) -> int:
        job_id = self.queued_job_ids.pop(0)

        def _runner() -> None:
            sleep(pause_seconds)
            job_tasks.process_job(job_id)

        Thread(target=_runner, daemon=True).start()
        return job_id


@pytest.fixture(autouse=True)
def test_database() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def override_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    app.dependency_overrides[api_deps.get_db] = override_get_db
    monkeypatch.setattr(job_tasks, "SessionLocal", TestingSessionLocal)

    settings = get_settings()
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir = str(upload_dir)
    settings.max_upload_size_bytes = 5_242_880

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def mock_celery_delay(monkeypatch: pytest.MonkeyPatch) -> MockCeleryDelay:
    controller = MockCeleryDelay()
    monkeypatch.setattr(job_routes.process_job, "delay", controller.delay)
    return controller


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
