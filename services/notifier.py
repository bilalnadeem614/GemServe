# notifier.py
import schedule
import time
import sqlite3
from datetime import datetime, timedelta
from plyer import notification
import threading
import os
from services.db_helper import update_task_status


DB_FILE = "todotasks.db"
DB_PATH = os.path.join("db", DB_FILE)


def check_due_tasks():
    """Check DB for tasks due today at current time and send notification."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")  # e.g., "2025-12-08"
        now_str = now.strftime("%I:%M %p").lower()  # e.g., "08:43 am"

        # Select tasks that are for today AND not done
        cursor.execute("""
            SELECT id, title FROM tasks
            WHERE task_date = ? AND LOWER(task_time) = ? AND is_done = 0
        """, (today_str, now_str))

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            id = row[0]
            title = row[1]

            notification.notify(
                title="⏰ Task Reminder",
                message=title,
                timeout=10
            )
            print("Reminder sent:", title)
            update_task_status(id, 1)

            
    except Exception as e:
        print("Error in check_due_tasks:", e)


def start_scheduler():
    """Start the scheduler in a separate thread."""
    schedule.every(1).minutes.do(check_due_tasks)
    print("Notification scheduler running...")

    def run():
        while True:
            schedule.run_pending()
            time.sleep(5)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
