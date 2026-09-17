"""
modules/allocation_manager.py
------------------------------
Seating arrangement generation and allocation management module.
Supports Student Master Database, Open Elective (OE) Classroom Allocation, Cross-Room Duplicate Prevention, Manual Exam Date, Academic Year, and Exam Selection.
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
        """SELECT roll_no, student_name, branch, section, open_elective, is_active FROM section_students 
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


def get_oe_students(semester=None, open_elective="", limit=None, exam_date=None, exclude_allocated=True):
    """
    Retrieve active students enrolled in a specific Open Elective (OE) subject across ALL colleges, branches, and sections.
    If `semester` is provided, filters by semester; otherwise aggregates across all semesters.
    If `exam_date` is provided and `exclude_allocated=True`, excludes students already allocated on that date.
    """
    db = get_db()
    query = """SELECT roll_no, student_name, branch, section, open_elective, college, program, semester, is_active 
               FROM section_students 
               WHERE (open_elective = ? OR open_elective LIKE ?) AND is_active = 1"""
    params = [str(open_elective), f"%{str(open_elective)}%"]
    if semester and str(semester).strip():
        query += " AND semester = ?"
        params.append(str(semester).strip())

    query += " ORDER BY semester, branch, section, roll_no"
    rows = db.execute(query, params).fetchall()
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
        """SELECT a.id, a.room_no, a.block, a.used_capacity, a.bench_mode, a.exam_date, a.academic_year, a.exam_name, a.allocation_type, a.created_at,
                  a.left_college, a.left_branch, a.left_section, a.left_oe_subject,
                  a.right_college, a.right_branch, a.right_section, a.right_oe_subject
           FROM allocations a
           ORDER BY a.id DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    db.close()
    return [dict(a) for a in allocations]


def get_allocation_paper_count_breakdown(allocation_id):
    """
    Calculates the exact count of question papers required per subject/OE subject for a room allocation.
    Returns list of dicts: [{'subject': 'Industry 4.0', 'count': 10}, ...]
    """
    db = get_db()
    allocation = db.execute("SELECT * FROM allocations WHERE id = ?", (allocation_id,)).fetchone()
    if not allocation:
        db.close()
        return []

    chart_rows = db.execute(
        "SELECT left_student, right_student FROM seating_chart WHERE allocation_id = ?",
        (allocation_id,)
    ).fetchall()

    rolls = []
    for r in chart_rows:
        if r["left_student"] and r["left_student"].strip():
            rolls.append(r["left_student"].strip())
        if r["right_student"] and r["right_student"].strip():
            rolls.append(r["right_student"].strip())

    if not rolls:
        db.close()
        return []

    placeholders = ",".join(["?"] * len(rolls))
    students = db.execute(
        f"SELECT roll_no, branch, open_elective FROM section_students WHERE roll_no IN ({placeholders})",
        rolls
    ).fetchall()

    student_map = {s["roll_no"]: s for s in students}
    subject_counts = {}

    is_oe_alloc = allocation["allocation_type"] == "OE"
    left_oe_sub = allocation["left_oe_subject"]
    right_oe_sub = allocation["right_oe_subject"]

    for r_no in rolls:
        stud = student_map.get(r_no)
        sub = ""

        if stud:
            if is_oe_alloc and stud["open_elective"]:
                sub = stud["open_elective"].strip()
            elif stud["open_elective"]:
                sub = stud["open_elective"].strip()
            else:
                sub = f"{stud['branch']} Paper"

        if not sub:
            if is_oe_alloc:
                sub = left_oe_sub or right_oe_sub or "OE Subject"
            else:
                sub = allocation["left_branch"] or "Regular Exam Paper"

        subject_counts[sub] = subject_counts.get(sub, 0) + 1

    db.close()

    result = [{"subject": k, "count": v} for k, v in subject_counts.items()]
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


def get_allocation_by_id(allocation_id):
    """Fetch allocation detail with its seating chart and paper count breakdown."""
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
    alloc_dict["paper_counts"] = get_allocation_paper_count_breakdown(allocation_id)
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
    Supports both Section Allocation and Open Elective (OE) Classroom Allocation.
    """
    room_no = data.get("room_no")
    block = data.get("block")
    bench_mode = data.get("bench_mode", "DOUBLE")  # DOUBLE or SINGLE
    allocation_type = data.get("allocation_type", "SECTION")  # 'SECTION' or 'OE'
    
    # Academic Year & Exam Selection
    academic_year = data.get("academic_year", "2026-2027").strip() or "2026-2027"
    exam_name = data.get("exam_name", "CAE-I").strip() or "CAE-I"

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
    left_oe_subject = data.get("left_oe_subject", "").strip()
    left_entry_mode = data.get("left_entry_mode", "dataset")

    left_students = []
    left_roll_prefix = ""
    left_roll_from = 0
    left_roll_to = 0

    if left_entry_mode == "oe":
        count = int(data.get("left_dataset_count", total_benches))
        student_rows = get_oe_students(left_semester, left_oe_subject, limit=count, exam_date=exam_date, exclude_allocated=True)
        left_students = [s["roll_no"] for s in student_rows]
        left_roll_prefix = f"OE-{left_oe_subject}"
        left_roll_from = 1
        left_roll_to = len(left_students)
        if not left_branch:
            left_branch = f"OE ({left_oe_subject})"
        if not left_section:
            left_section = "ALL"
    elif left_entry_mode == "dataset":
        count = int(data.get("left_dataset_count", total_benches))
        student_rows = get_section_students(left_branch, left_semester, left_section, count, college=left_college, exam_date=exam_date, exclude_allocated=True)
        left_students = [s["roll_no"] for s in student_rows]
        left_roll_prefix = "MASTER-DB"
        left_roll_from = 1
        left_roll_to = len(left_students)
    elif left_entry_mode == "manual":
        raw_manual = data.get("left_manual_rolls", "")
        parsed = [r.strip() for r in raw_manual.replace("\n", ",").split(",") if r.strip()]
        left_students = [r for r in parsed if r not in already_allocated_rolls]
        left_roll_prefix = "MANUAL"
        left_roll_from = 1
        left_roll_to = len(left_students)
    else:
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
    right_oe_subject = ""
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
        right_oe_subject = data.get("right_oe_subject", "").strip()
        right_entry_mode = data.get("right_entry_mode", "dataset")

        if right_entry_mode == "oe":
            r_count = int(data.get("right_dataset_count", total_benches))
            r_student_rows = get_oe_students(right_semester, right_oe_subject, limit=r_count, exam_date=exam_date, exclude_allocated=True)
            right_students = [s["roll_no"] for s in r_student_rows if s["roll_no"] not in already_allocated_rolls]
            right_roll_prefix = f"OE-{right_oe_subject}"
            right_roll_from = 1
            right_roll_to = len(right_students)
            if not right_branch:
                right_branch = f"OE ({right_oe_subject})"
            if not right_section:
                right_section = "ALL"
        elif right_entry_mode == "dataset":
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
            room_no, block, used_capacity, rows, row_layout, bench_mode, exam_date, academic_year, exam_name, allocation_type,
            left_college, left_program, left_branch, left_semester, left_section, left_oe_subject,
            left_roll_prefix, left_roll_from, left_roll_to, left_entry_mode,
            right_college, right_program, right_branch, right_semester, right_section, right_oe_subject,
            right_roll_prefix, right_roll_from, right_roll_to, right_entry_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            room_no, block, used_capacity, rows, row_layout, bench_mode, exam_date, academic_year, exam_name, allocation_type,
            left_college, left_program, left_branch, left_semester, left_section, left_oe_subject,
            left_roll_prefix, left_roll_from, left_roll_to, left_entry_mode,
            right_college, right_program, right_branch, right_semester, right_section, right_oe_subject,
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

    # Populate bench-wise seating chart (with optional CA Anti-Cheating row staggering)
    ca_stagger = data.get("ca_anti_cheating") in ("1", "true", True, 1) or exam_name in ("CAE-I", "CAE-II")
    bench_counter = 1

    for row_idx, bench_count in enumerate(benches_per_row):
        is_even_row = (row_idx % 2 == 1)
        for _ in range(bench_count):
            b = bench_counter
            l_stud = left_students[b - 1] if b <= len(left_students) else ""
            r_stud = right_students[b - 1] if (bench_mode == "DOUBLE" and b <= len(right_students)) else ""

            if ca_stagger and is_even_row and bench_mode == "DOUBLE":
                l_stud, r_stud = r_stud, l_stud

            db.execute(
                """INSERT INTO seating_chart (allocation_id, bench_no, left_student, right_student, room_no)
                   VALUES (?, ?, ?, ?, ?)""",
                (allocation_id, b, l_stud, r_stud, room_no)
            )
            bench_counter += 1

    db.commit()
    db.close()

    return True, f"Seating arrangement for Room {room_no} generated successfully for {exam_name} ({academic_year})!", allocation_id


