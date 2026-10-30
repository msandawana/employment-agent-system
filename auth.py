import sqlite3
import bcrypt
import os
import sys
from datetime import datetime, timedelta
from contextlib import contextmanager
import re

# ---------------- DB PATH (matches database.py) ----------------
if getattr(sys, "frozen", False):
    USER_DIR = os.path.expanduser("~/Documents/EmploymentAgent")
else:
    USER_DIR = os.path.dirname(os.path.abspath(__file__))

DB = os.path.join(USER_DIR, "employment_agent.db")
os.makedirs(USER_DIR, exist_ok=True)


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB)
    try:
        yield conn
    finally:
        conn.close()


# ---------------- PASSWORD VALIDATION ----------------
def validate_password_strength(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False


# ---------------- USERS TABLE ----------------
def create_users_table():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login TEXT,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TEXT
            )
        """)
        conn.commit()


def create_default_users():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            hashed = hash_password("Admin@2024!")
            cur.execute("""
                INSERT INTO users (username, password, role)
                VALUES (?, ?, ?)
            """, ("admin", hashed, "admin"))
            conn.commit()
            print("Default admin created — username: admin | password: Admin@2024!")


# ---------------- AUTHENTICATION ----------------
def authenticate(username, password):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, password, role, is_active, failed_login_attempts, locked_until
                FROM users WHERE username=?
            """, (username,))
            row = cur.fetchone()

            if not row:
                return None, "Invalid username or password"

            user_id, hashed_password, role, is_active, failed_attempts, locked_until = row

            # Check lockout
            if locked_until:
                lock_time = datetime.fromisoformat(locked_until)
                if datetime.now() < lock_time:
                    minutes_left = max(1, (lock_time - datetime.now()).seconds // 60)
                    return None, f"Account locked. Try again in {minutes_left} minute(s)"
                else:
                    cur.execute("""
                        UPDATE users SET locked_until=NULL, failed_login_attempts=0 WHERE id=?
                    """, (user_id,))
                    conn.commit()

            if not is_active:
                return None, "Account is deactivated. Contact administrator"

            if verify_password(password, hashed_password):
                cur.execute("""
                    UPDATE users SET last_login=?, failed_login_attempts=0, locked_until=NULL WHERE id=?
                """, (datetime.now().isoformat(), user_id))
                conn.commit()
                return role, "Login successful"
            else:
                failed_attempts += 1
                if failed_attempts >= 5:
                    lock_until = datetime.now() + timedelta(minutes=15)
                    cur.execute("""
                        UPDATE users SET failed_login_attempts=?, locked_until=? WHERE id=?
                    """, (failed_attempts, lock_until.isoformat(), user_id))
                    conn.commit()
                    return None, "Account locked due to too many failed attempts. Try again in 15 minutes"
                else:
                    cur.execute("""
                        UPDATE users SET failed_login_attempts=? WHERE id=?
                    """, (failed_attempts, user_id))
                    conn.commit()
                    attempts_left = 5 - failed_attempts
                    return None, f"Invalid username or password. {attempts_left} attempt(s) remaining"

    except Exception as e:
        print(f"Authentication error: {e}")
        return None, "An error occurred during authentication"


# ---------------- USER MANAGEMENT ----------------
def create_user(username, password, role):
    if not username or len(username.strip()) < 3:
        return False, "Username must be at least 3 characters long"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    is_valid, message = validate_password_strength(password)
    if not is_valid:
        return False, message
    if role not in ['admin', 'user']:
        return False, "Role must be either 'admin' or 'user'"
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            hashed = hash_password(password)
            cur.execute("""
                INSERT INTO users (username, password, role) VALUES (?, ?, ?)
            """, (username.strip(), hashed, role))
            conn.commit()
            return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except Exception as e:
        return False, f"Error creating user: {str(e)}"


def get_all_users():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, username, role, is_active, created_at, last_login
                FROM users ORDER BY username
            """)
            return cur.fetchall()
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []


def set_user_active(user_id, active):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            if active == 0:
                cur.execute("SELECT role FROM users WHERE id=?", (user_id,))
                user = cur.fetchone()
                if user and user[0] == 'admin':
                    cur.execute("""
                        SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1 AND id!=?
                    """, (user_id,))
                    if cur.fetchone()[0] == 0:
                        return False, "Cannot deactivate the last active admin account"
            cur.execute("UPDATE users SET is_active=? WHERE id=?", (active, user_id))
            conn.commit()
            status = "activated" if active else "deactivated"
            return True, f"User {status} successfully"
    except Exception as e:
        return False, f"Error updating user status: {str(e)}"


def change_password(username, new_password, require_strength=True):
    if require_strength:
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            return False, message
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=?", (username,))
            if not cur.fetchone():
                return False, "User not found"
            hashed = hash_password(new_password)
            cur.execute("""
                UPDATE users SET password=?, failed_login_attempts=0, locked_until=NULL WHERE username=?
            """, (hashed, username))
            conn.commit()
            return True, "Password changed successfully"
    except Exception as e:
        return False, f"Error changing password: {str(e)}"


def delete_user(user_id):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT role FROM users WHERE id=?", (user_id,))
            user = cur.fetchone()
            if not user:
                return False, "User not found"
            if user[0] == 'admin':
                cur.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND id!=?", (user_id,))
                if cur.fetchone()[0] == 0:
                    return False, "Cannot delete the last admin account"
            cur.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            return True, "User deleted successfully"
    except Exception as e:
        return False, f"Error deleting user: {str(e)}"


def unlock_user(user_id):
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE users SET failed_login_attempts=0, locked_until=NULL WHERE id=?
            """, (user_id,))
            conn.commit()
            return True, "User account unlocked successfully"
    except Exception as e:
        return False, f"Error unlocking user: {str(e)}"

    if __name__ == "__main__":
        main()


