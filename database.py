import sqlite3
import os
import sys
import shutil
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import re
from contextlib import contextmanager

APP_NAME = "EmploymentAgentSystem"


# ---------------- PATHS ----------------
def app_data_dir():
    """
    Writable per-user folder for the database and CV files.
    A double-clicked .app starts with '/' as its working directory (read-only),
    so we never rely on relative paths for user data.
    """
    if sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/.local/share")

    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def resource_path(name):
    """
    Path to a file bundled inside the app (e.g. logo.png).
    Works both when running from source and from a PyInstaller build.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


DATA_DIR = app_data_dir()
DB = os.path.join(DATA_DIR, "employment_agent.db")
CV_STORAGE_DIR = os.path.join(DATA_DIR, "cv_files")

# Ensure CV storage directory exists
os.makedirs(CV_STORAGE_DIR, exist_ok=True)


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB)
    try:
        yield conn
    finally:
        conn.close()


# ---------------- VALIDATION ----------------
def validate_email(email):
    """Validate email format"""
    if not email:
        return True  # Email is optional
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone):
    """Validate phone number format (South African format)"""
    if not phone:
        return True  # Phone is optional
    # Remove spaces and common separators
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    # Check for valid SA phone number (10 digits starting with 0, or with country code)
    return re.match(r'^(0\d{9}|\+27\d{9}|27\d{9})$', phone) is not None


def validate_id_number(id_number):
    """Basic South African ID number validation"""
    if not id_number:
        return True  # ID is optional
    # Remove spaces
    id_number = id_number.replace(' ', '')
    # Check if 13 digits
    if not re.match(r'^\d{13}$', id_number):
        return False
    return True


# ---------------- CV FILE MANAGEMENT ----------------
def resolve_cv_path(cv_path):
    """
    Return an absolute path for a stored CV path.
    Older records may hold a relative path like 'cv_files/12_Name.pdf';
    those are resolved against the app data folder.
    """
    if not cv_path:
        return cv_path
    if os.path.isabs(cv_path):
        return cv_path
    return os.path.join(DATA_DIR, cv_path)


def save_cv_file(source_path, candidate_name, candidate_id=None):
    """
    Copy CV file to storage directory with organized naming
    Returns the stored file path or None if failed
    """
    if not source_path or not os.path.exists(source_path):
        return None

    try:
        # Get file extension
        _, ext = os.path.splitext(source_path)

        # Create sanitized filename
        safe_name = re.sub(r'[^\w\s-]', '', candidate_name).strip().replace(' ', '_')

        # Create unique filename
        if candidate_id:
            filename = f"{candidate_id}_{safe_name}{ext}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_{timestamp}{ext}"

        dest_path = os.path.join(CV_STORAGE_DIR, filename)

        # Copy file
        shutil.copy2(source_path, dest_path)
        return dest_path
    except Exception as e:
        print(f"Error saving CV file: {e}")
        return None


def delete_cv_file(cv_path):
    """Delete CV file from storage"""
    cv_path = resolve_cv_path(cv_path)
    if cv_path and os.path.exists(cv_path):
        try:
            os.remove(cv_path)
            return True
        except Exception as e:
            print(f"Error deleting CV file: {e}")
            return False
    return False


# ---------------- CANDIDATES ----------------
def create_candidates_table():
    """Create candidates table with CV path column"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                id_number TEXT,
                cell TEXT,
                email TEXT,
                experience TEXT,
                cv_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def add_candidate(full_name, id_number="", cell="", email="", experience="", cv_source_path=""):
    """
    Add a new candidate with validation
    Returns tuple (success: bool, message: str, candidate_id: int or None)
    """
    # Validation
    if not full_name or full_name.strip() == "":
        return False, "Full name is required", None

    if email and not validate_email(email):
        return False, "Invalid email format", None

    if cell and not validate_phone(cell):
        return False, "Invalid phone number format", None

    if id_number and not validate_id_number(id_number):
        return False, "Invalid ID number format (should be 13 digits)", None

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # First insert without CV path to get the ID
            cur.execute("""
                INSERT INTO candidates (full_name, id_number, cell, email, experience, cv_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (full_name.strip(), id_number.strip(), cell.strip(), email.strip(), experience.strip(), ""))

            candidate_id = cur.lastrowid

            # Now save CV with the candidate ID
            cv_path = ""
            if cv_source_path:
                cv_path = save_cv_file(cv_source_path, full_name, candidate_id)
                if cv_path:
                    cur.execute("UPDATE candidates SET cv_path=? WHERE id=?", (cv_path, candidate_id))

            conn.commit()
            return True, "Candidate added successfully", candidate_id

    except sqlite3.IntegrityError as e:
        return False, f"Database error: {str(e)}", None
    except Exception as e:
        return False, f"Error adding candidate: {str(e)}", None


def update_candidate(candidate_id, full_name, id_number, cell, email, experience, cv_source_path=""):
    """
    Update candidate with validation
    Returns tuple (success: bool, message: str)
    """
    # Validation
    if not full_name or full_name.strip() == "":
        return False, "Full name is required"

    if email and not validate_email(email):
        return False, "Invalid email format"

    if cell and not validate_phone(cell):
        return False, "Invalid phone number format"

    if id_number and not validate_id_number(id_number):
        return False, "Invalid ID number format (should be 13 digits)"

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # Get current CV path
            cur.execute("SELECT cv_path FROM candidates WHERE id=?", (candidate_id,))
            row = cur.fetchone()
            if not row:
                return False, "Candidate not found"

            old_cv_path = row[0]
            cv_path = old_cv_path

            # Handle CV update
            if cv_source_path and cv_source_path != old_cv_path:
                new_cv_path = save_cv_file(cv_source_path, full_name, candidate_id)
                if new_cv_path:
                    cv_path = new_cv_path
                    # Delete old CV file (only if it is a different file)
                    if old_cv_path and resolve_cv_path(old_cv_path) != new_cv_path:
                        delete_cv_file(old_cv_path)

            # Update database
            cur.execute("""
                UPDATE candidates
                SET full_name=?,
                    id_number=?,
                    cell=?,
                    email=?,
                    experience=?,
                    cv_path=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (full_name.strip(), id_number.strip(), cell.strip(),
                  email.strip(), experience.strip(), cv_path, candidate_id))

            conn.commit()
            return True, "Candidate updated successfully"

    except Exception as e:
        return False, f"Error updating candidate: {str(e)}"


