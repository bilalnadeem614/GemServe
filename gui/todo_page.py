# todo_page.py
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QCheckBox,
    QSizePolicy,
)
from PySide6.QtGui import Qt
from PySide6.QtCore import QSize


class TodoList(QWidget):
    def __init__(self, go_back):
        super().__init__()

        self.go_back = go_back
        self.tasks = []  # Store task widgets
        self.dark_mode = False

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ====== TOP BAR ======
        top_bar = QHBoxLayout()

        self.back_btn = QPushButton("←")
        self.back_btn.setObjectName("backBtn")
        self.back_btn.setFixedSize(40, 30)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.go_back)

        self.title = QLabel("To-do")
        self.title.setObjectName("title")
        self.title.setAlignment(Qt.AlignCenter)

        top_bar.addWidget(self.back_btn)
        top_bar.addWidget(self.title, stretch=1)
        top_bar.addSpacing(40)

        main_layout.addLayout(top_bar)

        # Divider
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine)
        self.line.setObjectName("divider")
        main_layout.addWidget(self.line)

        # ====== TASK LIST AREA ======
        self.tasks_layout = QVBoxLayout()
        self.tasks_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        scroll.setObjectName("scrollArea")

        container = QWidget()
        container.setLayout(self.tasks_layout)
        scroll.setWidget(container)

        main_layout.addWidget(scroll)

        # ====== NEW TASK INPUT ROW ======
        add_layout = QHBoxLayout()

        self.task_input = QLineEdit()
        self.task_input.setObjectName("taskInput")
        self.task_input.setPlaceholderText("Enter new task...")
        self.task_input.setFixedHeight(35)

        self.add_button = QPushButton("+")
        self.add_button.setFixedSize(40, 35)
        self.add_button.setObjectName("newTaskBtn")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.create_task)

        add_layout.addWidget(self.add_button)
        add_layout.addWidget(self.task_input)

        main_layout.addLayout(add_layout)
        self.setLayout(main_layout)

    # -----------------------------------------
    # Dark Mode
    # -----------------------------------------
    def apply_dark_mode(self, enabled):
        self.dark_mode = enabled

        # Update existing tasks
        for task_data in self.tasks:
            task_box = task_data["box"]
            task_label = task_data["label"]
            checkbox = task_data["checkbox"]

            if enabled:
                # Dark mode for task box
                task_box.setStyleSheet(
                    """
                    QFrame#taskBox {
                        background-color: #2d2d2d;
                        border-radius: 8px;
                        padding: 6px;
                    }
                """
                )
                # Dark mode for task label
                is_checked = checkbox.isChecked()
                task_label.setStyleSheet(
                    f"""
                    QLabel#taskLabel {{
                        background-color: #3a3a3a;
                        color: {'#666' if is_checked else '#e0e0e0'};
                        padding: 8px;
                        border-radius: 6px;
                        text-decoration: {'line-through' if is_checked else 'none'};
                    }}
                """
                )
            else:
                # Light mode for task box
                task_box.setStyleSheet(
                    """
                    QFrame#taskBox {
                        background-color: white;
                        border-radius: 8px;
                        padding: 6px;
                        border: 1px solid #ddd;
                    }
                """
                )
                # Light mode for task label
                is_checked = checkbox.isChecked()
                task_label.setStyleSheet(
                    f"""
                    QLabel#taskLabel {{
                        background-color: #f8f8f8;
                        color: {'gray' if is_checked else 'black'};
                        padding: 8px;
                        border-radius: 6px;
                        border: 1px solid #ddd;
                        text-decoration: {'line-through' if is_checked else 'none'};
                    }}
                """
                )

        # Update main window style
        if enabled:
            # DARK MODE
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #1e1e1e;
                    font-family: Arial;
                    font-size: 15px;
                }
                QLabel#title {
                    font-size: 22px;
                    font-weight: bold;
                    color: #e0e0e0;
                    background-color: transparent;
                }
                QLineEdit#taskInput {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    padding: 8px;
                    border-radius: 6px;
                    border: 1px solid #555;
                }
                QCheckBox {
                    height: 20px;
                    width: 20px;
                }
                QPushButton#newTaskBtn {
                    background-color: #4CAF50;
                    color: white;  
                    border-radius: 4px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton#newTaskBtn:hover {
                    background-color: #45a049;
                }
                QPushButton#backBtn {
                    color: #e0e0e0;
                    font-weight: bold;
                    font-size: 18px;
                    background-color: transparent;
                    border: none;
                }
                QFrame#divider {
                    background-color: #444;
                    min-height: 2px;
                    max-height: 2px;
                }
                QScrollArea#scrollArea {
                    background-color: #1e1e1e;
                }
            """
            )
        else:
            # LIGHT MODE
            self.setStyleSheet(
                """
                QWidget {
                    background-color: #f0f0f0;
                    font-family: Arial;
                    font-size: 15px;
                }
                QLabel#title {
                    font-size: 22px;
                    font-weight: bold;
                    color: black;
                    background-color: transparent;
                }
                QLineEdit#taskInput {
                    background-color: white;
                    color: black;
                    padding: 8px;
                    border-radius: 6px;
                    border: 1px solid #ccc;
                }
                QCheckBox {
                    height: 20px;
                    width: 20px;
                }
                QPushButton#newTaskBtn {
                    background-color: black;
                    color: white;  
                    border-radius: 4px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton#newTaskBtn:hover {
                    background-color: #333;
                }
                QPushButton#backBtn {
                    color: black;
                    font-weight: bold;
                    font-size: 18px;
                    background-color: transparent;
                    border: none;
                }
                QFrame#divider {
                    background-color: #ccc;
                    min-height: 2px;
                    max-height: 2px;
                }
            """
            )

    # -----------------------------------------
    # ADD NEW TASK
    # -----------------------------------------
    def create_task(self):
        task_text = self.task_input.text().strip()
        if task_text == "":
            return

        task_box = QFrame()
        task_box.setObjectName("taskBox")
        if self.dark_mode:
            task_box.setStyleSheet(
                """
                QFrame#taskBox {
                    background-color: #2d2d2d;
                    border-radius: 8px;
                    padding: 6px;
                }
            """
            )
        else:
            task_box.setStyleSheet(
                """
                QFrame#taskBox {
                    background-color: white;
                    border-radius: 8px;
                    padding: 6px;
                    border: 1px solid #ddd;
                }
            """
            )

        task_layout = QHBoxLayout(task_box)
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.setSpacing(10)

        checkbox = QCheckBox()
        checkbox.setFixedSize(20, 20)
        checkbox.setCursor(Qt.PointingHandCursor)

        task_label = QLabel(task_text)
        task_label.setObjectName("taskLabel")
        if self.dark_mode:
            task_label.setStyleSheet(
                """
                QLabel#taskLabel {
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                    padding: 8px;
                    border-radius: 6px;
                }
            """
            )
        else:
            task_label.setStyleSheet(
                """
                QLabel#taskLabel {
                    background-color: #f8f8f8;
                    color: black;
                    padding: 8px;
                    border-radius: 6px;
                    border: 1px solid #ddd;
                }
            """
            )

        task_label.setFixedHeight(35)
        task_label.setMinimumWidth(200)
        task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        task_layout.addWidget(checkbox)
        task_layout.addWidget(task_label)

        # Store task reference
        task_data = {"box": task_box, "label": task_label, "checkbox": checkbox}
        self.tasks.append(task_data)

        def update_style(state):
            if self.dark_mode:
                task_label.setStyleSheet(
                    f"""
                    QLabel#taskLabel {{
                        background-color: #3a3a3a;
                        color: {'#666' if state else '#e0e0e0'};
                        padding: 8px;
                        border-radius: 6px;
                        text-decoration: {'line-through' if state else 'none'};
                    }}
                """
                )
            else:
                task_label.setStyleSheet(
                    f"""
                    QLabel#taskLabel {{
                        background-color: #f8f8f8;
                        color: {'gray' if state else 'black'};
                        padding: 8px;
                        border-radius: 6px;
                        border: 1px solid #ddd;
                        text-decoration: {'line-through' if state else 'none'};
                    }}
                """
                )

        checkbox.stateChanged.connect(update_style)

        self.tasks_layout.addWidget(task_box)
        self.tasks_layout.addStretch()

        self.task_input.clear()
        print("Task added.")
