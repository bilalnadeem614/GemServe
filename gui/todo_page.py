from db.todo_db_helper import insert_task, init_database, DB_PATH
from utils.extract_info import extract_info
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from datetime import datetime
import sqlite3

# Initialize database
init_database()


class TodoList(QWidget):
    task_updated = Signal()
    def __init__(self, go_back):
        super().__init__()

        self.go_back = go_back
        self.dark_mode = False  # Default: light mode

        # --- MAIN LAYOUT ---
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.setLayout(self.main_layout)

        self.build_ui()
        self.load_tasks()

    # =====================================================
    # BUILD UI
    # =====================================================
    def build_ui(self):
        # Top bar with back button and title
        top_bar = QHBoxLayout()
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedSize(40, 30)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.go_back)
        

        self.title = QLabel("To-do")
        self.title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title.setStyleSheet("font-size: 15px; font-weight: bold;")

        top_bar.addWidget(self.back_btn)
        top_bar.addWidget(self.title, 1)
        top_bar.addSpacing(10)
        self.main_layout.addLayout(top_bar)

        # Divider line
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        self.main_layout.addWidget(divider)

        # Two columns: Completed and Pending tasks
        list_container = QHBoxLayout()

        # Completed Tasks Column
        self.completed_layout = QVBoxLayout()
        completed_title = QLabel("Completed Tasks")
        completed_title.setObjectName("completedTitle")
        completed_title.setAlignment(Qt.AlignLeft)
        completed_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.completed_layout.addWidget(completed_title)

        completed_box = QWidget()
        completed_box.setLayout(self.completed_layout)
        completed_scroll = QScrollArea()
        completed_scroll.setWidgetResizable(True)
        completed_scroll.setWidget(completed_box)

        # Pending Tasks Column
        self.pending_layout = QVBoxLayout()
        pending_title = QLabel("Pending Tasks")
        pending_title.setObjectName("pendingTitle")
        pending_title.setAlignment(Qt.AlignLeft)
        pending_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.pending_layout.addWidget(pending_title)

        pending_box = QWidget()
        pending_box.setLayout(self.pending_layout)
        pending_scroll = QScrollArea()
        pending_scroll.setWidgetResizable(True)
        pending_scroll.setWidget(pending_box)

        list_container.addWidget(completed_scroll, 1)
        list_container.addWidget(pending_scroll, 1)
        self.main_layout.addLayout(list_container)

        # Input row for adding tasks
        add_layout = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter new task...")
        self.task_input.setFixedHeight(35)

        self.add_button = QPushButton("+")
        self.add_button.setObjectName("addBtn")
        self.add_button.setFixedSize(40, 35)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.create_task)

        add_layout.addWidget(self.add_button)
        add_layout.addWidget(self.task_input)
        self.main_layout.addLayout(add_layout)

    # =====================================================
    # DARK / LIGHT MODE
    # =====================================================
    def apply_dark_mode(self, enabled):
        self.dark_mode = enabled

        if enabled:
            self.setStyleSheet("""
            /* Global Background and Text */
            QWidget { 
                background-color: #1e1e1e; 
                color: #ddd; 
            }

            /* Section Titles */
            QLabel#completedTitle { 
                color: #7fff7f; 
                font-size: 18px; 
                font-weight: bold; 
            }
            QLabel#pendingTitle { 
                color: #fff; 
                font-size: 18px; 
                font-weight: bold; 
            }

            /* Input Fields */
            QLineEdit { 
                background-color: #333; 
                color: #fff; 
                border: 1px solid #555; 
                padding: 8px; 
            }

            /* Buttons */
            QPushButton#addBtn { 
                background-color: #4caf50; 
                color: white; 
                border-radius: 6px; 
            }
        """)
        else:
            self.setStyleSheet("""
            /* Global Background and Text */
            QWidget { 
                background-color: #f0f0f0; 
                color: #222; 
            }

            /* Section Titles */
            QLabel#completedTitle { 
                color: green; 
                font-size: 18px; 
                font-weight: bold; 
            }
            QLabel#pendingTitle { 
                color: black; 
                font-size: 18px; 
                font-weight: bold; 
            }

            /* Input Fields */
            QLineEdit { 
                background-color: #d9d9d9; 
                color: black; 
                padding: 5px; 
            }

            /* Buttons */
            QPushButton#addBtn { 
                background-color: black; 
                color: white; 
                border-radius: 6px; 
            }
        """)

        self.load_tasks()
        
    # =====================================================
    # CREATE TASK
    # =====================================================
    def create_task(self):
        raw_text = self.task_input.text().strip()
        if not raw_text:
            return

        title, task_date, task_time = extract_info(raw_text)
        task_time = datetime.strptime(task_time, "%I:%M %p").strftime("%I:%M %p")

        insert_task(title, task_date, task_time)
        self.task_updated.emit()
        self.task_input.clear()
        self.load_tasks()

    # =====================================================
    # LOAD TASKS FROM DATABASE
    # =====================================================
    def load_tasks(self):
        # Remove old widgets except titles
        for layout in [self.completed_layout, self.pending_layout]:
            while layout.count() > 1:
                item = layout.takeAt(1)
                if item.widget():
                    item.widget().deleteLater()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, is_done FROM tasks ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        for task_id, title, done in rows:
            if done:
                self.add_completed_task(task_id, title)
            else:
                self.add_pending_task(task_id, title)

    # =====================================================
    # ADD TASK WIDGET
    # =====================================================
    def _add_task_widget(self, layout, task_id, text, done=False):
        bg = "#2d2d2d" if self.dark_mode else "#e0e0e0"
        hover = "#444" if self.dark_mode else "#b0b0b0"
        text_color = "#ddd" if self.dark_mode else "#222"
        hover_text = "white"
        font_style = "font-size: 15px; font-weight: bold;"

        task_box = QFrame()
        task_box.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")

        h_layout = QHBoxLayout(task_box)
        h_layout.setContentsMargins(6, 6, 6, 6)
        h_layout.setSpacing(10)

        checkbox = QCheckBox()
        checkbox.setChecked(done)
        checkbox.setCursor(Qt.PointingHandCursor)

        label = QLabel(text)
        label.setStyleSheet(f"color: {text_color}; {font_style}")
        label.setFixedHeight(35)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        h_layout.addWidget(checkbox)
        h_layout.addWidget(label, 1)

        # Move task when checked
        checkbox.stateChanged.connect(lambda s, tid=task_id: self.mark_done(tid, s))

        # Hover effect
        def enter(event):
            task_box.setStyleSheet(f"background-color: {hover}; border-radius: 8px;")
            label.setStyleSheet(f"color: {hover_text}; {font_style}")

        def leave(event):
            task_box.setStyleSheet(f"background-color: {bg}; border-radius: 8px;")
            label.setStyleSheet(f"color: {text_color}; {font_style}")

        task_box.enterEvent = enter
        task_box.leaveEvent = leave

        layout.addWidget(task_box)

    def add_pending_task(self, task_id, text):
        self._add_task_widget(self.pending_layout, task_id, text, done=False)

    def add_completed_task(self, task_id, text):
        self._add_task_widget(self.completed_layout, task_id, text, done=True)

    # =====================================================
    # UPDATE DATABASE AND RELOAD
    # =====================================================
    def mark_done(self, task_id, state):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET is_done = ? WHERE id = ?", (1 if state else 0, task_id))
        conn.commit()
        conn.close()
        self.load_tasks()
