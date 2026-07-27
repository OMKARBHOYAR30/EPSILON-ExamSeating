"""
modules/login_manager.py
-------------------------
User authentication and session verification logic.
"""

from database.db import get_db
from werkzeug.security import check_password_hash, generate_password_hash


def authenticate_user(username, password):
    """Authenticate username & password. Returns user dict or None."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    db.close()

    if user and check_password_hash(user["password_hash"], password):
        return {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    return None


def change_user_password(username, old_password, new_password):
    """Update user password after validating old password."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], old_password):
        db.close()
        return False, "Current password is incorrect."

    new_hash = generate_password_hash(new_password)
    db.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
    db.commit()
    db.close()
    return True, "Password updated successfully."
