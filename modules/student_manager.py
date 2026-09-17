"""
modules/student_manager.py
---------------------------
Student Master Database Management logic for EPSILON.
Supports:
- Open Elective (OE) Subject management
- Bulk paste / manual typing of roll numbers
- Excel (.xlsx, .xls) and CSV importing with OE subjects
- Single student record creation, modification, deletion
- Active/Inactive status toggling (dropped / left college)
- Dynamic filtering and searching by College, Branch, Semester, Section, Open Elective, Keyword
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


def get_available_oe_subjects(semester=None):
    """Retrieve list of distinct Open Elective (OE) subjects registered in the system."""
    db = get_db()
    if semester:
        query = """SELECT open_elective, semester, COUNT(*) as count 
                   FROM section_students 
                   WHERE open_elective IS NOT NULL AND open_elective != '' AND is_active = 1 AND semester = ?
                   GROUP BY open_elective, semester ORDER BY open_elective"""
        rows = db.execute(query, (str(semester),)).fetchall()
    else:
        query = """SELECT open_elective, GROUP_CONCAT(DISTINCT semester) as semester, COUNT(*) as count 
                   FROM section_students 
                   WHERE open_elective IS NOT NULL AND open_elective != '' AND is_active = 1
                   GROUP BY open_elective ORDER BY open_elective"""
        rows = db.execute(query).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_students_filtered(college=None, branch=None, semester=None, section=None, open_elective=None, search=None, is_active=None):
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
    if open_elective:
        query += " AND (open_elective = ? OR open_elective LIKE ?)"
        params.extend([open_elective, f"%{open_elective}%"])
    if is_active is not None and is_active != "":
        query += " AND is_active = ?"
        params.append(int(is_active))
    if search:
        query += " AND (roll_no LIKE ? OR student_name LIKE ? OR open_elective LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])

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


def add_single_student(college, program, branch, semester, section, roll_no, student_name, open_elective="", is_active=1):
    """Adds a single student record to the Master Database."""
    college = (college or "GHRCE").strip()
    program = (program or "B.Tech").strip()
    branch = (branch or "").strip().upper()
    semester = (semester or "").strip()
    section = (section or "").strip().upper()
    roll_no = (roll_no or "").strip()
    student_name = (student_name or f"Student {roll_no}").strip()
    open_elective = (open_elective or "").strip()

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
        """INSERT INTO section_students (college, program, branch, semester, section, roll_no, student_name, open_elective, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (college, program, branch, semester, section, roll_no, student_name, open_elective, int(is_active))
    )
    db.commit()
    db.close()
    return True, f"Successfully added student {roll_no} ({student_name})."


