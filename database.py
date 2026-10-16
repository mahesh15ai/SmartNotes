import sqlite3


def create_database():
    connection = sqlite3.connect("notes.db")

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_material TEXT NOT NULL,
            summary TEXT NOT NULL,
            key_points TEXT,
            revision_questions TEXT
        )
    """)

    connection.commit()
    connection.close()


if __name__ == "__main__":
    create_database()
    print("Database created successfully!")