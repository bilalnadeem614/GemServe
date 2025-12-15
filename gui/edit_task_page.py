from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QDateEdit, QTimeEdit, QCheckBox
)
from PySide6.QtCore import Qt, QDate, QTime, Signal
from services.db_helper import update_task

class EditTaskPage(QWidget):
    task_updated = Signal()
    def __init__(self, task_id, title, task_date, task_time, is_done):
        super().__init__()
        self.task_id = task_id
        self.setWindowTitle("Edit Task")
        self.setFixedSize(350, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        self.title_input = QLineEdit(title)
        self.title_input.setPlaceholderText("Task title")

        # Date
        date = QDate.fromString(task_date, "yyyy-MM-dd") \
            if "-" in task_date else QDate.fromString(task_date, "dd/MM/yyyy")

        self.date_input = QDateEdit(date)
        self.date_input.setCalendarPopup(True)

        # Time
        if task_time:
            t = QTime.fromString(task_time, "hh:mm ap")
            if not t.isValid():
                t = QTime.fromString(task_time, "hh:mm")
        else:
            t = QTime(12, 0)

        self.time_input = QTimeEdit(t)

        # Checkbox
        self.status_checkbox = QCheckBox("Completed")
        self.status_checkbox.setChecked(bool(is_done))

        # Save Button
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_task)

        layout.addWidget(QLabel("Title"))
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("Date"))
        layout.addWidget(self.date_input)

        layout.addWidget(QLabel("Time"))
        layout.addWidget(self.time_input)

        layout.addWidget(self.status_checkbox)
        layout.addWidget(save_btn)

    
    def save_task(self):
        new_title = self.title_input.text()
        new_date = self.date_input.date().toString("yyyy-MM-dd")
        new_time = self.time_input.time().toString("hh:mm ap")
        new_status = 1 if self.status_checkbox.isChecked() else 0

        update_task(self.task_id, new_title, new_date, new_time, new_status)
        self.task_updated.emit()
        self.close()
