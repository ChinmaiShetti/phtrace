"""Verify the login database before the Windows launcher opens the browser."""
import shutil
import socket
import subprocess
import sys
import time

import psycopg

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    host, port = settings.pg_host, settings.pg_port
    try:
        with socket.create_connection((host, port), timeout=2):
            pass
    except OSError:
        docker = shutil.which("docker")
        if not (docker and host in {"localhost", "127.0.0.1", "::1"} and port == 5433):
            sys.exit(f"PostgreSQL is unreachable at {host}:{port}. Check the service and .env settings.")
        if subprocess.run([docker, "info"], capture_output=True).returncode:
            print("Starting Docker Desktop for the local demo database...", flush=True)
            if subprocess.run([docker, "desktop", "start", "--timeout", "90"]).returncode:
                sys.exit("Start Docker Desktop and run the launcher again.")
        if subprocess.run([docker, "start", "pharmatrace-pg-dev"]).returncode:
            sys.exit(f"Start the configured PostgreSQL server on {host}:{port} and run the launcher again.")

    for attempt in range(8):
        try:
            with psycopg.connect(settings.app_url, connect_timeout=2) as conn:
                conn.execute("SELECT staff_id FROM staff LIMIT 1")
            print(f"Staff database ready at {host}:{port}.")
            return
        except psycopg.OperationalError:
            if attempt < 7:
                time.sleep(1)
        except psycopg.Error:
            sys.exit("Cannot read the staff table. Check the schema and application role in the configured database.")
    sys.exit(f"Login database unavailable at {host}:{port}. Check PostgreSQL and the application credentials in .env.")


if __name__ == "__main__":
    main()
