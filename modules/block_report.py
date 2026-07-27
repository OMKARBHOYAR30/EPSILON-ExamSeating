"""
modules/block_report.py
------------------------
ReportLab notice-board style student seating chart PDF generator for a room.
Saves PDF to generated_reports/Block_Report.pdf (and generated_reports/Block_<RoomNo>.pdf).
Uses the manual Exam Date selected for the allocation.
"""

import os
from datetime import datetime, date
from database.db import get_db

from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors


def generate_block_report(allocation_id=None):
    """
    Generates a notice-board style seating chart PDF for a specific room allocation
    or the latest allocation if allocation_id is None.
    """
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_reports")
    os.makedirs(reports_dir, exist_ok=True)

    db = get_db()
    if allocation_id is None:
        allocation = db.execute("SELECT * FROM allocations ORDER BY id DESC LIMIT 1").fetchone()
    else:
        allocation = db.execute("SELECT * FROM allocations WHERE id = ?", (allocation_id,)).fetchone()

    if not allocation:
        db.close()
        print("No allocation found to generate Block Report.")
        return None

    room_no = allocation["room_no"]
    used_capacity = allocation["used_capacity"]
    row_layout = allocation["row_layout"]
    bench_mode = allocation["bench_mode"]

    exam_date_raw = allocation["exam_date"] if ("exam_date" in allocation.keys() and allocation["exam_date"]) else date.today().strftime("%Y-%m-%d")
    try:
        exam_date_formatted = datetime.strptime(exam_date_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        exam_date_formatted = exam_date_raw

    left_section = allocation["left_section"]
    left_branch = allocation["left_branch"]
    left_semester = allocation["left_semester"]
    left_roll_prefix = allocation["left_roll_prefix"] or ""
    left_roll_from = allocation["left_roll_from"] or ""
    left_roll_to = allocation["left_roll_to"] or ""

    right_section = allocation["right_section"] or ""
    right_branch = allocation["right_branch"] or ""
    right_semester = allocation["right_semester"] or ""
    right_roll_prefix = allocation["right_roll_prefix"] or ""
    right_roll_from = allocation["right_roll_from"] or ""
    right_roll_to = allocation["right_roll_to"] or ""

    benches_per_row = [int(v.strip()) for v in row_layout.split(",") if v.strip().isdigit()]

    # Fetch seating chart entries
    benches = db.execute(
        "SELECT bench_no, left_student, right_student FROM seating_chart WHERE allocation_id = ? ORDER BY bench_no",
        (allocation["id"],)
    ).fetchall()
    db.close()

    # Group benches according to row_layout
    grouped_benches = []
    idx = 0
    for count in benches_per_row:
        grouped_benches.append(benches[idx: idx + count])
        idx += count

    filename = os.path.join(reports_dir, "Block_Report.pdf")
    specific_filename = os.path.join(reports_dir, f"Block_{room_no}.pdf")

    page_size = landscape(A3)
    pdf = canvas.Canvas(filename, pagesize=page_size)
    width, height = page_size

    def draw_content():
        y = height - 40

        # Title
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawCentredString(width / 2, y, "STUDENT SEATING ARRANGEMENT CHART")

        y -= 35

        # Sub-header
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(40, y, f"Room No. {room_no}")
        pdf.drawRightString(width - 40, y, f"Date - {exam_date_formatted}")

        y -= 25

        # Summary info table
        left_label = f"{left_section}/{left_branch}/{left_semester}"
        right_label = f"{right_section}/{right_branch}/{right_semester}" if bench_mode == "DOUBLE" else "N/A"

        if allocation["left_entry_mode"] in ("manual", "dataset"):
            left_roll_range = "Section Roll List / Manual"
        else:
            left_roll_range = f"{left_roll_prefix}{left_roll_from} TO {left_roll_prefix}{left_roll_to}"

        if bench_mode == "DOUBLE":
            if allocation["right_entry_mode"] in ("manual", "dataset"):
                right_roll_range = "Section Roll List / Manual"
            else:
                right_roll_range = f"{right_roll_prefix}{right_roll_from} TO {right_roll_prefix}{right_roll_to}"
        else:
            right_roll_range = "-"

        info_data = [
            ["SEC/BRANCH/SEM", left_label, right_label],
            ["ROLL NO.", left_roll_range, right_roll_range],
            ["TOTAL", str(used_capacity), ""],
        ]

        info_table = Table(info_data, colWidths=[140, (width - 220) / 2, (width - 220) / 2])
        info_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("SPAN", (1, 2), (2, 2)),
        ]))

        _, table_height = info_table.wrapOn(pdf, width, height)
        info_table.drawOn(pdf, 40, y - table_height)

        y = y - table_height - 30

        # Main seating table grid
        num_groups = len(grouped_benches)
        max_benches = max([len(g) for g in grouped_benches]) if grouped_benches else 0

        header_row1 = []
        header_row2 = []

        for row_no in range(1, num_groups + 1):
            header_row1 += [f"ROW {row_no}", "", ""]
            header_row2 += [
                "TABLE NO.",
                f"SEM {left_semester}\nROLL NO.",
                f"SEM {right_semester if bench_mode == 'DOUBLE' else ''}\nROLL NO.",
            ]

        data = [header_row1, header_row2]

        for i in range(max_benches):
            row = []
            for group in grouped_benches:
                if i < len(group):
                    b_no, l_stud, r_stud = group[i]["bench_no"], group[i]["left_student"], group[i]["right_student"]
                    row += [str(b_no), str(l_stud), str(r_stud if bench_mode == "DOUBLE" else "-")]
                else:
                    row += ["", "", ""]
            data.append(row)

        col_count = num_groups * 3
        col_width = (width - 80) / max(col_count, 1)

        main_table = Table(data, colWidths=[col_width] * col_count, repeatRows=2)
        style_commands = [
            ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, 1), colors.whitesmoke),
        ]

        for g in range(num_groups):
            start_col = g * 3
            end_col = start_col + 2
            style_commands.append(("SPAN", (start_col, 0), (end_col, 0)))

        main_table.setStyle(TableStyle(style_commands))
        _, mt_height = main_table.wrapOn(pdf, width, height)

        if mt_height > y - 40:
            pdf.showPage()
            y = height - 40

        main_table.drawOn(pdf, 40, y - mt_height)

    draw_content()
    pdf.save()

    try:
        import shutil
        shutil.copyfile(filename, specific_filename)
    except Exception:
        pass

    print(f"Block Report PDF Generated: {filename}")
    return filename


if __name__ == "__main__":
    generate_block_report()
