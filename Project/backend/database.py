# ============================================================
# Database Management - Keystroke Biometric Authentication
# ============================================================

import sqlite3
import json
from pathlib import Path


# ============================================================
# Database Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "biometrics.db"

DB_NAME = str(DB_PATH)


# ============================================================
# Database Initialization
# ============================================================

def init_db():
    """
    Initialize the SQLite database and create the required tables.

    Tables:
    - users
    - audit_logs
    """

    with sqlite3.connect(DB_NAME) as conn:

        cursor = conn.cursor()

        # ====================================================
        # Users Table
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                biometric_profile TEXT NOT NULL
            )
            """
        )

        # ====================================================
        # Audit Logs Table
        # ====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                username TEXT,
                attempt_status TEXT,
                anomaly_score REAL
            )
            """
        )

        conn.commit()

    print("Database initialized successfully.")


# ============================================================
# User Management
# ============================================================

def add_user(
    username,
    password_hash,
    biometric_profile
):
    """
    Store a newly enrolled user.

    Returns:
        True  -> user successfully added
        False -> username already exists
    """

    try:

        profile_json = json.dumps(
            biometric_profile
        )

        with sqlite3.connect(DB_NAME) as conn:

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    biometric_profile
                )
                VALUES (?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    profile_json
                )
            )

            conn.commit()

        return True

    except sqlite3.IntegrityError:

        return False


def delete_user(username):
    """
    Delete a user.

    Mainly used when enrollment model creation fails after
    the database record has already been created.
    """

    with sqlite3.connect(DB_NAME) as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM users
            WHERE username = ?
            """,
            (username,)
        )

        conn.commit()


def get_user_password_hash(username):
    """
    Retrieve the bcrypt password hash for a user.

    Returns:
        Password hash string if user exists.
        None otherwise.
    """

    with sqlite3.connect(DB_NAME) as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT password_hash
            FROM users
            WHERE username = ?
            """,
            (username,)
        )

        record = cursor.fetchone()

    if record is None:
        return None

    return record[0]


def username_exists(username):
    """
    Check whether a username already exists.
    """

    return get_user_password_hash(username) is not None


# ============================================================
# Audit Logging
# ============================================================

def add_audit_log(
    username,
    attempt_status,
    anomaly_score=None
):
    """
    Store an authentication-related security event.
    """

    with sqlite3.connect(DB_NAME) as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO audit_logs (
                username,
                attempt_status,
                anomaly_score
            )
            VALUES (?, ?, ?)
            """,
            (
                username,
                attempt_status,
                anomaly_score
            )
        )

        conn.commit()


def get_all_audit_logs():
    """
    Retrieve all audit logs ordered from newest to oldest.
    """

    with sqlite3.connect(DB_NAME) as conn:

        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                timestamp,
                username,
                attempt_status,
                anomaly_score
            FROM audit_logs
            ORDER BY id DESC
            """
        )

        logs = [
            dict(row)
            for row in cursor.fetchall()
        ]

    return logs