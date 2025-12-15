# gui/Home_Page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QCheckBox
)
from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath
from PySide6.QtCore import QSize, Qt
import json
import os

from services.db_helper import get_today_or_upcoming_tasks, update_task_status
from gui.edit_task_page import EditTaskPage
from db import get_all_sessions

DATA_FILE = "user_data.json"

class HomePage(QWidget):
    def __init__(self, go_to_settings, go_to_tasks, go_to_chatbot, open_chat_session):
        super().__init__()

        self.go_to_settings = go_to_settings
        self.go_to_tasks = go_to_tasks
        self.go_to_chatbot = go_to_chatbot
        self.open_chat_session = open_chat_session
        self.dark_mode = False

        self.setup_ui()
        self.load_chat_sessions()
        self.load_task_rows(self.task_layout)

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ---------------- TOP NAVBAR ----------------
        navbar = QHBoxLayout()
        self.welcome_label = QLabel("Welcome")
        self.welcome_label.setObjectName("welcomeLabel")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        navbar.addWidget(self.welcome_label, stretch=1)

        self.profile_button = QPushButton()
        self.profile_button.setObjectName("profileButton")
        self.profile_button.setFixedSize(70, 70)
        user_data = self.load_user_data()
        self.set_profile_picture(user_data.get("image", ""))
        self.profile_button.clicked.connect(self.go_to_settings)
        navbar.addWidget(self.profile_button)

        main_layout.addLayout(navbar)

        # Divider
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setObjectName("divider")
        main_layout.addWidget(self.line)

        # ---------------- MAIN CONTENT ----------------
        content_layout = QHBoxLayout()

        # ------------- CHATS PANEL -------------
        chats_layout = QVBoxLayout()
        self.chats_title = QLabel("Chats")
        self.chats_title.setObjectName("sectionTitle")
        self.chats_title.setAlignment(Qt.AlignCenter)
        chats_layout.addWidget(self.chats_title)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setStyleSheet("QScrollArea { border: none; }")
        chat_container = QWidget()
        self.chat_buttons_layout = QVBoxLayout(chat_container)
        self.chat_buttons_layout.setSpacing(10)
        self.chat_buttons_layout.setContentsMargins(0,0,0,0)
        self.chat_scroll.setWidget(chat_container)
        chats_layout.addWidget(self.chat_scroll)

        self.new_chat_btn = QPushButton("New Chat")
        self.new_chat_btn.setObjectName("smallButton")
        self.new_chat_btn.clicked.connect(self.go_to_chatbot)
        chats_layout.addWidget(self.new_chat_btn, alignment=Qt.AlignCenter)

        content_layout.addLayout(chats_layout, stretch=1)

        # Vertical Divider
        divider_container = QWidget()
        divider_layout = QVBoxLayout(divider_container)
        divider_layout.setContentsMargins(0, 20, 0, 20)
        divider_layout.setSpacing(0)
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.VLine)
        self.divider.setObjectName("divider")
        self.divider.setLineWidth(2)
        self.divider.setFixedWidth(2)
        divider_layout.addWidget(self.divider)
        content_layout.addWidget(divider_container)
        content_layout.setSpacing(15)

        # ------------- TASKS PANEL (Updated) -------------
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(0,0,0,0)
        self.task_layout.setSpacing(10)

        # ------------------ TITLE LIKE CHAT PANEL ------------------
        self.tasks_title = QLabel("To-do List")
        self.tasks_title.setObjectName("sectionTitle")
        self.tasks_title.setAlignment(Qt.AlignCenter)
        self.task_layout.addWidget(self.tasks_title)

        # Scroll area for tasks
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.task_container)

        # Panel layout to include scroll + bottom button
        tasks_panel_layout = QVBoxLayout()
        tasks_panel_layout.addWidget(self.scroll_area)

        # Bottom button to add new tasks
        self.new_task_btn = QPushButton("New Task")
        self.new_task_btn.setObjectName("smallButton")
        self.new_task_btn.clicked.connect(self.go_to_tasks)
        tasks_panel_layout.addWidget(self.new_task_btn, alignment=Qt.AlignCenter)

        content_layout.addLayout(tasks_panel_layout, stretch=1)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    # ---------------- CHAT FUNCTIONS ----------------
    def load_chat_sessions(self):
        while self.chat_buttons_layout.count():
            item = self.chat_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        sessions = get_all_sessions()
        if not sessions:
            no_chats_label = QLabel("No chats yet.\nClick 'New Chat' to start!")
            no_chats_label.setObjectName("noChatsLabel")
            no_chats_label.setAlignment(Qt.AlignCenter)
            self.chat_buttons_layout.addWidget(no_chats_label)
        else:
            for session_id, title, updated_at in sessions:
                btn = QPushButton(title)
                btn.setObjectName("chatButton")
                btn.setToolTip(f"Last updated: {updated_at}")
                btn.clicked.connect(lambda checked, sid=session_id: self.open_chat_session(sid))
                self.chat_buttons_layout.addWidget(btn)
        self.chat_buttons_layout.addStretch()

    def refresh_chat_sessions(self):
        self.load_chat_sessions()

    # ---------------- TASK FUNCTIONS ----------------
    def load_task_rows(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        tasks = get_today_or_upcoming_tasks()
        tasks = [t for t in tasks if t[5] == 0]

        if not tasks:
            msg = QLabel("No pending tasks")
            msg.setAlignment(Qt.AlignCenter)
            layout.addWidget(msg)
            return

        for task in tasks:
            self.add_task_row(layout, task)

    def add_task_row(self, layout, task):
        task_id, title, task_date, task_time, created_at, is_done = task

        row = QWidget()
        row.setObjectName("taskRow")
        row.setCursor(Qt.PointingHandCursor)
        row.setFixedHeight(50)
        row.setStyleSheet("background-color: white; border-radius: 10px;")

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 5, 12, 5)
        row_layout.setSpacing(15)

        checkbox = QCheckBox()
        checkbox.setChecked(is_done == 1)
        checkbox.stateChanged.connect(lambda state, tid=task_id: update_task_status(tid, int(state == 2)))
        checkbox.setStyleSheet("""
            QCheckBox::indicator { width: 20px; height: 20px; }
            QCheckBox::indicator:unchecked { border: 2px solid #888; background: transparent; border-radius: 4px; }
            QCheckBox::indicator:checked { background-color: #4CAF50; border: 2px solid #4CAF50; border-radius: 4px; }
        """)

        title_label = QLabel(title, parent=row)
        time_label = QLabel(task_time or "No time", parent=row)
        date_label = QLabel(task_date, parent=row)
        title_label.setStyleSheet("color: #222; font-weight: bold; font-size: 15px;")
        for lbl in [time_label, date_label]:
            lbl.setStyleSheet("color: #555; font-weight: normal; font-size: 15px;")

        row_layout.addWidget(checkbox)
        row_layout.addWidget(title_label)
        row_layout.addStretch()
        row_layout.addWidget(time_label)
        row_layout.addWidget(date_label)

        def on_enter(event):
            row.setStyleSheet("background-color: #333; border-radius: 10px;")
            title_label.setStyleSheet("color: #eee; font-weight: bold; font-size: 15px;")
            for lbl in [time_label, date_label]:
                lbl.setStyleSheet("color: #eee; font-weight: normal; font-size: 15px;")
            event.accept()

        def on_leave(event):
            row.setStyleSheet("background-color: white; border-radius: 10px;")
            title_label.setStyleSheet("color: #222; font-weight: bold; font-size: 15px;")
            for lbl in [time_label, date_label]:
                lbl.setStyleSheet("color: #555; font-weight: normal; font-size: 15px;")
            event.accept()

        row.enterEvent = on_enter
        row.leaveEvent = on_leave
        row.mousePressEvent = lambda e, t=task: self.open_edit_page(*t)

        layout.addWidget(row)

    def refresh_tasks(self):
        for i in reversed(range(self.task_layout.count())):
            widget = self.task_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.load_task_rows(self.task_layout)

    def open_edit_page(self, task_id, title, task_date, task_time, created_at, is_done):
        self.edit_window = EditTaskPage(task_id, title, task_date, task_time, is_done)
        self.edit_window.task_updated.connect(self.refresh_tasks)
        self.edit_window.show()

    # ---------------- PROFILE FUNCTIONS ----------------
    def load_user_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if "image" not in data or not data["image"]:
                    data["image"] = "Profile-Icon.png"
                return data
        return {"image": "Profile-Icon.png"}

    def set_profile_picture(self, filename):
        if filename:
            image_path = self.get_image_path(filename)
            if os.path.exists(image_path):
                pix = QPixmap(image_path).scaled(70, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                circular = QPixmap(70, 70)
                circular.fill(Qt.transparent)
                painter = QPainter(circular)
                painter.setRenderHint(QPainter.Antialiasing)
                p = QPainterPath()
                p.addEllipse(0,0,70,70)
                painter.setClipPath(p)
                painter.drawPixmap(0,0,pix)
                painter.end()
                self.profile_button.setIcon(QIcon(circular))
                self.profile_button.setIconSize(QSize(70,70))
                return
        self.profile_button.setIcon(QIcon())

    def update_data(self, data):
        self.set_profile_picture(data.get("image", ""))

    def get_assets_path(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(current_dir, "..", "assets")
        return assets_dir

    def get_image_path(self, filename):
        if not filename:
            return ""
        return os.path.join(self.get_assets_path(), filename)

    # ---------------- DARK MODE ----------------
    def apply_dark_mode(self, enabled):
        self.dark_mode = enabled
        if enabled:
            self.setStyleSheet("""
                QWidget { background-color: #1e1e1e; font-family: Arial; }
                QLabel#welcomeLabel { font-size: 22px; color: #e0e0e0; font-weight: bold; background: transparent; }
                QLabel#sectionTitle { font-size: 20px; color: #e0e0e0; font-weight: bold; padding: 8px; }
                QLabel#noChatsLabel { color: #888; font-size: 14px; padding: 20px; }
                QPushButton#chatButton, QPushButton#taskButton { background-color: #2d2d2d; padding: 10px; margin:5px; border-radius:6px; font-size:15px; text-align:left; color:#e0e0e0; }
                QPushButton#chatButton:hover, QPushButton#taskButton:hover { color:white; background-color:#3a3a3a; }
                QPushButton#smallButton { background-color:#4CAF50; color:white; text-align:center; padding:8px 12px; border-radius:6px; margin:8px 0; font-size:14px; }
                QPushButton#smallButton:hover { background-color:#45a049; }
                QPushButton#profileButton { border:none; border-radius:35px; padding:0; margin:0; background-color:#2d2d2d; }
                QFrame#divider { background-color: #ffffff; border:none; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { background-color:#f0f0f0; font-family: Arial; }
                QLabel#welcomeLabel { font-size: 22px; color:black; font-weight:bold; }
                QLabel#sectionTitle { font-size:20px; color:black; font-weight:bold; padding:8px; }
                QLabel#noChatsLabel { color:#666; font-size:14px; padding:20px; }
                QPushButton#chatButton, QPushButton#taskButton { background-color:white; padding:10px; margin:5px; border-radius:6px; font-size:15px; text-align:left; color:black; }
                QPushButton#chatButton:hover, QPushButton#taskButton:hover { color:white; background-color:black; }
                QPushButton#smallButton { background-color:black; color:white; text-align:center; padding:8px 12px; border-radius:6px; margin:8px 0; font-size:14px; }
                QPushButton#smallButton:hover { background-color:#333; color:white; }
                QPushButton#profileButton { border:none; border-radius:35px; padding:0; margin:0; background-color:#ddd; }
                QFrame#divider { background-color:#000; border:none; }
            """)
