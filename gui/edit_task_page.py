from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QDateEdit, QTimeEdit, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QDate, QTime, Signal, QTimer
from db.todo_db_helper import update_task
import json
import os

DATA_FILE = "user_data.json"

class EditTaskPage(QWidget):
    task_updated = Signal()
    
    def __init__(self, task_id, title, task_date, task_time, is_done):
        super().__init__()
        self.task_id = task_id
        self.setWindowTitle("Edit Task")
        self.setFixedSize(520, 620)
        
        # Load dark mode preference
        self.dark_mode = self.load_dark_mode()
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header section with gradient
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(100)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(40, 30, 40, 25)
        
        header_title = QLabel("Edit Task")
        header_title.setObjectName("headerTitle")
        header_layout.addWidget(header_title)
        
        main_layout.addWidget(header)
        
        # Content section
        content = QFrame()
        content.setObjectName("content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 35, 40, 40)
        layout.setSpacing(25)

        # Title Input
        title_label = QLabel("TASK TITLE")
        title_label.setObjectName("fieldLabel")
        self.title_input = QLineEdit(title)
        self.title_input.setObjectName("inputField")
        self.title_input.setPlaceholderText("Enter your task title...")
        self.title_input.setFixedHeight(56)
        
        layout.addWidget(title_label)
        layout.addWidget(self.title_input)
        layout.addSpacing(8)

        # Date and Time Row
        datetime_layout = QHBoxLayout()
        datetime_layout.setSpacing(20)
        
        # Date Column
        date_column = QVBoxLayout()
        date_column.setSpacing(12)
        date_label = QLabel("DATE")
        date_label.setObjectName("fieldLabel")
        
        date = QDate.fromString(task_date, "yyyy-MM-dd") \
            if "-" in task_date else QDate.fromString(task_date, "dd/MM/yyyy")

        self.date_input = QDateEdit(date)
        self.date_input.setObjectName("inputField")
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("MMM dd, yyyy")
        self.date_input.setMinimumDate(QDate.currentDate())  # Restrict to current or future dates
        self.date_input.setFixedHeight(56)
        self.date_input.dateChanged.connect(self.update_time_limit)
        
        date_column.addWidget(date_label)
        date_column.addWidget(self.date_input)

        # Time Column
        time_column = QVBoxLayout()
        time_column.setSpacing(12)
        time_label = QLabel("TIME")
        time_label.setObjectName("fieldLabel")
        
        if task_time:
            t = QTime.fromString(task_time, "hh:mm ap")
            if not t.isValid():
                t = QTime.fromString(task_time, "hh:mm")
        else:
            t = QTime(12, 0)

        self.time_input = QTimeEdit(t)
        self.time_input.setObjectName("inputField")
        self.time_input.setDisplayFormat("hh:mm AP")
        self.time_input.setFixedHeight(56)
        # ⭐ Disable up/down arrow buttons
        self.time_input.setButtonSymbols(QTimeEdit.NoButtons)
        
        time_column.addWidget(time_label)
        time_column.addWidget(self.time_input)
        
        datetime_layout.addLayout(date_column, 1)
        datetime_layout.addLayout(time_column, 1)
        layout.addLayout(datetime_layout)
        layout.addSpacing(8)

        # Checkbox with beautiful frame
        checkbox_frame = QFrame()
        checkbox_frame.setObjectName("checkboxFrame")
        checkbox_frame.setFixedHeight(70)
        checkbox_layout = QHBoxLayout(checkbox_frame)
        checkbox_layout.setContentsMargins(24, 0, 24, 0)
        
        self.status_checkbox = QCheckBox("✓ Mark as completed")
        self.status_checkbox.setObjectName("statusCheckbox")
        self.status_checkbox.setChecked(bool(is_done))
        checkbox_layout.addWidget(self.status_checkbox)
        
        layout.addWidget(checkbox_frame)
        layout.addSpacing(8)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(16)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        cancel_btn.setFixedHeight(56)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.close)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("saveButton")
        save_btn.setFixedHeight(56)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self.save_task)
        
        button_layout.addWidget(cancel_btn, 1)
        button_layout.addWidget(save_btn, 2)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        main_layout.addWidget(content)
        
        # ⭐ Set initial time constraint based on selected date
        self.update_time_limit(date)
        
        # ⭐ Setup time constraint update timer (updates every minute)
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self.update_current_time_constraint)
        self.time_update_timer.start(60000)  # 60 seconds = 1 minute
        
        # Apply dark mode on initialization
        self.apply_dark_mode(self.dark_mode)

    def update_time_limit(self, selected_date):
        """Prevent selecting past time for today, allow any time for future dates"""
        today = QDate.currentDate()

        if selected_date == today:
            # Today → block past time (with current time, not static)
            self.time_input.setMinimumTime(QTime.currentTime())
        else:
            # Future date → allow any time
            self.time_input.setMinimumTime(QTime(0, 0))

    def update_current_time_constraint(self):
        """Update time constraint every minute if today's date is selected"""
        if self.date_input.date() == QDate.currentDate():
            self.time_input.setMinimumTime(QTime.currentTime())

    def load_dark_mode(self):
        """Load dark mode preference from user_data.json"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("dark_mode", False)
            except:
                return False
        return False
        
    def apply_dark_mode(self, enabled):
        """Applies consistent dark/light themes to the edit window."""
        if enabled:
            self.setStyleSheet("""
                /* Main Window */
                QWidget {
                    background-color: #0A0E27; 
                    font-family: 'Inter', 'Segoe UI Variable', sans-serif;
                }
                
                /* Header with Gradient */
                QFrame#header {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.3 #8B5CF6, stop:0.7 #A78BFA, stop:1 #6366F1);
                    border: none;
                }
                
                QLabel#headerTitle {
                    font-size: 30px;
                    font-weight: 700;
                    color: #FFFFFF;
                    letter-spacing: -2px;
                    background: transparent;
                }
                
                /* Content Area */
                QFrame#content {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0F172A, stop:1 #0A0E27);
                    border: none;
                }
                
                /* Field Labels */
                QLabel#fieldLabel { 
                    font-weight: 800; 
                    font-size: 10px;
                    letter-spacing: 2.5px;
                    color: #A78BFA; 
                    background: transparent;
                }

                /* Input Fields - Default State */
                QLineEdit#inputField, QDateEdit#inputField, QTimeEdit#inputField { 
                    background: rgba(30, 41, 59, 0.5);
                    color: #E2E8F0; 
                    border: 2.5px solid rgba(100, 116, 139, 0.3);
                    border-radius: 16px; 
                    padding: 16px 20px;
                    font-size: 17px;
                    font-weight: 500;
                }
                
                /* Input Fields - Hover State */
                QLineEdit#inputField:hover, QDateEdit#inputField:hover, QTimeEdit#inputField:hover {
                    border: 2.5px solid rgba(139, 92, 246, 0.6);
                    background: rgba(30, 41, 59, 0.7);
                }
                
                /* Input Fields - Focus/Active State */
                QLineEdit#inputField:focus, QDateEdit#inputField:focus, QTimeEdit#inputField:focus {
                    border: 3px solid #8B5CF6;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(139, 92, 246, 0.15), stop:1 rgba(30, 41, 59, 0.9));
                }
                
                /* Placeholder Text */
                QLineEdit#inputField::placeholder {
                    color: #64748B;
                    font-style: italic;
                }
                
                /* DateEdit & TimeEdit Dropdown */
                QDateEdit::drop-down, QTimeEdit::drop-down {
                    background: rgba(139, 92, 246, 0.15);
                    border: none;
                    border-radius: 10px;
                    width: 45px;
                    margin-right: 6px;
                }
                
                QDateEdit::drop-down:hover, QTimeEdit::drop-down:hover {
                    background: rgba(139, 92, 246, 0.25);
                }
                
                QDateEdit::down-arrow, QTimeEdit::down-arrow {
                    image: none;
                    border: 3px solid #A78BFA;
                    border-top: none;
                    border-right: none;
                    width: 11px;
                    height: 11px;
                    margin-right: 14px;
                }
                
                /* Calendar Widget */
                QCalendarWidget {
                    background-color: #1E293B;
                    color: #E2E8F0;
                    border: 3px solid rgba(139, 92, 246, 0.4);
                    border-radius: 16px;
                }
                
                QCalendarWidget QToolButton {
                    background-color: rgba(139, 92, 246, 0.25);
                    color: #E2E8F0;
                    border-radius: 10px;
                    padding: 10px;
                    font-weight: 700;
                }
                
                QCalendarWidget QToolButton:hover {
                    background-color: rgba(139, 92, 246, 0.4);
                }
                
                QCalendarWidget QMenu {
                    background-color: #1E293B;
                    color: #E2E8F0;
                }
                
                QCalendarWidget QSpinBox {
                    background-color: #0F172A;
                    color: #E2E8F0;
                    border: 2px solid #334155;
                    border-radius: 8px;
                    padding: 6px;
                }
                
                QCalendarWidget QAbstractItemView {
                    background-color: #0F172A;
                    color: #E2E8F0;
                    selection-background-color: #8B5CF6;
                    selection-color: white;
                    border-radius: 8px;
                }

                /* Checkbox Frame */
                QFrame#checkboxFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(139, 92, 246, 0.12), stop:1 rgba(99, 102, 241, 0.12));
                    border: 2.5px solid rgba(139, 92, 246, 0.3);
                    border-radius: 16px;
                }
                
                /* Checkbox */
                QCheckBox#statusCheckbox {
                    font-size: 17px;
                    font-weight: 600;
                    color: #E2E8F0;
                    spacing: 16px;
                    background: transparent;
                }
                
                QCheckBox#statusCheckbox::indicator { 
                    width: 28px; 
                    height: 28px; 
                    border-radius: 10px; 
                    border: 3px solid #64748B; 
                    background: rgba(15, 23, 42, 0.6); 
                }
                
                QCheckBox#statusCheckbox::indicator:hover { 
                    border-color: #A78BFA; 
                    background: rgba(139, 92, 246, 0.2);
                }
                
                QCheckBox#statusCheckbox::indicator:checked { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #8B5CF6, stop:0.5 #A78BFA, stop:1 #6366F1);
                    border-color: #A78BFA; 
                }

                /* Cancel Button */
                QPushButton#cancelButton { 
                    background: rgba(71, 85, 105, 0.4);
                    color: #CBD5E1; 
                    font-weight: 700; 
                    font-size: 16px;
                    border: 2.5px solid rgba(100, 116, 139, 0.5);
                    border-radius: 16px;
                }
                
                QPushButton#cancelButton:hover { 
                    background: rgba(71, 85, 105, 0.6);
                    border: 2.5px solid #64748B;
                    color: #F1F5F9;
                }
                
                /* Save Button with Gradient */
                QPushButton#saveButton { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A78BFA);
                    color: #FFFFFF; 
                    font-weight: 800; 
                    font-size: 17px;
                    border: none;
                    border-radius: 16px;
                }
                
                QPushButton#saveButton:hover { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #8B5CF6);
                }
            """)
        else:
            self.setStyleSheet("""
                /* Main Window */
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFFFFF, stop:1 #F8FAFC);
                    font-family: 'Inter', 'Segoe UI Variable', sans-serif;
                }
                
                /* Header with Gradient */
                QFrame#header {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.3 #8B5CF6, stop:0.7 #A78BFA, stop:1 #6366F1);
                    border: none;
                }
                
                QLabel#headerTitle {
                    font-size: 36px;
                    font-weight: 900;
                    color: #FFFFFF;
                    letter-spacing: -2px;
                    background: transparent;
                }
                
                /* Content Area */
                QFrame#content {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFFFFF, stop:1 #F8FAFC);
                    border: none;
                }
                
                /* Field Labels */
                QLabel#fieldLabel { 
                    font-weight: 800; 
                    font-size: 10px;
                    letter-spacing: 2.5px;
                    color: #7C3AED; 
                    background: transparent;
                }

                /* Input Fields - Default State */
                QLineEdit#inputField, QDateEdit#inputField, QTimeEdit#inputField { 
                    background: #FFFFFF;
                    color: #0F172A; 
                    border: 2.5px solid rgba(226, 232, 240, 0.8);
                    border-radius: 16px; 
                    padding: 16px 20px;
                    font-size: 17px;
                    font-weight: 500;
                }
                
                /* Input Fields - Hover State */
                QLineEdit#inputField:hover, QDateEdit#inputField:hover, QTimeEdit#inputField:hover {
                    border: 2.5px solid rgba(139, 92, 246, 0.5);
                    background: rgba(248, 250, 252, 0.9);
                }
                
                /* Input Fields - Focus/Active State */
                QLineEdit#inputField:focus, QDateEdit#inputField:focus, QTimeEdit#inputField:focus {
                    border: 3px solid #8B5CF6;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(245, 243, 255, 0.9), stop:1 #FFFFFF);
                }
                
                /* Placeholder Text */
                QLineEdit#inputField::placeholder {
                    color: #94A3B8;
                    font-style: italic;
                }
                
                /* DateEdit & TimeEdit Dropdown */
                QDateEdit::drop-down, QTimeEdit::drop-down {
                    background: rgba(139, 92, 246, 0.08);
                    border: none;
                    border-radius: 10px;
                    width: 45px;
                    margin-right: 6px;
                }
                
                QDateEdit::drop-down:hover, QTimeEdit::drop-down:hover {
                    background: rgba(139, 92, 246, 0.15);
                }
                
                QDateEdit::down-arrow, QTimeEdit::down-arrow {
                    image: none;
                    border: 3px solid #8B5CF6;
                    border-top: none;
                    border-right: none;
                    width: 11px;
                    height: 11px;
                    margin-right: 14px;
                }
                
                /* Calendar Widget */
                QCalendarWidget {
                    background-color: #FFFFFF;
                    color: #0F172A;
                    border: 3px solid rgba(139, 92, 246, 0.3);
                    border-radius: 16px;
                }
                
                QCalendarWidget QToolButton {
                    background-color: rgba(139, 92, 246, 0.12);
                    color: #0F172A;
                    border-radius: 10px;
                    padding: 10px;
                    font-weight: 700;
                }
                
                QCalendarWidget QToolButton:hover {
                    background-color: rgba(139, 92, 246, 0.2);
                }
                
                QCalendarWidget QMenu {
                    background-color: #FFFFFF;
                    color: #0F172A;
                }
                
                QCalendarWidget QSpinBox {
                    background-color: #F8FAFC;
                    color: #0F172A;
                    border: 2px solid #E2E8F0;
                    border-radius: 8px;
                    padding: 6px;
                }
                
                QCalendarWidget QAbstractItemView {
                    background-color: #F8FAFC;
                    color: #0F172A;
                    selection-background-color: #8B5CF6;
                    selection-color: white;
                    border-radius: 8px;
                }

                /* Checkbox Frame */
                QFrame#checkboxFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(139, 92, 246, 0.08), stop:1 rgba(99, 102, 241, 0.08));
                    border: 2.5px solid rgba(139, 92, 246, 0.25);
                    border-radius: 16px;
                }
                
                /* Checkbox */
                QCheckBox#statusCheckbox {
                    font-size: 17px;
                    font-weight: 600;
                    color: #1E293B;
                    spacing: 16px;
                    background: transparent;
                }
                
                QCheckBox#statusCheckbox::indicator { 
                    width: 28px; 
                    height: 28px; 
                    border-radius: 10px; 
                    border: 3px solid #CBD5E1; 
                    background: #FFFFFF; 
                }
                
                QCheckBox#statusCheckbox::indicator:hover { 
                    border-color: #8B5CF6; 
                    background: rgba(139, 92, 246, 0.08);
                }
                
                QCheckBox#statusCheckbox::indicator:checked { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A78BFA);
                    border-color: #8B5CF6; 
                }

                /* Cancel Button */
                QPushButton#cancelButton { 
                    background: #F1F5F9;
                    color: #475569; 
                    font-weight: 700; 
                    font-size: 16px;
                    border: 2.5px solid #E2E8F0;
                    border-radius: 16px;
                }
                
                QPushButton#cancelButton:hover { 
                    background: #E2E8F0;
                    border: 2.5px solid #CBD5E1;
                    color: #334155;
                }
                
                /* Save Button with Gradient */
                QPushButton#saveButton { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A78BFA);
                    color: #FFFFFF; 
                    font-weight: 800; 
                    font-size: 17px;
                    border: none;
                    border-radius: 16px;
                }
                
                QPushButton#saveButton:hover { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #8B5CF6);
                }
            """)
    
    def save_task(self):
        new_title = self.title_input.text()
        new_date = self.date_input.date().toString("yyyy-MM-dd")
        new_time = self.time_input.time().toString("hh:mm ap")
        new_status = 1 if self.status_checkbox.isChecked() else 0

        update_task(self.task_id, new_title, new_date, new_time, new_status)
        self.task_updated.emit()
        self.close()

    def closeEvent(self, event):
        """Stop the timer when widget is closed"""
        if hasattr(self, 'time_update_timer'):
            self.time_update_timer.stop()
        event.accept()