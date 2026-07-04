import os
from urllib.parse import parse_qsl, quote, urlencode, urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value


def _postgres_sslmode() -> str | None:
    return _env("POSTGRES_SSLMODE") or _env("PGSSLMODE")


def _normalize_sqlalchemy_database_url(database_url: str) -> str:
    sslmode = _postgres_sslmode()
    if sslmode and "://" in database_url:
        parsed = urlsplit(database_url)
        query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != "sslmode"]
        query.append(("sslmode", sslmode))
        database_url = parsed._replace(query=urlencode(query)).geturl()

    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


def _postgres_connection_fields(db_name: str) -> dict[str, str | int]:
    port = _env("POSTGRES_PORT") or _env("PGPORT") or "5432"
    fields: dict[str, str | int] = {
        "host": _env("POSTGRES_HOST") or _env("PGHOST") or "postgres",
        "port": int(port),
        "dbname": db_name,
        "user": _env("POSTGRES_USER") or _env("PGUSER") or "postgres",
        "password": _env("POSTGRES_PASSWORD") or _env("PGPASSWORD") or "postgres",
    }
    sslmode = _postgres_sslmode()
    if sslmode:
        fields["sslmode"] = sslmode
    return fields


def build_vector_store_config() -> dict[str, str | int]:
    database_url = _env("DATABASE_URL")
    if database_url and not any(_env(name) for name in ("POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB")):
        config: dict[str, str | int] = {"connection_string": database_url}
        sslmode = _postgres_sslmode()
        if sslmode:
            config["sslmode"] = sslmode
    else:
        config = _postgres_connection_fields(_env("POSTGRES_DB") or _env("PGDATABASE") or "postgres")

    config["collection_name"] = _env("POSTGRES_COLLECTION_NAME") or "memories"
    return config


def _build_database_url() -> str:
    database_url = _env("DATABASE_URL")
    if database_url and not any(_env(name) for name in ("POSTGRES_HOST", "POSTGRES_PORT", "APP_DB_NAME")):
        return _normalize_sqlalchemy_database_url(database_url)

    fields = _postgres_connection_fields(_env("APP_DB_NAME") or _env("PGDATABASE") or "mem0_app")
    user = quote(str(fields["user"]), safe="")
    password = quote(str(fields["password"]), safe="")
    host = fields["host"]
    port = fields["port"]
    db = quote(str(fields["dbname"]), safe="")
    query = f"?sslmode={quote(str(fields['sslmode']), safe='')}" if fields.get("sslmode") else ""
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}{query}"


engine = create_engine(_build_database_url(), pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a SQLAlchemy session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
