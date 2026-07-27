"""
modules/allocation_pdf.py
-------------------------
ReportLab master seating arrangement chart (Allocation Summary) PDF generator.
Saves PDF to generated_reports/Allocation_Summary.pdf.
Uses the manual Exam Date selected for each allocation.
"""

import os
from datetime import datetime, date
from database.db import get_db

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors


def generate_allocation_pdf(allocation_id=None):
    """
    Generates the master seating allocation summary PDF for all rooms.
    """
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_reports")
    os.makedirs(reports_dir, exist_ok=True)

    db = get_db()
    allocations = db.execute(
        """SELECT a.*, c.block 
           FROM allocations a
           LEFT JOIN classrooms c ON a.room_no = c.room_no
           ORDER BY a.exam_date DESC, c.block, a.room_no"""
    ).fetchall()
    db.close()

    filename = os.path.join(reports_dir, "Allocation_Summary.pdf")

    page_size = A4
    pdf = canvas.Canvas(filename, pagesize=page_size)
    width, height = page_size

    y = height - 40

    # Title
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, y, "SEATING ARRANGEMENT CHART")

    y -= 20
    pdf.setFont("Helvetica", 10)

    # Use date of first allocation or today
    header_date = date.today().strftime("%d/%m/%Y")
    if allocations and "exam_date" in allocations[0].keys() and allocations[0]["exam_date"]:
        try:
            header_date = datetime.strptime(allocations[0]["exam_date"], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            header_date = allocations[0]["exam_date"]

    pdf.drawRightString(width - 40, y, f"Date - {header_date}")

    y -= 25

    if not allocations:
        pdf.setFont("Helvetica-Oblique", 12)
        pdf.drawCentredString(width / 2, y - 50, "No Allocations Available.")
        pdf.save()
        return filename

    # Build summary table data
    header = ["BLOCK", "ROOM NO.", "COLLEGE", "BRANCH", "ROLL NO. RANGE", "EXAM DATE", "TOTAL"]
    data = [header]
    span_commands = []
    row_index = 1

    for row in allocations:
        block = row["block"] or row["room_no"].split("-")[0] if "-" in row["room_no"] else ""
        room_no = row["room_no"]
        l_college = row["left_college"]
        l_branch = row["left_branch"]
        l_prefix = row["left_roll_prefix"] or ""
        l_from = row["left_roll_from"] or 0
        l_to = row["left_roll_to"] or 0
        l_mode = row["left_entry_mode"]

        if l_mode in ("manual", "dataset"):
            l_range = "Section Roll List"
        else:
            l_range = f"{l_prefix}{l_from} To {l_prefix}{l_to}"

        r_college = row["right_college"] or "-"
        r_branch = row["right_branch"] or "-"
        r_prefix = row["right_roll_prefix"] or ""
        r_from = row["right_roll_from"] or 0
        r_to = row["right_roll_to"] or 0
        r_mode = row["right_entry_mode"]

        if row["bench_mode"] == "DOUBLE":
            if r_mode in ("manual", "dataset"):
                r_range = "Section Roll List"
            else:
                r_range = f"{r_prefix}{r_from} To {r_prefix}{r_to}"
        else:
            r_range = "-"

        used_capacity = row["used_capacity"]
        ex_date = row["exam_date"] if "exam_date" in row.keys() else ""

        data.append([block, room_no, l_college, l_branch, l_range, ex_date, str(used_capacity)])
        data.append(["", "", r_college, r_branch, r_range, ex_date, str(used_capacity)])

        # Merge Block, Room No, and Exam Date across 2 stacked rows
        span_commands.append(("SPAN", (0, row_index), (0, row_index + 1)))
        span_commands.append(("SPAN", (1, row_index), (1, row_index + 1)))
        span_commands.append(("SPAN", (5, row_index), (5, row_index + 1)))
        row_index += 2

    usable_width = width - 80
    col_widths = [
        usable_width * 0.09,  # BLOCK
        usable_width * 0.13,  # ROOM NO.
        usable_width * 0.22,  # COLLEGE
        usable_width * 0.16,  # BRANCH
        usable_width * 0.22,  # ROLL NO.
        usable_width * 0.11,  # EXAM DATE
        usable_width * 0.07,  # TOTAL
    ]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    style_commands = [
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (2, 1), (3, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ] + span_commands

    table.setStyle(TableStyle(style_commands))
    _, table_height = table.wrapOn(pdf, width, height)

    if table_height > y - 40:
        pdf.showPage()
        y = height - 40

    table.drawOn(pdf, 40, y - table_height)
    pdf.save()

    print(f"Allocation Summary PDF Generated: {filename}")
    return filename


if __name__ == "__main__":
    generate_allocation_pdf()
