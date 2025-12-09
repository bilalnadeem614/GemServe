# Home_Page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath, Qt
from PySide6.QtCore import QSize
import json
import os

DATA_FILE = "user_data.json"


class HomePage(QWidget):
    def __init__(self, go_to_settings, go_to_tasks, go_to_chatbot):
        super().__init__()

        self.go_to_settings = go_to_settings
        self.go_to_tasks = go_to_tasks
        self.go_to_chatbot = go_to_chatbot
        self.dark_mode = False

        self.setup_ui()

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

        self.chat_buttons = []
        for i in range(1, 4):
            btn = QPushButton(f"Chat-{i}")
            btn.setObjectName("chatButton")
            btn.clicked.connect(self.go_to_chatbot)
            chats_layout.addWidget(btn)
            self.chat_buttons.append(btn)

        chats_layout.addStretch()

        self.new_chat_btn = QPushButton("New Chat")
        self.new_chat_btn.setObjectName("smallButton")
        self.new_chat_btn.clicked.connect(self.go_to_chatbot)
        chats_layout.addWidget(self.new_chat_btn, alignment=Qt.AlignCenter)

        content_layout.addLayout(chats_layout)

        # Vertical Divider
        self.divider = QFrame()
        self.divider.setFrameShape(QFrame.VLine)
        self.divider.setObjectName("divider")
        content_layout.addWidget(self.divider)

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

        content_layout.addLayout(tasks_layout)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

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
                QPushButton#chatButton, QPushButton#taskButton {
                    background-color: #2d2d2d;
                    padding: 10px;
                    margin: 10px;
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
                    background-color: #444;
                    min-height: 2px;
                    max-height: 2px;
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
                QPushButton#chatButton, QPushButton#taskButton {
                    background-color: white;
                    padding: 10px;
                    margin: 10px;
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
                    background-color: #ccc;
                    min-height: 2px;
                    max-height: 2px;
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
                # If no image is set, use default
                if "image" not in data or not data["image"]:
                    data["image"] = "Profile-Icon.png"
                return data
        return {"image": "Profile-Icon.png"}

    def set_profile_picture(self, filename):
        """Load profile picture from assets folder"""
        if filename:
            # Get full path from assets folder
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
        
        # If image not found, show empty icon
        self.profile_button.setIcon(QIcon())

    def update_data(self, data):
        """Called when settings are saved - update profile picture"""
        self.set_profile_picture(data.get("image", ""))