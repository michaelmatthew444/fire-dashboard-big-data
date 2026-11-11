"""
Initialise the fire_forest_db database from a pg_dump file and keep the demo dates current.

Safe to run on every container start:
  * waits until PostgreSQL accepts connections
  * creates the database if it does not exist
  * restores the dump ONLY if the database is empty (use --reset to force a rebuild)
  * moves the demo dates forward so the newest day is always "yesterday" (no double shifting)

Usage:
    python init_db.py             # normal start-up
    python init_db.py --reset     # wipe the public schema and restore again
    python init_db.py --no-shift  # restore only, leave dates untouched
"""
import argparse
import io
import os
import re
import sys
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2 import sql

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
HOP_DAYS = 100_000  # temporary far-away position used while shifting dates


# ----------------------------------------------------------------------------- config
def load_config() -> dict:
    cfg = {"host": "localhost", "port": 5432, "dbname": "fire_forest_db",
           "user": "matthew", "password": "fire1234"}
    url = os.getenv("DATABASE_URL")
    if url:
        u = urlparse(url)
        cfg.update(
            host=u.hostname or cfg["host"],
            port=u.port or cfg["port"],
            dbname=u.path.lstrip("/") or cfg["dbname"],
            user=unquote(u.username) if u.username else cfg["user"],
            password=unquote(u.password) if u.password else cfg["password"],
        )
    # Explicit DB_* variables win over DATABASE_URL
    cfg["host"] = os.getenv("DB_HOST", cfg["host"])
    cfg["port"] = int(os.getenv("DB_PORT", cfg["port"]))
    cfg["dbname"] = os.getenv("DB_NAME", cfg["dbname"])
    cfg["user"] = os.getenv("DB_USER", cfg["user"])
    cfg["password"] = os.getenv("DB_PASSWORD", cfg["password"])
    return cfg


def connect(cfg: dict, dbname: str | None = None):
    return psycopg2.connect(dbname=dbname or cfg["dbname"], user=cfg["user"],
                            password=cfg["password"], host=cfg["host"], port=cfg["port"])


def log(msg: str) -> None:
    print(f"[Database Init] {msg}", flush=True)


# ----------------------------------------------------------------------------- steps
def wait_for_server(cfg: dict, timeout: int) -> None:
    deadline = time.time() + timeout
    while True:
        try:
            connect(cfg, "postgres").close()
            return
        except psycopg2.OperationalError as exc:
            if "password authentication failed" in str(exc) or time.time() > deadline:
                raise
            log(f"Waiting for PostgreSQL at {cfg['host']}:{cfg['port']} ...")
            time.sleep(2)


def ensure_database(cfg: dict) -> None:
    conn = connect(cfg, "postgres")
    conn.autocommit = True  # CREATE DATABASE cannot run inside a transaction
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (cfg["dbname"],))
        if cur.fetchone() is None:
            log(f"Creating database '{cfg['dbname']}'")
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(cfg["dbname"])))
    finally:
        conn.close()


def reset_schema(cfg: dict) -> None:
    log("Resetting: dropping and recreating schema 'public'")
    conn = connect(cfg)
    conn.autocommit = True
    try:
        conn.cursor().execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
    finally:
        conn.close()


def is_initialised(cfg: dict) -> bool:
    conn = connect(cfg)
    try:
        cur = conn.cursor()
        cur.execute("SELECT to_regclass('public.region')")
        if cur.fetchone()[0] is None:
            return False
        cur.execute("SELECT EXISTS (SELECT 1 FROM public.region)")
        return cur.fetchone()[0]
    finally:
        conn.close()


