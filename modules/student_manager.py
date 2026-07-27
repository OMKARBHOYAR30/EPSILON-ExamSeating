"""
modules/student_manager.py
---------------------------
Student Master Database Management logic for EPSILON.
Supports:
- Bulk paste / manual typing of roll numbers
- Excel (.xlsx, .xls) and CSV importing
- Single student record creation, modification, deletion
- Active/Inactive status toggling (dropped / left college)
- Dynamic filtering and searching by College, Branch, Semester, Section, Keyword
"""

import csv
import io
from database.db import get_db

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def get_all_student_sections():
    """Retrieve summary of all section datasets registered in the system."""
    db = get_db()
    sections = db.execute(
        """SELECT college, program, branch, semester, section,
                  COUNT(*) as student_count,
                  SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count,
                  SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive_count,
                  MIN(roll_no) as roll_from, MAX(roll_no) as roll_to
           FROM section_students 
           GROUP BY college, program, branch, semester, section
           ORDER BY college, branch, semester, section"""
    ).fetchall()
    db.close()
    return [dict(s) for s in sections]


def get_students_filtered(college=None, branch=None, semester=None, section=None, search=None, is_active=None):
    """Retrieve student records based on search filters."""
    db = get_db()
    query = "SELECT * FROM section_students WHERE 1=1"
    params = []

    if college:
        query += " AND college = ?"
        params.append(college)
    if branch:
        query += " AND branch = ?"
        params.append(branch)
    if semester:
        query += " AND semester = ?"
        params.append(semester)
    if section:
        query += " AND section = ?"
        params.append(section)
    if is_active is not None and is_active != "":
        query += " AND is_active = ?"
        params.append(int(is_active))
    if search:
        query += " AND (roll_no LIKE ? OR student_name LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term])

    query += " ORDER BY college, branch, semester, section, roll_no"
    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_students_for_section(branch, semester, section, college="GHRCE"):
    """Fetch all active students registered for a section."""
    db = get_db()
    students = db.execute(
        """SELECT * FROM section_students 
           WHERE branch = ? AND semester = ? AND section = ? AND is_active = 1
           ORDER BY id""",
        (branch, semester, section)
    ).fetchall()
    db.close()
    return [dict(s) for s in students]


