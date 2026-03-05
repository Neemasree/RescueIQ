import os
import sys
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from sqlalchemy import text


def _mask_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.netloc:
        return "<invalid DATABASE_URL>"
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    db = parsed.path or ""
    return f"{parsed.scheme}://***@{host}{port}{db}"


def _warn_if_supabase_ssl_missing(url: str) -> None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    is_supabase = "supabase.co" in (parsed.hostname or "")
    has_sslmode = "sslmode" in query
    if is_supabase and not has_sslmode:
        print("[WARN] Supabase URL detected without sslmode query param.")
        print("[WARN] Consider appending '?sslmode=require' to DATABASE_URL if connection issues appear.")


def main() -> int:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        print("[FAIL] DATABASE_URL is not set.")
        return 1

    print(f"[INFO] Using DATABASE_URL: {_mask_url(database_url)}")
    _warn_if_supabase_ssl_missing(database_url)

    try:
        from models.session import engine

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        if result == 1:
            print("[PASS] Database connectivity OK (SELECT 1 returned 1).")
            return 0
        print(f"[FAIL] Unexpected DB response: {result}")
        return 2
    except Exception as exc:
        print(f"[FAIL] Database connectivity failed: {exc}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