def find_dump(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
    elif os.getenv("DUMP_PATH"):
        path = Path(os.environ["DUMP_PATH"])
    else:
        dumps = sorted(DATA_DIR.glob("dump-*.sql"))  # newest timestamp in the name sorts last
        if not dumps:
            raise FileNotFoundError(f"No dump-*.sql file found in {DATA_DIR}")
        path = dumps[-1]
    if not path.exists():
        raise FileNotFoundError(f"Dump file not found: {path}")
    return path


COPY_START = re.compile(r"^COPY .+ FROM stdin;\s*$")


def prepare_dump(path: Path, owner: str) -> list:
    """Turn a pg_dump file into a list of steps that is safe to run inside an existing database.
    Returns [("sql", text), ("copy", statement, data), ...] in file order.
    Works with both INSERT-style dumps and pg_dump's default COPY-style dumps."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"{path.name} is not UTF-8. If you created it with PowerShell's '>' redirect it was saved as "
            "UTF-16: export it with 'pg_dump -f file.sql' (inside the container) or from DBeaver instead."
        ) from exc
    text = text.replace("\r\n", "\n")

    # Cut the old one-off date-shift block at the end (it runs with an empty search_path and
    # would double-shift on a second run). Dates are handled by shift_dates() instead.
    marker = re.search(r"^DO \$\$", text, flags=re.M)
    if marker:
        text = text[:marker.start()]

    # Split out COPY ... FROM stdin data blocks: they must be sent with the COPY protocol.
    parts, sql_lines, lines, i = [], [], text.split("\n"), 0
    while i < len(lines):
        if COPY_START.match(lines[i]):
            j = i + 1
            while j < len(lines) and lines[j] != "\\.":
                j += 1
            parts.append(("sql", "\n".join(sql_lines)))
            parts.append(("copy", lines[i], "\n".join(lines[i + 1:j]) + "\n"))
            sql_lines, i = [], j + 1
        else:
            sql_lines.append(lines[i])
            i += 1
    parts.append(("sql", "\n".join(sql_lines)))

    def clean(block: str) -> str:
        # Database-level statements: the database already exists, and DROP/CREATE DATABASE
        # cannot run inside a transaction or a multi-statement string.
        block = re.sub(r"^(DROP|CREATE|ALTER) DATABASE\b.*?;[ \t]*$", "", block, flags=re.M)
        # Setting that only exists in PostgreSQL 17 (the server is 16)
        block = re.sub(r"^SET transaction_timeout\b.*?;[ \t]*$", "", block, flags=re.M)
        # psql-only meta-commands (\connect, \restrict, ...) are not valid SQL
        block = re.sub(r"^\\.*$", "", block, flags=re.M)
        # Make object owners match the user we are connecting as
        return re.sub(r"(OWNER TO )\w+;", rf"\1{owner};", block)

    return [("sql", clean(p[1])) if p[0] == "sql" else p for p in parts]


def restore(cfg: dict, dump_path: Path) -> None:
    log(f"Restoring {dump_path.name} ...")
    steps = prepare_dump(dump_path, cfg["user"])
    conn = connect(cfg)
    try:
        cur = conn.cursor()
        for step in steps:  # one transaction: either everything is restored or nothing
            if step[0] == "sql":
                # skip chunks that hold only blank lines / comments (psycopg2 rejects an "empty query")
                if any(ln.strip() and not ln.strip().startswith("--") for ln in step[1].splitlines()):
                    cur.execute(step[1])
            else:
                cur.copy_expert(step[1], io.StringIO(step[2]))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    log("Dump restored.")


def shift_dates(cfg: dict, tz_name: str) -> None:
    """Move all demo dates forward so the newest weather day is yesterday (in tz_name).
    Idempotent: if the data is already current the offset is 0 and nothing changes."""
    conn = connect(cfg)
    try:
        cur = conn.cursor()
        cur.execute("SELECT (now() AT TIME ZONE %s)::date", (tz_name,))
        today = cur.fetchone()[0]
        cur.execute("SELECT MAX(target_date) FROM public.weather")
        newest = cur.fetchone()[0]
        if newest is None:
            log("No weather data, skipping date shift.")
            return
        offset = (today - timedelta(days=1) - newest).days
        if offset <= 0:
            log(f"Dates already current (newest data day: {newest}). Nothing to shift.")
            return
        # The tables have unique constraints on their date columns (e.g. region_id + acq_date), so
        # a small shift would make rows collide with rows that have not moved yet. Hop every row far
        # away first, then back to its final position: rows never meet unmoved rows.
        for step in (HOP_DAYS, -(HOP_DAYS - offset)):
            cur.execute("UPDATE public.hotspot SET acq_date = acq_date + %s", (step,))
            cur.execute("UPDATE public.weather SET acq_date = acq_date + %(s)s, "
                        "target_date = target_date + %(s)s", {"s": step})
            cur.execute("UPDATE public.fire_prediction "
                        "SET forecast_timestamp = forecast_timestamp + make_interval(days => %s)", (step,))
        cur.execute("UPDATE public.weather SET is_forecast = (target_date > %s)", (today,))
        conn.commit()
        log(f"Shifted dates forward by {offset} day(s): newest data day {newest} -> {newest + timedelta(days=offset)}.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def summary(cfg: dict) -> None:
    conn = connect(cfg)
    try:
        cur = conn.cursor()
        parts = []
        for table in ("region", "hotspot", "weather", "fire_prediction"):
            cur.execute(sql.SQL("SELECT COUNT(*) FROM public.{}").format(sql.Identifier(table)))
            parts.append(f"{table}={cur.fetchone()[0]}")
        log("Row counts: " + ", ".join(parts))
    finally:
        conn.close()


# ----------------------------------------------------------------------------- main
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="wipe the public schema and restore the dump again")
    parser.add_argument("--no-shift", action="store_true", help="do not move dates forward")
    parser.add_argument("--dump", help="path to a .sql dump (default: newest data/dump-*.sql)")
    parser.add_argument("--wait", type=int, default=int(os.getenv("DB_WAIT_SECONDS", 90)),
                        help="seconds to wait for PostgreSQL to come up")
    args = parser.parse_args()

    cfg = load_config()
    tz_name = os.getenv("APP_TIMEZONE", "Asia/Jakarta")
    reset = args.reset or os.getenv("RESET_DB", "").lower() in ("1", "true", "yes")

    try:
        wait_for_server(cfg, args.wait)
        ensure_database(cfg)
        if reset:
            reset_schema(cfg)
        if is_initialised(cfg):
            log("Database already contains data, skipping restore.")
        else:
            restore(cfg, find_dump(args.dump))
        if not args.no_shift:
            shift_dates(cfg, tz_name)
        summary(cfg)
        return 0
    except Exception as exc:
        log(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())