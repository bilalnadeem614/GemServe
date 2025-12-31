from db.todo_db_helper import insert_task, init_database, delete_task, get_all_tasks, update_task_status
from utils.extract_info import extract_info
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QCheckBox, QDateEdit, QTimeEdit
)
from PySide6.QtCore import Qt, Signal, QDate, QTime, QTimer
from datetime import datetime

# Initialize database
init_database()


class TodoList(QWidget):
    task_updated = Signal()
    
    def __init__(self, go_back):
        super().__init__()

        self.go_back = go_back
        self.dark_mode = False

        # Main Layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        self.build_ui()
        self.load_tasks()
        
        # ⭐ Setup auto-refresh timer (checks every 10 seconds for database changes)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_for_updates)
        self.refresh_timer.start(10000)  # 10 seconds = 10000 milliseconds
        
        # ⭐ Setup time constraint update timer (updates every minute to keep time limit current)
        self.time_update_timer = QTimer()
        self.time_update_timer.timeout.connect(self.update_current_time_constraint)
        self.time_update_timer.start(60000)  # 60 seconds = 1 minute

    def check_for_updates(self):
        """Check if database has changed and refresh UI if needed"""
        try:
            tasks = get_all_tasks()
            current_count = len(tasks)
            
            # Count completed tasks
            completed_count = sum(1 for task in tasks if int(task[5]) == 1)
            current_state = (current_count, completed_count)
            
            # Compare with last known state
            if not hasattr(self, 'last_state'):
                self.last_state = current_state
                return
                
            if current_state != self.last_state:
                self.load_tasks()  # Refresh the UI
                self.last_state = current_state
        except Exception as e:
            print(f"Error checking for updates: {e}")

    def update_current_time_constraint(self):
        """Update time constraint every minute if today's date is selected"""
        if self.date_input.date() == QDate.currentDate():
            self.time_input.setMinimumTime(QTime.currentTime())

    def build_ui(self):
        # Header Section
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(80)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)
        
        self.back_btn = QPushButton("←")
        self.back_btn.setObjectName("backButton")
        self.back_btn.setFixedSize(45, 45)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.go_back)
        
        self.title = QLabel("To-Do List")
        self.title.setObjectName("headerTitle")
        
        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        
        self.main_layout.addWidget(header)
        
        # Content Area
        content = QFrame()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)
        
        # Two Column Layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(25)
        
        # Pending Tasks Column
        pending_container = QFrame()
        pending_container.setObjectName("taskColumn")
        pending_col_layout = QVBoxLayout(pending_container)
        pending_col_layout.setContentsMargins(25, 25, 25, 25)
        pending_col_layout.setSpacing(15)
        
        pending_header = QLabel("PENDING TASKS")
        pending_header.setObjectName("pendingTitle")
        pending_col_layout.addWidget(pending_header)
        
        self.pending_scroll = QScrollArea()
        self.pending_scroll.setObjectName("taskScroll")
        self.pending_scroll.setWidgetResizable(True)
        self.pending_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        pending_box = QWidget()
        pending_box.setObjectName("scrollContent")
        self.pending_layout = QVBoxLayout(pending_box)
        self.pending_layout.setSpacing(12)
        self.pending_layout.addStretch()
        self.pending_scroll.setWidget(pending_box)
        
        pending_col_layout.addWidget(self.pending_scroll)
        
        # Completed Tasks Column
        completed_container = QFrame()
        completed_container.setObjectName("taskColumn")
        completed_col_layout = QVBoxLayout(completed_container)
        completed_col_layout.setContentsMargins(25, 25, 25, 25)
        completed_col_layout.setSpacing(15)
        
        completed_header = QLabel("COMPLETED TASKS")
        completed_header.setObjectName("completedTitle")
        completed_col_layout.addWidget(completed_header)
        
        self.completed_scroll = QScrollArea()
        self.completed_scroll.setObjectName("taskScroll")
        self.completed_scroll.setWidgetResizable(True)
        self.completed_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        completed_box = QWidget()
        completed_box.setObjectName("scrollContent")
        self.completed_layout = QVBoxLayout(completed_box)
        self.completed_layout.setSpacing(12)
        self.completed_layout.addStretch()
        self.completed_scroll.setWidget(completed_box)
        
        completed_col_layout.addWidget(self.completed_scroll)
        
        columns_layout.addWidget(pending_container, 1)
        columns_layout.addWidget(completed_container, 1)
        content_layout.addLayout(columns_layout)
        
        # Input Section
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(15)
        
        self.add_button = QPushButton("+")
        self.add_button.setObjectName("addButton")
        self.add_button.setFixedSize(55, 55)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.create_task)
        
        # Title Input
        self.task_input = QLineEdit()
        self.task_input.setObjectName("taskInput")
        self.task_input.setPlaceholderText("Task title...")
        self.task_input.setFixedHeight(55)
        self.task_input.returnPressed.connect(self.create_task)
        
        # Date Input
        self.date_input = QDateEdit()
        self.date_input.setObjectName("dateInput")
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setMinimumDate(QDate.currentDate())
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setFixedHeight(55)
        self.date_input.setCursor(Qt.PointingHandCursor)
        self.date_input.dateChanged.connect(self.update_time_limit)

        # Time Input
        self.time_input = QTimeEdit()
        self.time_input.setObjectName("timeInput")
        self.time_input.setTime(QTime.currentTime())
        self.time_input.setDisplayFormat("hh:mm AP")
        self.time_input.setFixedHeight(55)
        self.time_input.setCursor(Qt.PointingHandCursor)
        # ⭐ Disable up/down arrow buttons
        self.time_input.setButtonSymbols(QTimeEdit.NoButtons)
        
        # ⭐ Set initial time constraint for today (blocks past time)
        self.time_input.setMinimumTime(QTime.currentTime())
        
        input_layout.addWidget(self.add_button)
        input_layout.addWidget(self.task_input, 2)
        input_layout.addWidget(self.date_input, 1)
        input_layout.addWidget(self.time_input, 1)

        content_layout.addWidget(input_frame)
        self.main_layout.addWidget(content)

    def update_time_limit(self, selected_date):
        """Prevent selecting past time for today, allow any time for future dates"""
        today = QDate.currentDate()

        if selected_date == today:
            # Today → block past time (with current time, not static)
            self.time_input.setMinimumTime(QTime.currentTime())
        else:
            # Future date → allow any time
            self.time_input.setMinimumTime(QTime(0, 0))

    def apply_dark_mode(self, enabled):
        self.dark_mode = enabled
        
        scroll_style = """
            QScrollArea#taskScroll {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(139, 92, 246, 0.3);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(139, 92, 246, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """
        
        if enabled:
            self.setStyleSheet(scroll_style + """
                /* Main Background */
                QWidget {
                    background-color: #0A0E27;
                    font-family: 'Inter', 'Segoe UI Variable', sans-serif;
                }
                
                /* Header */
                QFrame#header {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #6366F1);
                    border: none;
                }
                
                QPushButton#backButton {
                    background: rgba(255, 255, 255, 0.15);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 22px;
                    font-size: 22px;
                    font-weight: bold;
                }
                QPushButton#backButton:hover {
                    background: rgba(255, 255, 255, 0.25);
                }
                
                QLabel#headerTitle {
                    color: #FFFFFF;
                    font-size: 28px;
                    font-weight: 800;
                    letter-spacing: -1px;
                    background: transparent;
                }
                
                /* Content */
                QFrame#content {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0F172A, stop:1 #0A0E27);
                }
                
                /* Task Columns */
                QFrame#taskColumn {
                    background: rgba(30, 41, 59, 0.4);
                    border: 2px solid rgba(139, 92, 246, 0.2);
                    border-radius: 20px;
                }
                
                QWidget#scrollContent {
                    background: transparent;
                }
                
                /* Column Titles */
                QLabel#pendingTitle {
                    color: #60A5FA;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 2px;
                    background: transparent;
                }
                
                QLabel#completedTitle {
                    color: #8B5CF6;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 2px;
                    background: transparent;
                }
                
                /* Input Frame */
                QFrame#inputFrame {
                    background: transparent;
                }
                
                /* Add Button */
                QPushButton#addButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:1 #8B5CF6);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 27px;
                    font-size: 24px;
                    font-weight: bold;
                }
                QPushButton#addButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4F46E5, stop:1 #7C3AED);
                }
                
                /* Task Input */
                QLineEdit#taskInput {
                    background: rgba(30, 41, 59, 0.6);
                    color: #E2E8F0;
                    border: 2.5px solid rgba(139, 92, 246, 0.25);
                    border-radius: 27px;
                    padding: 0 25px;
                    font-size: 16px;
                    font-weight: 500;
                }
                QLineEdit#taskInput:focus {
                    border: 2.5px solid #8B5CF6;
                }
                QLineEdit#taskInput::placeholder {
                    color: #64748B;
                    font-style: italic;
                }
                
                /* Date and Time Inputs */
                QDateEdit#dateInput, QTimeEdit#timeInput {
                    background: rgba(30, 41, 59, 0.6);
                    color: #E2E8F0;
                    border: 2.5px solid rgba(139, 92, 246, 0.25);
                    border-radius: 27px;
                    padding: 0 20px;
                    font-size: 15px;
                    font-weight: 500;
                }
                QDateEdit#dateInput:focus, QTimeEdit#timeInput:focus {
                    border: 2.5px solid #8B5CF6;
                }
                QDateEdit::drop-down, QTimeEdit::drop-down {
                    border: none;
                    width: 30px;
                }
                QDateEdit::down-arrow, QTimeEdit::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #8B5CF6;
                    margin-right: 8px;
                }
                
                /* Calendar Widget */
                QCalendarWidget {
                    background: rgba(15, 23, 42, 0.95);
                    color: #E2E8F0;
                    border: 2px solid rgba(139, 92, 246, 0.3);
                    border-radius: 12px;
                }
                QCalendarWidget QToolButton {
                    color: #E2E8F0;
                    background: transparent;
                    border: none;
                    padding: 5px;
                }
                QCalendarWidget QToolButton:hover {
                    background: rgba(139, 92, 246, 0.2);
                    border-radius: 6px;
                }
                QCalendarWidget QMenu {
                    background: rgba(15, 23, 42, 0.95);
                    color: #E2E8F0;
                    border: 1px solid rgba(139, 92, 246, 0.3);
                }
                QCalendarWidget QSpinBox {
                    background: rgba(30, 41, 59, 0.6);
                    color: #E2E8F0;
                    border: 1px solid rgba(139, 92, 246, 0.3);
                    padding: 3px;
                }
                QCalendarWidget QAbstractItemView:enabled {
                    color: #E2E8F0;
                    background: transparent;
                    selection-background-color: rgba(139, 92, 246, 0.4);
                    selection-color: #FFFFFF;
                }
                QCalendarWidget QAbstractItemView:disabled {
                    color: #475569;
                }
                
                /* Task Items */
                QFrame#taskItem {
                    background: rgba(30, 41, 59, 0.5);
                    border: 2px solid rgba(71, 85, 105, 0.3);
                    border-radius: 14px;
                }
                QFrame#taskItem:hover {
                    background: rgba(139, 92, 246, 0.1);
                    border: 2px solid rgba(139, 92, 246, 0.4);
                }
                
                QLabel#taskText {
                    color: #E2E8F0;
                    font-size: 15px;
                    font-weight: 500;
                    background: transparent;
                }
                
                /* Checkbox */
                QCheckBox::indicator {
                    width: 24px;
                    height: 24px;
                    border-radius: 8px;
                    border: 2.5px solid #64748B;
                    background: rgba(15, 23, 42, 0.6);
                }
                QCheckBox::indicator:hover {
                    border-color: #8B5CF6;
                }
               QCheckBox::indicator:checked { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8B5CF6, stop:1 #6366F1);
                    border-color: #8B5CF6; 
                }
                
                /* Delete Button */
                QPushButton#deleteButton {
                    background: rgba(239, 68, 68, 0.15);
                    color: #F87171;
                    border: none;
                    border-radius: 14px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton#deleteButton:hover {
                    background: rgba(239, 68, 68, 0.3);
                    color: #EF4444;
                }
            """)
        else:
            self.setStyleSheet(scroll_style + """
                /* Main Background */
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #F8FAFC, stop:1 #EFF6FF);
                    font-family: 'Inter', 'Segoe UI Variable', sans-serif;
                }
                
                /* Header */
                QFrame#header {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #6366F1);
                    border: none;
                }
                
                QPushButton#backButton {
                    background: rgba(255, 255, 255, 0.2);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 22px;
                    font-size: 22px;
                    font-weight: bold;
                }
                QPushButton#backButton:hover {
                    background: rgba(255, 255, 255, 0.35);
                }
                
                QLabel#headerTitle {
                    color: #FFFFFF;
                    font-size: 28px;
                    font-weight: 800;
                    letter-spacing: -1px;
                    background: transparent;
                }
                
                /* Content */
                QFrame#content {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #F8FAFC, stop:1 #EFF6FF);
                }
                
                /* Task Columns */
                QFrame#taskColumn {
                    background: #FFFFFF;
                    border: 2px solid rgba(139, 92, 246, 0.15);
                    border-radius: 20px;
                }
                
                QWidget#scrollContent {
                    background: transparent;
                }
                
                /* Column Titles */
                QLabel#pendingTitle {
                    color: #2563EB;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 2px;
                    background: transparent;
                }
                
                QLabel#completedTitle {
                    color: #8B5CF6;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 2px;
                    background: transparent;
                }
                
                /* Input Frame */
                QFrame#inputFrame {
                    background: transparent;
                }
                
                /* Add Button */
                QPushButton#addButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:1 #8B5CF6);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 27px;
                    font-size: 24px;
                    font-weight: bold;
                }
                QPushButton#addButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4F46E5, stop:1 #7C3AED);
                }
                
                /* Task Input */
                QLineEdit#taskInput {
                    background: #FFFFFF;
                    color: #0F172A;
                    border: 2.5px solid rgba(226, 232, 240, 0.8);
                    border-radius: 27px;
                    padding: 0 25px;
                    font-size: 16px;
                    font-weight: 500;
                }
                QLineEdit#taskInput:focus {
                    border: 2.5px solid #8B5CF6;
                }
                QLineEdit#taskInput::placeholder {
                    color: #94A3B8;
                    font-style: italic;
                }
                
                /* Date and Time Inputs */
                QDateEdit#dateInput, QTimeEdit#timeInput {
                    background: #FFFFFF;
                    color: #0F172A;
                    border: 2.5px solid rgba(226, 232, 240, 0.8);
                    border-radius: 27px;
                    padding: 0 20px;
                    font-size: 15px;
                    font-weight: 500;
                }
                QDateEdit#dateInput:focus, QTimeEdit#timeInput:focus {
                    border: 2.5px solid #8B5CF6;
                }
                QDateEdit::drop-down, QTimeEdit::drop-down {
                    border: none;
                    width: 30px;
                }
                QDateEdit::down-arrow, QTimeEdit::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #8B5CF6;
                    margin-right: 8px;
                }
                
                /* Calendar Widget */
                QCalendarWidget {
                    background: #FFFFFF;
                    color: #0F172A;
                    border: 2px solid rgba(139, 92, 246, 0.2);
                    border-radius: 12px;
                }
                QCalendarWidget QToolButton {
                    color: #0F172A;
                    background: transparent;
                    border: none;
                    padding: 5px;
                }
                QCalendarWidget QToolButton:hover {
                    background: rgba(139, 92, 246, 0.1);
                    border-radius: 6px;
                }
                QCalendarWidget QMenu {
                    background: #FFFFFF;
                    color: #0F172A;
                    border: 1px solid rgba(139, 92, 246, 0.2);
                }
                QCalendarWidget QSpinBox {
                    background: #FFFFFF;
                    color: #0F172A;
                    border: 1px solid rgba(226, 232, 240, 0.8);
                    padding: 3px;
                }
                QCalendarWidget QAbstractItemView:enabled {
                    color: #0F172A;
                    background: transparent;
                    selection-background-color: rgba(139, 92, 246, 0.3);
                    selection-color: #FFFFFF;
                }
                QCalendarWidget QAbstractItemView:disabled {
                    color: #94A3B8;
                }
                
                /* Task Items */
                QFrame#taskItem {
                    background: rgba(248, 250, 252, 0.8);
                    border: 2px solid rgba(226, 232, 240, 0.8);
                    border-radius: 14px;
                }
                QFrame#taskItem:hover {
                    background: rgba(245, 243, 255, 0.9);
                    border: 2px solid rgba(139, 92, 246, 0.3);
                }
                
                QLabel#taskText {
                    color: #1E293B;
                    font-size: 15px;
                    font-weight: 500;
                    background: transparent;
                }
                
                /* Checkbox */
                QCheckBox::indicator {
                    width: 24px;
                    height: 24px;
                    border-radius: 8px;
                    border: 2.5px solid #CBD5E1;
                    background: #FFFFFF;
                }
                QCheckBox::indicator:hover {
                    border-color: #8B5CF6;
                }
                QCheckBox::indicator:checked { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #8B5CF6, stop:1 #6366F1);
                    border-color: #8B5CF6; 
                }
                
                /* Delete Button */
                QPushButton#deleteButton {
                    background: rgba(239, 68, 68, 0.1);
                    color: #DC2626;
                    border: none;
                    border-radius: 14px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton#deleteButton:hover {
                    background: rgba(239, 68, 68, 0.2);
                    color: #B91C1C;
                }
            """)
        
        self.load_tasks()

    def create_task(self):
        # Get values from separate inputs
        title = self.task_input.text().strip()
        if not title:
            return

        # Get date in YYYY-MM-DD format
        task_date = self.date_input.date().toString("yyyy-MM-dd")
        
        # Get time in HH:MM AM/PM format
        task_time = self.time_input.time().toString("hh:mm AP")

        insert_task(title, task_date, task_time)
        self.task_updated.emit()
        self.task_input.clear()
        # Reset date and time to current values
        self.date_input.setDate(QDate.currentDate())
        self.time_input.setTime(QTime.currentTime())
        # ⭐ Reset time constraint when resetting to today
        self.time_input.setMinimumTime(QTime.currentTime())
        self.load_tasks()

    def refresh_page(self):
        """Refresh the todo list"""
        self.load_tasks()

    def load_tasks(self):
        # Clear existing tasks
        for layout in [self.pending_layout, self.completed_layout]:
            while layout.count() > 1:
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        # Get all tasks
        tasks = get_all_tasks()

        for task in tasks:
            # Handle tuple unpacking safely
            task_id = task[0]
            title = task[1]
            is_done = int(task[5])
            
            if is_done:
                self.add_completed_task(task_id, title)
            else:
                self.add_pending_task(task_id, title)

    def _add_task_widget(self, layout, task_id, text, done=False):
        task_frame = QFrame()
        task_frame.setObjectName("taskItem")
        task_frame.setFixedHeight(60)
        
        task_layout = QHBoxLayout(task_frame)
        task_layout.setContentsMargins(16, 0, 16, 0)
        task_layout.setSpacing(12)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(done)
        checkbox.setCursor(Qt.PointingHandCursor)
        checkbox.stateChanged.connect(lambda s, tid=task_id: self.mark_done(tid, s))
        
        # Task Text
        task_label = QLabel(text)
        task_label.setObjectName("taskText")
        
        # Delete Button
        delete_btn = QPushButton("✕")
        delete_btn.setObjectName("deleteButton")
        delete_btn.setFixedSize(32, 32)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.delete_task(task_id))
        
        task_layout.addWidget(checkbox)
        task_layout.addWidget(task_label, 1)
        task_layout.addWidget(delete_btn)
        
        layout.insertWidget(layout.count() - 1, task_frame)

    def add_pending_task(self, task_id, text):
        self._add_task_widget(self.pending_layout, task_id, text, done=False)

    def add_completed_task(self, task_id, text):
        self._add_task_widget(self.completed_layout, task_id, text, done=True)

    def mark_done(self, task_id, checked):
        is_done = 1 if checked else 0
        update_task_status(task_id, is_done)
        self.task_updated.emit()
        self.load_tasks()

    def delete_task(self, task_id):
        """Delete a task from the database"""
        delete_task(task_id)
        self.task_updated.emit()
        self.load_tasks()
    
    def closeEvent(self, event):
        """Stop the timer when widget is closed"""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        event.accept()