import sqlite3
import os
from datetime import datetime

DB_FILE = "todotasks.db"
DB_PATH = os.path.join("data", DB_FILE)

def init_database():
    # Make sure the db folder exists
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            task_date TEXT,
            task_time TEXT,
            created_at TEXT,
            is_done INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def insert_task(title, task_date, task_time):
    """Insert task with proper 12-hour format for task_time."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure task_time format is like "08:43 AM"
    try:
        task_time = datetime.strptime(task_time, "%H:%M").strftime("%I:%M %p")
    except:
        # Assume user passed already correct format
        pass

    cursor.execute("""
        INSERT INTO tasks (title, task_date, task_time, created_at, is_done)
        VALUES (?, ?, ?, ?, ?)
    """, (
        title,
        task_date,
        task_time,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        0
    ))
    conn.commit()
    conn.close()

def get_all_tasks():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, task_date, task_time, created_at, is_done
        FROM tasks
        ORDER BY task_date, task_time
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def update_task_status(task_id, is_done):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET is_done = ?
        WHERE id = ?
    """, (1 if is_done else 0, task_id))

    conn.commit()
    conn.close()



def update_task(task_id, title, date, time, is_done):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE tasks
        SET title = ?, task_date = ?, task_time = ?, is_done = ?
        WHERE id = ?
    """, (title, date, time, is_done, task_id))

    conn.commit()
    conn.close()


from datetime import datetime

def get_today_or_upcoming_tasks():
    tasks = get_all_tasks()

    # Sort tasks by date + time
    try:
        tasks.sort(key=lambda x: (x[2], x[3] if x[3] else "00:00"))
    except:
        pass

    return tasks