def auto_generate_multi_room_seating(data):
    """
    Automatically distributes unallocated students across multiple classrooms for a dataset (SECTION or OE).
    Fills room by room until all students are seated or available rooms are exhausted.
    """
    allocation_type = data.get("allocation_type", "SECTION")
    bench_mode = data.get("bench_mode", "DOUBLE")
    academic_year = data.get("academic_year", "2026-2027").strip() or "2026-2027"
    exam_name = data.get("exam_name", "CAE-I").strip() or "CAE-I"
    exam_date = data.get("exam_date", "").strip() or datetime.now().strftime("%Y-%m-%d")

    # Get room list
    room_nos = data.get("selected_rooms", [])
    if isinstance(room_nos, str):
        room_nos = [r.strip() for r in room_nos.split(",") if r.strip()]

    if not room_nos:
        # Fallback to all rooms in block if block provided
        block = data.get("block", "").strip()
        db = get_db()
        if block:
            rooms_db = db.execute("SELECT room_no FROM classrooms WHERE block = ? ORDER BY room_no", (block,)).fetchall()
        else:
            rooms_db = db.execute("SELECT room_no FROM classrooms ORDER BY block, room_no").fetchall()
        db.close()
        room_nos = [r["room_no"] for r in rooms_db]

    if not room_nos:
        return False, "No classrooms selected for auto-allocation.", []

    already_allocated_rolls = get_allocated_students_by_date(exam_date)

    # Fetch Left Group Students
    left_college = data.get("left_college", "GHRCE")
    left_program = data.get("left_program", "B.Tech")
    left_branch = data.get("left_branch", "")
    left_semester = data.get("left_semester", "")
    left_section = data.get("left_section", "")
    left_oe_subject = data.get("left_oe_subject", "").strip()
    left_entry_mode = data.get("left_entry_mode", "dataset")

    if allocation_type == "OE" or left_entry_mode == "oe" or (left_oe_subject and not left_branch):
        left_entry_mode = "oe"

    if left_entry_mode == "oe":
        left_student_rows = get_oe_students(left_semester, left_oe_subject, exam_date=exam_date, exclude_allocated=True)
        left_students = [s["roll_no"] for s in left_student_rows]
        left_roll_prefix = f"OE-{left_oe_subject}"
        if not left_branch:
            left_branch = f"OE ({left_oe_subject})"
        if not left_section:
            left_section = "ALL"
    else:
        left_student_rows = get_section_students(left_branch, left_semester, left_section, college=left_college, exam_date=exam_date, exclude_allocated=True)
        left_students = [s["roll_no"] for s in left_student_rows]
        left_roll_prefix = "MASTER-DB"

    # Fetch Right Group Students (if DOUBLE mode)
    right_college = data.get("right_college", "GHRCE")
    right_program = data.get("right_program", "B.Tech")
    right_branch = data.get("right_branch", "")
    right_semester = data.get("right_semester", "")
    right_section = data.get("right_section", "")
    right_oe_subject = data.get("right_oe_subject", "").strip()
    right_entry_mode = data.get("right_entry_mode", "dataset")
    right_students = []
    right_roll_prefix = ""

    if allocation_type == "OE" or right_entry_mode == "oe" or (right_oe_subject and not right_branch):
        right_entry_mode = "oe"

    if bench_mode == "DOUBLE":
        if right_entry_mode == "oe":
            right_student_rows = get_oe_students(right_semester, right_oe_subject, exam_date=exam_date, exclude_allocated=True)
            right_students = [s["roll_no"] for s in right_student_rows if s["roll_no"] not in left_students]
            right_roll_prefix = f"OE-{right_oe_subject}"
            if not right_branch:
                right_branch = f"OE ({right_oe_subject})"
            if not right_section:
                right_section = "ALL"
        else:
            right_student_rows = get_section_students(right_branch, right_semester, right_section, college=right_college, exam_date=exam_date, exclude_allocated=True)
            right_students = [s["roll_no"] for s in right_student_rows if s["roll_no"] not in left_students]
            right_roll_prefix = "MASTER-DB"

    if not left_students and not right_students:
        return False, "No unallocated students found for the selected section/OE dataset on this exam date.", []

    total_left_to_seat = len(left_students)
    total_right_to_seat = len(right_students)

    created_allocations = []
    db = get_db()

    left_idx = 0
    right_idx = 0

    for r_no in room_nos:
        if left_idx >= len(left_students) and (bench_mode == "SINGLE" or right_idx >= len(right_students)):
            break

        room = db.execute("SELECT * FROM classrooms WHERE room_no = ?", (r_no,)).fetchone()
        if not room:
            continue

        rows, capacity, benches_per_row = parse_row_layout(room["default_row_layout"])
        total_benches = sum(benches_per_row)
        block = room["block"]

        # Chunk for room
        r_left_chunk = left_students[left_idx : left_idx + total_benches]
        left_idx += len(r_left_chunk)

        r_right_chunk = []
        if bench_mode == "DOUBLE":
            r_right_chunk = right_students[right_idx : right_idx + total_benches]
            right_idx += len(r_right_chunk)

        if not r_left_chunk and not r_right_chunk:
            continue

        used_cap = max(len(r_left_chunk), len(r_right_chunk))

        cur = db.execute(
            """INSERT INTO allocations (
                room_no, block, used_capacity, rows, row_layout, bench_mode, exam_date, academic_year, exam_name, allocation_type,
                left_college, left_program, left_branch, left_semester, left_section, left_oe_subject,
                left_roll_prefix, left_roll_from, left_roll_to, left_entry_mode,
                right_college, right_program, right_branch, right_semester, right_section, right_oe_subject,
                right_roll_prefix, right_roll_from, right_roll_to, right_entry_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                r_no, block, used_cap, rows, room["default_row_layout"], bench_mode, exam_date, academic_year, exam_name, allocation_type,
                left_college, left_program, left_branch, left_semester, left_section, left_oe_subject,
                left_roll_prefix, 1, len(r_left_chunk), left_entry_mode,
                right_college, right_program, right_branch, right_semester, right_section, right_oe_subject,
                right_roll_prefix, 1, len(r_right_chunk), right_entry_mode
            )
        )
        alloc_id = cur.lastrowid
        created_allocations.append(alloc_id)

        for s_roll in r_left_chunk:
            db.execute("INSERT INTO manual_rolls (allocation_id, side, roll_no) VALUES (?, 'LEFT', ?)", (alloc_id, s_roll))
        for s_roll in r_right_chunk:
            db.execute("INSERT INTO manual_rolls (allocation_id, side, roll_no) VALUES (?, 'RIGHT', ?)", (alloc_id, s_roll))

        ca_stagger = data.get("ca_anti_cheating") in ("1", "true", True, 1) or exam_name in ("CAE-I", "CAE-II")
        bench_counter = 1

        for row_idx, bench_count in enumerate(benches_per_row):
            is_even_row = (row_idx % 2 == 1)
            for _ in range(bench_count):
                b = bench_counter
                l_stud = r_left_chunk[b - 1] if b <= len(r_left_chunk) else ""
                r_stud = r_right_chunk[b - 1] if (bench_mode == "DOUBLE" and b <= len(r_right_chunk)) else ""

                if ca_stagger and is_even_row and bench_mode == "DOUBLE":
                    l_stud, r_stud = r_stud, l_stud

                db.execute(
                    """INSERT INTO seating_chart (allocation_id, bench_no, left_student, right_student, room_no)
                       VALUES (?, ?, ?, ?, ?)""",
                    (alloc_id, b, l_stud, r_stud, r_no)
                )
                bench_counter += 1

    db.commit()
    db.close()

    total_seated_left = min(left_idx, total_left_to_seat)
    total_seated_right = min(right_idx, total_right_to_seat)
    summary_msg = f"Auto-allocated {total_seated_left + total_seated_right} students across {len(created_allocations)} rooms for {exam_name} ({exam_date})!"

    return True, summary_msg, created_allocations
