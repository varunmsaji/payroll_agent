import psycopg2

conn = psycopg2.connect(
    "postgresql://postgres:UsQEjXLkuPQiVJyv@db.djdkwwalomqbecqajltr.supabase.co:5432/postgres",
    sslmode="require"
)

print("✅ Connected to Supabase")
conn.close()