def delete_candidate(candidate_id):
    """
    Delete candidate and associated CV file
    Returns tuple (success: bool, message: str)
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # Get CV path before deleting
            cur.execute("SELECT cv_path FROM candidates WHERE id=?", (candidate_id,))
            row = cur.fetchone()
            if not row:
                return False, "Candidate not found"

            cv_path = row[0]

            # Delete from database
            cur.execute("DELETE FROM candidates WHERE id=?", (candidate_id,))
            conn.commit()

            # Delete CV file
            if cv_path:
                delete_cv_file(cv_path)

            return True, "Candidate deleted successfully"

    except Exception as e:
        return False, f"Error deleting candidate: {str(e)}"


def get_all_candidates():
    """Get all candidates ordered by creation date"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, full_name, id_number, cell, email, experience, cv_path
                FROM candidates
                ORDER BY created_at DESC
            """)
            return cur.fetchall()
    except Exception as e:
        print(f"Error fetching candidates: {e}")
        return []


def search_candidates(term):
    """Search candidates by name, ID, phone, or email"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            query = """
                SELECT id, full_name, id_number, cell, email, experience, cv_path
                FROM candidates
                WHERE full_name LIKE ?
                OR id_number LIKE ?
                OR cell LIKE ?
                OR email LIKE ?
                ORDER BY created_at DESC
            """
            term = f"%{term}%"
            cur.execute(query, (term, term, term, term))
            return cur.fetchall()
    except Exception as e:
        print(f"Error searching candidates: {e}")
        return []


# ---------------- EXPORT ----------------
def export_candidates_to_excel(rows, filename="candidates.xlsx"):
    """Export candidates to Excel with improved formatting"""
    try:
        if not rows:
            return False, "No candidates to export"

        wb = Workbook()
        ws = wb.active
        ws.title = "Candidates"

        # Headers
        headers = ["ID", "Full Name", "ID Number", "Cell", "Email", "Experience", "CV Path"]
        ws.append(headers)

        # Make headers bold
        for cell in ws[1]:
            cell.font = Font(bold=True)

        # Add data
        for row in rows:
            ws.append([str(r) if r else "" for r in row])

        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        wb.save(filename)
        return True, f"Exported {len(rows)} candidates to {filename}"

    except Exception as e:
        return False, f"Error exporting to Excel: {str(e)}"


def export_candidates_to_pdf(rows, filename="candidates.pdf"):
    """Export candidates to PDF with improved formatting"""
    try:
        if not rows:
            return False, "No candidates to export"

        doc = SimpleDocTemplate(filename, pagesize=letter)
        elements = []

        # Title
        styles = getSampleStyleSheet()
        title = Paragraph("<b>Candidates Report</b>", styles['Title'])
        elements.append(title)

        # Date
        date_text = Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                              styles['Normal'])
        elements.append(date_text)
        elements.append(Paragraph("<br/>", styles['Normal']))

        # Table data
        headers = ["ID", "Name", "ID Number", "Cell", "Email", "Experience"]
        data = [headers]

        for row in rows:
            # Exclude CV path from PDF, truncate long fields
            formatted_row = [
                str(row[0]),
                str(row[1])[:30],
                str(row[2])[:13] if row[2] else "",
                str(row[3])[:15] if row[3] else "",
                str(row[4])[:30] if row[4] else "",
                str(row[5])[:40] if row[5] else ""
            ]
            data.append(formatted_row)

        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))

        elements.append(table)
        doc.build(elements)

        return True, f"Exported {len(rows)} candidates to {filename}"

    except Exception as e:
        return False, f"Error exporting to PDF: {str(e)}"


# ---------------- SETTINGS ----------------
def create_settings_table():
    """Create settings table"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def set_setting(key, value):
    """Set a configuration value"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error setting configuration: {e}")
        return False


def get_setting(key, default=None):
    """Get a configuration value"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = cur.fetchone()
            return row[0] if row else default
    except Exception as e:
        print(f"Error getting configuration: {e}")
        return default