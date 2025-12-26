# gui/Home_Page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QCheckBox
)
from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath
from PySide6.QtCore import QSize, Qt
import json
import os

from db.todo_db_helper import get_today_or_upcoming_tasks, update_task_status
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
        main_layout = QVBoxLayout(self)
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
        self.chat_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
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
        self.v_line = QFrame()
        self.v_line.setFrameShape(QFrame.VLine)
        self.v_line.setObjectName("divider")
        self.v_line.setFixedWidth(2)
        content_layout.addWidget(self.v_line)

        # ------------- TASKS PANEL -------------
        tasks_layout = QVBoxLayout()
        self.tasks_title = QLabel("To-do List")
        self.tasks_title.setObjectName("sectionTitle")
        self.tasks_title.setAlignment(Qt.AlignCenter)
        tasks_layout.addWidget(self.tasks_title)

        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        self.task_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.task_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.task_content = QWidget()
        self.task_layout = QVBoxLayout(self.task_content)
        self.task_layout.setSpacing(10)
        self.task_layout.setContentsMargins(5, 5, 5, 5)

        self.task_scroll.setWidget(self.task_content)
        tasks_layout.addWidget(self.task_scroll)

        self.new_task_btn = QPushButton("New Task")
        self.new_task_btn.setObjectName("smallButton")
        self.new_task_btn.clicked.connect(self.go_to_tasks)
        tasks_layout.addWidget(self.new_task_btn, alignment=Qt.AlignCenter)

        content_layout.addLayout(tasks_layout, stretch=1)
        main_layout.addLayout(content_layout)

    def load_chat_sessions(self):
        while self.chat_buttons_layout.count():
            item = self.chat_buttons_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        sessions = get_all_sessions()
        if not sessions:
            lbl = QLabel("No chats yet.")
            lbl.setAlignment(Qt.AlignCenter)
            self.chat_buttons_layout.addWidget(lbl)
        else:
            for session_id, title, updated_at in sessions:
                btn = QPushButton(title)
                btn.setObjectName("chatButton")
                # Enforce height to match taskRow height (50px)
                btn.setFixedHeight(50) 
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked, sid=session_id: self.open_chat_session(sid))
                self.chat_buttons_layout.addWidget(btn)
        
        self.chat_buttons_layout.addStretch()

    def refresh_chat_sessions(self):
        self.load_chat_sessions()

    def load_task_rows(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        tasks = [t for t in get_today_or_upcoming_tasks() if t[5] == 0]
        if not tasks:
            msg = QLabel("No pending tasks")
            msg.setAlignment(Qt.AlignCenter)
            layout.addWidget(msg)
            return
        for task in tasks:
            self.add_task_row(layout, task)
        layout.addStretch()

    def add_task_row(self, layout, task):
        task_id, title, task_date, task_time, created_at, is_done = task
        row = QWidget()
        row.setObjectName("taskRow")
        row.setFixedHeight(50)
        row.setCursor(Qt.PointingHandCursor)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 5, 12, 5)
        row_layout.setSpacing(15)

        checkbox = QCheckBox()
        checkbox.setChecked(is_done == 1)
        checkbox.stateChanged.connect(lambda s, tid=task_id: (update_task_status(tid, int(s == 2)), self.refresh_tasks()))

        # FIX: Removed TranslucentBackground and added Stretch
        t_lbl = QLabel(str(title))
        t_lbl.setObjectName("taskTitle")
        
        info_lbl = QLabel(f"{task_time or ''}  {task_date}")
        info_lbl.setObjectName("taskInfo")

        row_layout.addWidget(checkbox)
        row_layout.addWidget(t_lbl, 1) # '1' ensures the title fills the space
        row_layout.addWidget(info_lbl)

        row.mousePressEvent = lambda e, t=task: self.open_edit_page(*t)
        layout.addWidget(row)

    def refresh_tasks(self):
        self.load_task_rows(self.task_layout)

    def open_edit_page(self, task_id, title, task_date, task_time, created_at, is_done):
        self.edit_window = EditTaskPage(task_id, title, task_date, task_time, is_done)
        self.edit_window.task_updated.connect(self.refresh_tasks)
        self.edit_window.show()

    def load_user_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f: return json.load(f)
        return {"image": "Profile-Icon.png"}

    def set_profile_picture(self, filename):
        path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)
        if os.path.exists(path):
            pix = QPixmap(path).scaled(70, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            canvas = QPixmap(70, 70)
            canvas.fill(Qt.transparent)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.Antialiasing)
            p = QPainterPath()
            p.addEllipse(0, 0, 70, 70)
            painter.setClipPath(p)
            painter.drawPixmap(0, 0, pix)
            painter.end()
            self.profile_button.setIcon(QIcon(canvas))
            self.profile_button.setIconSize(QSize(70, 70))

    def update_data(self, data):
        self.set_profile_picture(data.get("image", ""))

    def apply_dark_mode(self, enabled):
        self.dark_mode = enabled
    
        if enabled:
            self.setStyleSheet("""
            /* Global and Typography */
            QWidget { 
                background-color: #1e1e1e; 
                font-family: Arial; 
            }
            QLabel#welcomeLabel { 
                color: #e0e0e0; 
                font-weight: bold; 
                font-size: 22px; 
            }
            QLabel#sectionTitle { 
                color: #e0e0e0; 
                font-weight: bold; 
                font-size: 20px; 
            }

            /* Buttons */
            QPushButton#chatButton { 
                background-color: #2d2d2d; 
                color: #e0e0e0; 
                padding: 10px; 
                font-weight: bold; 
                font-size: 15px; 
                border-radius: 10px; 
                border: none; 
                text-align: left; 
            }
            QPushButton#chatButton:hover { 
                background-color: #3a3a3a; 
            }
            QPushButton#smallButton { 
                background-color: #4CAF50; 
                color: white; 
                padding: 8px 15px; 
                border-radius: 6px; 
                border: none; 
            }

            /* Task Row Items */
            QWidget#taskRow { 
                background-color: #2d2d2d; 
                border-radius: 10px; 
            }
            QWidget#taskRow:hover { 
                background-color: #3a3a3a; 
            }
            QLabel#taskTitle { 
                color: #ffffff !important; 
                font-weight: bold; 
                font-size: 15px; 
                background: transparent; 
            }
            QLabel#taskInfo { 
                color: #cccccc !important; 
                font-size: 13px; 
                background: transparent; 
            }

            /* Dividers */
            QFrame#divider { 
                background-color: #444; 
            }
            """)
        else:
            self.setStyleSheet("""
            /* Global and Typography */
            QWidget { 
                background-color: #f0f0f0; 
                font-family: Arial; 
            }
            QLabel#welcomeLabel { 
                color: black; 
                font-weight: bold; 
                font-size: 22px; 
            }
            QLabel#sectionTitle { 
                color: black; 
                font-weight: bold; 
                font-size: 20px; 
            }

            /* Buttons */
            QPushButton#chatButton { 
                background-color: white; 
                color: black; 
                padding: 10px;
                font-weight: bold; 
                font-size: 15px; 
                border-radius: 10px; 
                border: none; 
                text-align: left; 
            }
            QPushButton#chatButton:hover { 
                background-color: #e0e0e0; 
            }
            QPushButton#smallButton { 
                background-color: black; 
                color: white; 
                padding: 8px 15px; 
                border-radius: 6px; 
                border: none; 
                font-weight: bold; 
            }

            /* Task Row Items (Light Mode) */
            QWidget#taskRow { 
                background-color: white; 
                border-radius: 10px; 
            }
            QWidget#taskRow:hover { 
                background-color: #e0e0e0; 
            }
            QLabel#taskTitle { 
                color: black !important; 
                font-weight: bold; 
                font-size: 15px; 
                background: transparent; 
            }
            QLabel#taskInfo { 
                color: #444444 !important; 
                font-size: 13px; 
                background: transparent; 
            }

            /* Dividers */
            QFrame#divider { 
                background-color: black; 
            }
        """)