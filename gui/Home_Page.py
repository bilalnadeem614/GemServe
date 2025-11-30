from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath, Qt
from PySide6.QtCore import QSize
import json
import os

DATA_FILE = "user_data.json"

class HomePage(QWidget):
    def __init__(self, go_to_settings, go_to_tasks):
        
        super().__init__()
        
        self.go_to_settings = go_to_settings
        self.go_to_tasks = go_to_tasks
        
        # -------------------- STYLE --------------------
        self.setStyleSheet(
            """
    QWidget {
        background-color: #f0f0f0;
        font-family: Arial;
    }

    QLabel {
        font-size: 22px;
        color: black;
        font-weight: bold;
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
        color: #e6e6e6;
        background-color: black;
    }

    QPushButton#smallButton {
        background-color: black;
        text-align: center;
        padding: 8px 12px;
        border-radius: 6px;
        margin: 8px 0;
        font-size: 14px;
    }

    QPushButton#smallButton:hover {
        background-color: black;
        color: #e6e6e6;
    }

    QPushButton#profileButton {
        border: none;
        border-radius: 35px;
        padding: 0;
        margin: 0;
        background-color: black;
    }
    """
        )

        # ================== MAIN LAYOUT ==================
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ---------------- TOP NAVBAR ----------------
        navbar = QHBoxLayout()

        # Left placeholder
        left_placeholder = QWidget()
        left_placeholder.setFixedWidth(40)
        navbar.addWidget(left_placeholder)

        # Center title
        welcome_label = QLabel("Welcome")
        welcome_label.setAlignment(Qt.AlignCenter)
        navbar.addWidget(welcome_label, stretch=1)

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
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: black;")
        main_layout.addWidget(line)

        # ---------------- MAIN CONTENT AREA ----------------
        content_layout = QHBoxLayout()

        # ------------- CHATS PANEL -------------
        chats_layout = QVBoxLayout()
        chats_title = QLabel("Chats")
        chats_title.setAlignment(Qt.AlignCenter)
        chats_layout.addWidget(chats_title)

        self.add_chat_button(chats_layout, "Chat-1")
        self.add_chat_button(chats_layout, "Chat-2")
        self.add_chat_button(chats_layout, "Chat-3")

        chats_layout.addStretch()

        new_chat_btn = QPushButton("New Chat")
        new_chat_btn.setObjectName("smallButton")
        new_chat_btn.setCursor(Qt.PointingHandCursor)
        chats_layout.addWidget(new_chat_btn, alignment=Qt.AlignCenter)

        # Left side added
        content_layout.addLayout(chats_layout)

        # Vertical Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setStyleSheet("color: black;")
        content_layout.addWidget(divider)

        # ------------- TASKS PANEL -------------
        tasks_layout = QVBoxLayout()
        tasks_title = QLabel("To-do List")
        tasks_title.setAlignment(Qt.AlignCenter)
        tasks_layout.addWidget(tasks_title)

        self.add_task_button(tasks_layout, "Task-1")
        self.add_task_button(tasks_layout, "Task-2")
        self.add_task_button(tasks_layout, "Task-3")

        tasks_layout.addStretch()

        new_task_btn = QPushButton("New Task")
        new_task_btn.setObjectName("smallButton")
        new_task_btn.setCursor(Qt.PointingHandCursor)
        new_task_btn.clicked.connect(self.go_to_tasks)
        tasks_layout.addWidget(new_task_btn, alignment=Qt.AlignCenter)

        content_layout.addLayout(tasks_layout)

        # Add main content
        main_layout.addLayout(content_layout)

        # Final layout set
        self.setLayout(main_layout)

    # -----------------------------------------------------------
    # Helper Functions
    # -----------------------------------------------------------

    def add_chat_button(self, layout, name):
        btn = QPushButton(name)
        btn.setObjectName("chatButton")
        btn.clicked.connect(lambda: self.open_chat(name))
        layout.addWidget(btn)

    def add_task_button(self, layout, name):
        btn = QPushButton(name)
        btn.setObjectName("taskButton")
        btn.clicked.connect(lambda: self.open_task(name))
        layout.addWidget(btn)

    # ---------------- PROFILE IMAGE HANDLING ----------------
    def load_user_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        return {}

    def set_profile_picture(self, path):
        if path and os.path.exists(path):
            # Load image and scale to button size
            pix = QPixmap(path).scaled(70, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            
            # Create a circular pixmap
            circular = QPixmap(70, 70)
            circular.fill(Qt.transparent)
            painter = QPainter(circular)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 70, 70)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pix)
            painter.end()
            
            # Set as button icon
            self.profile_button.setIcon(QIcon(circular))
            self.profile_button.setIconSize(QSize(70, 70))
            self.profile_button.setCursor(Qt.PointingHandCursor)
            self.profile_button.setToolTip("Profile Settings")
            self.profile_button.setStyleSheet(
                "border: none; border-radius: 35px; background-color: black;"
            )
        else:
            # default gray bg
            self.profile_button.setIcon(QIcon())
            self.profile_button.setStyleSheet(
                "border: 2px solid #aaa; border-radius: 35px; background-color: black;"
            )


    # -----------------------------------------------------------
    # Navigation Methods
    # -----------------------------------------------------------

    def open_chat(self, chat_name):
        print(f"Opening chat: {chat_name}")

    def open_task(self, task_name):
        print(f"Opening task: {task_name}")

    def update_data(self, data):
        """Refresh the home page after saving settings"""
        self.set_profile_picture(data.get("image", ""))
        print("Data Updated.")
