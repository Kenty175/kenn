import os
import unittest
import uuid
from unittest.mock import patch

import storage
from connect import connect_to_mysql


class ValidationTests(unittest.TestCase):
    def test_student_input_is_trimmed(self):
        self.assertEqual(storage.validate("students", {
            "name": "  Ada Lovelace  ", "email": " ada@example.edu ", "course_id": "12",
        }), {"name": "Ada Lovelace", "email": "ada@example.edu", "course_id": 12})

    def test_invalid_records_are_rejected(self):
        cases = [
            ("departments", {"name": " "}),
            ("courses", {"title": "A" * 101}),
            ("students", {"name": "A" * 51, "email": "a@example.edu"}),
            ("students", {"name": "Ada", "email": "invalid"}),
            ("students", {"name": "Ada", "email": "a@example.edu", "course_id": "wrong"}),
            ("courses", {"title": "Computing", "department_id": -1}),
            ("unexpected_table", {"name": "Ada"}),
        ]
        for entity, values in cases:
            with self.subTest(entity=entity, values=values):
                with self.assertRaises(storage.StorageError):
                    storage.validate(entity, values)

    def test_unassigned_relations_are_allowed(self):
        result = storage.validate("courses", {"title": "Computing", "department_id": None})
        self.assertIsNone(result["department_id"])

    def test_unavailable_database_has_actionable_error(self):
        with patch("storage.connect_to_mysql", return_value=None):
            with self.assertRaisesRegex(storage.StorageError, "Start MySQL"):
                storage.snapshot()


@unittest.skipUnless(os.getenv("RUN_MYSQL_TESTS") == "1", "Set RUN_MYSQL_TESTS=1 for isolated MySQL tests")
class MySQLIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = connect_to_mysql()
        if cls.admin is None:
            raise RuntimeError("MySQL must be running for integration tests")
        cls.database_name = "studenthub_test_" + uuid.uuid4().hex
        cursor = cls.admin.cursor()
        try:
            cursor.execute(f"CREATE DATABASE `{cls.database_name}`")
        finally:
            cursor.close()
        cls.environment = patch.dict(os.environ, {"MYSQL_DATABASE": cls.database_name})
        cls.environment.start()
        try:
            storage.initialize()
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.environment.stop()
        cursor = cls.admin.cursor()
        try:
            cursor.execute(f"DROP DATABASE `{cls.database_name}`")
        finally:
            cursor.close()
            cls.admin.close()

    def test_crud_persistence_relations_and_cascades(self):
        department_id = storage.save("departments", {"name": "Computing"})
        course_id = storage.save("courses", {"title": "Information Management", "department_id": department_id})
        student_id = storage.save("students", {"name": "Ada", "email": "ada@example.edu", "course_id": course_id})
        loaded = storage.snapshot()
        self.assertEqual(loaded["students"][0]["department_name"], "Computing")
        self.assertEqual(loaded["students"][0]["course_id"], course_id)
        self.assertEqual(loaded["departments"][0]["course_count"], 1)
        self.assertEqual(loaded["courses"][0]["student_count"], 1)

        storage.save("students", {"name": "Ada Updated", "email": "updated@example.edu", "course_id": course_id}, student_id)
        self.assertEqual(storage.snapshot()["students"][0]["name"], "Ada Updated")
        storage.save("courses", {"title": "Database Systems", "department_id": department_id}, course_id)
        storage.save("departments", {"name": "Technology"}, department_id)
        loaded = storage.snapshot()
        self.assertEqual(loaded["students"][0]["course_title"], "Database Systems")
        self.assertEqual(loaded["students"][0]["department_name"], "Technology")

        with self.assertRaisesRegex(storage.StorageError, "already belongs"):
            storage.save("students", {"name": "Duplicate", "email": "updated@example.edu", "course_id": None})
        with self.assertRaises(storage.StorageError):
            storage.save("courses", {"title": "Missing parent", "department_id": 999999})
        self.assertEqual(len(storage.snapshot()["courses"]), 1)

        storage.delete("students", student_id)
        self.assertEqual(storage.snapshot()["students"], [])
        storage.save("students", {"name": "Grace", "email": "grace@example.edu", "course_id": course_id})
        storage.delete("departments", department_id)
        self.assertEqual(storage.snapshot(), {"departments": [], "courses": [], "students": []})

        with self.assertRaisesRegex(storage.StorageError, "removed"):
            storage.save("students", {"name": "Missing", "email": "missing@example.edu", "course_id": None}, student_id)


if __name__ == "__main__":
    unittest.main()
