"""
app.py
------
EPSILON - Exam Seating Arrangement Management System
Developed by Constant Technologies

Main Flask Application Entry Point
"""

import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file

from database.db import init_db, get_db, reset_database_data
from modules.login_manager import authenticate_user, change_user_password
from modules.room_manager import get_all_rooms, get_rooms_by_block, get_blocks, add_room, delete_room, get_room_details
from modules.student_manager import (
    get_all_student_sections, get_available_oe_subjects, get_students_filtered, get_students_for_section,
    add_single_student, add_section_students, import_students_from_excel,
    update_student, toggle_student_status, delete_student, delete_section_dataset, batch_update_student_oe,
    get_student_by_roll, update_student_info_by_roll
)
from modules.allocation_manager import (
    create_seating_allocation, auto_generate_multi_room_seating, get_all_allocations, get_recent_allocations,
    get_allocation_by_id, delete_allocation, check_existing_allocation,
    get_available_sections, get_section_students, get_oe_students, get_allocated_students_by_date
)
from modules.report_manager import generate_all_reports, get_report_filepath
from modules.block_report import generate_block_report
from modules.allocation_pdf import generate_allocation_pdf

app = Flask(__name__)
app.secret_key = "epsilon_constant_technologies_secret_key_2025"

# Initialize database schema, migrations and default seeds on app startup
init_db()


@app.context_processor
def inject_global_data():
    """Inject current date and date string into all templates."""
    now = datetime.now()
    date_str = now.strftime("%d %b %Y, %A")
    default_exam_date = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    return dict(current_date=date_str, default_exam_date=default_exam_date)


