# from PySide6.QtWidgets import (
#     QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
# )
# from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath, Qt
# from PySide6.QtCore import QSize
# import json
# import os

# DATA_FILE = "user_data.json"


# class HomePage(QWidget):
#     def __init__(self, go_to_settings, go_to_tasks, go_to_chatbot):
#         super().__init__()

#         self.go_to_settings = go_to_settings
#         self.go_to_tasks = go_to_tasks
#         self.go_to_chatbot = go_to_chatbot   # <-- NEW

#         # -------------------- STYLE --------------------
#         self.setStyleSheet("""
#             QWidget {
#                 background-color: #f0f0f0;
#                 font-family: Arial;
#             }

#             QLabel {
#                 font-size: 22px;
#                 color: black;
#                 font-weight: bold;
#             }

#             QPushButton#navButton {
#                 background-color: white;
#                 border-radius: 8px;
#                 padding: 8px 12px;
#             }

#             QPushButton#navButton:hover {
#                 background-color: black;
#                 color: white;
#             }

#             QPushButton#chatButton, QPushButton#taskButton {
#                 background-color: white;
#                 padding: 10px;
#                 margin: 10px;
#                 border-radius: 6px;
#                 font-size: 15px;
#                 text-align: left;
#                 color: black;
#             }

#             QPushButton#chatButton:hover, QPushButton#taskButton:hover {
#                 color: #e6e6e6;
#                 background-color: black;
#             }

#             QPushButton#smallButton {
#                 background-color: black;
#                 text-align: center;
#                 padding: 8px 12px;
#                 border-radius: 6px;
#                 margin: 8px 0;
#                 font-size: 14px;
#             }

#             QPushButton#smallButton:hover {
#                 background-color: #333;
#                 color: #e6e6e6;
#             }

#             QPushButton#profileButton {
#                 border: none;
#                 border-radius: 35px;
#                 padding: 0;
#                 margin: 0;
#                 background-color: black;
#             }
#         """)

#         # ================== MAIN LAYOUT ==================
#         main_layout = QVBoxLayout()
#         main_layout.setSpacing(15)
#         main_layout.setContentsMargins(20, 20, 20, 20)

#         # ---------------- TOP NAVBAR ----------------
#         navbar = QHBoxLayout()

#         # LEFT: Chatbot Button (NEW)
#         self.chatbot_button = QPushButton("🤖 Chatbot")
#         self.chatbot_button.setObjectName("navButton")
#         self.chatbot_button.setCursor(Qt.PointingHandCursor)
#         self.chatbot_button.clicked.connect(self.go_to_chatbot)
#         navbar.addWidget(self.chatbot_button)

#         # Center Title
#         welcome_label = QLabel("Welcome")
#         welcome_label.setAlignment(Qt.AlignCenter)
#         navbar.addWidget(welcome_label, stretch=1)

#         # RIGHT: Profile Button
#         self.profile_button = QPushButton()
#         self.profile_button.setObjectName("profileButton")
#         self.profile_button.setFixedSize(70, 70)

#         user_data = self.load_user_data()
#         self.set_profile_picture(user_data.get("image", ""))

#         self.profile_button.clicked.connect(self.go_to_settings)
#         navbar.addWidget(self.profile_button)

#         main_layout.addLayout(navbar)

#         # Divider
#         line = QFrame()
#         line.setFrameShape(QFrame.HLine)
#         line.setStyleSheet("color: black;")
#         main_layout.addWidget(line)

#         # ---------------- MAIN CONTENT AREA ----------------
#         content_layout = QHBoxLayout()

#         # ------------- CHATS PANEL -------------
#         chats_layout = QVBoxLayout()
#         chats_title = QLabel("Chats")
#         chats_title.setAlignment(Qt.AlignCenter)
#         chats_layout.addWidget(chats_title)

#         self.add_chat_button(chats_layout, "Chat-1")
#         self.add_chat_button(chats_layout, "Chat-2")
#         self.add_chat_button(chats_layout, "Chat-3")

#         chats_layout.addStretch()

#         new_chat_btn = QPushButton("New Chat")
#         new_chat_btn.setObjectName("smallButton")
#         chats_layout.addWidget(new_chat_btn, alignment=Qt.AlignCenter)

#         content_layout.addLayout(chats_layout)

