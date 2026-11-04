"""Database operations for the desktop interface, independent of Tkinter."""

import re
from contextlib import contextmanager

from mysql.connector import Error, IntegrityError

from connect import connect_to_mysql


class StorageError(Exception):
    """A database or validation failure suitable for display in the interface."""


@contextmanager
def database():
    connection = connect_to_mysql()
    if connection is None:
        raise StorageError(
            "Could not connect to MySQL. Start MySQL and check that the database "
            "and your connection settings are correct, then click Refresh."
        )
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        yield connection, cursor
    except IntegrityError as error:
        connection.rollback()
        if error.errno == 1062:
            raise StorageError("That email address already belongs to another student.") from error
        raise StorageError("The linked record is no longer available. Refresh and try again.") from error
    except Error as error:
        connection.rollback()
        raise StorageError(f"MySQL could not complete the request: {error.msg}") from error
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def initialize():
    with database() as (connection, cursor):
        for statement in (
            """CREATE TABLE IF NOT EXISTS departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(100) NOT NULL,
                department_id INT,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                email VARCHAR(250) NOT NULL UNIQUE,
                course_id INT,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )""",
        ):
            cursor.execute(statement)
        connection.commit()


def snapshot():
    """Read one consistent set of records, including relation IDs for editing."""
    with database() as (_, cursor):
        cursor.execute("""
            SELECT d.id, d.name, COUNT(DISTINCT c.id) AS course_count,
                   COUNT(s.id) AS student_count
            FROM departments d
            LEFT JOIN courses c ON c.department_id = d.id
            LEFT JOIN students s ON s.course_id = c.id
            GROUP BY d.id, d.name ORDER BY d.name, d.id
        """)
        departments = cursor.fetchall()
        cursor.execute("""
            SELECT c.id, c.title, c.department_id, d.name AS department_name,
                   COUNT(s.id) AS student_count
            FROM courses c
            LEFT JOIN departments d ON d.id = c.department_id
            LEFT JOIN students s ON s.course_id = c.id
            GROUP BY c.id, c.title, c.department_id, d.name ORDER BY c.title, c.id
        """)
        courses = cursor.fetchall()
        cursor.execute("""
            SELECT s.id, s.name, s.email, s.course_id,
                   c.title AS course_title, c.department_id, d.name AS department_name
            FROM students s
            LEFT JOIN courses c ON c.id = s.course_id
            LEFT JOIN departments d ON d.id = c.department_id
            ORDER BY s.name, s.id
        """)
        return {"departments": departments, "courses": courses, "students": cursor.fetchall()}


TABLE_FIELDS = {
    "students": ("name", "email", "course_id"),
    "courses": ("title", "department_id"),
    "departments": ("name",),
}


def validate(entity, values):
    if entity not in TABLE_FIELDS:
        raise StorageError("Unknown record type.")
    clean = {field: values.get(field) for field in TABLE_FIELDS[entity]}
    text_field = "title" if entity == "courses" else "name"
    clean[text_field] = str(clean[text_field] or "").strip()
    limit = 50 if entity == "students" else 100
    if not clean[text_field] or len(clean[text_field]) > limit:
        raise StorageError(f"Enter a {text_field} between 1 and {limit} characters.")
    if entity == "students":
        clean["email"] = str(clean["email"] or "").strip()
        if len(clean["email"]) > 250 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", clean["email"]):
            raise StorageError("Enter a valid email address, such as name@school.edu.")
    for field in ("course_id", "department_id"):
        if field in clean and clean[field] is not None:
            try:
                clean[field] = int(clean[field])
            except (TypeError, ValueError) as error:
                raise StorageError("Select a valid linked record.") from error
            if clean[field] <= 0:
                raise StorageError("Select a valid linked record.")
    return clean


def save(entity, values, record_id=None):
    clean = validate(entity, values)
    fields = TABLE_FIELDS[entity]
    # Identifiers come exclusively from the allowlist; values are parameterized.
    with database() as (connection, cursor):
        if record_id is None:
            columns = ", ".join(fields)
            placeholders = ", ".join("%s" for _ in fields)
            cursor.execute(f"INSERT INTO {entity} ({columns}) VALUES ({placeholders})", tuple(clean[f] for f in fields))
            record_id = cursor.lastrowid
        else:
            cursor.execute(f"SELECT id FROM {entity} WHERE id = %s FOR UPDATE", (record_id,))
            if cursor.fetchone() is None:
                raise StorageError("This record was removed. Refresh the list and try again.")
            assignments = ", ".join(f"{field} = %s" for field in fields)
            cursor.execute(f"UPDATE {entity} SET {assignments} WHERE id = %s", tuple(clean[f] for f in fields) + (record_id,))
        connection.commit()
        return record_id


def delete(entity, record_id):
    if entity not in TABLE_FIELDS:
        raise StorageError("Unknown record type.")
    with database() as (connection, cursor):
        cursor.execute(f"DELETE FROM {entity} WHERE id = %s", (record_id,))
        if cursor.rowcount == 0:
            raise StorageError("This record was already removed. Refresh the list.")
        connection.commit()
