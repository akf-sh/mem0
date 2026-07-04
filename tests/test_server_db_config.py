import os
import sys

import pytest

pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed")

_SERVER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "server")
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

import db  # noqa: E402


POSTGRES_ENV_VARS = (
    "APP_DB_NAME",
    "DATABASE_URL",
    "PGDATABASE",
    "PGHOST",
    "PGPASSWORD",
    "PGPORT",
    "PGSSLMODE",
    "PGUSER",
    "POSTGRES_COLLECTION_NAME",
    "POSTGRES_DB",
    "POSTGRES_HOST",
    "POSTGRES_PASSWORD",
    "POSTGRES_PORT",
    "POSTGRES_SSLMODE",
    "POSTGRES_USER",
)


@pytest.fixture(autouse=True)
def _clear_postgres_env(monkeypatch):
    for name in POSTGRES_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_build_database_url_honors_managed_postgres_sslmode(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", '"us-east-5.pg.psdb.cloud"')
    monkeypatch.setenv("POSTGRES_PORT", '"6432"')
    monkeypatch.setenv("APP_DB_NAME", '"mem0"')
    monkeypatch.setenv("POSTGRES_USER", "mem0_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p/a@ss")
    monkeypatch.setenv("PGSSLMODE", '"require"')

    assert (
        db._build_database_url()
        == "postgresql+psycopg://mem0_user:p%2Fa%40ss@us-east-5.pg.psdb.cloud:6432/mem0?sslmode=require"
    )


def test_build_vector_store_config_honors_managed_postgres_sslmode(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "us-east-5.pg.psdb.cloud")
    monkeypatch.setenv("POSTGRES_PORT", "6432")
    monkeypatch.setenv("POSTGRES_DB", "mem0")
    monkeypatch.setenv("POSTGRES_USER", "mem0_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_COLLECTION_NAME", "memories")
    monkeypatch.setenv("PGSSLMODE", "require")

    assert db.build_vector_store_config() == {
        "host": "us-east-5.pg.psdb.cloud",
        "port": 6432,
        "dbname": "mem0",
        "user": "mem0_user",
        "password": "secret",
        "sslmode": "require",
        "collection_name": "memories",
    }


def test_database_url_fallback_uses_railway_style_url_and_sslmode(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@postgres.railway.internal:5432/railway")
    monkeypatch.setenv("PGSSLMODE", "require")

    assert (
        db._build_database_url()
        == "postgresql+psycopg://user:secret@postgres.railway.internal:5432/railway?sslmode=require"
    )
    assert db.build_vector_store_config() == {
        "connection_string": "postgresql://user:secret@postgres.railway.internal:5432/railway",
        "sslmode": "require",
        "collection_name": "memories",
    }
