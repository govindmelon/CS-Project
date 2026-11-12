"""
LAB EQUIPMENT CIRCULATION & MAINTENANCE TRACKER
Class XII CBSE Computer Science Project
Technology: Python + MySQL

The program maintains laboratory equipment records, tracks issue/return
transactions, records maintenance activities and generates CSV reports.
"""

import csv
import os
from datetime import datetime, date
from getpass import getpass

import mysql.connector
from mysql.connector import Error

DB_HOST = "localhost"
DB_USER = "root"
DB_NAME = "lab_equipment_db"

EQUIPMENT_TABLE = "equipment"
CIRCULATION_TABLE = "circulation"
MAINTENANCE_TABLE = "maintenance"

CATEGORIES = (
    "Physics", "Chemistry", "Biology", "Computer Science", "Electronics", "Other"
)
CONDITIONS = ("Good", "Fair", "Damaged")
STATUSES = ("Available", "Issued", "Under Maintenance")


def connect_database():
    """Connect to MySQL and create the project database if required."""
    password = os.getenv("LAB_DB_PASSWORD")
    if password is None:
        password = getpass("Enter MySQL password: ")

    try:
        server = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=password
        )
        cursor = server.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.close()
        server.close()

        connection = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=password, database=DB_NAME
        )
        return connection
    except Error as error:
        print("\nDatabase connection failed:", error)
        return None


def create_tables(connection):
    """Create all three project tables if they do not already exist."""
    queries = [
        """
        CREATE TABLE IF NOT EXISTS equipment (
            equipment_id INT AUTO_INCREMENT PRIMARY KEY,
            equipment_name VARCHAR(80) NOT NULL,
            category VARCHAR(30) NOT NULL,
            serial_no VARCHAR(40) UNIQUE,
            equipment_condition VARCHAR(20) NOT NULL DEFAULT 'Good',
            status VARCHAR(25) NOT NULL DEFAULT 'Available',
            location VARCHAR(60) DEFAULT 'Laboratory',
            remarks VARCHAR(150) DEFAULT 'N/A'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS circulation (
            circulation_id INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id INT NOT NULL,
            issued_to VARCHAR(80) NOT NULL,
            issue_date DATE NOT NULL,
            due_date DATE NOT NULL,
            return_date DATE DEFAULT NULL,
            purpose VARCHAR(150) DEFAULT 'N/A',
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS maintenance (
            maintenance_id INT AUTO_INCREMENT PRIMARY KEY,
            equipment_id INT NOT NULL,
            maintenance_date DATE NOT NULL,
            maintenance_type VARCHAR(40) NOT NULL,
            description VARCHAR(150) DEFAULT 'N/A',
            cost DECIMAL(10,2) DEFAULT 0.00,
            performed_by VARCHAR(80) DEFAULT 'Not specified',
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        )
        """
    ]

    cursor = connection.cursor()
    try:
        for query in queries:
            cursor.execute(query)
        connection.commit()
    finally:
        cursor.close()


def print_heading(heading):
    """Print a centred heading between separator lines."""
    print("\n" + "=" * 76)
    print(heading.center(76))
    print("=" * 76)


def read_non_empty(prompt, maximum=80):
    """Read a non-empty string within the specified length."""
    while True:
        value = input(prompt).strip()
        if value and len(value) <= maximum:
            return value
        print(f"Enter a value containing 1 to {maximum} characters.")


def read_optional(prompt, maximum=150):
    """Read optional text and use N/A when the input is blank."""
    value = input(prompt).strip()
    if not value:
        return "N/A"
    if len(value) > maximum:
        print(f"Input is too long. It will be shortened to {maximum} characters.")
        value = value[:maximum]
    return value


def read_integer(prompt, minimum=1):
    """Read an integer greater than or equal to the specified minimum."""
    while True:
        try:
            value = int(input(prompt))
            if value >= minimum:
                return value
            print(f"Enter a number greater than or equal to {minimum}.")
        except ValueError:
            print("Please enter a valid whole number.")


def read_date(prompt):
    """Read a date in YYYY-MM-DD format and return a date object."""
    while True:
        value = input(prompt).strip()
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            print("Enter the date in YYYY-MM-DD format.")


