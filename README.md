# EPSILON – Product of Constant Technologies

**EPSILON** is a modern desktop ERP application for college examination seating management. Built with Python, Flask, SQLite, and ReportLab PDF generation.

---

## Project Structure

```
EPSILON/
│
├── app.py                    # Main application entry point
├── college.db                # SQLite Database
├── requirements.txt          # Dependencies
├── README.md                 # Project documentation
│
├── templates/                # HTML Templates
│   ├── login.html
│   ├── dashboard.html
│   ├── room_management.html
│   ├── new_seating.html
│   ├── view_allocations.html
│   ├── block_report.html
│   ├── allocation_summary.html
│   ├── settings.html
│   └── base.html
│
├── static/                   # Static Assets
│   ├── css/
│   │   ├── style.css
│   │   ├── dashboard.css
│   │   ├── forms.css
│   │   └── tables.css
│   │
│   ├── js/
│   │   ├── dashboard.js
│   │   ├── room.js
│   │   ├── allocation.js
│   │   └── reports.js
│   │
│   ├── images/
│   │   ├── logo.png
│   │   ├── favicon.ico
│   │   └── icons/
│   │
│   └── fonts/
│
├── generated_reports/        # PDF Reports Output
│   ├── Block_Report.pdf
│   └── Allocation_Summary.pdf
│
├── database/                 # Database Schema & Connector
│   ├── db.py
│   └── schema.sql
│
├── modules/                  # Business Logic Modules
│   ├── login_manager.py
│   ├── room_manager.py
│   ├── allocation_manager.py
│   ├── report_manager.py
│   ├── block_report.py
│   └── allocation_pdf.py
│
└── assets/
```

---

## Key Features

1. **Clean Professional ERP Design**:
   - `#0b1d3a` Dark blue left navigation panel.
   - White content area with blue accent elements.
   - Zero charts or clutter; purely operational dashboard with 5 large action cards.

2. **Room Management**:
   - Auto-calculates Capacity and Rows count from `Row Layout` input strings (e.g. `10,9,10` $\rightarrow$ 29 Seats, 3 Rows).

3. **New Seating Arrangement**:
   - Multi-step wizard supporting single-side and double-side seating.
   - Automatic Roll Range generation and Manual Roll entry support.
   - Duplicate Room Allocation detection modal.

4. **PDF Reports & Direct Printing**:
   - **Block Report**: Notice-board style seating chart PDF.
   - **Allocation Summary**: Master room allocation summary PDF.
   - **Direct Printing**: Instant system print trigger (`window.print()` / iframe printing) without download popups.

---

## How to Run

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Application**:
   ```bash
   python app.py
   ```

3. **Open in Browser**:
   Navigate to `http://127.0.0.1:5000`
   - **Default Host / Admin Credentials**:
     - **Username**: `HOST1`
     - **Password**: `admin123`