#         # Vertical Divider
#         divider = QFrame()
#         divider.setFrameShape(QFrame.VLine)
#         divider.setStyleSheet("color: black;")
#         content_layout.addWidget(divider)

#         # ------------- TASKS PANEL -------------
#         tasks_layout = QVBoxLayout()
#         tasks_title = QLabel("To-do List")
#         tasks_title.setAlignment(Qt.AlignCenter)
#         tasks_layout.addWidget(tasks_title)

#         self.add_task_button(tasks_layout, "Task-1")
#         self.add_task_button(tasks_layout, "Task-2")
#         self.add_task_button(tasks_layout, "Task-3")

#         tasks_layout.addStretch()

#         new_task_btn = QPushButton("New Task")
#         new_task_btn.setObjectName("smallButton")
#         new_task_btn.clicked.connect(self.go_to_tasks)
#         tasks_layout.addWidget(new_task_btn, alignment=Qt.AlignCenter)

#         content_layout.addLayout(tasks_layout)

#         main_layout.addLayout(content_layout)

#         self.setLayout(main_layout)

#     # -----------------------------------------------------------
#     # Helper Functions
#     # -----------------------------------------------------------

#     def add_chat_button(self, layout, name):
#         btn = QPushButton(name)
#         btn.setObjectName("chatButton")
#         layout.addWidget(btn)

#     def add_task_button(self, layout, name):
#         btn = QPushButton(name)
#         btn.setObjectName("taskButton")
#         layout.addWidget(btn)

#     # ---------------- PROFILE IMAGE ----------------
#     def load_user_data(self):
#         if os.path.exists(DATA_FILE):
#             with open(DATA_FILE, "r") as f:
#                 return json.load(f)
#         return {}

#     def set_profile_picture(self, path):
#         if path and os.path.exists(path):
#             pix = QPixmap(path).scaled(70, 70, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
#             circular = QPixmap(70, 70)
#             circular.fill(Qt.transparent)

#             painter = QPainter(circular)
#             painter.setRenderHint(QPainter.Antialiasing)
#             p = QPainterPath()
#             p.addEllipse(0, 0, 70, 70)
#             painter.setClipPath(p)
#             painter.drawPixmap(0, 0, pix)
#             painter.end()

#             self.profile_button.setIcon(QIcon(circular))
#             self.profile_button.setIconSize(QSize(70, 70))
#         else:
#             self.profile_button.setIcon(QIcon())

#     # -----------------------------------------------------------
#     # Update Function
#     # -----------------------------------------------------------
#     def update_data(self, data):
#         self.set_profile_picture(data.get("image", ""))


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
    def __init__(self, go_to_settings, go_to_tasks, go_to_chatbot):
        super().__init__()

        self.go_to_settings = go_to_settings
        self.go_to_tasks = go_to_tasks
        self.go_to_chatbot = go_to_chatbot

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

            QPushButton#navButton {
                background-color: white;
                border-radius: 8px;
                padding: 8px 12px;
            }

            QPushButton#navButton:hover {
                background-color: black;
                color: white;
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
                background-color: #333;
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

        # Center Title
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
        new_chat_btn.clicked.connect(self.go_to_chatbot)  # Connected to chatbot
        chats_layout.addWidget(new_chat_btn, alignment=Qt.AlignCenter)

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
        new_task_btn.clicked.connect(self.go_to_tasks)
        tasks_layout.addWidget(new_task_btn, alignment=Qt.AlignCenter)

        content_layout.addLayout(tasks_layout)

        main_layout.addLayout(content_layout)

        self.setLayout(main_layout)

    # -----------------------------------------------------------
    # Helper Functions
    # -----------------------------------------------------------

    def add_chat_button(self, layout, name):
        btn = QPushButton(name)
        btn.setObjectName("chatButton")
        layout.addWidget(btn)

    def add_task_button(self, layout, name):
        btn = QPushButton(name)
        btn.setObjectName("taskButton")
        layout.addWidget(btn)

    # ---------------- PROFILE IMAGE ----------------
    def load_user_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        return {}

    def set_profile_picture(self, path):
        if path and os.path.exists(path):
            pix = QPixmap(path).scaled(
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
        else:
            self.profile_button.setIcon(QIcon())

    # -----------------------------------------------------------
    # Update Function
    # -----------------------------------------------------------
    def update_data(self, data):
        self.set_profile_picture(data.get("image", ""))