def add_section_students(college, program, branch, semester, section, raw_rolls_text, default_open_elective="", replace_existing=True):
    """
    Bulk adds student roll numbers by manually typing or pasting text.
    Handles formats:
    - CE-101
    - CE-101, CE-102, CE-103
    - CE-101: John Doe
    - CE-101: John Doe, IPR
    - CE-101, John Doe, Industry 4.0
    """
    college = (college or "GHRCE").strip()
    program = (program or "B.Tech").strip()
    branch = (branch or "").strip().upper()
    semester = (semester or "").strip()
    section = (section or "").strip().upper()
    default_open_elective = (default_open_elective or "").strip()

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

        # Check comma separated parts
        parts = [p.strip() for p in line.split(",") if p.strip()]

        if len(parts) >= 3:
            # Format: Roll, Name, OE Subject
            student_entries.append((parts[0], parts[1], parts[2]))
        elif len(parts) == 2:
            if ":" in parts[0]:
                r, n = parts[0].split(":", 1)
                student_entries.append((r.strip(), n.strip(), parts[1]))
            elif not any(ch.isdigit() for ch in parts[1]):
                student_entries.append((parts[0], parts[1], default_open_elective))
            else:
                for p in parts:
                    student_entries.append((p, f"Student {p}", default_open_elective))
        else:
            if ":" in line:
                r, n = line.split(":", 1)
                student_entries.append((r.strip(), n.strip(), default_open_elective))
            else:
                student_entries.append((line, f"Student {line}", default_open_elective))

    if not student_entries:
        return False, "No valid roll numbers parsed from input."

    db = get_db()
    if replace_existing:
        db.execute(
            "DELETE FROM section_students WHERE college = ? AND branch = ? AND semester = ? AND section = ?",
            (college, branch, semester, section)
        )

    inserted = 0
    for roll_no, student_name, oe_subject in student_entries:
        oe_val = oe_subject or default_open_elective
        if not replace_existing:
            dup = db.execute(
                """SELECT id FROM section_students 
                   WHERE college = ? AND branch = ? AND semester = ? AND section = ? AND roll_no = ?""",
                (college, branch, semester, section, roll_no)
            ).fetchone()
            if dup:
                continue

        db.execute(
            """INSERT INTO section_students (college, program, branch, semester, section, roll_no, student_name, open_elective, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (college, program, branch, semester, section, roll_no, student_name, oe_val)
        )
        inserted += 1

    db.commit()
    db.close()
    return True, f"Successfully saved {inserted} student records for {branch} Sem {semester} Sec {section}!"


def _extract_field(row_dict, field_aliases, default_val=""):
    """
    Extracts a value from row_dict using a list of potential column header aliases.
    Checks exact matches, lowercased matches, and normalized matches (removing non-alphanumerics).
    """
    # 1. Exact or direct lowercased key lookup
    for alias in field_aliases:
        alias_lower = alias.lower().strip()
        if alias_lower in row_dict and row_dict[alias_lower] is not None and str(row_dict[alias_lower]).strip() != "":
            return str(row_dict[alias_lower]).strip()
    
    # 2. Normalized lookup (removing spaces, underscores, dashes, dots, parens)
    normalized_dict = {}
    for k, v in row_dict.items():
        if v is None:
            continue
        clean_k = ''.join(c for c in str(k).lower() if c.isalnum())
        if clean_k and clean_k not in normalized_dict:
            normalized_dict[clean_k] = str(v).strip()
            
    for alias in field_aliases:
        clean_alias = ''.join(c for c in str(alias).lower() if c.isalnum())
        if clean_alias in normalized_dict and normalized_dict[clean_alias] != "":
            return normalized_dict[clean_alias]
            
    return default_val


def import_students_from_excel(file_storage, default_college="GHRCE", default_program="B.Tech",
                              default_branch="", default_semester="", default_section="", default_oe=""):
    """
    Import student master records from Excel (.xlsx, .xls) or CSV file.
    Supports columns: Roll No, Name / Student Name, College, Program, Branch, Semester, Section, Open Elective / Allotted Course / OE / Subject, Status.
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

    roll_aliases = ["roll_no", "roll no", "roll", "rollnumber", "roll_number", "roll_no.", "roll no.", "enrollment_no", "enrollment no", "student_id", "student id", "id_no", "id no", "registration_no", "reg_no"]
    name_aliases = ["student_name", "student name", "name", "name of student", "name of the student", "candidate_name", "candidate name", "student", "full_name", "full name"]
    college_aliases = ["college", "college name", "college_name", "institute", "institution"]
    program_aliases = ["program", "course_program", "degree", "branch_program", "stream"]
    branch_aliases = ["branch", "department", "dept", "discipline", "branch_name"]
    semester_aliases = ["semester", "sem", "term", "year_sem"]
    section_aliases = ["section", "sec", "class_section", "group"]
    oe_aliases = [
        "open_elective", "open elective", "oe", "allotted course", "allotted_course", "allottedcourse",
        "allotted subject", "allotted_subject", "course", "course_name", "course name",
        "course allocated", "allocated course", "elective", "elective_subject", "elective subject",
        "subject", "subject_name", "subject name", "oe_subject", "oe subject", "oe_name", "oe name"
    ]
    status_aliases = ["status", "is_active", "active", "student_status"]

    for r in records:
        roll_no = _extract_field(r, roll_aliases, "")
        student_name = _extract_field(r, name_aliases, f"Student {roll_no}" if roll_no else "Unknown Student")
        college = _extract_field(r, college_aliases, default_college)
        program = _extract_field(r, program_aliases, default_program)
        branch = _extract_field(r, branch_aliases, default_branch).upper()
        semester = str(_extract_field(r, semester_aliases, default_semester))
        section = _extract_field(r, section_aliases, default_section).upper()

        open_elective = _extract_field(r, oe_aliases, default_oe)

        status_val = _extract_field(r, status_aliases, "1").lower()
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
                   SET student_name = ?, open_elective = ?, is_active = ?, program = ?
                   WHERE id = ?""",
                (student_name, open_elective, is_active, program, existing["id"])
            )
        else:
            db.execute(
                """INSERT INTO section_students (college, program, branch, semester, section, roll_no, student_name, open_elective, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (college, program, branch, semester, section, roll_no, student_name, open_elective, is_active)
            )
        imported_count += 1

    db.commit()
    db.close()

    if imported_count > 0:
        return True, f"Successfully imported/updated {imported_count} student records with Open Electives from file!"
    return False, "Failed to import student records. Please ensure file contains required columns (Roll No, Branch, Semester, Section)."


def update_student(student_id, roll_no, student_name, college, program, branch, semester, section, open_elective, is_active):
    """Updates an existing student record."""
    db = get_db()
    cur = db.execute(
        """UPDATE section_students 
           SET roll_no = ?, student_name = ?, college = ?, program = ?, branch = ?, semester = ?, section = ?, open_elective = ?, is_active = ?
           WHERE id = ?""",
        (roll_no.strip(), student_name.strip(), college.strip(), program.strip(),
         branch.strip().upper(), semester.strip(), section.strip().upper(), (open_elective or "").strip(), int(is_active), student_id)
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


def batch_update_student_oe(college, branch, semester, section, rolls_oe_text):
    """
    Updates Open Elective (OE) subject for existing students in a section.
    Supports formats:
    - ALL: Subject Name
    - CE-101: Industry 4.0
    - CE-101, IPR
    - CE-101 to CE-120: Cyber Security
    """
    college = (college or "GHRCE").strip()
    branch = (branch or "").strip().upper()
    semester = str(semester or "").strip()
    section = (section or "").strip().upper()

    if not branch or not semester or not section:
        return False, "Branch, Semester, and Section are required."

    if not rolls_oe_text or not rolls_oe_text.strip():
        return False, "Please enter roll numbers and OE subjects to update."

    lines = rolls_oe_text.strip().splitlines()
    db = get_db()
    updated_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.lower().startswith("all:") or line.lower().startswith("all,"):
            oe_sub = line.split(":", 1)[-1].split(",", 1)[-1].strip()
            cur = db.execute(
                "UPDATE section_students SET open_elective = ? WHERE college = ? AND branch = ? AND semester = ? AND section = ?",
                (oe_sub, college, branch, semester, section)
            )
            updated_count += cur.rowcount
            continue

        if " to " in line.lower() and ":" in line:
            range_part, oe_sub = line.split(":", 1)
            oe_sub = oe_sub.strip()
            start_r, end_r = range_part.lower().split(" to ", 1)
            start_r = start_r.strip()
            end_r = end_r.strip()

            rows = db.execute(
                "SELECT id, roll_no FROM section_students WHERE college = ? AND branch = ? AND semester = ? AND section = ?",
                (college, branch, semester, section)
            ).fetchall()

            for r in rows:
                r_no = r["roll_no"].lower()
                if start_r in r_no or end_r in r_no or (r_no >= start_r and r_no <= end_r):
                    db.execute("UPDATE section_students SET open_elective = ? WHERE id = ?", (oe_sub, r["id"]))
                    updated_count += 1
            continue

        parts = []
        if ":" in line:
            parts = [p.strip() for p in line.split(":", 1)]
        elif "," in line:
            parts = [p.strip() for p in line.split(",", 1)]

        if len(parts) == 2:
            roll_no, oe_sub = parts[0], parts[1]
            cur = db.execute(
                "UPDATE section_students SET open_elective = ? WHERE college = ? AND branch = ? AND semester = ? AND section = ? AND (roll_no = ? OR roll_no LIKE ?)",
                (oe_sub, college, branch, semester, section, roll_no, f"%{roll_no}%")
            )
            updated_count += cur.rowcount

    db.commit()
    db.close()

    if updated_count > 0:
        return True, f"Successfully updated Open Elective subject for {updated_count} student records in {branch} Sem {semester} Sec {section}!"
    return False, f"No matching student records found in {branch} Sem {semester} Sec {section} to update."


def get_student_by_roll(roll_no, branch=None, semester=None):
    """Fetch single student record by Roll No (and optional branch/semester)."""
    if not roll_no:
        return None
    db = get_db()
    query = "SELECT * FROM section_students WHERE (roll_no = ? OR roll_no LIKE ?)"
    params = [roll_no.strip(), f"%{roll_no.strip()}%"]

    if branch and branch.strip():
        query += " AND branch = ?"
        params.append(branch.strip().upper())
    if semester and str(semester).strip():
        query += " AND semester = ?"
        params.append(str(semester).strip())

    query += " ORDER BY id LIMIT 1"
    row = db.execute(query, params).fetchone()
    db.close()
    return dict(row) if row else None


def update_student_info_by_roll(roll_no, student_name=None, branch=None, semester=None, section=None, open_elective=None, is_active=1):
    """Updates student information directly by Roll No."""
    if not roll_no:
        return False, "Roll number is required."

    db = get_db()
    student = db.execute("SELECT id FROM section_students WHERE roll_no = ?", (roll_no.strip(),)).fetchone()
    if not student:
        db.close()
        return False, f"Student record for Roll No '{roll_no}' not found."

    cur = db.execute(
        """UPDATE section_students 
           SET student_name = COALESCE(?, student_name),
               branch = COALESCE(?, branch),
               semester = COALESCE(?, semester),
               section = COALESCE(?, section),
               open_elective = ?,
               is_active = ?
           WHERE id = ?""",
        (
            student_name.strip() if student_name else None,
            branch.strip().upper() if branch else None,
            str(semester).strip() if semester else None,
            section.strip().upper() if section else None,
            (open_elective or "").strip(),
            int(is_active) if is_active is not None else 1,
            student["id"]
        )
    )
    db.commit()
    affected = cur.rowcount > 0
    db.close()
    return affected, f"Student {roll_no} information & Open Elective updated successfully!" if affected else "Failed to update student record."