def read_choice(options, heading):
    """Display a numbered list and return the selected option."""
    print("\n" + heading)
    for index, item in enumerate(options, start=1):
        print(f"{index}. {item}")
    while True:
        try:
            choice = int(input("Enter your choice: "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            print("Choose a number from the displayed list.")
        except ValueError:
            print("Please enter a valid number.")


def display_equipment(rows):
    """Display equipment records in a formatted table."""
    if not rows:
        print("\nNo equipment records found.")
        return

    print()
    print("-" * 112)
    print(
        f"{'ID':<6}{'EQUIPMENT':<23}{'CATEGORY':<19}"
        f"{'SERIAL NO.':<17}{'CONDITION':<14}{'STATUS':<22}{'LOCATION':<12}"
    )
    print("-" * 112)
    for row in rows:
        equipment_id, name, category, serial, condition, status, location, remarks = row
        print(
            f"{equipment_id:<6}{name[:21]:<23}{category[:17]:<19}"
            f"{str(serial or 'N/A')[:15]:<17}{condition:<14}"
            f"{status:<22}{str(location or 'N/A')[:10]:<12}"
        )
    print("-" * 112)
    print("Records displayed:", len(rows))


def get_equipment_by_id(cursor, equipment_id):
    """Fetch and return one equipment record using its ID."""
    cursor.execute(
        """
        SELECT equipment_id, equipment_name, category, serial_no,
               equipment_condition, status, location, remarks
        FROM equipment WHERE equipment_id = %s
        """,
        (equipment_id,)
    )
    return cursor.fetchone()


def add_equipment(connection):
    """Add a new item of laboratory equipment to the database."""
    print_heading("ADD NEW LAB EQUIPMENT")
    name = read_non_empty("Enter equipment name: ")
    category = read_choice(CATEGORIES, "Equipment categories:")
    serial = input("Enter serial number (press Enter if unavailable): ").strip() or None
    condition = read_choice(CONDITIONS, "Equipment condition:")
    location = read_optional("Enter laboratory/location: ", 60)
    remarks = read_optional("Enter remarks: ")

    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO equipment
            (equipment_name, category, serial_no, equipment_condition,
             status, location, remarks)
            VALUES (%s, %s, %s, %s, 'Available', %s, %s)
            """,
            (name, category, serial, condition, location, remarks)
        )
        connection.commit()
        print("\nEquipment added successfully.")
        print("Generated equipment ID:", cursor.lastrowid)
    except Error as error:
        connection.rollback()
        print("Unable to add equipment:", error)
    finally:
        cursor.close()


def show_all_equipment(connection):
    """Display all equipment records, ordered by equipment ID."""
    print_heading("ALL LAB EQUIPMENT")
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT equipment_id, equipment_name, category, serial_no,
                   equipment_condition, status, location, remarks
            FROM equipment ORDER BY equipment_id
            """
        )
        display_equipment(cursor.fetchall())
    except Error as error:
        print("Unable to retrieve equipment:", error)
    finally:
        cursor.close()


def search_equipment(connection):
    """Search for equipment by its name or serial number."""
    print_heading("SEARCH LAB EQUIPMENT")
    term = read_non_empty("Enter equipment name or serial number: ", 80)
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT equipment_id, equipment_name, category, serial_no,
                   equipment_condition, status, location, remarks
            FROM equipment
            WHERE equipment_name LIKE %s OR serial_no = %s
            ORDER BY equipment_id
            """,
            (f"%{term}%", term)
        )
        rows = cursor.fetchall()
        if rows:
            display_equipment(rows)
        else:
            print("No matching equipment found.")
    except Error as error:
        print("Search failed:", error)
    finally:
        cursor.close()


def update_equipment(connection):
    """Update the descriptive details of an existing equipment record."""
    print_heading("UPDATE EQUIPMENT DETAILS")
    equipment_id = read_integer("Enter equipment ID to update: ")
    cursor = connection.cursor()
    try:
        record = get_equipment_by_id(cursor, equipment_id)
        if record is None:
            print("Equipment record not found.")
            return

        display_equipment([record])
        print("\n1. Change equipment name")
        print("2. Change category")
        print("3. Change condition")
        print("4. Change location")
        print("5. Change remarks")
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            value = read_non_empty("Enter new equipment name: ")
            query = "UPDATE equipment SET equipment_name = %s WHERE equipment_id = %s"
        elif choice == "2":
            value = read_choice(CATEGORIES, "Equipment categories:")
            query = "UPDATE equipment SET category = %s WHERE equipment_id = %s"
        elif choice == "3":
            value = read_choice(CONDITIONS, "Equipment condition:")
            query = (
                "UPDATE equipment SET equipment_condition = %s "
                "WHERE equipment_id = %s"
            )
        elif choice == "4":
            value = read_non_empty("Enter new location: ", 60)
            query = "UPDATE equipment SET location = %s WHERE equipment_id = %s"
        elif choice == "5":
            value = read_optional("Enter new remarks: ")
            query = "UPDATE equipment SET remarks = %s WHERE equipment_id = %s"
        else:
            print("Invalid choice.")
            return

        cursor.execute(query, (value, equipment_id))
        connection.commit()
        print("Equipment details updated successfully.")
    except Error as error:
        connection.rollback()
        print("Update failed:", error)
    finally:
        cursor.close()


def delete_equipment(connection):
    """Delete an equipment record only when it has no circulation history."""
    print_heading("DELETE EQUIPMENT RECORD")
    equipment_id = read_integer("Enter equipment ID to delete: ")
    cursor = connection.cursor()
    try:
        record = get_equipment_by_id(cursor, equipment_id)
        if record is None:
            print("Equipment record not found.")
            return

        display_equipment([record])
        cursor.execute(
            "SELECT COUNT(*) FROM circulation WHERE equipment_id = %s",
            (equipment_id,)
        )
        circulation_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM maintenance WHERE equipment_id = %s",
            (equipment_id,)
        )
        maintenance_count = cursor.fetchone()[0]

        if circulation_count or maintenance_count:
            print(
                "Deletion is not allowed because this equipment has circulation "
                "or maintenance history."
            )
            print("This preserves the linked transaction records.")
            return

        confirm = input("Are you sure you want to delete it? (Y/N): ").strip().upper()
        if confirm == "Y":
            cursor.execute(
                "DELETE FROM equipment WHERE equipment_id = %s", (equipment_id,)
            )
            connection.commit()
            print("Equipment record deleted successfully.")
        else:
            print("Deletion cancelled.")
    except Error as error:
        connection.rollback()
        print("Deletion failed:", error)
    finally:
        cursor.close()


def issue_equipment(connection):
    """Issue available equipment and create a circulation transaction."""
    print_heading("ISSUE LAB EQUIPMENT")
    equipment_id = read_integer("Enter equipment ID: ")
    issued_to = read_non_empty("Enter name of person receiving equipment: ")
    issue_date = read_date("Enter issue date (YYYY-MM-DD): ")
    due_date = read_date("Enter due date (YYYY-MM-DD): ")
    if due_date < issue_date:
        print("Due date cannot be earlier than the issue date.")
        return
    purpose = read_optional("Enter purpose of issue: ")

    cursor = connection.cursor()
    try:
        record = get_equipment_by_id(cursor, equipment_id)
        if record is None:
            print("Equipment record not found.")
            return
        if record[5] != "Available":
            print("Equipment is not available. Current status:", record[5])
            return
        if record[4] == "Damaged":
            print("Damaged equipment cannot be issued.")
            return

        cursor.execute(
            """
            INSERT INTO circulation
            (equipment_id, issued_to, issue_date, due_date, purpose)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (equipment_id, issued_to, issue_date, due_date, purpose)
        )
        circulation_id = cursor.lastrowid
        cursor.execute(
            "UPDATE equipment SET status = 'Issued' WHERE equipment_id = %s",
            (equipment_id,)
        )
        connection.commit()
        print("\nEquipment issued successfully.")
        print("Generated circulation ID:", circulation_id)
    except Error as error:
        connection.rollback()
        print("Unable to issue equipment:", error)
    finally:
        cursor.close()


