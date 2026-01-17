"""
Export PostgreSQL table data into pure INSERT SQL.
Safe to run on Supabase.

Schema must already exist.
"""

import psycopg2
import json
from datetime import date, datetime

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

DB_CONFIG ={
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}

OUTPUT_FILE = "hrms_data.sql"

EXCLUDED_TABLES = {
    "schema_migrations",
}

# --------------------------------------------------
# SQL VALUE CONVERTER
# --------------------------------------------------

def sql_value(v):
    if v is None:
        return "NULL"

    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"

    if isinstance(v, (int, float)):
        return str(v)

    if isinstance(v, (date, datetime)):
        return f"'{v.isoformat()}'"

    if isinstance(v, dict):
        dumped = json.dumps(v)
        dumped = dumped.replace("'", "''")
        return f"'{dumped}'::jsonb"

    if isinstance(v, list):
        dumped = json.dumps(v)
        dumped = dumped.replace("'", "''")
        return f"'{dumped}'"

    # string fallback
    s = str(v)
    s = s.replace("'", "''")
    return f"'{s}'"


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)

    tables = [
        r[0]
        for r in cur.fetchall()
        if r[0] not in EXCLUDED_TABLES
    ]

    sql = [
        "-- ================================================",
        "-- HRMS DATA EXPORT",
        "-- Generated from local PostgreSQL",
        "-- ================================================",
        "",
        "BEGIN;",
        "SET session_replication_role = replica;",
        "",
    ]

    for table in tables:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position;
        """, (table,))

        columns = [r[0] for r in cur.fetchall()]

        cur.execute(f"SELECT * FROM {table};")
        rows = cur.fetchall()

        if not rows:
            continue

        sql.append(f"-- -----------------------------")
        sql.append(f"-- Table: {table}")
        sql.append(f"-- -----------------------------")

        col_list = ", ".join(columns)

        for row in rows:
            values = ", ".join(sql_value(v) for v in row)
            sql.append(
                f"INSERT INTO {table} ({col_list}) VALUES ({values});"
            )

        sql.append("")

    sql.extend([
        "SET session_replication_role = DEFAULT;",
        "COMMIT;",
        "",
        "-- ================================================",
        "-- END OF DATA EXPORT",
        "-- ================================================",
    ])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sql))

    cur.close()
    conn.close()

    print(f"✅ Data exported successfully → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
