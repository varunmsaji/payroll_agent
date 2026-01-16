import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UsQEjXLkuPQiVJyv@db.djdkwwalomqbecqajltr.supabase.co:5432/postgres'

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")


def get_connection():
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        sslmode="require",  # 🔴 REQUIRED for Supabase
    )
