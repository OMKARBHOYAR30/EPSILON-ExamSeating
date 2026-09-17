"""
database/db.py
----------------
SQLite Connection Manager, Auto-Migrator and Seed Initializer for EPSILON
"""

import os
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "college.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_db():
    """Return a sqlite3 connection with Row factory enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize SQLite database tables, run migrations and seed sample datasets."""
    conn = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    # Migration: Add missing columns to section_students table
    cur = conn.execute("PRAGMA table_info(section_students)")
    sec_cols = [col["name"] for col in cur.fetchall()]
    if "open_elective" not in sec_cols:
        conn.execute("ALTER TABLE section_students ADD COLUMN open_elective TEXT DEFAULT ''")
        conn.commit()

    # Migration: Add missing columns to allocations table
    cur = conn.execute("PRAGMA table_info(allocations)")
    cols = [col["name"] for col in cur.fetchall()]
    if "exam_date" not in cols:
        conn.execute("ALTER TABLE allocations ADD COLUMN exam_date TEXT NOT NULL DEFAULT (date('now'))")
        conn.commit()
    if "academic_year" not in cols:
        conn.execute("ALTER TABLE allocations ADD COLUMN academic_year TEXT NOT NULL DEFAULT '2026-2027'")
        conn.commit()
    if "exam_name" not in cols:
        conn.execute("ALTER TABLE allocations ADD COLUMN exam_name TEXT NOT NULL DEFAULT 'CAE-I'")
        conn.commit()
    if "allocation_type" not in cols:
        conn.execute("ALTER TABLE allocations ADD COLUMN allocation_type TEXT NOT NULL DEFAULT 'SECTION'")
        conn.commit()
    if "left_oe_subject" not in cols:
        conn.execute("ALTER TABLE allocations ADD COLUMN left_oe_subject TEXT DEFAULT ''")
        conn.commit()
    if "right_oe_subject" not in cols:
        conn.execute("ALTER TABLE allocations ADD COLUMN right_oe_subject TEXT DEFAULT ''")
        conn.commit()

    # Create performance indexes after column migrations
    conn.execute("CREATE INDEX IF NOT EXISTS idx_section_students_sec ON section_students(college, branch, semester, section, is_active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_section_students_oe ON section_students(semester, open_elective, is_active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_section_students_roll ON section_students(roll_no)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_allocations_date ON allocations(exam_date, room_no)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_seating_chart_alloc ON seating_chart(allocation_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_seating_chart_left ON seating_chart(left_student)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_seating_chart_right ON seating_chart(right_student)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_manual_rolls_alloc ON manual_rolls(allocation_id, roll_no)")
    conn.commit()

    # Seed default HOST1 account if users table is empty
    cur = conn.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            ("HOST1", generate_password_hash("admin123"), "HOST1 / Admin", "Admin"),
        )
        conn.commit()

    # Seed sample classrooms if empty
    cur = conn.execute("SELECT COUNT(*) AS c FROM classrooms")
    if cur.fetchone()["c"] == 0:
        sample_rooms = [
            ("A", "A-101", 30, 3, "10,10,10"),
            ("A", "A-102", 29, 3, "10,9,10"),
            ("B", "B-201", 24, 3, "8,8,8"),
            ("B", "B-202", 24, 3, "8,8,8"),
            ("C", "C-301", 30, 3, "10,10,10"),
        ]
        for block, room_no, cap, rows, layout in sample_rooms:
            conn.execute(
                """INSERT INTO classrooms (block, room_no, default_capacity, default_rows, default_row_layout)
                   VALUES (?, ?, ?, ?, ?)""",
                (block, room_no, cap, rows, layout)
            )
        conn.commit()

    conn.close()


def reset_database_data():
    """Wipe all student master records, seating allocations, and seating charts."""
    conn = get_db()
    conn.execute("DELETE FROM section_students")
    conn.execute("DELETE FROM allocations")
    conn.execute("DELETE FROM seating_chart")
    conn.execute("DELETE FROM manual_rolls")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"EPSILON database initialized at: {DB_PATH}")