def add_single_student(college, program, branch, semester, section, roll_no, student_name, is_active=1):
    """Adds a single student record to the Master Database."""
    college = (college or "GHRCE").strip()
    program = (program or "B.Tech").strip()
    branch = (branch or "").strip().upper()
    semester = (semester or "").strip()
    section = (section or "").strip().upper()
    roll_no = (roll_no or "").strip()
    student_name = (student_name or f"Student {roll_no}").strip()

    if not branch or not semester or not section or not roll_no:
        return False, "Branch, Semester, Section, and Roll Number are required."

    db = get_db()
    # Check if student roll number exists in the same section
    existing = db.execute(
        """SELECT id FROM section_students 
           WHERE college = ? AND branch = ? AND semester = ? AND section = ? AND roll_no = ?""",
        (college, branch, semester, section, roll_no)
    ).fetchone()

    if existing:
        db.close()
        return False, f"Student Roll No '{roll_no}' already exists in {branch} Sem {semester} Sec {section}."

    db.execute(
        """INSERT INTO section_students (college, program, branch, semester, section, roll_no, student_name, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (college, program, branch, semester, section, roll_no, student_name, int(is_active))
    )
    db.commit()
    db.close()
    return True, f"Successfully added student {roll_no} ({student_name})."


def add_section_students(college, program, branch, semester, section, raw_rolls_text, replace_existing=True):
    """
    Bulk adds student roll numbers by manually typing or pasting text.
    Handles lines formatted as:
    - CE-101
    - CE-101, CE-102, CE-103
    - CE-101: John Doe
    - CE-101, John Doe
    """
    college = (college or "GHRCE").strip()
    program = (program or "B.Tech").strip()
    branch = (branch or "").strip().upper()
    semester = (semester or "").strip()
    section = (section or "").strip().upper()

    if not branch or not semester or not section:
        return False, "Branch, Semester, and Section are required."

    if not raw_rolls_text or not raw_rolls_text.strip():
        return False, "Please enter at least one valid student roll number."

    lines = raw_rolls_text.strip().splitlines()
    student_entries = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # If commas separate roll numbers on a single line
        parts = [p.strip() for p in line.split(",") if p.strip()]

        # Check if line was formatted as "RollNo, Student Name" or "RollNo: Student Name"
        if len(parts) == 2 and not any(ch.isdigit() for ch in parts[1]):
            roll, name = parts[0], parts[1]
            student_entries.append((roll, name))
        else:
            for part in parts:
                if ":" in part:
                    r, n = part.split(":", 1)
                    student_entries.append((r.strip(), n.strip()))
                elif "-" in part and not part.split("-")[0].replace(" ", "").isalpha():
                    # Format like "101 - John"
                    sub = part.split("-", 1)
                    if len(sub) == 2 and not any(ch.isdigit() for ch in sub[1]):
                        student_entries.append((sub[0].strip(), sub[1].strip()))
                    else:
                        student_entries.append((part.strip(), f"Student {part.strip()}"))
                else:
                    student_entries.append((part.strip(), f"Student {part.strip()}"))

    if not student_entries:
        return False, "No valid roll numbers parsed from input."

    db = get_db()
    if replace_existing:
        db.execute(
            "DELETE FROM section_students WHERE college = ? AND branch = ? AND semester = ? AND section = ?",
            (college, branch, semester, section)
        )

    inserted = 0
    for roll_no, student_name in student_entries:
        # Check duplicate if appending
        if not replace_existing:
            dup = db.execute(
                """SELECT id FROM section_students 
                   WHERE college = ? AND branch = ? AND semester = ? AND section = ? AND roll_no = ?""",
                (college, branch, semester, section, roll_no)
            ).fetchone()
            if dup:
                continue

        db.execute(
            """INSERT INTO section_students (college, program, branch, semester, section, roll_no, student_name, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (college, program, branch, semester, section, roll_no, student_name)
        )
        inserted += 1

    db.commit()
    db.close()
    return True, f"Successfully saved {inserted} student records for {branch} Sem {semester} Sec {section}!"


def import_students_from_excel(file_storage, default_college="GHRCE", default_program="B.Tech",
                              default_branch="", default_semester="", default_section=""):
    """
    Import student master records from Excel (.xlsx, .xls) or CSV file.
    Supports columns: Roll No / Roll Number / Roll, Name / Student Name, College, Program, Branch, Semester, Section, Status.
    """
    filename = file_storage.filename.lower()
    records = []

    if filename.endswith(".csv"):
        stream = io.StringIO(file_storage.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.reader(stream)
        header = None
        for row in csv_reader:
            if not row or not any(row):
                continue
            if header is None:
                header = [c.strip().lower() for c in row]
                continue

            # Process row using header mapping or standard position
            row_dict = {}
            for i, val in enumerate(row):
                if i < len(header):
                    row_dict[header[i]] = val.strip()
            records.append(row_dict)

    elif filename.endswith((".xlsx", ".xls")):
        if not HAS_OPENPYXL:
            return False, "openpyxl library is required to read Excel files."
        
        wb = openpyxl.load_workbook(file_storage)
        sheet = wb.active

        header = []
        for row in sheet.iter_rows(values_only=True):
            if not row or not any(row):
                continue
            if not header:
                header = [str(c).strip().lower() if c is not None else "" for c in row]
                continue

            row_dict = {}
            for i, val in enumerate(row):
                if i < len(header) and val is not None:
                    row_dict[header[i]] = str(val).strip()
            records.append(row_dict)

    else:
        return False, "Unsupported file format. Please upload an Excel (.xlsx, .xls) or CSV file."

    if not records:
        return False, "No data rows found in the uploaded file."

    db = get_db()
    imported_count = 0

    for r in records:
        # Resolve fields from header variations or default fallback
        roll_no = r.get("roll_no") or r.get("roll no") or r.get("roll") or r.get("rollnumber") or r.get("roll_number") or ""
        student_name = r.get("student_name") or r.get("name") or r.get("student name") or f"Student {roll_no}"
        college = r.get("college") or default_college
        program = r.get("program") or default_program
        branch = (r.get("branch") or default_branch).upper()
        semester = str(r.get("semester") or default_semester)
        section = (r.get("section") or default_section).upper()

        status_val = str(r.get("status") or r.get("is_active") or "1").lower()
        is_active = 0 if status_val in ("0", "false", "inactive", "left", "dropped") else 1

        if not roll_no or not branch or not semester or not section:
            continue

        # Upsert student record
        existing = db.execute(
            """SELECT id FROM section_students 
               WHERE college = ? AND branch = ? AND semester = ? AND section = ? AND roll_no = ?""",
            (college, branch, semester, section, roll_no)
        ).fetchone()

        if existing:
            db.execute(
                """UPDATE section_students 
                   SET student_name = ?, is_active = ?, program = ?
                   WHERE id = ?""",
                (student_name, is_active, program, existing["id"])
            )
        else:
            db.execute(
                """INSERT INTO section_students (college, program, branch, semester, section, roll_no, student_name, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (college, program, branch, semester, section, roll_no, student_name, is_active)
            )
        imported_count += 1

    db.commit()
    db.close()

    if imported_count > 0:
        return True, f"Successfully imported/updated {imported_count} student records from file!"
    return False, "Failed to import student records. Please ensure file contains required columns (Roll No, Branch, Semester, Section)."


def update_student(student_id, roll_no, student_name, college, program, branch, semester, section, is_active):
    """Updates an existing student record."""
    db = get_db()
    cur = db.execute(
        """UPDATE section_students 
           SET roll_no = ?, student_name = ?, college = ?, program = ?, branch = ?, semester = ?, section = ?, is_active = ?
           WHERE id = ?""",
        (roll_no.strip(), student_name.strip(), college.strip(), program.strip(),
         branch.strip().upper(), semester.strip(), section.strip().upper(), int(is_active), student_id)
    )
    db.commit()
    affected = cur.rowcount > 0
    db.close()
    return affected, "Student record updated successfully." if affected else "Student record not found."


def toggle_student_status(student_id):
    """Toggles student status between active (1) and inactive/dropped (0)."""
    db = get_db()
    row = db.execute("SELECT is_active, roll_no, student_name FROM section_students WHERE id = ?", (student_id,)).fetchone()
    if not row:
        db.close()
        return False, "Student not found."

    new_status = 0 if row["is_active"] == 1 else 1
    db.execute("UPDATE section_students SET is_active = ? WHERE id = ?", (new_status, student_id))
    db.commit()
    db.close()

    status_str = "Active" if new_status == 1 else "Inactive (Left/Dropped)"
    return True, f"Status for student {row['roll_no']} updated to {status_str}."


def delete_student(student_id):
    """Deletes a student record from database."""
    db = get_db()
    cur = db.execute("DELETE FROM section_students WHERE id = ?", (student_id,))
    db.commit()
    affected = cur.rowcount > 0
    db.close()
    return affected, "Student deleted successfully." if affected else "Student not found."


def delete_section_dataset(branch, semester, section, college="GHRCE"):
    """Delete a section student dataset."""
    db = get_db()
    cur = db.execute(
        "DELETE FROM section_students WHERE branch = ? AND semester = ? AND section = ? AND college = ?",
        (branch, semester, section, college)
    )
    db.commit()
    affected = cur.rowcount > 0
    db.close()
    if affected:
        return True, f"Deleted student dataset for {branch} Sem {semester} Sec {section}."
    return False, "Section dataset not found."
