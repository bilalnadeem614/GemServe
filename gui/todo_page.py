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
    QSizePolicy
)
from PySide6.QtGui import Qt
from PySide6.QtCore import QSize


class TodoList(QWidget):
    def __init__(self, go_back):
        super().__init__()

        self.go_back = go_back
        self.tasks = []

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
            }
            QLineEdit {
                background-color: #d9d9d9;
                color: black;
                padding: 5px;
                border-radius: 6px;
            }
            QCheckBox{
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
        """
        )

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ====== TOP BAR ======
        top_bar = QHBoxLayout()

        back_btn = QPushButton("←")
        back_btn.setFixedSize(40, 30)
        back_btn.setStyleSheet("color: black; font-weight: bold; font-size: 18px;")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self.go_back)

        title = QLabel("To-do")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)

        top_bar.addWidget(back_btn)
        top_bar.addWidget(title, stretch=1)
        top_bar.addSpacing(40)

        main_layout.addLayout(top_bar)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: black;")
        main_layout.addWidget(line)

        # ====== TASK LIST AREA ======
        self.tasks_layout = QVBoxLayout()
        self.tasks_layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        container = QWidget()
        container.setLayout(self.tasks_layout)
        scroll.setWidget(container)

        main_layout.addWidget(scroll)

        # ====== NEW TASK INPUT ROW ======
        add_layout = QHBoxLayout()

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter new task...")
        self.task_input.setFixedHeight(35)

        add_button = QPushButton("+")
        add_button.setFixedSize(40, 35)
        add_button.setObjectName("newTaskBtn")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self.create_task)

        add_layout.addWidget(add_button)
        add_layout.addWidget(self.task_input)

        main_layout.addLayout(add_layout)

        self.setLayout(main_layout)

        
    # -----------------------------------------
    # ADD NEW TASK
        # -----------------------------------------
    def create_task(self):
        task_text = self.task_input.text().strip()
        if task_text == "":
            return

        task_box = QFrame()
        task_box.setStyleSheet("""
            QFrame {
                background-color: #e0e0e0;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        task_layout = QHBoxLayout(task_box)
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.setSpacing(10)

        checkbox = QCheckBox()
        checkbox.setFixedSize(20, 20)
        checkbox.setCursor(Qt.PointingHandCursor)
        
        task_label = QLabel(task_text)
        task_label.setStyleSheet("""
            QLabel {
                background-color: white;
                color: black;
                padding: 6px;
                border-radius: 8px;
            }
        """)
        task_label.setFixedHeight(35)
        task_label.setMinimumWidth(200)
        task_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        task_layout.addWidget(checkbox)
        task_layout.addWidget(task_label)
        checkbox.stateChanged.connect(lambda state, lbl=task_label: 
            lbl.setStyleSheet(f"""
                QLabel {{
                    background-color: white;
                    color: {'gray' if state else 'black'};
                    padding: 6px;
                    border-radius: 8px;
                    text-decoration: {'line-through' if state else 'none'};
                }}
            """)
        )
        self.tasks_layout.addWidget(task_box)
        self.tasks_layout.addStretch()

        self.task_input.clear()
        print("task addd.")

