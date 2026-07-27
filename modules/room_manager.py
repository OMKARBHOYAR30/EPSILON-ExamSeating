"""
modules/room_manager.py
------------------------
Classroom management logic with automatic capacity and row calculations.
"""

from database.db import get_db


def parse_row_layout(layout_string):
    """
    Parses comma-separated string of bench counts per row (e.g. '10,9,10').
    Returns tuple of (rows_count, total_capacity, list_of_benches_per_row).
    """
    if not layout_string:
        return 0, 0, []

    parts = [p.strip() for p in layout_string.split(",") if p.strip()]
    benches_per_row = [int(p) for p in parts if p.isdigit()]
    
    rows = len(benches_per_row)
    capacity = sum(benches_per_row)
    return rows, capacity, benches_per_row


def get_all_rooms():
    """Retrieve all classrooms ordered by block and room_no."""
    db = get_db()
    rooms = db.execute("SELECT * FROM classrooms ORDER BY block, room_no").fetchall()
    db.close()
    return [dict(r) for r in rooms]


def get_rooms_by_block(block):
    """Retrieve classrooms for a specific block."""
    db = get_db()
    rooms = db.execute(
        "SELECT * FROM classrooms WHERE block = ? ORDER BY room_no", (block,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rooms]


def get_blocks():
    """Retrieve unique block names."""
    db = get_db()
    blocks = db.execute("SELECT DISTINCT block FROM classrooms ORDER BY block").fetchall()
    db.close()
    return [b["block"] for b in blocks]


def get_room_details(room_no):
    """Fetch single classroom by room number."""
    db = get_db()
    room = db.execute("SELECT * FROM classrooms WHERE room_no = ?", (room_no,)).fetchone()
    db.close()
    return dict(room) if room else None


def add_room(room_no, block, row_layout):
    """Add a new classroom with auto-calculated rows and capacity."""
    room_no = room_no.strip()
    block = block.strip().upper()
    row_layout = row_layout.strip()

    rows, capacity, _ = parse_row_layout(row_layout)
    if rows == 0 or capacity == 0:
        return False, "Invalid Row Layout. Format should be comma-separated numbers (e.g., 10,9,10)."

    db = get_db()
    existing = db.execute("SELECT id FROM classrooms WHERE room_no = ?", (room_no,)).fetchone()
    if existing:
        db.close()
        return False, f"Room {room_no} already exists."

    db.execute(
        """INSERT INTO classrooms (block, room_no, default_capacity, default_rows, default_row_layout)
           VALUES (?, ?, ?, ?, ?)""",
        (block, room_no, capacity, rows, row_layout),
    )
    db.commit()
    db.close()
    return True, f"Room {room_no} added successfully! (Capacity: {capacity}, Rows: {rows})"


def update_row_layout(room_no, row_layout):
    """Update row layout for an existing room and auto-recalculate capacity."""
    row_layout = row_layout.strip()
    rows, capacity, _ = parse_row_layout(row_layout)
    if rows == 0 or capacity == 0:
        return False, "Invalid Row Layout format."

    db = get_db()
    cur = db.execute(
        """UPDATE classrooms 
           SET default_capacity = ?, default_rows = ?, default_row_layout = ?
           WHERE room_no = ?""",
        (capacity, rows, row_layout, room_no),
    )
    db.commit()
    success = cur.rowcount > 0
    db.close()
    if success:
        return True, f"Updated Room {room_no} (Capacity: {capacity}, Rows: {rows})"
    return False, f"Room {room_no} not found."


def delete_room(room_no):
    """Delete classroom by room_no."""
    db = get_db()
    cur = db.execute("DELETE FROM classrooms WHERE room_no = ?", (room_no,))
    db.commit()
    success = cur.rowcount > 0
    db.close()
    if success:
        return True, f"Room {room_no} deleted successfully."
    return False, f"Room {room_no} not found."
