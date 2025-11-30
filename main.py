# main.py
from PySide6.QtWidgets import QApplication, QStackedWidget

import sys
from gui.Home_Page import HomePage
from gui.profile_update import SettingsPage
from gui.todo_page import TodoList

class App(QStackedWidget):
    def __init__(self):
        super().__init__()

        # Pages
        self.home_page = HomePage(self.open_settings, self.open_task)
        self.settings_page = SettingsPage(self.settings_saved)
        self.todo_page = TodoList(self.go_home)

        # Add pages to the stack
        self.addWidget(self.home_page)
        self.addWidget(self.settings_page)
        self.addWidget(self.todo_page)
        
        # Default page
        self.setCurrentWidget(self.home_page)

    def open_settings(self):
        """Navigate to Settings Page"""
        self.setCurrentWidget(self.settings_page)

    def settings_saved(self, data):
        """
        Called when user presses 'Save' in Settings page.
        data = { 'name': ..., 'email': ..., 'image_path': ... }
        """
        self.home_page.update_data(data)
        self.setCurrentWidget(self.home_page)

    def open_task(self):
        """Navigate to Todo List Page"""
        self.setCurrentWidget(self.todo_page)
        
    def go_home(self):
        """Navigate back to Home Page"""
        self.setCurrentWidget(self.home_page)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.resize(900, 600)
    window.setStyleSheet("background-color: #f0f0f0;")
    window.setWindowTitle("AI Assistant")
    window.show()
    sys.exit(app.exec())
