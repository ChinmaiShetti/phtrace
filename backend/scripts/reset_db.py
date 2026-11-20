"""Drop and rebuild the PharmaTrace database from db/*.sql, then (optionally) seed it.

Usage (from backend/):
    uv run python -m scripts.reset_db            # rebuild + seed demo data
    uv run python -m scripts.reset_db --no-seed  # empty schema only
    uv run python -m scripts.reset_db --db pharmatrace_test --no-seed
"""

import argparse
import sys

import psycopg
from psycopg import sql

from app.config import ROOT, get_settings

SQL_DIR = ROOT / "db"


def create_roles_and_db(db_name: str) -> None:
    s = get_settings()
    with psycopg.connect(s.admin_url, autocommit=True) as conn:
        for role, password in (("pharmatrace_owner", s.pg_owner_password), ("pharmatrace_app", s.pg_app_password)):
            exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role]).fetchone()
            verb = "ALTER" if exists else "CREATE"
            conn.execute(sql.SQL("{} ROLE {} LOGIN PASSWORD {}").format(
                sql.SQL(verb), sql.Identifier(role), sql.Literal(password)))
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(db_name)))
        conn.execute(sql.SQL("CREATE DATABASE {} OWNER pharmatrace_owner ENCODING 'UTF8'").format(sql.Identifier(db_name)))
    # btree_gist is a trusted extension, but creating it as superuser avoids any privilege surprises
    with psycopg.connect(s.url(s.pg_admin_user, s.pg_admin_password, db_name), autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(db_name)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO pharmatrace_app").format(sql.Identifier(db_name)))


def apply_schema(db_name: str) -> None:
    s = get_settings()
    with psycopg.connect(s.url("pharmatrace_owner", s.pg_owner_password, db_name)) as conn:
        for path in sorted(SQL_DIR.glob("[0-9][0-9]_*.sql")):
            print(f"  applying {path.name}")
            # a parameterless execute may contain many statements, including $$-quoted bodies
            conn.execute(path.read_text(encoding="utf-8"))
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=None, help="database name (default: DB_NAME from .env)")
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()
    db_name = args.db or get_settings().db_name

    if not get_settings().pg_admin_password:
        sys.exit("PG_ADMIN_PASSWORD is empty: copy .env.example to .env and fill it in.")
    print(f"Rebuilding database {db_name}")
    create_roles_and_db(db_name)
    apply_schema(db_name)
    if not args.no_seed:
        from scripts.seed import seed
        seed(db_name)
    print("Done.")


if __name__ == "__main__":
    main()
