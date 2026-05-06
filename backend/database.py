from __future__ import annotations

import os
import sqlite3
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

try:
    from psycopg import connect
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - local sqlite fallback without postgres deps
    connect = None
    dict_row = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _is_serverless_runtime() -> bool:
    return bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))


def _sqlite_path() -> Path:
    configured_path = os.getenv("AVIVA_DB_PATH")
    if configured_path:
        return Path(configured_path)

    return BASE_DIR / "aviva.sqlite3"


SQLITE_DB_PATH = _sqlite_path()
POSTGRES_URL = (
    os.getenv("SUPABASE_DB_URL")
    or os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRES_URL_NON_POOLING")
    or os.getenv("POSTGRES_PRISMA_URL")
    or os.getenv("POSTGRES_URL_NO_SSL")
)
SUPABASE_URL = (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_KEY")
)


def using_postgres() -> bool:
    return bool(POSTGRES_URL)


def using_supabase_rest() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _normalize_query(query: str) -> str:
    if using_postgres():
        return query.replace("?", "%s")
    return query


def get_connection():
    if using_postgres():
        if connect is None:
            raise RuntimeError("Instale psycopg[binary] para usar Supabase/Postgres.")
        return connect(POSTGRES_URL, row_factory=dict_row)

    if _is_serverless_runtime():
        raise RuntimeError(
            "Banco Postgres nao configurado. Defina SUPABASE_DB_URL, DATABASE_URL ou POSTGRES_URL na Vercel."
        )

    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(SQLITE_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _api_request(
    table: str,
    *,
    method: str = "GET",
    query: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if query:
        url = f"{url}?{urlencode(query)}"

    headers = {
        "apikey": SUPABASE_KEY or "",
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if method in {"POST", "PATCH", "DELETE"}:
        headers["Prefer"] = "return=representation"

    data = json.dumps(body).encode() if body is not None else None
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=12) as response:
            content = response.read().decode()
    except HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"Erro Supabase {exc.code}: {detail}") from exc

    if not content:
        return None
    return json.loads(content)


def _select_from_query(query: str) -> str:
    compact = " ".join(query.split())
    return compact.split("SELECT ", 1)[1].split(" FROM ", 1)[0].replace(" ", "")


def _rest_fetch_one(query: str, params: tuple[Any, ...] = ()):
    select = _select_from_query(query)
    compact = " ".join(query.split()).lower()

    if " from users where email" in compact:
        rows = _api_request("users", query={"select": select, "email": f"eq.{params[0]}", "limit": "1"})
    elif " from users where id" in compact:
        rows = _api_request("users", query={"select": select, "id": f"eq.{params[0]}", "limit": "1"})
    elif " from events where id" in compact:
        rows = _api_request("events", query={"select": select, "id": f"eq.{params[0]}", "limit": "1"})
    else:
        raise RuntimeError(f"Consulta Supabase nao mapeada: {query}")

    return rows[0] if rows else None


def _rest_fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[Any]:
    select = _select_from_query(query)
    compact = " ".join(query.split()).lower()

    if " from events " in compact or compact.endswith(" from events"):
        return _api_request("events", query={"select": select, "order": "date.asc,start_time.asc"}) or []

    raise RuntimeError(f"Consulta Supabase nao mapeada: {query}")


def _rest_execute(query: str, params: tuple[Any, ...] = ()) -> int:
    compact = " ".join(query.split()).lower()

    if compact.startswith("insert into users"):
        rows = _api_request(
            "users",
            method="POST",
            body={"name": params[0], "email": params[1], "password_hash": params[2], "role": params[3]},
        )
        return int(rows[0]["id"])

    if compact.startswith("insert into events"):
        rows = _api_request(
            "events",
            method="POST",
            body={
                "title": params[0],
                "description": params[1],
                "date": params[2],
                "start_time": params[3],
                "end_time": params[4],
                "location": params[5],
                "image_url": params[6],
            },
        )
        return int(rows[0]["id"])

    if compact.startswith("update events"):
        _api_request(
            "events",
            method="PATCH",
            query={"id": f"eq.{params[7]}"},
            body={
                "title": params[0],
                "description": params[1],
                "date": params[2],
                "start_time": params[3],
                "end_time": params[4],
                "location": params[5],
                "image_url": params[6],
            },
        )
        return 0

    if compact.startswith("delete from events"):
        _api_request("events", method="DELETE", query={"id": f"eq.{params[0]}"})
        return 0

    raise RuntimeError(f"Comando Supabase nao mapeado: {query}")


def fetch_one(query: str, params: tuple[Any, ...] = ()):
    if using_supabase_rest() and not using_postgres():
        return _rest_fetch_one(query, params)

    with get_connection() as connection:
        cursor = connection.execute(_normalize_query(query), params)
        return cursor.fetchone()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[Any]:
    if using_supabase_rest() and not using_postgres():
        return _rest_fetch_all(query, params)

    with get_connection() as connection:
        cursor = connection.execute(_normalize_query(query), params)
        return cursor.fetchall()


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    if using_supabase_rest() and not using_postgres():
        return _rest_execute(query, params)

    normalized_query = _normalize_query(query)
    with get_connection() as connection:
        if using_postgres() and normalized_query.lstrip().upper().startswith("INSERT"):
            cursor = connection.execute(f"{normalized_query} RETURNING id", params)
            row = cursor.fetchone()
            connection.commit()
            return int(row["id"])

        cursor = connection.execute(normalized_query, params)
        connection.commit()
        return int(getattr(cursor, "lastrowid", 0) or 0)


def _schema_statements(schema: str) -> list[str]:
    return [statement.strip() for statement in schema.split(";") if statement.strip()]


def initialize_database() -> None:
    if using_supabase_rest() and not using_postgres():
        return

    if using_postgres():
        schema = """
        CREATE TABLE IF NOT EXISTS users (
          id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('member', 'admin')),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS events (
          id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
          title TEXT NOT NULL,
          description TEXT NOT NULL,
          date DATE NOT NULL,
          start_time TIME NOT NULL,
          end_time TIME NOT NULL,
          location TEXT NOT NULL,
          image_url TEXT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    else:
        schema = """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('member', 'admin')),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          description TEXT NOT NULL,
          date TEXT NOT NULL,
          start_time TEXT NOT NULL,
          end_time TEXT NOT NULL,
          location TEXT NOT NULL,
          image_url TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """

    with get_connection() as connection:
        if using_postgres():
            with connection.cursor() as cursor:
                for statement in _schema_statements(schema):
                    cursor.execute(statement)
        else:
            connection.executescript(schema)
        connection.commit()
