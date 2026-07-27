"""
modules/allocation_manager.py
------------------------------
Seating arrangement generation and allocation management module.
Supports Student Master Database, Cross-Room Duplicate Allocation Prevention, and Manual Exam Date selection.
"""

from datetime import datetime
from database.db import get_db
from modules.room_manager import parse_row_layout


def get_available_sections():
    """Retrieve unique section datasets available in section_students."""
    db = get_db()
    rows = db.execute(
        """SELECT DISTINCT college, program, branch, semester, section,
                  COUNT(*) as total_count,
                  SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count
           FROM section_students 
           WHERE is_active = 1
           GROUP BY college, program, branch, semester, section
           ORDER BY college, branch, semester, section"""
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_allocated_students_by_date(exam_date):
    """Retrieve set of roll numbers already allocated in any room for a specific exam date."""
    if not exam_date:
        return set()

    db = get_db()
    rows = db.execute(
        """SELECT s.left_student, s.right_student 
           FROM seating_chart s
           JOIN allocations a ON s.allocation_id = a.id
           WHERE a.exam_date = ?""",
        (exam_date,)
    ).fetchall()
    db.close()

    allocated = set()
    for r in rows:
        if r["left_student"] and r["left_student"].strip():
            allocated.add(r["left_student"].strip())
        if r["right_student"] and r["right_student"].strip():
            allocated.add(r["right_student"].strip())
    return allocated


def get_section_students(branch, semester, section, limit=None, college="GHRCE", exam_date=None, exclude_allocated=True):
    """
    Retrieve active student roll numbers for a specific class section.
    If `exam_date` is provided and `exclude_allocated=True`, excludes students already allocated on that date.
    """
    db = get_db()
    rows = db.execute(
        """SELECT roll_no, student_name, is_active FROM section_students 
           WHERE branch = ? AND semester = ? AND section = ? AND is_active = 1 
           ORDER BY id""",
        (branch, semester, section)
    ).fetchall()
    db.close()

    all_students = [dict(r) for r in rows]

    if exam_date and exclude_allocated:
        allocated_rolls = get_allocated_students_by_date(exam_date)
        filtered = [s for s in all_students if s["roll_no"] not in allocated_rolls]
    else:
        filtered = all_students

    if limit and int(limit) > 0:
        filtered = filtered[:int(limit)]

    return filtered


def check_existing_allocation(room_no, exam_date=None):
    """Check if room already has an active seating allocation (optionally for exam_date)."""
    db = get_db()
    if exam_date:
        existing = db.execute(
            "SELECT id, room_no, block, exam_date, created_at FROM allocations WHERE room_no = ? AND exam_date = ? ORDER BY id DESC LIMIT 1",
            (room_no, exam_date)
        ).fetchone()
    else:
        existing = db.execute(
            "SELECT id, room_no, block, exam_date, created_at FROM allocations WHERE room_no = ? ORDER BY id DESC LIMIT 1",
            (room_no,)
        ).fetchone()
    db.close()
    return dict(existing) if existing else None


def get_all_allocations():
    """Retrieve all saved allocations ordered by exam_date / ID descending."""
    db = get_db()
    allocations = db.execute(
        """SELECT a.*, c.block 
           FROM allocations a
           LEFT JOIN classrooms c ON a.room_no = c.room_no
           ORDER BY a.exam_date DESC, a.id DESC"""
    ).fetchall()
    db.close()
    return [dict(a) for a in allocations]


def get_recent_allocations(limit=5):
    """Retrieve recent allocations for dashboard view."""
    db = get_db()
    allocations = db.execute(
        """SELECT a.id, a.room_no, a.block, a.used_capacity, a.bench_mode, a.exam_date, a.created_at,
                  a.left_college, a.left_branch, a.left_section,
                  a.right_college, a.right_branch, a.right_section
           FROM allocations a
           ORDER BY a.id DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    db.close()
    return [dict(a) for a in allocations]


def get_allocation_by_id(allocation_id):
    """Fetch allocation detail with its seating chart."""
    db = get_db()
    allocation = db.execute("SELECT * FROM allocations WHERE id = ?", (allocation_id,)).fetchone()
    if not allocation:
        db.close()
        return None

    alloc_dict = dict(allocation)
    chart_rows = db.execute(
        "SELECT bench_no, left_student, right_student FROM seating_chart WHERE allocation_id = ? ORDER BY bench_no",
        (allocation_id,)
    ).fetchall()
    db.close()

    alloc_dict["seating_chart"] = [dict(c) for c in chart_rows]
    return alloc_dict


def delete_allocation(allocation_id):
    """Delete an allocation and its seating chart entries."""
    db = get_db()
    cur = db.execute("DELETE FROM allocations WHERE id = ?", (allocation_id,))
    db.commit()
    affected = cur.rowcount > 0
    db.close()
    return affected, "Allocation deleted successfully." if affected else "Allocation not found."


def create_seating_allocation(data):
    """
    Creates a new seating allocation and populates bench-by-bench seating chart.
    `data` dictionary contains all form fields including exam_date.
    Automatically prevents duplicate allocations across rooms on the same exam date.
    """
    room_no = data.get("room_no")
    block = data.get("block")
    bench_mode = data.get("bench_mode", "DOUBLE")  # DOUBLE or SINGLE
    
    # Manual Exam Date selection
    exam_date = data.get("exam_date", "").strip()
    if not exam_date:
        exam_date = datetime.now().strftime("%Y-%m-%d")

    # Retrieve existing allocated students for this exam date to prevent cross-room duplicate allocation
    already_allocated_rolls = get_allocated_students_by_date(exam_date)

    # Get room details to extract row_layout
    db = get_db()
    room = db.execute("SELECT * FROM classrooms WHERE room_no = ?", (room_no,)).fetchone()
    if not room:
        db.close()
        return False, "Selected room does not exist.", None

    row_layout = room["default_row_layout"]
    rows, capacity, benches_per_row = parse_row_layout(row_layout)
    total_benches = sum(benches_per_row)

    # Left Group processing
    left_college = data.get("left_college", "GHRCE")
    left_program = data.get("left_program", "B.Tech")
    left_branch = data.get("left_branch", "")
    left_semester = data.get("left_semester", "")
    left_section = data.get("left_section", "")
    left_entry_mode = data.get("left_entry_mode", "dataset")

    left_students = []
    left_roll_prefix = ""
    left_roll_from = 0
    left_roll_to = 0

    if left_entry_mode == "dataset":
        count = int(data.get("left_dataset_count", total_benches))
        student_rows = get_section_students(left_branch, left_semester, left_section, count, college=left_college, exam_date=exam_date, exclude_allocated=True)
        left_students = [s["roll_no"] for s in student_rows]
        left_roll_prefix = "MASTER-DB"
        left_roll_from = 1
        left_roll_to = len(left_students)
    elif left_entry_mode == "manual":
        raw_manual = data.get("left_manual_rolls", "")
        parsed = [r.strip() for r in raw_manual.replace("\n", ",").split(",") if r.strip()]
        # Exclude already allocated roll numbers for cross-room duplicate prevention
        left_students = [r for r in parsed if r not in already_allocated_rolls]
        left_roll_prefix = "MANUAL"
        left_roll_from = 1
        left_roll_to = len(left_students)
    else:
        # Fallback auto range
        left_roll_prefix = data.get("left_roll_prefix", "")
        left_roll_from = int(data.get("left_roll_from", 1))
        left_roll_to = int(data.get("left_roll_to", total_benches))
        raw_auto = [f"{left_roll_prefix}{i}" for i in range(left_roll_from, left_roll_to + 1)]
        left_students = [r for r in raw_auto if r not in already_allocated_rolls]

    # Update set of allocated rolls for right side check within same room
    for r in left_students:
        already_allocated_rolls.add(r)

    # Right Group processing
    right_college = ""
    right_program = ""
    right_branch = ""
    right_semester = ""
    right_section = ""
    right_roll_prefix = ""
    right_roll_from = 0
    right_roll_to = 0
    right_entry_mode = "dataset"
    right_students = []

    if bench_mode == "DOUBLE":
        right_college = data.get("right_college", "GHRCE")
        right_program = data.get("right_program", "B.Tech")
        right_branch = data.get("right_branch", "")
        right_semester = data.get("right_semester", "")
        right_section = data.get("right_section", "")
        right_entry_mode = data.get("right_entry_mode", "dataset")

        if right_entry_mode == "dataset":
            r_count = int(data.get("right_dataset_count", total_benches))
            r_student_rows = get_section_students(right_branch, right_semester, right_section, r_count, college=right_college, exam_date=exam_date, exclude_allocated=True)
            right_students = [s["roll_no"] for s in r_student_rows if s["roll_no"] not in already_allocated_rolls]
            right_roll_prefix = "MASTER-DB"
            right_roll_from = 1
            right_roll_to = len(right_students)
        elif right_entry_mode == "manual":
            raw_manual_r = data.get("right_manual_rolls", "")
            parsed_r = [r.strip() for r in raw_manual_r.replace("\n", ",").split(",") if r.strip()]
            right_students = [r for r in parsed_r if r not in already_allocated_rolls]
            right_roll_prefix = "MANUAL"
            right_roll_from = 1
            right_roll_to = len(right_students)
        else:
            right_roll_prefix = data.get("right_roll_prefix", "")
            right_roll_from = int(data.get("right_roll_from", 1))
            right_roll_to = int(data.get("right_roll_to", total_benches))
            raw_auto_r = [f"{right_roll_prefix}{i}" for i in range(right_roll_from, right_roll_to + 1)]
            right_students = [r for r in raw_auto_r if r not in already_allocated_rolls]

    used_capacity = max(len(left_students), len(right_students))
    if used_capacity > total_benches:
        used_capacity = total_benches

    # Insert into allocations table
    cur = db.execute(
        """INSERT INTO allocations (
            room_no, block, used_capacity, rows, row_layout, bench_mode, exam_date,
            left_college, left_program, left_branch, left_semester, left_section,
            left_roll_prefix, left_roll_from, left_roll_to, left_entry_mode,
            right_college, right_program, right_branch, right_semester, right_section,
            right_roll_prefix, right_roll_from, right_roll_to, right_entry_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            room_no, block, used_capacity, rows, row_layout, bench_mode, exam_date,
            left_college, left_program, left_branch, left_semester, left_section,
            left_roll_prefix, left_roll_from, left_roll_to, left_entry_mode,
            right_college, right_program, right_branch, right_semester, right_section,
            right_roll_prefix, right_roll_from, right_roll_to, right_entry_mode
        )
    )
    allocation_id = cur.lastrowid

    # Save manual roll numbers if any
    for r in left_students:
        db.execute("INSERT INTO manual_rolls (allocation_id, side, roll_no) VALUES (?, 'LEFT', ?)", (allocation_id, r))
    if bench_mode == "DOUBLE":
        for r in right_students:
            db.execute("INSERT INTO manual_rolls (allocation_id, side, roll_no) VALUES (?, 'RIGHT', ?)", (allocation_id, r))

    # Populate bench-wise seating chart
    for b in range(1, total_benches + 1):
        l_stud = left_students[b - 1] if b <= len(left_students) else ""
        r_stud = right_students[b - 1] if (bench_mode == "DOUBLE" and b <= len(right_students)) else ""
        db.execute(
            """INSERT INTO seating_chart (allocation_id, bench_no, left_student, right_student, room_no)
               VALUES (?, ?, ?, ?, ?)""",
            (allocation_id, b, l_stud, r_stud, room_no)
        )

    db.commit()
    db.close()

    return True, f"Seating arrangement for Room {room_no} generated successfully for Exam Date: {exam_date}! (Duplicate student allocations prevented)", allocation_id
