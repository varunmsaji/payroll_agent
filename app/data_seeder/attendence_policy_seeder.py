import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta


# ==========================================
# DATABASE CONNECTION
# ==========================================
DB_PARAMS = {
    "dbname": "hrms_db",
    "user": "varun",
    "password": "varun@123",
    "host": "localhost",
    "port": 5432,
}

def get_connection():
    return psycopg2.connect(**DB_PARAMS)


# ==========================================
# ATTENDANCE POLICY SEEDER
# ==========================================
def seed_attendance_policies():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("\n🚀 SEEDING ATTENDANCE POLICY HISTORY\n")

    policies = [
        {
            "late_grace_minutes": 10,
            "early_exit_grace_minutes": 10,
            "full_day_fraction": 0.75,
            "half_day_fraction": 0.5,
            "night_shift_enabled": True,
            "overtime_enabled": True,
            "created_at": datetime.now() - timedelta(days=180)
        },
        {
            "late_grace_minutes": 15,
            "early_exit_grace_minutes": 10,
            "full_day_fraction": 0.80,
            "half_day_fraction": 0.5,
            "night_shift_enabled": True,
            "overtime_enabled": True,
            "created_at": datetime.now() - timedelta(days=90)
        },
        {
            "late_grace_minutes": 5,
            "early_exit_grace_minutes": 5,
            "full_day_fraction": 0.85,
            "half_day_fraction": 0.6,
            "night_shift_enabled": False,
            "overtime_enabled": True,
            "created_at": datetime.now() - timedelta(days=30)
        },
        {
            "late_grace_minutes": 10,
            "early_exit_grace_minutes": 10,
            "full_day_fraction": 0.80,
            "half_day_fraction": 0.6,
            "night_shift_enabled": True,
            "overtime_enabled": False,
            "created_at": datetime.now()
        }
    ]

    for idx, p in enumerate(policies, start=1):
        cur.execute("""
            INSERT INTO attendance_policies (
                late_grace_minutes,
                early_exit_grace_minutes,
                full_day_fraction,
                half_day_fraction,
                night_shift_enabled,
                overtime_enabled,
                created_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            RETURNING *;
        """, (
            p["late_grace_minutes"],
            p["early_exit_grace_minutes"],
            p["full_day_fraction"],
            p["half_day_fraction"],
            p["night_shift_enabled"],
            p["overtime_enabled"],
            p["created_at"]
        ))

        row = cur.fetchone()
        print(f"✅ Policy {idx} inserted → Effective from {row['created_at']}")

    conn.commit()
    cur.close()
    conn.close()

    print("\n✅ ATTENDANCE POLICY MOCK DATA SEEDED SUCCESSFULLY\n")


# ==========================================
# RUN
# ==========================================
if __name__ == "__main__":
    seed_attendance_policies()
