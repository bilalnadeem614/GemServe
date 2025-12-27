# profile_update.py
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QFrame, QTextEdit, QCheckBox, QScrollArea
)
from PySide6.QtGui import QPixmap, Qt, QPainter, QPainterPath
from PySide6.QtCore import QSize
import json
import os
import shutil

DATA_FILE = "user_data.json"
NOTES_FILE = "user_notes.json"


class SettingsPage(QWidget):
    def __init__(self, on_saved):
        super().__init__()
        self.on_saved = on_saved
        self.user_data = self.load_user_data()
        self.notes_data = self.load_notes()
        self.dark_mode = self.user_data.get("dark_mode", False)
        
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        # Main layout with no margins
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        # Header Section
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(80)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)
        
        header_title = QLabel("Settings")
        header_title.setObjectName("headerTitle")
        
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        
        root_layout.addWidget(header)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setObjectName("scrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        container = QWidget()
        container.setObjectName("scrollContent")
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # ==================== SECTION 1: USER PROFILE ====================
        profile_section = QFrame()
        profile_section.setObjectName("section")
        profile_layout = QVBoxLayout(profile_section)
        profile_layout.setSpacing(25)
        profile_layout.setContentsMargins(30, 30, 30, 30)

        # Profile Picture (centered at top)
        pic_layout = QVBoxLayout()
        pic_layout.setAlignment(Qt.AlignCenter)
        pic_layout.setSpacing(15)

        self.profile_pic = QLabel()
        self.profile_pic.setObjectName("profilePic")
        self.profile_pic.setFixedSize(120, 120)
        self.set_profile_picture(self.user_data.get("image", ""))

        btn_change_img = QPushButton("Change Picture")
        btn_change_img.setObjectName("changeBtn")
        btn_change_img.setFixedHeight(40)
        btn_change_img.setFixedWidth(150)
        btn_change_img.setCursor(Qt.PointingHandCursor)
        btn_change_img.clicked.connect(self.change_picture)

        pic_layout.addWidget(self.profile_pic)
        pic_layout.addWidget(btn_change_img)
        profile_layout.addLayout(pic_layout)

        # Name Input
        name_layout = QVBoxLayout()
        name_layout.setSpacing(10)
        name_label = QLabel("NAME")
        name_label.setObjectName("fieldLabel")
        self.name_input = QLineEdit(self.user_data.get("name", ""))
        self.name_input.setObjectName("inputField")
        self.name_input.setPlaceholderText("Enter your name...")
        self.name_input.setFixedHeight(50)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        profile_layout.addLayout(name_layout)

        # Email Input
        email_layout = QVBoxLayout()
        email_layout.setSpacing(10)
        email_label = QLabel("EMAIL")
        email_label.setObjectName("fieldLabel")
        self.email_input = QLineEdit(self.user_data.get("email", ""))
        self.email_input.setObjectName("inputField")
        self.email_input.setPlaceholderText("Enter your email...")
        self.email_input.setFixedHeight(50)
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        profile_layout.addLayout(email_layout)

        main_layout.addWidget(profile_section)

        # ==================== SECTION 2: SETTINGS ====================
        settings_section = QFrame()
        settings_section.setObjectName("section")
        settings_layout = QVBoxLayout(settings_section)
        settings_layout.setSpacing(20)
        settings_layout.setContentsMargins(30, 30, 30, 30)

        settings_title = QLabel("PREFERENCES")
        settings_title.setObjectName("sectionTitle")
        settings_layout.addWidget(settings_title)

        # Dark Mode Toggle
        dark_mode_frame = QFrame()
        dark_mode_frame.setObjectName("toggleFrame")
        dark_mode_frame.setFixedHeight(60)
        
        dark_mode_layout = QHBoxLayout(dark_mode_frame)
        dark_mode_layout.setContentsMargins(20, 0, 20, 0)
        
        dark_mode_label = QLabel("Dark Mode")
        dark_mode_label.setObjectName("toggleLabel")

        self.dark_mode_toggle = QCheckBox()
        self.dark_mode_toggle.setObjectName("toggleSwitch")
        self.dark_mode_toggle.setChecked(self.dark_mode)
        self.dark_mode_toggle.setCursor(Qt.PointingHandCursor)
        self.dark_mode_toggle.stateChanged.connect(self.toggle_dark_mode)

        dark_mode_layout.addWidget(dark_mode_label)
        dark_mode_layout.addStretch()
        dark_mode_layout.addWidget(self.dark_mode_toggle)

        settings_layout.addWidget(dark_mode_frame)
        main_layout.addWidget(settings_section)

        # ==================== SECTION 3: NOTES ====================
        notes_section = QFrame()
        notes_section.setObjectName("section")
        notes_layout = QVBoxLayout(notes_section)
        notes_layout.setSpacing(15)
        notes_layout.setContentsMargins(30, 30, 30, 30)

        notes_title = QLabel("PERSONAL NOTES")
        notes_title.setObjectName("sectionTitle")
        notes_layout.addWidget(notes_title)

        self.notes_text = QTextEdit()
        self.notes_text.setObjectName("notesField")
        self.notes_text.setPlaceholderText("Write your personal notes here...")
        self.notes_text.setMinimumHeight(180)
        self.notes_text.setText(self.notes_data.get("notes", ""))
        notes_layout.addWidget(self.notes_text)

        main_layout.addWidget(notes_section)

        # ==================== SAVE BUTTON ====================
        btn_save = QPushButton("Save All Changes")
        btn_save.setObjectName("saveBtn")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(55)
        btn_save.setFixedWidth(250)
        btn_save.clicked.connect(self.save_data)
        main_layout.addWidget(btn_save, alignment=Qt.AlignCenter)

        main_layout.addStretch()
        
        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    # ==================== THEME FUNCTIONS ====================
    def apply_theme(self):
        scroll_style = """
            QScrollArea#scrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(139, 92, 246, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(139, 92, 246, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """
        
        if self.dark_mode:
            self.setStyleSheet(scroll_style + """
                /* Main Background */
                QWidget {
                    background-color: #0A0E27;
                    font-family: 'Inter', 'Segoe UI Variable', sans-serif;
                }
                
                QWidget#scrollContent {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0F172A, stop:1 #0A0E27);
                }
                
                /* Header */
                QFrame#header {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #6366F1);
                    border: none;
                }
                
                QLabel#headerTitle {
                    color: #FFFFFF;
                    font-size: 28px;
                    font-weight: 800;
                    letter-spacing: -1px;
                    background: transparent;
                }
                
                /* Sections */
                QFrame#section {
                    background: rgba(30, 41, 59, 0.4);
                    border: 2px solid rgba(139, 92, 246, 0.2);
                    border-radius: 20px;
                }
                
                /* Profile Picture */
                QLabel#profilePic {
                    border: 3px solid rgba(139, 92, 246, 0.5);
                    border-radius: 60px;
                    background: #1E293B;
                }
                
                /* Section Titles */
                QLabel#sectionTitle {
                    color: #A78BFA;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 2px;
                    background: transparent;
                }
                
                /* Field Labels */
                QLabel#fieldLabel {
                    color: #A78BFA;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 2px;
                    background: transparent;
                }
                
                /* Input Fields */
                QLineEdit#inputField {
                    background: rgba(30, 41, 59, 0.6);
                    color: #E2E8F0;
                    border: 2.5px solid rgba(139, 92, 246, 0.25);
                    border-radius: 14px;
                    padding: 14px 18px;
                    font-size: 16px;
                    font-weight: 500;
                }
                QLineEdit#inputField:focus {
                    border: 2.5px solid #8B5CF6;
                    background: rgba(30, 41, 59, 0.8);
                }
                QLineEdit#inputField::placeholder {
                    color: #64748B;
                    font-style: italic;
                }
                
                /* Notes Field */
                QTextEdit#notesField {
                    background: rgba(30, 41, 59, 0.6);
                    color: #E2E8F0;
                    border: 2.5px solid rgba(139, 92, 246, 0.25);
                    border-radius: 14px;
                    padding: 14px 18px;
                    font-size: 15px;
                    font-weight: 500;
                }
                QTextEdit#notesField:focus {
                    border: 2.5px solid #8B5CF6;
                }
                
                /* Toggle Frame */
                QFrame#toggleFrame {
                    background: rgba(30, 41, 59, 0.5);
                    border: 2px solid rgba(71, 85, 105, 0.3);
                    border-radius: 14px;
                }
                
                QLabel#toggleLabel {
                    color: #E2E8F0;
                    font-size: 16px;
                    font-weight: 600;
                    background: transparent;
                }
                
                /* Toggle Switch */
                QCheckBox#toggleSwitch::indicator {
                    width: 50px;
                    height: 26px;
                    border-radius: 13px;
                }
                QCheckBox#toggleSwitch::indicator:unchecked {
                    background: rgba(71, 85, 105, 0.5);
                    border: 2px solid #475569;
                }
                QCheckBox#toggleSwitch::indicator:checked {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #34D399, stop:1 #10B981);
                    border: 2px solid #34D399;
                }
                
                /* Change Picture Button */
                QPushButton#changeBtn {
                    background: rgba(139, 92, 246, 0.2);
                    color: #C4B5FD;
                    border: 2px solid rgba(139, 92, 246, 0.3);
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton#changeBtn:hover {
                    background: rgba(139, 92, 246, 0.3);
                    border: 2px solid #8B5CF6;
                    color: #E9D5FF;
                }
                
                /* Save Button */
                QPushButton#saveBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A78BFA);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 27px;
                    font-size: 17px;
                    font-weight: 800;
                }
                QPushButton#saveBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #8B5CF6);
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
                
                QWidget#scrollContent {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #F8FAFC, stop:1 #EFF6FF);
                }
                
                /* Header */
                QFrame#header {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #6366F1);
                    border: none;
                }
                
                QLabel#headerTitle {
                    color: #FFFFFF;
                    font-size: 28px;
                    font-weight: 800;
                    letter-spacing: -1px;
                    background: transparent;
                }
                
                /* Sections */
                QFrame#section {
                    background: #FFFFFF;
                    border: 2px solid rgba(139, 92, 246, 0.15);
                    border-radius: 20px;
                }
                
                /* Profile Picture */
                QLabel#profilePic {
                    border: 3px solid rgba(139, 92, 246, 0.3);
                    border-radius: 60px;
                    background: #F8FAFC;
                }
                
                /* Section Titles */
                QLabel#sectionTitle {
                    color: #7C3AED;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 2px;
                    background: transparent;
                }
                
                /* Field Labels */
                QLabel#fieldLabel {
                    color: #7C3AED;
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: 2px;
                    background: transparent;
                }
                
                /* Input Fields */
                QLineEdit#inputField {
                    background: #F8FAFC;
                    color: #0F172A;
                    border: 2.5px solid rgba(226, 232, 240, 0.8);
                    border-radius: 14px;
                    padding: 14px 18px;
                    font-size: 16px;
                    font-weight: 500;
                }
                QLineEdit#inputField:focus {
                    border: 2.5px solid #8B5CF6;
                    background: #FFFFFF;
                }
                QLineEdit#inputField::placeholder {
                    color: #94A3B8;
                    font-style: italic;
                }
                
                /* Notes Field */
                QTextEdit#notesField {
                    background: #F8FAFC;
                    color: #0F172A;
                    border: 2.5px solid rgba(226, 232, 240, 0.8);
                    border-radius: 14px;
                    padding: 14px 18px;
                    font-size: 15px;
                    font-weight: 500;
                }
                QTextEdit#notesField:focus {
                    border: 2.5px solid #8B5CF6;
                }
                
                /* Toggle Frame */
                QFrame#toggleFrame {
                    background: rgba(248, 250, 252, 0.8);
                    border: 2px solid rgba(226, 232, 240, 0.8);
                    border-radius: 14px;
                }
                
                QLabel#toggleLabel {
                    color: #1E293B;
                    font-size: 16px;
                    font-weight: 600;
                    background: transparent;
                }
                
                /* Toggle Switch */
                QCheckBox#toggleSwitch::indicator {
                    width: 50px;
                    height: 26px;
                    border-radius: 13px;
                }
                QCheckBox#toggleSwitch::indicator:unchecked {
                    background: #E2E8F0;
                    border: 2px solid #CBD5E1;
                }
                QCheckBox#toggleSwitch::indicator:checked {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #34D399, stop:1 #10B981);
                    border: 2px solid #34D399;
                }
                
                /* Change Picture Button */
                QPushButton#changeBtn {
                    background: rgba(139, 92, 246, 0.1);
                    color: #7C3AED;
                    border: 2px solid rgba(139, 92, 246, 0.2);
                    border-radius: 12px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton#changeBtn:hover {
                    background: rgba(139, 92, 246, 0.15);
                    border: 2px solid #8B5CF6;
                    color: #6D28D9;
                }
                
                /* Save Button */
                QPushButton#saveBtn {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A78BFA);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 27px;
                    font-size: 17px;
                    font-weight: 800;
                }
                QPushButton#saveBtn:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #8B5CF6);
                }
            """)

    def toggle_dark_mode(self, state):
        self.dark_mode = bool(state)
        self.apply_theme()

    # ==================== ASSETS FOLDER HELPER ====================
    def get_assets_path(self):
        """Get the assets folder path relative to this file"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(current_dir, "..", "assets")
        os.makedirs(assets_dir, exist_ok=True)
        return assets_dir

    def get_image_path(self, filename):
        """Get full path to image in assets folder"""
        if not filename:
            return ""
        assets_dir = self.get_assets_path()
        return os.path.join(assets_dir, filename)

    # ==================== DATA FUNCTIONS ====================
    def load_user_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if "image" not in data or not data["image"]:
                    data["image"] = "Profile-Icon.png"
                return data
        return {"image": "Profile-Icon.png"}

    def load_notes(self):
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, "r") as f:
                return json.load(f)
        return {}

    def set_profile_picture(self, filename):
        """Load profile picture from assets folder"""
        if filename:
            image_path = self.get_image_path(filename)
            
            if os.path.exists(image_path):
                pix = QPixmap(image_path).scaled(
                    120, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                circular = QPixmap(120, 120)
                circular.fill(Qt.transparent)

                painter = QPainter(circular)
                painter.setRenderHint(QPainter.Antialiasing)
                path_obj = QPainterPath()
                path_obj.addEllipse(0, 0, 120, 120)
                painter.setClipPath(path_obj)
                painter.drawPixmap(0, 0, pix)
                painter.end()

                self.profile_pic.setPixmap(circular)
                return
        
        self.profile_pic.setPixmap(QPixmap())

    def change_picture(self):
        """Let user select an image and copy it to assets folder"""
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file:
            try:
                assets_dir = self.get_assets_path()
                file_ext = os.path.splitext(file)[1]
                filename = f"user_profile{file_ext}"
                dest_path = os.path.join(assets_dir, filename)
                shutil.copy(file, dest_path)
                print(f"✅ Image copied to: {dest_path}")
                self.user_data["image"] = filename
                self.set_profile_picture(filename)
            except Exception as e:
                print(f"❌ Error copying image: {e}")

    def save_data(self):
        # Save user data
        self.user_data["name"] = self.name_input.text()
        self.user_data["email"] = self.email_input.text()
        self.user_data["dark_mode"] = self.dark_mode

        with open(DATA_FILE, "w") as f:
            json.dump(self.user_data, f, indent=4)

        # Save notes
        notes_content = self.notes_text.toPlainText()
        notes_data = {"notes": notes_content}

        with open(NOTES_FILE, "w") as f:
            json.dump(notes_data, f, indent=4)

        print("✅ All data saved successfully!")
        self.on_saved(self.user_data)