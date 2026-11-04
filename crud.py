from connect import connect_to_mysql

def create_tables():
    connection = connect_to_mysql()
    if connection is None:
        print("Failed to connect to database. Please make sure MySQL is running.")
        print("If you haven't set up the database yet, please run the setup script first.")
        return

    cursor = connection.cursor()
    try:
        # 1. Departments Table (Parent)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL
                
            )
        """)

        # 2. Courses Table (Connected to Departments)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(100) NOT NULL,
                department_id INT,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
            )
        """)

        # 3. Students Table (Connected to Courses)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                email VARCHAR(250) NOT NULL UNIQUE,
                course_id INT,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        """)
        
        connection.commit()
        print("All database tables (Departments, Courses, Students) are ready!")
    except Exception as e:
        print(f"Error creating tables: {e}")
    finally:
        cursor.close()
        connection.close()
        
# Add a new department
def create_department(name):
    connection = connect_to_mysql()
    if connection is None:
        return
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO departments (name) VALUES (%s)", (name,))
        connection.commit()
        print(f"Department created with ID {cursor.lastrowid}")
    except Exception as e:
        print(f"Error creating department: {e}")
    finally:
        cursor.close()
        connection.close()

# Add a new course
def create_course(title, department_id):
    connection = connect_to_mysql()
    if connection is None:
        return
    cursor = connection.cursor()
    try:
        dept_id = int(department_id) if department_id else None
        cursor.execute("INSERT INTO courses (title, department_id) VALUES (%s, %s)", (title, dept_id))
        connection.commit()
        print(f"Course created with ID {cursor.lastrowid}")
    except Exception as e:
        print(f"Error creating course: {e}")
    finally:
        cursor.close()
        connection.close()

# Add a new student to the database.
def create_student(name, email, course_id):
    connection = connect_to_mysql()
    if connection is None:
        return

    cursor = connection.cursor()
    try:
        c_id = int(course_id) if course_id else None
        cursor.execute(
            "INSERT INTO students (name, email, course_id) VALUES (%s, %s, %s)",
            (name, email, c_id),
        )
        connection.commit()
        print(f"Student created with ID {cursor.lastrowid}")
    except Exception as e:
        print(f"Error creating student: {e}")
    finally:
        cursor.close()
        connection.close()

# Retrieve and display all students with their joined Course and Department info.
def read_students():
    connection = connect_to_mysql()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        query = """
            SELECT s.id, s.name, s.email, c.title AS course_title, d.name AS department_name
            FROM students s
            LEFT JOIN courses c ON s.course_id = c.id
            LEFT JOIN departments d ON c.department_id = d.id
            ORDER BY s.id
        """
        cursor.execute(query)
        students = cursor.fetchall()

        if not students:
            print("No students found.")
            return students

        headers = ("ID", "Name", "Email", "Course", "Department")
        rows = [
            (
                str(student["id"]),
                student["name"],
                student["email"],
                student["course_title"] or "N/A",
                student["department_name"] or "N/A"
            )
            for student in students
        ]
        
        widths = [
            max(len(header), *(len(str(row[index])) for row in rows))
            for index, header in enumerate(headers)
        ]

        def format_row(row):
            return " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row))

        print(format_row(headers))
        print("-+-".join("-" * width for width in widths))
        for row in rows:
            print(format_row(row))
        return students
    except Exception as e:
        print(f"Error reading students: {e}")
    finally:
        cursor.close()
        connection.close()

# Update the information for an existing student.
def update_student(student_id, name, email, course_id):
    connection = connect_to_mysql()
    if connection is None:
        return

    cursor = connection.cursor()
    try:
        c_id = int(course_id) if course_id else None
        cursor.execute(
            """
            UPDATE students
            SET name = %s, email = %s, course_id = %s
            WHERE id = %s
            """,
            (name, email, c_id, int(student_id)),
        )
        connection.commit()
        print(f"Student updated: {cursor.rowcount} row(s)")
    except Exception as e:
        print(f"Error updating student: {e}")
    finally:
        cursor.close()
        connection.close()

# Delete a student using the student's ID.
def delete_student(student_id):
    connection = connect_to_mysql()
    if connection is None:
        return

    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM students WHERE id = %s", (int(student_id),))
        connection.commit()
        print(f"Student deleted: {cursor.rowcount} row(s)")
    except Exception as e:
        print(f"Error deleting student: {e}")
    finally:
        cursor.close()
        connection.close()

# Helper to get student details
def get_student_details():
    name = input("Enter student name: ").strip()
    email = input("Enter student email: ").strip()
    course_id = input("Enter course ID: ").strip()
    return name, email, course_id

# Display the menu and run the selected CRUD operation.
def run_menu():
    create_tables()

    while True:
        print("\n--- Relational Student CRUD Menu ---")
        print("1. Add Department")
        print("2. Add Course")
        print("3. Add Student")
        print("4. View Students")
        print("5. Update Student")
        print("6. Delete Student")
        print("7. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            dept_name = input("Enter department name: ").strip()
            create_department(dept_name)
        elif choice == "2":
            title = input("Enter course title: ").strip()
            dept_id = input("Enter department ID for this course: ").strip()
            create_course(title, dept_id)
        elif choice == "3":
            create_student(*get_student_details())
        elif choice == "4":
            read_students()
        elif choice == "5":
            student_id = input("Enter the student ID to update: ").strip()
            details = get_student_details()
            update_student(student_id, *details)
        elif choice == "6":
            student_id = input("Enter the student ID to delete: ").strip()
            delete_student(student_id)
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    run_menu()
