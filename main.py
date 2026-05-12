from PySide6.QtWidgets import QApplication, QStackedWidget
import sys
import json
import os
import logging

from gui.Home_Page import HomePage
from gui.profile_update import SettingsPage
from gui.todo_page import TodoList
from gui.Chat_Bot import ChatWindow
from services.notifier import start_scheduler
from db import init_database
from services.model_manager import ModelManager

DATA_FILE = "user_data.json"


logger = logging.getLogger(__name__)

class App(QStackedWidget):
    def __init__(self):
        super().__init__()

        # Initialize database
        init_database()
        print("✅ Application started")

        # Load dark mode preference
        self.dark_mode = self.load_dark_mode()
        self.model_manager = ModelManager()
        try:
            logger.info("Loading tiny Whisper model at app startup...")
            self.model_manager.get_tiny_model()
            logger.info("Tiny Whisper model warmed at startup.")
        except Exception as exc:
            logger.warning("Tiny Whisper model could not be warmed at startup: %s", exc)
        # Pages
        self.home_page = HomePage(
            self.open_settings,
            self.open_task,
            self.open_chatbot_new,
            self.open_chatbot_session  # New: open specific session
        )
        self.settings_page = SettingsPage(self.settings_saved)
        self.todo_page = TodoList(self.go_back_home_and_refresh)
        self.chatbot_page = ChatWindow(self.go_home, self.refresh_home, model_manager=self.model_manager)
        self.wake_word_detector = None

        try:
            self.wake_word_detector = self.chatbot_page.setup_wake_word_detector(self.model_manager)
            self.chatbot_page.wake_word_detector = self.wake_word_detector
            logger.info("Wake word detector initialized.")
        except RuntimeError as exc:
            self.wake_word_detector = None
            logger.warning("Wake word detector unavailable: %s", exc)
        except Exception as exc:
            self.wake_word_detector = None
            logger.exception("Unexpected wake word detector initialization failure.")

        self.home_page.task_status_changed.connect(self.todo_page.refresh_page)
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

    def _switch_page(self, target_widget):
        """Switch pages while managing wake-word detector lifecycle."""
        current_widget = self.currentWidget()

        if current_widget is self.chatbot_page and target_widget is not self.chatbot_page:
            logger.info("Stopping wake word detection before leaving ChatWindow.")
            self.chatbot_page.stop_wake_word_detection()

        self.setCurrentWidget(target_widget)

        if target_widget is self.chatbot_page:
            logger.info("Starting wake word detection for ChatWindow.")
            self.chatbot_page.start_wake_word_detection()

    def open_settings(self):
        self._switch_page(self.settings_page)

    def settings_saved(self, data):
        # Update dark mode if changed
        self.dark_mode = data.get("dark_mode", False)
        self.apply_dark_mode()
        self.home_page.update_data(data)
        self._switch_page(self.home_page)

    def open_task(self):
        self._switch_page(self.todo_page)

    def open_chatbot_new(self):
        """Open chatbot for new session"""
        logger.info("New Chat clicked. Switching to ChatWindow and starting wake-word detection.")
        self.chatbot_page.start_new_session()
        self._switch_page(self.chatbot_page)

    def open_chatbot_session(self, session_id):
        """Open chatbot with specific session loaded"""
        self.chatbot_page.load_session(session_id)
        self._switch_page(self.chatbot_page)

    def go_home(self):
        self.refresh_home()
        self._switch_page(self.home_page)

    def refresh_home(self):
        """Refresh home page chat sessions"""
        self.home_page.refresh_chat_sessions()
    # -------- Dark Mode Functions ---------

    def go_back_home_and_refresh(self):
        self.home_page.refresh_tasks()
        self._switch_page(self.home_page)

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

    def closeEvent(self, event):
        if getattr(self, "wake_word_detector", None) is not None:
            logger.info("Stopping wake word detector.")
            try:
                self.wake_word_detector.stop_detector_gracefully()
            except Exception:
                logger.exception("Failed to stop wake word detector cleanly.")
        super().closeEvent(event)

            # ---------------- MAIN APP ----------------
            
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    app = QApplication(sys.argv)
    start_scheduler()
    window = App()
    window.resize(900, 600)
    window.setWindowTitle("GemServe - AI Assistant")
    window.show()
    sys.exit(app.exec())