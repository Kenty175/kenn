import time
import unittest
from unittest.mock import patch

from app import RecordDialog, StudentHub
from storage import StorageError


DATA = {
    "departments": [{"id": 1, "name": "Computing", "course_count": 1, "student_count": 1}],
    "courses": [{"id": 2, "title": "Databases", "department_id": 1,
                 "department_name": "Computing", "student_count": 1}],
    "students": [
        {"id": 3, "name": "Ada", "email": "ada@example.edu", "course_id": 2,
         "course_title": "Databases", "department_id": 1, "department_name": "Computing"},
        {"id": 4, "name": "Grace", "email": "grace@example.edu", "course_id": None,
         "course_title": None, "department_id": None, "department_name": None},
    ],
}


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.initialize = patch("app.storage.initialize").start()
        self.snapshot = patch("app.storage.snapshot", return_value=DATA).start()
        self.addCleanup(patch.stopall)
        self.app = StudentHub()
        self.app.withdraw()
        self.addCleanup(self.app.destroy)
        self.wait_for(lambda: self.app.ready)

    def wait_for(self, condition):
        deadline = time.monotonic() + 4
        while not condition() and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.assertTrue(condition(), "Desktop operation timed out")

    def test_navigation_search_and_relation_filter(self):
        self.assertEqual(len(self.app.table.get_children()), 2)
        self.app.search.set("ADA@")
        self.assertEqual(self.app.table.get_children(), ("3",))
        self.app.search.set("")
        self.app.filter.set("Unassigned")
        self.app.render()
        self.assertEqual(self.app.table.get_children(), ("4",))
        self.app.table.selection_set("4")
        self.app.navigate("courses")
        self.assertEqual(self.app.table.get_children(), ("2",))
        self.assertIsNone(self.app.selected())
        self.app.navigate("departments")
        self.assertEqual(self.app.table.get_children(), ("1",))

    def test_edit_form_preserves_course_and_reports_save_failure(self):
        dialog = RecordDialog(self.app, "students", DATA["students"][0])
        dialog.withdraw()
        self.assertEqual(dialog.fields["course_id"].get(), "Databases · #2")
        dialog.fields["email"].set("invalid")
        dialog.save()
        self.assertIn("valid email", dialog.error.cget("text"))
        dialog.fields["email"].set("ada@example.edu")
        with patch("app.storage.save", side_effect=StorageError("Duplicate email")):
            dialog.save()
            self.wait_for(lambda: not dialog.saving)
        self.assertEqual(dialog.error.cget("text"), "Duplicate email")
        self.assertTrue(dialog.winfo_exists())
        dialog.close()

    def test_successful_save_refreshes_and_closes_form(self):
        dialog = RecordDialog(self.app, "departments", None)
        dialog.withdraw()
        dialog.fields["name"].set("Science")
        with patch("app.storage.save", return_value=10) as save:
            dialog.save()
            self.wait_for(lambda: not dialog.winfo_exists() and not self.app.busy)
        save.assert_called_once_with("departments", {"name": "Science"}, None)
        self.assertGreaterEqual(self.snapshot.call_count, 2)

    def test_refresh_failure_keeps_loaded_records_and_allows_retry(self):
        with patch("app.storage.snapshot", side_effect=StorageError("Database unavailable")):
            self.app.refresh()
            self.wait_for(lambda: not self.app.busy)
        self.assertFalse(self.app.ready)
        self.assertEqual(len(self.app.table.get_children()), 2)
        self.assertEqual(str(self.app.add_button.cget("state")), "disabled")
        self.app.refresh()
        self.wait_for(lambda: self.app.ready and not self.app.busy)
        self.assertEqual(str(self.app.add_button.cget("state")), "normal")


if __name__ == "__main__":
    unittest.main()
