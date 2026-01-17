import os
import psycopg2
from psycopg2.extras import RealDictCursor

# --------------------------------------------------
# DATABASE CONFIG
# --------------------------------------------------

DATABASE_URL = DATABASE_URL = 'postgresql://postgres:t3dPZJwoCApEGgBU@db.fmhhqmmntpnxxqvnffej.supabase.co:5432/postgres'


if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Use .env or export DATABASE_URL before running."
    )

# --------------------------------------------------
# CONNECTION FACTORY
# --------------------------------------------------

def get_connection():
    """
    Returns a psycopg2 connection.
    - Uses SSL automatically for Supabase
    - Uses plain connection for local Postgres
    """
    use_ssl = "supabase.co" in DATABASE_URL

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        sslmode="require" if use_ssl else "disable",
    )