def return_equipment(connection):
    """Record the return of an issued item and make it available again."""
    print_heading("RETURN LAB EQUIPMENT")
    circulation_id = read_integer("Enter circulation ID: ")
    return_date = read_date("Enter return date (YYYY-MM-DD): ")
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT circulation_id, equipment_id, issued_to, issue_date,
                   due_date, return_date
            FROM circulation WHERE circulation_id = %s
            """,
            (circulation_id,)
        )
        record = cursor.fetchone()
        if record is None:
            print("Circulation record not found.")
            return
        if record[5] is not None:
            print("This equipment has already been returned.")
            return
        if return_date < record[3]:
            print("Return date cannot be earlier than the issue date.")
            return

        cursor.execute(
            """
            UPDATE circulation SET return_date = %s
            WHERE circulation_id = %s
            """,
            (return_date, circulation_id)
        )
        cursor.execute(
            "UPDATE equipment SET status = 'Available' WHERE equipment_id = %s",
            (record[1],)
        )
        connection.commit()
        print("Equipment return recorded successfully.")
        if return_date > record[4]:
            print("Note: The equipment was returned after its due date.")
    except Error as error:
        connection.rollback()
        print("Return operation failed:", error)
    finally:
        cursor.close()


def show_circulation_records(connection):
    """Display all issue and return transactions."""
    print_heading("EQUIPMENT CIRCULATION HISTORY")
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT c.circulation_id, e.equipment_name, c.issued_to,
                   c.issue_date, c.due_date, c.return_date, c.purpose
            FROM circulation c
            JOIN equipment e ON c.equipment_id = e.equipment_id
            ORDER BY c.circulation_id DESC
            """
        )
        rows = cursor.fetchall()
        if not rows:
            print("No circulation records found.")
            return
        print("-" * 112)
        print(
            f"{'CIRC ID':<10}{'EQUIPMENT':<23}{'ISSUED TO':<20}"
            f"{'ISSUE DATE':<14}{'DUE DATE':<14}{'RETURN DATE':<15}{'PURPOSE':<16}"
        )
        print("-" * 112)
        for row in rows:
            cid, name, person, issued, due, returned, purpose = row
            print(
                f"{cid:<10}{name[:21]:<23}{person[:18]:<20}"
                f"{str(issued):<14}{str(due):<14}"
                f"{str(returned or 'Pending'):<15}{str(purpose)[:14]:<16}"
            )
        print("-" * 112)
        print("Records displayed:", len(rows))
    except Error as error:
        print("Unable to retrieve circulation history:", error)
    finally:
        cursor.close()


