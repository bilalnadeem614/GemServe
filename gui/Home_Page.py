# gui/Home_Page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea
)
from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath, Qt
from PySide6.QtCore import QSize
import json
import os

# Import database functions
from db import get_all_sessions

DATA_FILE = "user_data.json"


class HomePage(QWidget):
    def __init__(self, go_to_settings, go_to_tasks, go_to_chatbot, open_chat_session):
        super().__init__()

        self.go_to_settings = go_to_settings
        self.go_to_tasks = go_to_tasks
        self.go_to_chatbot = go_to_chatbot
        self.open_chat_session = open_chat_session  # New callback for opening specific session
        self.dark_mode = False

        self.setup_ui()
        self.load_chat_sessions()  # Load sessions from database

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ---------------- TOP NAVBAR ----------------
        navbar = QHBoxLayout()

        # Center Title
        self.welcome_label = QLabel("Welcome")
        self.welcome_label.setObjectName("welcomeLabel")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        navbar.addWidget(self.welcome_label, stretch=1)

        # RIGHT: Profile Button
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

        # ---------------- MAIN CONTENT AREA ----------------
        content_layout = QHBoxLayout()

        # ------------- CHATS PANEL -------------
        chats_layout = QVBoxLayout()
        self.chats_title = QLabel("Chats")
        self.chats_title.setObjectName("sectionTitle")
        self.chats_title.setAlignment(Qt.AlignCenter)
        chats_layout.addWidget(self.chats_title)

        # Scroll area for chat sessions
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        chat_container = QWidget()
        self.chat_buttons_layout = QVBoxLayout(chat_container)
        self.chat_buttons_layout.setSpacing(10)
        self.chat_buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_scroll.setWidget(chat_container)
        chats_layout.addWidget(self.chat_scroll)

        self.new_chat_btn = QPushButton("New Chat")
        self.new_chat_btn.setObjectName("smallButton")
        self.new_chat_btn.clicked.connect(self.go_to_chatbot)
        chats_layout.addWidget(self.new_chat_btn, alignment=Qt.AlignCenter)

        content_layout.addLayout(chats_layout, stretch=1)

        # Vertical Divider with gaps
        divider_container = QWidget()
        divider_layout = QVBoxLayout(divider_container)
        divider_layout.setContentsMargins(0, 20, 0, 20)  # Top and bottom gaps
        divider_layout.setSpacing(0)
        
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.VLine)
        self.divider.setObjectName("divider")
        self.divider.setLineWidth(2)
        self.divider.setFixedWidth(2)
        divider_layout.addWidget(self.divider)
        
        content_layout.addWidget(divider_container)
        content_layout.setSpacing(15)  # Add spacing between panels and divider

        # ------------- TASKS PANEL -------------
        tasks_layout = QVBoxLayout()
        self.tasks_title = QLabel("To-do List")
        self.tasks_title.setObjectName("sectionTitle")
        self.tasks_title.setAlignment(Qt.AlignCenter)
        tasks_layout.addWidget(self.tasks_title)

        self.task_buttons = []
        for i in range(1, 4):
            btn = QPushButton(f"Task-{i}")
            btn.setObjectName("taskButton")
            btn.clicked.connect(self.go_to_tasks)
            tasks_layout.addWidget(btn)
            self.task_buttons.append(btn)

        tasks_layout.addStretch()

        self.new_task_btn = QPushButton("New Task")
        self.new_task_btn.setObjectName("smallButton")
        self.new_task_btn.clicked.connect(self.go_to_tasks)
        tasks_layout.addWidget(self.new_task_btn, alignment=Qt.AlignCenter)

        content_layout.addLayout(tasks_layout, stretch=1)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

    # -----------------------------------------------------------
    # Load Chat Sessions from Database
    # -----------------------------------------------------------
    def load_chat_sessions(self):
        """Load chat sessions from database and display them"""
        # Clear existing buttons
        while self.chat_buttons_layout.count():
            item = self.chat_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get sessions from database
        sessions = get_all_sessions()
        
        if not sessions:
            # Show "No chats yet" message
            no_chats_label = QLabel("No chats yet.\nClick 'New Chat' to start!")
            no_chats_label.setObjectName("noChatsLabel")
            no_chats_label.setAlignment(Qt.AlignCenter)
            self.chat_buttons_layout.addWidget(no_chats_label)
        else:
            # Create button for each session
            for session_id, title, updated_at in sessions:
                btn = QPushButton(title)
                btn.setObjectName("chatButton")
                btn.setToolTip(f"Last updated: {updated_at}")
                
                # Connect to open specific session
                btn.clicked.connect(lambda checked, sid=session_id: self.open_chat_session(sid))
                
                self.chat_buttons_layout.addWidget(btn)
        
        self.chat_buttons_layout.addStretch()

    def refresh_chat_sessions(self):
        """Refresh the chat sessions list (called after creating/deleting sessions)"""
        self.load_chat_sessions()

    # -----------------------------------------------------------
    # Dark Mode
    # -----------------------------------------------------------
    def apply_dark_mode(self, enabled):
        self.dark_mode = enabled
        if enabled:
            # DARK MODE
            self.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    font-family: Arial;
                }
                QLabel#welcomeLabel {
                    font-size: 22px;
                    color: #e0e0e0;
                    font-weight: bold;
                    background-color: transparent;
                }
                QLabel#sectionTitle {
                    font-size: 20px;
                    color: #e0e0e0;
                    font-weight: bold;
                    background-color: transparent;
                    padding: 8px;
                }
                QLabel#noChatsLabel {
                    color: #888;
                    font-size: 14px;
                    padding: 20px;
                }
                QPushButton#chatButton, QPushButton#taskButton {
                    background-color: #2d2d2d;
                    padding: 10px;
                    margin: 5px;
                    border-radius: 6px;
                    font-size: 15px;
                    text-align: left;
                    color: #e0e0e0;
                }
                QPushButton#chatButton:hover, QPushButton#taskButton:hover {
                    color: white;
                    background-color: #3a3a3a;
                }
                QPushButton#smallButton {
                    background-color: #4CAF50;
                    color: white;
                    text-align: center;
                    padding: 8px 12px;
                    border-radius: 6px;
                    margin: 8px 0;
                    font-size: 14px;
                }
                QPushButton#smallButton:hover {
                    background-color: #45a049;
                }
                QPushButton#profileButton {
                    border: none;
                    border-radius: 35px;
                    padding: 0;
                    margin: 0;
                    background-color: #2d2d2d;
                }
                QFrame#divider {
                    background-color: #ffffff;
                    border: none;
                }
            """)
        else:
            # LIGHT MODE
            self.setStyleSheet("""
                QWidget {
                    background-color: #f0f0f0;
                    font-family: Arial;
                }
                QLabel#welcomeLabel {
                    font-size: 22px;
                    color: black;
                    font-weight: bold;
                    background-color: transparent;
                }
                QLabel#sectionTitle {
                    font-size: 20px;
                    color: black;
                    font-weight: bold;
                    background-color: transparent;
                    padding: 8px;
                }
                QLabel#noChatsLabel {
                    color: #666;
                    font-size: 14px;
                    padding: 20px;
                }
                QPushButton#chatButton, QPushButton#taskButton {
                    background-color: white;
                    padding: 10px;
                    margin: 5px;
                    border-radius: 6px;
                    font-size: 15px;
                    text-align: left;
                    color: black;
                }
                QPushButton#chatButton:hover, QPushButton#taskButton:hover {
                    color: white;
                    background-color: black;
                }
                QPushButton#smallButton {
                    background-color: black;
                    color: white;
                    text-align: center;
                    padding: 8px 12px;
                    border-radius: 6px;
                    margin: 8px 0;
                    font-size: 14px;
                }
                QPushButton#smallButton:hover {
                    background-color: #333;
                    color: white;
                }
                QPushButton#profileButton {
                    border: none;
                    border-radius: 35px;
                    padding: 0;
                    margin: 0;
                    background-color: #ddd;
                }
                QFrame#divider {
                    background-color: #000000;
                    border: none;
                }
            """)

    # ==================== ASSETS FOLDER HELPER ====================
    def get_assets_path(self):
        """Get the assets folder path relative to this file"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(current_dir, "..", "assets")
        return assets_dir

    def get_image_path(self, filename):
        """Get full path to image in assets folder"""
        if not filename:
            return ""
        assets_dir = self.get_assets_path()
        return os.path.join(assets_dir, filename)

    # ---------------- PROFILE IMAGE ----------------
    def load_user_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if "image" not in data or not data["image"]:
                    data["image"] = "Profile-Icon.png"
                return data
        return {"image": "Profile-Icon.png"}

    def set_profile_picture(self, filename):
        """Load profile picture from assets folder"""
        if filename:
            image_path = self.get_image_path(filename)
            
            if os.path.exists(image_path):
                pix = QPixmap(image_path).scaled(
                    70, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                circular = QPixmap(70, 70)
                circular.fill(Qt.transparent)

                painter = QPainter(circular)
                painter.setRenderHint(QPainter.Antialiasing)
                p = QPainterPath()
                p.addEllipse(0, 0, 70, 70)
                painter.setClipPath(p)
                painter.drawPixmap(0, 0, pix)
                painter.end()

                self.profile_button.setIcon(QIcon(circular))
                self.profile_button.setIconSize(QSize(70, 70))
                return
        
        self.profile_button.setIcon(QIcon())

    def update_data(self, data):
        """Called when settings are saved - update profile picture"""
        self.set_profile_picture(data.get("image", ""))