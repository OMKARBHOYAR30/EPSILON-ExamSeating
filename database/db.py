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

    # Create performance indexes if missing
    conn.execute("CREATE INDEX IF NOT EXISTS idx_section_students_sec ON section_students(college, branch, semester, section, is_active)")
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

    # Seed sample section_students dataset if empty (includes dropped student gaps)
    cur = conn.execute("SELECT COUNT(*) AS c FROM section_students")
    if cur.fetchone()["c"] == 0:
        # CE - Sem 5 - Sec A (active roll numbers with gaps for dropped students)
        ce_rolls = [r for r in range(101, 140) if r not in (104, 107, 110, 115, 122)]
        for r in ce_rolls:
            conn.execute(
                """INSERT INTO section_students (college, program, branch, semester, section, roll_no, student_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("GHRCE", "B.Tech", "CE", "5", "A", f"CE-{r}", f"Student CE-{r}")
            )

        # IT - Sem 5 - Sec B (active roll numbers with gaps for dropped students)
        it_rolls = [r for r in range(201, 240) if r not in (203, 208, 214, 219, 225)]
        for r in it_rolls:
            conn.execute(
                """INSERT INTO section_students (college, program, branch, semester, section, roll_no, student_name)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("GHRCE", "B.Tech", "IT", "5", "B", f"IT-{r}", f"Student IT-{r}")
            )
        conn.commit()

    # Seed sample allocation if empty
    cur = conn.execute("SELECT COUNT(*) AS c FROM allocations")
    if cur.fetchone()["c"] == 0:
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        cur_alloc = conn.execute(
            """INSERT INTO allocations (
                room_no, block, used_capacity, rows, row_layout, bench_mode, exam_date, academic_year, exam_name,
                left_college, left_program, left_branch, left_semester, left_section,
                left_roll_prefix, left_roll_from, left_roll_to, left_entry_mode,
                right_college, right_program, right_branch, right_semester, right_section,
                right_roll_prefix, right_roll_from, right_roll_to, right_entry_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "A-101", "A", 30, 3, "10,10,10", "DOUBLE", tomorrow_str, "2026-2027", "CAE-I",
                "GHRCE", "B.Tech", "CE", "5", "A", "CE-", 101, 130, "dataset",
                "GHRCE", "B.Tech", "IT", "5", "B", "IT-", 201, 230, "dataset"
            )
        )
        alloc_id = cur_alloc.lastrowid
        # Fetch active rolls for CE Sec A and IT Sec B
        ce_active = [r["roll_no"] for r in conn.execute(
            "SELECT roll_no FROM section_students WHERE branch='CE' AND semester='5' AND section='A' ORDER BY id LIMIT 30"
        ).fetchall()]
        it_active = [r["roll_no"] for r in conn.execute(
            "SELECT roll_no FROM section_students WHERE branch='IT' AND semester='5' AND section='B' ORDER BY id LIMIT 30"
        ).fetchall()]

        for b in range(1, 31):
            l_s = ce_active[b - 1] if b <= len(ce_active) else ""
            r_s = it_active[b - 1] if b <= len(it_active) else ""
            conn.execute(
                """INSERT INTO seating_chart (allocation_id, bench_no, left_student, right_student, room_no)
                   VALUES (?, ?, ?, ?, ?)""",
                (alloc_id, b, l_s, r_s, "A-101")
            )
        conn.commit()

    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"EPSILON database initialized at: {DB_PATH}")