def record_maintenance(connection):
    """Record a maintenance or repair activity for an equipment item."""
    print_heading("RECORD EQUIPMENT MAINTENANCE")
    equipment_id = read_integer("Enter equipment ID: ")
    maintenance_date = read_date("Enter maintenance date (YYYY-MM-DD): ")
    maintenance_type = read_choice(
        ("Routine Service", "Repair", "Inspection", "Calibration", "Other"),
        "Maintenance type:"
    )
    description = read_optional("Enter maintenance description: ")
    while True:
        try:
            cost = float(input("Enter maintenance cost (0 if none): "))
            if cost >= 0:
                break
            print("Cost cannot be negative.")
        except ValueError:
            print("Enter a valid amount.")
    performed_by = read_optional("Enter technician/person responsible: ", 80)

    cursor = connection.cursor()
    try:
        record = get_equipment_by_id(cursor, equipment_id)
        if record is None:
            print("Equipment record not found.")
            return

        cursor.execute(
            """
            INSERT INTO maintenance
            (equipment_id, maintenance_date, maintenance_type,
             description, cost, performed_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                equipment_id, maintenance_date, maintenance_type,
                description, cost, performed_by
            )
        )
        cursor.execute(
            """
            UPDATE equipment
            SET status = 'Under Maintenance'
            WHERE equipment_id = %s
            """,
            (equipment_id,)
        )
        maintenance_id = cursor.lastrowid
        connection.commit()
        print("Maintenance record saved successfully.")
        print("Generated maintenance ID:", maintenance_id)
        print("Equipment status changed to Under Maintenance.")
    except Error as error:
        connection.rollback()
        print("Unable to save maintenance record:", error)
    finally:
        cursor.close()


def complete_maintenance(connection):
    """Mark maintenance as complete and return the item to available status."""
    print_heading("COMPLETE EQUIPMENT MAINTENANCE")
    equipment_id = read_integer("Enter equipment ID: ")
    cursor = connection.cursor()
    try:
        record = get_equipment_by_id(cursor, equipment_id)
        if record is None:
            print("Equipment record not found.")
            return
        if record[5] != "Under Maintenance":
            print("This equipment is not marked as Under Maintenance.")
            return

        new_condition = read_choice(CONDITIONS, "Condition after maintenance:")
        remarks = read_optional("Enter completion remarks: ")
        cursor.execute(
            """
            UPDATE equipment
            SET status = 'Available', equipment_condition = %s, remarks = %s
            WHERE equipment_id = %s
            """,
            (new_condition, remarks, equipment_id)
        )
        connection.commit()
        print("Maintenance marked as complete.")
        print("Equipment status changed to Available.")
    except Error as error:
        connection.rollback()
        print("Unable to complete maintenance:", error)
    finally:
        cursor.close()


def show_maintenance_history(connection):
    """Display maintenance records along with equipment names."""
    print_heading("MAINTENANCE HISTORY")
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT m.maintenance_id, e.equipment_name, m.maintenance_date,
                   m.maintenance_type, m.description, m.cost, m.performed_by
            FROM maintenance m
            JOIN equipment e ON m.equipment_id = e.equipment_id
            ORDER BY m.maintenance_date DESC, m.maintenance_id DESC
            """
        )
        rows = cursor.fetchall()
        if not rows:
            print("No maintenance records found.")
            return
        print("-" * 112)
        print(
            f"{'ID':<7}{'EQUIPMENT':<22}{'DATE':<13}{'TYPE':<19}"
            f"{'DESCRIPTION':<23}{'COST':<12}{'PERFORMED BY':<16}"
        )
        print("-" * 112)
        for row in rows:
            mid, name, mdate, mtype, desc, cost, person = row
            print(
                f"{mid:<7}{name[:20]:<22}{str(mdate):<13}{mtype[:17]:<19}"
                f"{str(desc)[:21]:<23}{float(cost):<12.2f}{str(person)[:14]:<16}"
            )
        print("-" * 112)
        print("Records displayed:", len(rows))
    except Error as error:
        print("Unable to retrieve maintenance history:", error)
    finally:
        cursor.close()


