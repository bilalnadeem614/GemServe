# main.py
from PySide6.QtWidgets import QApplication, QStackedWidget
import sys

from gui.Home_Page import HomePage
from gui.profile_update import SettingsPage
from gui.todo_page import TodoList
from gui.Chat_Bot import ChatWindow   # <-- Chatbot import


class App(QStackedWidget):
    def __init__(self):
        super().__init__()

        # Pages
        self.home_page = HomePage(
            self.open_settings,
            self.open_task,
            self.open_chatbot  # <-- Chatbot ko open karne ka function
        )

        self.settings_page = SettingsPage(self.settings_saved)
        self.todo_page = TodoList(self.go_home)
        self.chatbot_page = ChatWindow(self.go_home)   # <-- Pass go_home callback

        # Add pages
        self.addWidget(self.home_page)
        self.addWidget(self.settings_page)
        self.addWidget(self.todo_page)
        self.addWidget(self.chatbot_page)  # <-- Added chatbot page
        
        # Default page
        self.setCurrentWidget(self.home_page)

    # -------- Navigation Functions ---------

    def open_settings(self):
        self.setCurrentWidget(self.settings_page)

    def settings_saved(self, data):
        self.home_page.update_data(data)
        self.setCurrentWidget(self.home_page)

    def open_task(self):
        self.setCurrentWidget(self.todo_page)

    def open_chatbot(self):   # <-- NEW
        self.setCurrentWidget(self.chatbot_page)

    def go_home(self):
        self.setCurrentWidget(self.home_page)


# ---------------- MAIN APP ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.resize(900, 600)
    window.setStyleSheet("background-color: #f0f0f0;")
    window.setWindowTitle("AI Assistant")
    window.show()
    sys.exit(app.exec())
