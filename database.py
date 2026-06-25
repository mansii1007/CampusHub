"""
database.py
===========
Database module for CampusHub - College Management System.

Handles:
    - SQLite connection management
    - Schema creation for all tables
    - Insertion of default seed data (admin, sample faculty, sample student)
    - Reusable CRUD helper functions

All other modules import the `Database` class to talk to SQLite.
"""

import os
import sqlite3
import hashlib
from datetime import datetime


# -----------------------------------------------------------------------------
# Path configuration
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DB_DIR, "campushub.db")


def hash_password(password: str) -> str:
    """Hash a plain-text password using SHA-256 and return hex digest."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Database:
    """
    Central database handler for the CampusHub application.

    Provides:
        - Connection management (context-manager friendly)
        - Schema initialization
        - Default data seeding
        - Generic CRUD helpers used across modules
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Make sure the database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Enable foreign-key support & create schema right away
        self._init_schema()
        self._seed_default_data()

    # -------------------------------------------------------------------------
    # Connection helpers
    # -------------------------------------------------------------------------
    def get_connection(self) -> sqlite3.Connection:
        """Return a new SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        # Allow column-name access from rows
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single write query and commit."""
        try:
            with self.get_connection() as conn:
                cur = conn.execute(query, params)
                conn.commit()
                return cur
        except sqlite3.Error as e:
            print(f"[DB ERROR] {e}")
            raise

    def fetch_all(self, query: str, params: tuple = ()) -> list:
        """Return all matching rows as list of dicts."""
        try:
            with self.get_connection() as conn:
                cur = conn.execute(query, params)
                return [dict(row) for row in cur.fetchall()]
        except sqlite3.Error as e:
            print(f"[DB ERROR] {e}")
            return []

    def fetch_one(self, query: str, params: tuple = ()) -> dict:
        """Return a single matching row as dict or None."""
        try:
            with self.get_connection() as conn:
                cur = conn.execute(query, params)
                row = cur.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"[DB ERROR] {e}")
            return None

    # -------------------------------------------------------------------------
    # Schema creation
    # -------------------------------------------------------------------------
    def _init_schema(self) -> None:
        """Create all tables if they do not already exist."""
        with self.get_connection() as conn:
            cur = conn.cursor()

            # --- Users (authentication for all three roles) ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    username    TEXT    UNIQUE NOT NULL,
                    password    TEXT    NOT NULL,
                    role        TEXT    NOT NULL CHECK (role IN ('admin','faculty','student')),
                    ref_id      TEXT,
                    created_at  TEXT    DEFAULT (datetime('now','localtime'))
                )
                """
            )

            # --- Departments ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS departments (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    name            TEXT UNIQUE NOT NULL,
                    hod             TEXT,
                    description     TEXT
                )
                """
            )

            # --- Students ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    roll_no     TEXT    UNIQUE NOT NULL,
                    name        TEXT    NOT NULL,
                    department  TEXT,
                    semester    INTEGER DEFAULT 1,
                    phone       TEXT,
                    email       TEXT,
                    address     TEXT,
                    cgpa        REAL    DEFAULT 0.0,
                    dob         TEXT,
                    gender      TEXT,
                    admission_date TEXT DEFAULT (date('now','localtime'))
                )
                """
            )

            # --- Faculty ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS faculty (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    faculty_id  TEXT    UNIQUE NOT NULL,
                    name        TEXT    NOT NULL,
                    department  TEXT,
                    designation TEXT,
                    phone       TEXT,
                    email       TEXT,
                    subjects    TEXT,
                    join_date   TEXT    DEFAULT (date('now','localtime'))
                )
                """
            )

            # --- Courses ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    course_id     TEXT    UNIQUE NOT NULL,
                    course_name   TEXT    NOT NULL,
                    department    TEXT,
                    semester      INTEGER,
                    credits       INTEGER DEFAULT 3,
                    faculty_id    TEXT,
                    PRIMARY KEY (course_id)
                )
                """
            )

            # --- Attendance ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id  TEXT    NOT NULL,
                    subject     TEXT,
                    date        TEXT,
                    status      TEXT    CHECK (status IN ('Present','Absent')),
                    FOREIGN KEY (student_id) REFERENCES students(roll_no)
                )
                """
            )

            # --- Marks ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS marks (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id      TEXT    NOT NULL,
                    subject         TEXT,
                    internal        REAL DEFAULT 0,
                    practical       REAL DEFAULT 0,
                    semester_exam   REAL DEFAULT 0,
                    grade           TEXT,
                    FOREIGN KEY (student_id) REFERENCES students(roll_no)
                )
                """
            )

            # --- Fees ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS fees (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id    TEXT    NOT NULL,
                    amount        REAL    NOT NULL,
                    payment_date  TEXT    DEFAULT (date('now','localtime')),
                    status        TEXT    CHECK (status IN ('Paid','Pending','Partial')),
                    receipt_no    TEXT,
                    FOREIGN KEY (student_id) REFERENCES students(roll_no)
                )
                """
            )

            # --- Library ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS library (
                    book_id      TEXT UNIQUE NOT NULL,
                    book_name    TEXT NOT NULL,
                    author       TEXT,
                    category     TEXT,
                    availability TEXT DEFAULT 'Available',
                    issued_to    TEXT,
                    issue_date   TEXT,
                    return_date  TEXT,
                    fine         REAL DEFAULT 0
                )
                """
            )

            # --- Timetable ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS timetable (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    department  TEXT,
                    semester    INTEGER,
                    day         TEXT,
                    time_slot   TEXT,
                    subject     TEXT,
                    faculty_id  TEXT,
                    room        TEXT
                )
                """
            )

            # --- Activity log (for dashboard "recent activities") ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity    TEXT,
                    created_at  TEXT DEFAULT (datetime('now','localtime'))
                )
                """
            )

            conn.commit()

    # -------------------------------------------------------------------------
    # Default seed data
    # -------------------------------------------------------------------------
    def _seed_default_data(self) -> None:
        """Insert default admin, departments, and sample accounts if absent."""
        # Default admin
        admin = self.fetch_one("SELECT * FROM users WHERE username = ?", ("admin",))
        if not admin:
            self.execute(
                "INSERT INTO users (username, password, role, ref_id) VALUES (?,?,?,?)",
                ("admin", hash_password("admin123"), "admin", "ADMIN"),
            )

        # Sample faculty login
        fac = self.fetch_one("SELECT * FROM users WHERE username = ?", ("faculty001",))
        if not fac:
            self.execute(
                "INSERT INTO users (username, password, role, ref_id) VALUES (?,?,?,?)",
                ("faculty001", hash_password("faculty123"), "faculty", "FAC001"),
            )
            # Matching faculty profile
            fac_prof = self.fetch_one("SELECT * FROM faculty WHERE faculty_id = ?", ("FAC001",))
            if not fac_prof:
                self.execute(
                    "INSERT INTO faculty (faculty_id, name, department, designation, "
                    "phone, email, subjects) VALUES (?,?,?,?,?,?,?)",
                    ("FAC001", "Dr. Anita Sharma", "Computer Science",
                     "Professor", "9876543210", "anita.sharma@campus.edu",
                     "Data Structures,Algorithms"),
                )

        # Sample student login
        stu = self.fetch_one("SELECT * FROM users WHERE username = ?", ("student001",))
        if not stu:
            self.execute(
                "INSERT INTO users (username, password, role, ref_id) VALUES (?,?,?,?)",
                ("student001", hash_password("student123"), "student", "STU001"),
            )
            stu_prof = self.fetch_one("SELECT * FROM students WHERE roll_no = ?", ("STU001",))
            if not stu_prof:
                self.execute(
                    "INSERT INTO students (roll_no, name, department, semester, "
                    "phone, email, address, cgpa) VALUES (?,?,?,?,?,?,?,?)",
                    ("STU001", "Rahul Verma", "Computer Science", 3,
                     "9123456780", "rahul.verma@campus.edu",
                     "12 MG Road, Pune", 8.4),
                )

        # Default departments
        depts = self.fetch_one("SELECT COUNT(*) AS c FROM departments")
        if depts and depts["c"] == 0:
            default_depts = [
                ("Computer Science", "Dr. Anita Sharma", "Computing & IT"),
                ("Electronics", "Dr. R. Iyer", "Electronics & Communication"),
                ("Mechanical", "Dr. S. Kulkarni", "Mechanical Engineering"),
                ("Civil", "Dr. M. Reddy", "Civil Engineering"),
                ("Management", "Dr. P. Nair", "Business Administration"),
            ]
            for d in default_depts:
                self.execute(
                    "INSERT OR IGNORE INTO departments (name, hod, description) VALUES (?,?,?)",
                    d,
                )

    # -------------------------------------------------------------------------
    # Activity log helper (used by other modules)
    # -------------------------------------------------------------------------
    def log_activity(self, activity: str) -> None:
        """Record an activity entry used by the dashboard's recent-activity feed."""
        try:
            self.execute(
                "INSERT INTO activity_log (activity) VALUES (?)",
                (activity,),
            )
        except sqlite3.Error:
            pass  # logging must never break the calling action


# -----------------------------------------------------------------------------
# Module-level convenience instance
# -----------------------------------------------------------------------------
db = Database()