def inventory_summary(connection):
    """Display total equipment and counts grouped by status and category."""
    print_heading("LAB INVENTORY SUMMARY")
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM equipment")
        total = cursor.fetchone()[0]
        print("Total equipment items:", total)

        cursor.execute(
            """
            SELECT status, COUNT(*) FROM equipment
            GROUP BY status ORDER BY COUNT(*) DESC
            """
        )
        print("\nStatus-wise summary:")
        rows = cursor.fetchall()
        if rows:
            for status, count in rows:
                print(f"{status:<22}: {count}")
        else:
            print("No inventory data available.")

        cursor.execute(
            """
            SELECT category, COUNT(*) FROM equipment
            GROUP BY category ORDER BY COUNT(*) DESC
            """
        )
        print("\nCategory-wise summary:")
        rows = cursor.fetchall()
        if rows:
            for category, count in rows:
                print(f"{category:<22}: {count}")
    except Error as error:
        print("Unable to generate inventory summary:", error)
    finally:
        cursor.close()


def overdue_equipment(connection):
    """List equipment that has not been returned by its due date."""
    print_heading("OVERDUE EQUIPMENT REPORT")
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT c.circulation_id, e.equipment_name, c.issued_to,
                   c.issue_date, c.due_date
            FROM circulation c
            JOIN equipment e ON c.equipment_id = e.equipment_id
            WHERE c.return_date IS NULL AND c.due_date < %s
            ORDER BY c.due_date
            """,
            (date.today(),)
        )
        rows = cursor.fetchall()
        if not rows:
            print("No overdue equipment found.")
            return
        print("-" * 86)
        print(
            f"{'CIRC ID':<10}{'EQUIPMENT':<24}{'ISSUED TO':<20}"
            f"{'ISSUE DATE':<15}{'DUE DATE':<15}"
        )
        print("-" * 86)
        for row in rows:
            cid, name, person, issued, due = row
            print(
                f"{cid:<10}{name[:22]:<24}{person[:18]:<20}"
                f"{str(issued):<15}{str(due):<15}"
            )
        print("-" * 86)
        print("Overdue items:", len(rows))
    except Error as error:
        print("Unable to generate overdue report:", error)
    finally:
        cursor.close()


def export_to_csv(connection):
    """Export equipment inventory, circulation and maintenance to CSV files."""
    print_heading("EXPORT PROJECT DATA TO CSV")
    folder = input("Enter folder name (press Enter for current folder): ").strip()
    if not folder:
        folder = "."
    try:
        os.makedirs(folder, exist_ok=True)
        exports = {
            "equipment_report.csv": """
                SELECT equipment_id, equipment_name, category, serial_no,
                       equipment_condition, status, location, remarks
                FROM equipment ORDER BY equipment_id
            """,
            "circulation_report.csv": """
                SELECT circulation_id, equipment_id, issued_to, issue_date,
                       due_date, return_date, purpose
                FROM circulation ORDER BY circulation_id
            """,
            "maintenance_report.csv": """
                SELECT maintenance_id, equipment_id, maintenance_date,
                       maintenance_type, description, cost, performed_by
                FROM maintenance ORDER BY maintenance_id
            """
        }

        cursor = connection.cursor()
        total = 0
        try:
            for filename, query in exports.items():
                cursor.execute(query)
                rows = cursor.fetchall()
                headers = [column[0] for column in cursor.description]
                path = os.path.join(folder, filename)
                with open(path, "w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow(headers)
                    writer.writerows(rows)
                total += len(rows)
                print(f"{filename}: {len(rows)} record(s) exported.")
        finally:
            cursor.close()

        print("\nCSV export completed successfully.")
        print("Folder:", os.path.abspath(folder))
        print("Total data rows exported:", total)
    except (Error, OSError) as error:
        print("CSV export failed:", error)


def display_menu():
    """Display the main menu and its numbered operations."""
    print_heading("LAB EQUIPMENT CIRCULATION & MAINTENANCE TRACKER")
    print("EQUIPMENT MANAGEMENT")
    print("1. Add new equipment")
    print("2. Display all equipment")
    print("3. Search equipment")
    print("4. Update equipment details")
    print("5. Delete equipment record")
    print("\nCIRCULATION MANAGEMENT")
    print("6. Issue equipment")
    print("7. Return equipment")
    print("8. View circulation history")
    print("\nMAINTENANCE MANAGEMENT")
    print("9. Record maintenance")
    print("10. Complete maintenance")
    print("11. View maintenance history")
    print("\nREPORTS")
    print("12. Inventory summary")
    print("13. Overdue equipment report")
    print("14. Export data to CSV")
    print("15. Exit")


def main():
    """Connect to MySQL, create tables and run the menu-driven application."""
    print_heading("WELCOME TO LAB EQUIPMENT CIRCULATION & MAINTENANCE TRACKER")
    print("A Python and MySQL based laboratory inventory management project.")

    connection = connect_database()
    if connection is None:
        print("Program terminated because the database is unavailable.")
        return

    try:
        create_tables(connection)
        print("\nDatabase connected successfully.")
        print("Equipment, circulation and maintenance tables are ready.")

        operations = {
            "1": add_equipment,
            "2": show_all_equipment,
            "3": search_equipment,
            "4": update_equipment,
            "5": delete_equipment,
            "6": issue_equipment,
            "7": return_equipment,
            "8": show_circulation_records,
            "9": record_maintenance,
            "10": complete_maintenance,
            "11": show_maintenance_history,
            "12": inventory_summary,
            "13": overdue_equipment,
            "14": export_to_csv
        }

        while True:
            display_menu()
            choice = input("\nEnter your choice (1-15): ").strip()

            if choice == "15":
                print("\nThank you for using the Lab Equipment Tracker.")
                break

            operation = operations.get(choice)
            if operation is None:
                print("Invalid choice. Please select from 1 to 15.")
                continue

            operation(connection)
            input("\nPress Enter to return to the main menu...")

    except Error as error:
        print("A database error occurred:", error)
    finally:
        if connection.is_connected():
            connection.close()
        print("\nMySQL connection closed.")


if __name__ == "__main__":
    main()
