"""
modules/report_manager.py
--------------------------
Unified PDF Report Generator Manager for EPSILON.
"""

import os
from modules.block_report import generate_block_report
from modules.allocation_pdf import generate_allocation_pdf


def generate_all_reports(allocation_id=None):
    """Regenerate both Block Report and Allocation Summary PDFs."""
    block_pdf = generate_block_report(allocation_id)
    summary_pdf = generate_allocation_pdf(allocation_id)
    return {
        "block_report": block_pdf,
        "allocation_summary": summary_pdf
    }


def get_report_filepath(report_type):
    """Return the absolute path of the generated PDF file."""
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "generated_reports")
    if report_type == "block":
        path = os.path.join(reports_dir, "Block_Report.pdf")
    else:
        path = os.path.join(reports_dir, "Allocation_Summary.pdf")
    
    # Generate default if missing
    if not os.path.exists(path):
        generate_all_reports()

    return path
