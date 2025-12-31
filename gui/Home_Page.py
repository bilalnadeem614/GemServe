# gui/Home_Page.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QCheckBox, QMessageBox
)
from PySide6.QtGui import QPixmap, QIcon, QPainter, QPainterPath, QColor
from PySide6.QtCore import QSize, Qt, Signal, QTimer
import json
import os
from datetime import datetime
from db.todo_db_helper import get_all_tasks, update_task_status
from gui.edit_task_page import EditTaskPage
from db import get_all_sessions, delete_session
from db.vector_store import delete_session_collection

DATA_FILE = "user_data.json"

class HomePage(QWidget):
    task_status_changed = Signal()
    
    def __init__(self, go_to_settings, go_to_tasks, go_to_chatbot, open_chat_session):
        super().__init__()
        self.go_to_settings = go_to_settings
        self.go_to_tasks = go_to_tasks
        self.go_to_chatbot = go_to_chatbot
        self.open_chat_session = open_chat_session
        self.dark_mode = False

        self.setup_ui()
        self.load_chat_sessions()
        self.load_task_rows(self.task_layout)
        
        # ⭐ Setup auto-refresh timer (checks every 10 seconds for database changes)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_for_updates)
        self.refresh_timer.start(10000)  # 10 seconds

    def check_for_updates(self):
        """Check if database has changed and refresh UI if needed"""
        try:
            all_tasks = get_all_tasks()
            # Filter only pending tasks (is_done == 0)
            tasks = [t for t in all_tasks if t[5] == 0]
            current_count = len(tasks)
            
            # Compare with last known state
            if not hasattr(self, 'last_task_count'):
                self.last_task_count = current_count
                return
                
            if current_count != self.last_task_count:
                self.refresh_tasks()  # Refresh the UI
                self.last_task_count = current_count
        except Exception as e:
            print(f"Error checking for updates on home page: {e}")

    def setup_ui(self):
        # Overall container layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 35, 40, 40)
        self.main_layout.setSpacing(30)

        # ---------------- TOP NAVBAR ----------------
        navbar = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(4)
        
        self.welcome_label = QLabel("Welcome Back!")
        self.welcome_label.setObjectName("welcomeLabel")
        
        # Load user data to get the name
        user_data = self.load_user_data()
        user_name = user_data.get("name", "User")
        
        self.name_label = QLabel(user_name)
        self.name_label.setObjectName("nameLabel")
        
        self.date_label = QLabel("Here is what's happening today.")
        self.date_label.setObjectName("subLabel")
        
        header_text_layout.addWidget(self.welcome_label)
        header_text_layout.addWidget(self.name_label)
        header_text_layout.addWidget(self.date_label)
        navbar.addLayout(header_text_layout, stretch=1)

        self.profile_button = QPushButton()
        self.profile_button.setObjectName("profileButton")
        self.profile_button.setFixedSize(85, 85)
        self.profile_button.setCursor(Qt.PointingHandCursor)
        
        self.set_profile_picture(user_data.get("image", ""))
        self.profile_button.clicked.connect(self.go_to_settings)
        navbar.addWidget(self.profile_button)
        self.main_layout.addLayout(navbar)

        # ---------------- MAIN CONTENT ----------------
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(30)

        # --- CHAT HISTORY (60% WIDTH) ---
        self.chat_card = QFrame()
        self.chat_card.setObjectName("chatCard")
        chat_vbox = QVBoxLayout(self.chat_card)
        chat_vbox.setContentsMargins(25, 25, 25, 25)

        chat_header = QHBoxLayout()
        self.chats_title = QLabel("CHAT HISTORY")
        self.chats_title.setObjectName("sectionTitleChat")
        
        self.new_chat_btn = QPushButton("+")
        self.new_chat_btn.setFixedSize(36, 36)
        self.new_chat_btn.setObjectName("circularAddBtnChat")
        self.new_chat_btn.clicked.connect(self.go_to_chatbot)
        
        chat_header.addWidget(self.chats_title)
        chat_header.addStretch()
        chat_header.addWidget(self.new_chat_btn)
        chat_vbox.addLayout(chat_header)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setObjectName("modernScroll")
        
        chat_content = QWidget()
        chat_content.setObjectName("transparentBg")
        self.chat_buttons_layout = QVBoxLayout(chat_content)
        self.chat_buttons_layout.setSpacing(12)
        self.chat_scroll.setWidget(chat_content)
        chat_vbox.addWidget(self.chat_scroll)

        # --- PRIORITY TASKS (40% WIDTH) ---
        self.task_card = QFrame()
        self.task_card.setObjectName("taskCard")
        task_vbox = QVBoxLayout(self.task_card)
        task_vbox.setContentsMargins(25, 25, 25, 25)

        task_header = QHBoxLayout()
        self.tasks_title = QLabel("PRIORITY TASKS")
        self.tasks_title.setObjectName("sectionTitleTask")
        
        self.new_task_btn = QPushButton("+")
        self.new_task_btn.setFixedSize(36, 36)
        self.new_task_btn.setObjectName("circularAddBtnTask")
        self.new_task_btn.clicked.connect(self.go_to_tasks)
        
        task_header.addWidget(self.tasks_title)
        task_header.addStretch()
        task_header.addWidget(self.new_task_btn)
        task_vbox.addLayout(task_header)

        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        self.task_scroll.setObjectName("modernScroll")

        self.task_content = QWidget()
        self.task_content.setObjectName("transparentBg")
        self.task_layout = QVBoxLayout(self.task_content)
        self.task_layout.setSpacing(12)
        self.task_scroll.setWidget(self.task_content)
        task_vbox.addWidget(self.task_scroll)

        grid_layout.addWidget(self.chat_card, 5.5) # 55%
        grid_layout.addWidget(self.task_card, 4.5) # 45%
        self.main_layout.addLayout(grid_layout)

    def update_data(self, data):
        self.set_profile_picture(data.get("image", ""))
        # Update the name label when data changes
        user_name = data.get("name", "User")
        self.name_label.setText(user_name)

    def refresh_chat_sessions(self):
        self.load_chat_sessions()

    def delete_chat_session(self, session_id, title):
        """Delete a chat session with confirmation"""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Delete Chat",
            f"Are you sure you want to delete this chat?\n\n'{title}'\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Delete from database
                delete_session(session_id)
                
                # Delete vector store collection
                delete_session_collection(session_id)
                
                print(f"✅ Chat session {session_id} deleted successfully")
                
                # Refresh the chat list
                self.refresh_chat_sessions()
                
                # Show success message
                QMessageBox.information(
                    self,
                    "Chat Deleted",
                    f"'{title}' has been deleted.",
                    QMessageBox.Ok
                )
            except Exception as e:
                print(f"❌ Error deleting chat: {e}")
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to delete chat: {str(e)}",
                    QMessageBox.Ok
                )

    def load_chat_sessions(self):
        while self.chat_buttons_layout.count():
            item = self.chat_buttons_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        sessions = get_all_sessions()
        if not sessions:
            lbl = QLabel("No recent activity")
            lbl.setObjectName("emptyMsg")
            self.chat_buttons_layout.addWidget(lbl, alignment=Qt.AlignCenter)
        else:
            for session_id, title, updated_at in sessions:
                # Create a container for chat row with delete button
                row_container = QWidget()
                row_layout = QHBoxLayout(row_container)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(8)
                
                # Chat button
                btn = QPushButton(f"  {title}")
                btn.setObjectName("chatRow")
                btn.setFixedHeight(50)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked, sid=session_id: self.open_chat_session(sid))
                row_layout.addWidget(btn)
                
                # Delete button (X)
                delete_btn = QPushButton("✕")
                delete_btn.setObjectName("chatDeleteBtn")
                delete_btn.setFixedSize(40, 50)
                delete_btn.setCursor(Qt.PointingHandCursor)
                delete_btn.clicked.connect(lambda checked, sid=session_id, title=title: self.delete_chat_session(sid, title))
                row_layout.addWidget(delete_btn)
                
                self.chat_buttons_layout.addWidget(row_container)
        self.chat_buttons_layout.addStretch()

    def load_task_rows(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        all_tasks = get_all_tasks()
        # Filter only pending tasks (is_done == 0)
        tasks = [t for t in all_tasks if t[5] == 0]
        
        for task in tasks:
            self.add_task_row(layout, task)
        layout.addStretch()

    def add_task_row(self, layout, task):
        task_id, title, task_date, task_time, created_at, is_done = task
        row = QWidget()
        row.setObjectName("taskRow")
        row.setFixedHeight(58)
        row.setCursor(Qt.PointingHandCursor)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(15, 0, 15, 0)

        checkbox = QCheckBox()
        checkbox.setChecked(is_done == 1)
        checkbox.stateChanged.connect(lambda s, tid=task_id: (
            update_task_status(tid, int(s == 2)), 
            self.refresh_tasks(),
            self.task_status_changed.emit()
        ))
        t_lbl = QLabel(str(title))
        t_lbl.setObjectName("itemTitle")
        
        try:
            clean_date = datetime.strptime(task_date, '%Y-%m-%d').strftime('%b %d')
        except:
            clean_date = task_date

        info_lbl = QLabel(f"{task_time or ''} • {clean_date}")
        info_lbl.setObjectName("itemTime")

        row_layout.addWidget(checkbox)
        row_layout.addWidget(t_lbl, 1)
        row_layout.addWidget(info_lbl)

        row.mousePressEvent = lambda e, t=task: self.open_edit_page(*t)
        layout.addWidget(row)

    def refresh_tasks(self): 
        self.load_task_rows(self.task_layout)

    def open_edit_page(self, task_id, title, task_date, task_time, created_at, is_done):
        self.edit_window = EditTaskPage(task_id, title, task_date, task_time, is_done)
        self.edit_window.task_updated.connect(self.refresh_tasks)
        self.edit_window.show()

    def load_user_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f: return json.load(f)
        return {"image": "Profile-Icon.png", "name": "User"}

    def set_profile_picture(self, filename):
        path = os.path.join(os.path.dirname(__file__), "..", "assets", filename)
        if os.path.exists(path):
            pix = QPixmap(path).scaled(85, 85, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            canvas = QPixmap(85, 85)
            canvas.fill(Qt.transparent)
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.Antialiasing)
            p = QPainterPath()
            p.addEllipse(0, 0, 85, 85)
            painter.setClipPath(p)
            painter.drawPixmap(0, 0, pix)
            painter.end()
            self.profile_button.setIcon(QIcon(canvas))
            self.profile_button.setIconSize(QSize(85, 85))
    
    def closeEvent(self, event):
        """Stop the timer when widget is closed"""
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        event.accept()

    def apply_dark_mode(self, enabled):
        self.dark_mode = enabled
        scroll_style = """
            QScrollArea#modernScroll { 
                background: transparent; 
                border: none; 
            } 
            QScrollBar:vertical { 
                width: 6px; 
                background: transparent; 
                margin: 4px;
            } 
            QScrollBar::handle:vertical { 
                background: rgba(148, 163, 184, 0.3); 
                border-radius: 3px; 
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { 
                background: rgba(148, 163, 184, 0.5); 
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """
        
        if enabled:
            # Modern Dark Mode - Deep Blue/Purple theme
            self.setStyleSheet(scroll_style + """
                QWidget { 
                    background-color: #0A0E27; 
                    font-family: 'Inter', 'Segoe UI Variable', 'SF Pro Display', sans-serif; 
                    color: #94A3B8; 
                }
                
                QLabel#welcomeLabel { 
                    font-size: 22px; 
                    font-weight: 600; 
                    color: #64748B; 
                    letter-spacing: 0.5px; 
                    background: transparent; 
                }
                
                QLabel#nameLabel { 
                    font-size: 48px; 
                    font-weight: 800; 
                    color: #8B5CF6;
                    letter-spacing: -2px; 
                    background: transparent;
                    margin: 4px 0px;
                }
                
                QLabel#subLabel { 
                    color: #64748B; 
                    font-size: 15px; 
                    font-weight: 500;
                    background: transparent; 
                    margin-top: 2px;
                }
                
                QPushButton#profileButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #8B5CF6, stop:1 #6366F1);
                    border: 3px solid #1E293B;
                    border-radius: 32px;
                }
                QPushButton#profileButton:hover {
                    border: 3px solid #8B5CF6;
                }
                
                QFrame#chatCard { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(139, 92, 246, 0.08), stop:1 rgba(30, 41, 59, 0.6));
                    border-radius: 28px; 
                    border: 1px solid rgba(139, 92, 246, 0.2);
                }
                
                QFrame#taskCard { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(59, 130, 246, 0.08), stop:1 rgba(30, 41, 59, 0.6));
                    border-radius: 28px; 
                    border: 1px solid rgba(59, 130, 246, 0.2);
                }
                
                QLabel#sectionTitleChat { 
                    color: #A78BFA; 
                    font-weight: 700; 
                    font-size: 11px; 
                    letter-spacing: 2.5px; 
                    background: transparent; 
                }
                
                QLabel#sectionTitleTask { 
                    color: #60A5FA; 
                    font-weight: 700; 
                    font-size: 11px; 
                    letter-spacing: 2.5px; 
                    background: transparent; 
                }
                
                QPushButton#circularAddBtnChat { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #8B5CF6, stop:1 #6366F1);
                    color: white; 
                    border-radius: 18px; 
                    border: none; 
                    font-size: 20px; 
                    font-weight: bold; 
                }
                QPushButton#circularAddBtnChat:hover { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #7C3AED, stop:1 #4F46E5);
                }
                
                QPushButton#circularAddBtnTask { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #3B82F6, stop:1 #2563EB);
                    color: white; 
                    border-radius: 18px; 
                    border: none; 
                    font-size: 20px; 
                    font-weight: bold; 
                }
                QPushButton#circularAddBtnTask:hover { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2563EB, stop:1 #1D4ED8);
                }
                
                QPushButton#chatRow { 
                    background: rgba(30, 41, 59, 0.4);
                    border-radius: 16px; 
                    border: 1px solid rgba(71, 85, 105, 0.3); 
                    text-align: left; 
                    padding: 12px; 
                    color: #E2E8F0;
                    font-weight: 600;
                    font-size: 15px;
                }
                QPushButton#chatRow:hover { 
                    background: rgba(139, 92, 246, 0.15);
                    border: 1px solid rgba(139, 92, 246, 0.4);
                }
                
                QPushButton#chatDeleteBtn {
                    background: rgba(220, 38, 38, 0.1);
                    border-radius: 8px;
                    border: 1px solid rgba(220, 38, 38, 0.3);
                    color: #FCA5A5;
                    font-weight: bold;
                    font-size: 18px;
                }
                QPushButton#chatDeleteBtn:hover {
                    background: rgba(220, 38, 38, 0.3);
                    border: 1px solid rgba(220, 38, 38, 0.6);
                    color: #FEE2E2;
                }
                QPushButton#chatDeleteBtn:pressed {
                    background: rgba(220, 38, 38, 0.5);
                }
                
                QWidget#taskRow {
                    background: rgba(30, 41, 59, 0.4);
                    border-radius: 16px; 
                    border: 1px solid rgba(71, 85, 105, 0.3); 
                    padding: 12px; 
                }
                QWidget#taskRow:hover { 
                    background: rgba(59, 130, 246, 0.15);
                    border: 1px solid rgba(59, 130, 246, 0.4);
                }

                QLabel#itemTitle { 
                    font-weight: 600; 
                    font-size: 15px; 
                    color: #F1F5F9; 
                    background: transparent; 
                }
                
                QLabel#itemTime { 
                    color: #E2E8F0; 
                    font-size: 12px; 
                    font-weight: 500;
                    background: transparent; 
                }
                
                QLabel#emptyMsg {
                    color: #475569;
                    font-size: 14px;
                    font-weight: 500;
                    background: transparent;
                }
                
                QCheckBox::indicator { 
                    width: 22px; 
                    height: 22px; 
                    border-radius: 7px; 
                    border: 2.5px solid #475569; 
                    background: rgba(15, 23, 42, 0.6); 
                }
                QCheckBox::indicator:hover { 
                    border-color: #60A5FA; 
                }
                QCheckBox::indicator:checked { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #8B5CF6, stop:1 #6366F1);
                    border-color: #8B5CF6; 
                }
                
                QWidget#transparentBg { 
                    background: transparent; 
                }
            """)
        else:
            # Modern Light Mode - Clean & Vibrant
            self.setStyleSheet(scroll_style + """
                QWidget { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #F8FAFC, stop:1 #EFF6FF);
                    font-family: 'Inter', 'Segoe UI Variable', 'SF Pro Display', sans-serif; 
                    color: #475569; 
                }
                
                QLabel#welcomeLabel { 
                    font-size: 22px; 
                    font-weight: 600; 
                    color: #64748B; 
                    letter-spacing: 0.5px; 
                    background: transparent; 
                }
                
                QLabel#nameLabel { 
                    font-size: 48px; 
                    font-weight: 800; 
                    color: #7C3AED;
                    letter-spacing: -2px; 
                    background: transparent;
                    margin: 4px 0px;
                }
                
                QLabel#subLabel { 
                    color: #64748B; 
                    font-size: 15px; 
                    font-weight: 500;
                    background: transparent; 
                    margin-top: 2px;
                }
                
                QPushButton#profileButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #8B5CF6, stop:1 #6366F1);
                    border: 3px solid #FFFFFF;
                    border-radius: 32px;
                }
                QPushButton#profileButton:hover {
                    border: 3px solid #8B5CF6;
                }
                
                QFrame#chatCard { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFFFFF, stop:1 rgba(245, 243, 255, 0.8));
                    border-radius: 28px; 
                    border: 2px solid rgba(139, 92, 246, 0.15);
                }
                
                QFrame#taskCard { 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFFFFF, stop:1 rgba(239, 246, 255, 0.8));
                    border-radius: 28px; 
                    border: 2px solid rgba(59, 130, 246, 0.15);
                }
                
                QLabel#sectionTitleChat { 
                    color: #7C3AED; 
                    font-weight: 700; 
                    font-size: 11px; 
                    letter-spacing: 2.5px; 
                    background: transparent; 
                }
                
                QLabel#sectionTitleTask { 
                    color: #2563EB; 
                    font-weight: 700; 
                    font-size: 11px; 
                    letter-spacing: 2.5px; 
                    background: transparent; 
                }
                
                QPushButton#circularAddBtnChat { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #8B5CF6, stop:1 #6366F1);
                    color: white; 
                    border-radius: 18px; 
                    border: none; 
                    font-size: 20px; 
                    font-weight: bold; 
                }
                QPushButton#circularAddBtnChat:hover { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #7C3AED, stop:1 #4F46E5);
                }
                
                QPushButton#circularAddBtnTask { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #3B82F6, stop:1 #2563EB);
                    color: white; 
                    border-radius: 18px; 
                    border: none; 
                    font-size: 20px; 
                    font-weight: bold; 
                }
                QPushButton#circularAddBtnTask:hover { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2563EB, stop:1 #1D4ED8);
                }
                
                QPushButton#chatRow { 
                    background: rgba(255, 255, 255, 0.8);
                    border-radius: 16px; 
                    border: 1.5px solid rgba(226, 232, 240, 0.8); 
                    text-align: left; 
                    padding: 12px; 
                    color: #1E293B;
                    font-weight: 600;
                    font-size: 15px;
                }
                QPushButton#chatRow:hover { 
                    background: rgba(245, 243, 255, 0.9);
                    border: 1.5px solid rgba(139, 92, 246, 0.3);
                }
                
                QPushButton#chatDeleteBtn {
                    background: rgba(254, 226, 226, 0.5);
                    border-radius: 8px;
                    border: 1px solid rgba(220, 38, 38, 0.3);
                    color: #991B1B;
                    font-weight: bold;
                    font-size: 18px;
                }
                QPushButton#chatDeleteBtn:hover {
                    background: rgba(254, 226, 226, 0.8);
                    border: 1px solid rgba(220, 38, 38, 0.6);
                    color: #7F1D1D;
                }
                QPushButton#chatDeleteBtn:pressed {
                    background: rgba(220, 38, 38, 0.4);
                }
                
                QWidget#taskRow {
                    background: rgba(255, 255, 255, 0.8);
                    border-radius: 16px; 
                    border: 1.5px solid rgba(226, 232, 240, 0.8); 
                    padding: 12px; 
                }
                QWidget#taskRow:hover { 
                    background: rgba(239, 246, 255, 0.9);
                    border: 1.5px solid rgba(59, 130, 246, 0.3);
                }

                QLabel#itemTitle { 
                    font-weight: 600; 
                    font-size: 15px; 
                    color: #0F172A; 
                    background: transparent; 
                }
                
                QLabel#itemTime { 
                    color: #1E293B; 
                    font-size: 12px; 
                    font-weight: 600;
                    background: transparent; 
                }
                
                QLabel#emptyMsg {
                    color: #94A3B8;
                    font-size: 14px;
                    font-weight: 500;
                    background: transparent;
                }
                
                QCheckBox::indicator { 
                    width: 22px; 
                    height: 22px; 
                    border-radius: 7px; 
                    border: 2.5px solid #CBD5E1; 
                    background: white; 
                }
                QCheckBox::indicator:hover { 
                    border-color: #8B5CF6; 
                }
                QCheckBox::indicator:checked { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #8B5CF6, stop:1 #6366F1);
                    border-color: #8B5CF6; 
                }
                
                QWidget#transparentBg { 
                    background: transparent; 
                }
            """)