def login_required(f):
    """Decorator to enforce login session check."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access the system.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = authenticate_user(username, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid Username or Password. Default login is HOST1 / admin123", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully.", "info")
    return redirect(url_for("login"))


# ============================================================
# DASHBOARD ROUTE
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():
    recents = get_recent_allocations(5)
    return render_template("dashboard.html", active_page="dashboard", recent_allocations=recents)


# ============================================================
# ROOM MANAGEMENT ROUTES
# ============================================================

@app.route("/room_management")
@login_required
def room_management():
    selected_block = request.args.get("block", "").strip()
    blocks = get_blocks()

    if selected_block:
        rooms = get_rooms_by_block(selected_block)
    else:
        rooms = get_all_rooms()

    return render_template(
        "room_management.html",
        active_page="room_management",
        rooms=rooms,
        blocks=blocks,
        selected_block=selected_block
    )


@app.route("/save_room", methods=["POST"])
@login_required
def save_room():
    block = request.form.get("block")
    room_no = request.form.get("room_no")
    row_layout = request.form.get("row_layout")

    success, msg = add_room(room_no, block, row_layout)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("room_management"))


@app.route("/delete_room/<room_no>")
@login_required
def delete_room_route(room_no):
    success, msg = delete_room(room_no)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("room_management"))


# ============================================================
# STUDENT MASTER DATABASE MANAGEMENT ROUTES
# ============================================================

@app.route("/student_management")
@login_required
def student_management():
    college_filter = request.args.get("college", "").strip()
    branch_filter = request.args.get("branch", "").strip()
    semester_filter = request.args.get("semester", "").strip()
    section_filter = request.args.get("section", "").strip()
    oe_filter = request.args.get("open_elective", "").strip()
    search_query = request.args.get("search", "").strip()
    active_filter = request.args.get("is_active", "").strip()

    datasets = get_all_student_sections()
    oe_subjects = get_available_oe_subjects()
    students = get_students_filtered(
        college=college_filter,
        branch=branch_filter,
        semester=semester_filter,
        section=section_filter,
        open_elective=oe_filter,
        search=search_query,
        is_active=active_filter
    )

    return render_template(
        "student_management.html",
        active_page="student_management",
        datasets=datasets,
        students=students,
        oe_subjects=oe_subjects,
        college_filter=college_filter,
        branch_filter=branch_filter,
        semester_filter=semester_filter,
        section_filter=section_filter,
        oe_filter=oe_filter,
        search_query=search_query,
        active_filter=active_filter
    )


@app.route("/save_section_students", methods=["POST"])
@login_required
def save_section_students_route():
    college = request.form.get("college", "GHRCE")
    program = request.form.get("program", "B.Tech")
    branch = request.form.get("branch")
    semester = request.form.get("semester")
    section = request.form.get("section")
    rolls_text = request.form.get("rolls_text", "")
    default_open_elective = request.form.get("default_open_elective", "")
    mode = request.form.get("save_mode", "replace")  # 'replace' or 'append'

    replace_existing = (mode == "replace")
    success, msg = add_section_students(college, program, branch, semester, section, rolls_text, default_open_elective=default_open_elective, replace_existing=replace_existing)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("student_management"))


@app.route("/import_students_excel", methods=["POST"])
@login_required
def import_students_excel_route():
    if "excel_file" not in request.files or not request.files["excel_file"].filename:
        flash("Please select a valid Excel or CSV file to import.", "danger")
        return redirect(url_for("student_management"))

    file = request.files["excel_file"]
    default_college = request.form.get("default_college", "GHRCE")
    default_program = request.form.get("default_program", "B.Tech")
    default_branch = request.form.get("default_branch", "")
    default_semester = request.form.get("default_semester", "")
    default_section = request.form.get("default_section", "")
    default_oe = request.form.get("default_oe", "")

    success, msg = import_students_from_excel(
        file,
        default_college=default_college,
        default_program=default_program,
        default_branch=default_branch,
        default_semester=default_semester,
        default_section=default_section,
        default_oe=default_oe
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("student_management"))


@app.route("/add_single_student", methods=["POST"])
@login_required
def add_single_student_route():
    college = request.form.get("college", "GHRCE")
    program = request.form.get("program", "B.Tech")
    branch = request.form.get("branch")
    semester = request.form.get("semester")
    section = request.form.get("section")
    roll_no = request.form.get("roll_no")
    student_name = request.form.get("student_name", "")
    open_elective = request.form.get("open_elective", "")
    is_active = request.form.get("is_active", 1)

    success, msg = add_single_student(college, program, branch, semester, section, roll_no, student_name, open_elective=open_elective, is_active=is_active)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("student_management"))


@app.route("/edit_student", methods=["POST"])
@login_required
def edit_student_route():
    student_id = request.form.get("student_id", type=int)
    college = request.form.get("college", "GHRCE")
    program = request.form.get("program", "B.Tech")
    branch = request.form.get("branch")
    semester = request.form.get("semester")
    section = request.form.get("section")
    roll_no = request.form.get("roll_no")
    student_name = request.form.get("student_name", "")
    open_elective = request.form.get("open_elective", "")
    is_active = request.form.get("is_active", 1)

    success, msg = update_student(student_id, roll_no, student_name, college, program, branch, semester, section, open_elective, is_active)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("student_management"))


@app.route("/toggle_student_status/<int:student_id>")
@login_required
def toggle_student_status_route(student_id):
    success, msg = toggle_student_status(student_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("student_management"))


@app.route("/delete_student/<int:student_id>")
@login_required
def delete_student_route(student_id):
    success, msg = delete_student(student_id)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("student_management"))


@app.route("/delete_section_dataset")
@login_required
def delete_section_dataset_route():
    branch = request.args.get("branch", "")
    semester = request.args.get("semester", "")
    section = request.args.get("section", "")
    college = request.args.get("college", "GHRCE")

    success, msg = delete_section_dataset(branch, semester, section, college)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("student_management"))


@app.route("/batch_update_oe", methods=["POST"])
@login_required
def batch_update_oe_route():
    college = request.form.get("college", "GHRCE")
    branch = request.form.get("branch")
    semester = request.form.get("semester")
    section = request.form.get("section")
    rolls_oe_text = request.form.get("rolls_oe_text", "")

    success, msg = batch_update_student_oe(college, branch, semester, section, rolls_oe_text)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("student_management"))


@app.route("/reset_database")
@login_required
def reset_database_route():
    reset_database_data()
    flash("All existing student records and seating allocations wiped successfully. Database is clean for your new dataset upload!", "success")
    return redirect(url_for("student_management"))


@app.route("/api/get_student_by_roll")
@login_required
def api_get_student_by_roll():
    roll_no = request.args.get("roll_no", "").strip()
    branch = request.args.get("branch", "").strip()
    semester = request.args.get("semester", "").strip()
    student = get_student_by_roll(roll_no, branch, semester)
    if student:
        return jsonify({"success": True, "student": student})
    return jsonify({"success": False, "message": "Student not found"}), 404


@app.route("/update_student_by_roll", methods=["POST"])
@login_required
def update_student_by_roll_route():
    roll_no = request.form.get("roll_no", "").strip()
    student_name = request.form.get("student_name", "").strip()
    branch = request.form.get("branch", "").strip()
    semester = request.form.get("semester", "").strip()
    section = request.form.get("section", "").strip()
    open_elective = request.form.get("open_elective", "").strip()
    is_active = request.form.get("is_active", 1)

    success, msg = update_student_info_by_roll(roll_no, student_name, branch, semester, section, open_elective, is_active)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")

    return redirect(url_for("student_management"))


# ============================================================
# NEW SEATING ARRANGEMENT ROUTES & APIS
# ============================================================

@app.route("/new_seating")
@login_required
def new_seating():
    blocks = get_blocks()
    sections = get_available_sections()
    oe_subjects = get_available_oe_subjects()
    return render_template("new_seating.html", active_page="new_seating", blocks=blocks, sections=sections, oe_subjects=oe_subjects)


@app.route("/oe_seating")
@login_required
def oe_seating():
    return redirect(url_for("new_seating"))


@app.route("/create_seating", methods=["POST"])
@login_required
def create_seating():
    data = request.form.to_dict()
    success, msg, alloc_id = create_seating_allocation(data)

    if success:
        generate_all_reports(alloc_id)
        flash(msg, "success")
        return redirect(url_for("block_report", alloc_id=alloc_id))
    else:
        flash(msg, "danger")
        return redirect(url_for("new_seating"))


@app.route("/auto_create_seating", methods=["POST"])
@login_required
def auto_create_seating():
    data = request.form.to_dict()
    selected_rooms = request.form.getlist("selected_rooms")
    if selected_rooms:
        data["selected_rooms"] = selected_rooms

    success, msg, alloc_ids = auto_generate_multi_room_seating(data)

    if success and alloc_ids:
        generate_all_reports()
        flash(msg, "success")
        return redirect(url_for("block_report", alloc_id=alloc_ids[0]))
    else:
        flash(msg if not success else "No allocations generated.", "danger")
        return redirect(url_for("new_seating"))


@app.route("/api/get_rooms")
@login_required
def api_get_rooms():
    block = request.args.get("block", "").strip()
    rooms = get_rooms_by_block(block) if block else get_all_rooms()
    return jsonify(rooms)


@app.route("/api/check_duplicate")
@login_required
def api_check_duplicate():
    room_no = request.args.get("room_no", "").strip()
    exam_date = request.args.get("exam_date", "").strip()
    existing = check_existing_allocation(room_no, exam_date)
    return jsonify({"has_allocation": existing is not None, "allocation": existing})


@app.route("/api/get_section_students")
@login_required
def api_get_section_students():
    college = request.args.get("college", "GHRCE").strip()
    branch = request.args.get("branch", "").strip()
    semester = request.args.get("semester", "").strip()
    section = request.args.get("section", "").strip()
    exam_date = request.args.get("exam_date", "").strip()
    limit = request.args.get("limit", 0)

    all_active = get_section_students(branch, semester, section, limit=None, college=college, exam_date=None, exclude_allocated=False)
    unallocated = get_section_students(branch, semester, section, limit=limit, college=college, exam_date=exam_date, exclude_allocated=True)

    already_allocated_set = get_allocated_students_by_date(exam_date)
    allocated_count = len([s for s in all_active if s["roll_no"] in already_allocated_set])

    return jsonify({
        "students": unallocated,
        "total_active": len(all_active),
        "total_unallocated": len(unallocated),
        "total_already_allocated": allocated_count
    })


@app.route("/api/get_oe_students")
@login_required
def api_get_oe_students():
    semester = request.args.get("semester", "").strip()
    open_elective = request.args.get("open_elective", "").strip()
    exam_date = request.args.get("exam_date", "").strip()
    limit = request.args.get("limit", 0)

    all_active = get_oe_students(semester, open_elective, limit=None, exam_date=None, exclude_allocated=False)
    unallocated = get_oe_students(semester, open_elective, limit=limit, exam_date=exam_date, exclude_allocated=True)

    already_allocated_set = get_allocated_students_by_date(exam_date)
    allocated_count = len([s for s in all_active if s["roll_no"] in already_allocated_set])

    return jsonify({
        "students": unallocated,
        "total_active": len(all_active),
        "total_unallocated": len(unallocated),
        "total_already_allocated": allocated_count
    })


@app.route("/api/search_students")
@login_required
def api_search_students():
    college = request.args.get("college", "").strip()
    branch = request.args.get("branch", "").strip()
    semester = request.args.get("semester", "").strip()
    section = request.args.get("section", "").strip()
    open_elective = request.args.get("open_elective", "").strip()
    search = request.args.get("search", "").strip()
    is_active = request.args.get("is_active", "").strip()

    students = get_students_filtered(college, branch, semester, section, open_elective, search, is_active)
    return jsonify({"students": students, "total": len(students)})


# ============================================================
# VIEW ALLOCATIONS ROUTES & APIS
# ============================================================

@app.route("/view_allocations")
@login_required
def view_allocations():
    allocations = get_all_allocations()
    return render_template("view_allocations.html", active_page="view_allocations", allocations=allocations)


@app.route("/api/allocation_detail/<int:alloc_id>")
@login_required
def api_allocation_detail(alloc_id):
    detail = get_allocation_by_id(alloc_id)
    if detail:
        return jsonify(detail)
    return jsonify({"error": "Allocation not found"}), 404


@app.route("/delete_allocation/<int:alloc_id>")
@login_required
def delete_allocation_route(alloc_id):
    success, msg = delete_allocation(alloc_id)
    if success:
        generate_all_reports()
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("view_allocations"))


# ============================================================
# REPORTS AND DIRECT PRINT ROUTES
# ============================================================

@app.route("/block_report")
@login_required
def block_report():
    alloc_id = request.args.get("alloc_id")
    allocations = get_all_allocations()
    if alloc_id:
        generate_block_report(int(alloc_id))
    else:
        generate_block_report()

    return render_template("block_report.html", active_page="block_report", allocations=allocations)


@app.route("/api/get_oe_subjects")
@login_required
def api_get_oe_subjects():
    semester = request.args.get("semester", "").strip()
    subjects = get_available_oe_subjects(semester=semester if semester else None)
    return jsonify({"subjects": subjects})


@app.route("/oe_paper_allocation")
@login_required
def oe_paper_allocation():
    """
    Independent Class-Wise OE Paper Allocation Page.
    Groups students by class/section (college, program, branch, semester, section),
    and counts students enrolled in each Open Elective subject independently.
    """
    db = get_db()
    sections = db.execute(
        """SELECT college, program, branch, semester, section 
           FROM section_students 
           WHERE is_active = 1 
           GROUP BY college, program, branch, semester, section 
           ORDER BY college, branch, semester, section"""
    ).fetchall()

    class_data = []
    total_students_enrolled = 0
    distinct_subjects = set()

    for sec in sections:
        c_name = sec["college"] or "GHRCE"
        p_name = sec["program"] or "B.Tech"
        b_name = sec["branch"]
        sem = sec["semester"]
        section_code = sec["section"]

        sub_rows = db.execute(
            """SELECT open_elective, COUNT(*) as count 
               FROM section_students 
               WHERE branch = ? AND semester = ? AND section = ? AND is_active = 1 
                 AND open_elective IS NOT NULL AND open_elective != ''
               GROUP BY open_elective 
               ORDER BY open_elective""",
            (b_name, sem, section_code)
        ).fetchall()

        if sub_rows:
            subjects_list = []
            class_total = 0
            for r in sub_rows:
                sub_name = r["open_elective"].strip()
                cnt = r["count"]
                subjects_list.append({"subject": sub_name, "count": cnt})
                class_total += cnt
                distinct_subjects.add(sub_name)

            total_students_enrolled += class_total
            class_label = f"{b_name} Sem {sem} (Sec {section_code})"
            class_data.append({
                "college": c_name,
                "program": p_name,
                "branch": b_name,
                "semester": sem,
                "section": section_code,
                "class_label": class_label,
                "subjects": subjects_list,
                "total_papers": class_total
            })

    db.close()

    return render_template(
        "oe_paper_allocation.html",
        active_page="oe_paper_allocation",
        class_data=class_data,
        total_classes=len(class_data),
        total_students=total_students_enrolled,
        total_subjects=len(distinct_subjects)
    )


@app.route("/allocation_summary")
@login_required
def allocation_summary():
    generate_allocation_pdf()
    return render_template("allocation_summary.html", active_page="allocation_summary")


@app.route("/generated_reports/preview_block")
@login_required
def preview_block_pdf():
    alloc_id = request.args.get("id")
    if alloc_id:
        generate_block_report(int(alloc_id))
    else:
        generate_block_report()
    path = get_report_filepath("block")
    return send_file(path, mimetype="application/pdf")


@app.route("/generated_reports/preview_summary")
@login_required
def preview_summary_pdf():
    generate_allocation_pdf()
    path = get_report_filepath("summary")
    return send_file(path, mimetype="application/pdf")


# ============================================================
# SETTINGS & MAINTENANCE ROUTES
# ============================================================

@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", active_page="settings")


@app.route("/update_password", methods=["POST"])
@login_required
def update_password():
    old_p = request.form.get("old_password")
    new_p = request.form.get("new_password")
    username = session.get("username")

    success, msg = change_user_password(username, old_p, new_p)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for("settings"))


@app.route("/clear_allocations")
@login_required
def clear_allocations_route():
    db = get_db()
    db.execute("DELETE FROM allocations")
    db.execute("DELETE FROM seating_chart")
    db.execute("DELETE FROM manual_rolls")
    db.commit()
    db.close()

    generate_all_reports()
    flash("All saved allocations cleared successfully.", "success")
    return redirect(url_for("settings"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
