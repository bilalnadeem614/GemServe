from PySide6.QtWidgets import QApplication, QStackedWidget
import sys
import json
import os

from gui.Home_Page import HomePage
from gui.profile_update import SettingsPage
from gui.todo_page import TodoList
from gui.Chat_Bot import ChatWindow
from services.notifier import start_scheduler
from db import init_database

DATA_FILE = "user_data.json"

class App(QStackedWidget):
    def __init__(self):
        super().__init__()

        # Initialize database
        init_database()
        print("✅ Application started")

        # Load dark mode preference
        self.dark_mode = self.load_dark_mode()
        # Pages
        self.home_page = HomePage(
            self.open_settings,
            self.open_task,
            self.open_chatbot_new,
            self.open_chatbot_session  # New: open specific session
        )
        self.settings_page = SettingsPage(self.settings_saved)
        self.todo_page = TodoList(self.go_home)
        self.chatbot_page = ChatWindow(self.go_home, self.refresh_home)

        # Add pages
        self.addWidget(self.home_page)
        self.addWidget(self.settings_page)
        self.addWidget(self.todo_page)
        self.addWidget(self.chatbot_page)
        
        # Apply dark mode to all pages
        self.apply_dark_mode()
        
        # Default page
        self.setCurrentWidget(self.home_page)

        # -------- Navigation Functions ---------

    def open_settings(self):
        self.setCurrentWidget(self.settings_page)

    def settings_saved(self, data):
        # Update dark mode if changed
        self.dark_mode = data.get("dark_mode", False)
        self.apply_dark_mode()
        self.home_page.update_data(data)
        self.setCurrentWidget(self.home_page)

    def open_task(self):
        self.setCurrentWidget(self.todo_page)

    def open_chatbot_new(self):
        """Open chatbot for new session"""
        self.chatbot_page.start_new_session()
        self.setCurrentWidget(self.chatbot_page)
    def open_chatbot_session(self, session_id):
        """Open chatbot with specific session loaded"""
        self.chatbot_page.load_session(session_id)
        self.setCurrentWidget(self.chatbot_page)

    def go_home(self):
        self.refresh_home()
        self.setCurrentWidget(self.home_page)

    def refresh_home(self):
        """Refresh home page chat sessions"""
        self.home_page.refresh_chat_sessions()
    # -------- Dark Mode Functions ---------

    def load_dark_mode(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data.get("dark_mode", False)
        return False

    def apply_dark_mode(self):
        if self.dark_mode:
            self.setStyleSheet("background-color: #1e1e1e;")
            self.home_page.apply_dark_mode(True)
            self.todo_page.apply_dark_mode(True)
            self.chatbot_page.apply_dark_mode(True)
        else:
            self.setStyleSheet("background-color: #f0f0f0;")
            self.home_page.apply_dark_mode(False)
            self.todo_page.apply_dark_mode(False)
            self.chatbot_page.apply_dark_mode(False)

            # ---------------- MAIN APP ----------------
            
if __name__ == "__main__":
    app = QApplication(sys.argv)
    start_scheduler()
    window = App()
    window.resize(900, 600)
    window.setWindowTitle("GemServe - AI Assistant")
    window.show()
    sys.exit(app.exec())