# StudentHub

A Python desktop frontend for the existing MySQL student records application.

## Run

Requires Python 3.10+ with Tkinter (included with the standard Windows Python installer) and a running MySQL server.

```powershell
python -m pip install -r requirements.txt
python app.py
```

The default connection is `127.0.0.1:3306`, user `root`, blank password, database `three_tb_db`, matching the original application. Create the database first if needed:

```sql
CREATE DATABASE IF NOT EXISTS three_tb_db;
```

The app creates missing tables automatically and uses your existing records. You can override connection settings in PowerShell before launching:

```powershell
$env:MYSQL_HOST = "127.0.0.1"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "your-password"
$env:MYSQL_DATABASE = "three_tb_db"
python app.py
```

## Features

- Add, view, edit, and delete students, courses, and departments.
- Search records and filter students by course or courses by department.
- Select related records by name rather than entering database IDs.
- View live record totals and export the current filtered list as CSV.
- Validate required fields and email addresses, with duplicate-email feedback.
- Load and save in the background so the window stays responsive.
- Double-click a row to edit. Press Ctrl+F to search or Ctrl+N to add.

Deleting a course also deletes its students. Deleting a department also deletes its courses and their students, as defined by the existing database schema. The app asks for confirmation and shows the affected counts before deletion.

The original command-line application remains available with `python crud.py`.

## Checks

```powershell
python -m unittest discover -s tests -v
```

Database integration tests are optional. They create and remove their own temporary database and require a MySQL account with database creation privileges:

```powershell
$env:RUN_MYSQL_TESTS = "1"
python -m unittest discover -s tests -v
```
