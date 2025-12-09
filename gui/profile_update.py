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
        # Scroll area for the whole page
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ==================== SECTION 1: USER PROFILE ====================
        profile_section = QFrame()
        profile_section.setObjectName("section")
        profile_layout = QHBoxLayout(profile_section)
        profile_layout.setSpacing(20)

        # LEFT: Name & Email
        info_layout = QVBoxLayout()
        info_layout.setSpacing(15)

        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_label.setFixedWidth(80)
        self.name_input = QLineEdit(self.user_data.get("name", ""))
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        info_layout.addLayout(name_layout)

        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setFixedWidth(80)
        self.email_input = QLineEdit(self.user_data.get("email", ""))
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        info_layout.addLayout(email_layout)

        profile_layout.addLayout(info_layout, stretch=1)

        # RIGHT: Profile Picture
        pic_layout = QVBoxLayout()
        pic_layout.setAlignment(Qt.AlignCenter)

        self.profile_pic = QLabel()
        self.profile_pic.setFixedSize(120, 120)
        self.profile_pic.setStyleSheet("border-radius: 60px; background-color: #999;")
        self.set_profile_picture(self.user_data.get("image", ""))

        btn_change_img = QPushButton("Change Picture")
        btn_change_img.setObjectName("changeBtn")
        btn_change_img.setCursor(Qt.PointingHandCursor)
        btn_change_img.clicked.connect(self.change_picture)

        pic_layout.addWidget(self.profile_pic)
        pic_layout.addWidget(btn_change_img)

        profile_layout.addLayout(pic_layout)
        main_layout.addWidget(profile_section)

        # Divider
        divider1 = QFrame()
        divider1.setFrameShape(QFrame.HLine)
        divider1.setObjectName("divider")
        main_layout.addWidget(divider1)

        # ==================== SECTION 2: SETTINGS ====================
        settings_section = QFrame()
        settings_section.setObjectName("section")
        settings_layout = QVBoxLayout(settings_section)
        settings_layout.setSpacing(15)

        settings_title = QLabel("⚙️ Settings")
        settings_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        settings_layout.addWidget(settings_title)

        # Dark Mode Toggle
        dark_mode_layout = QHBoxLayout()
        dark_mode_label = QLabel("Dark Mode:")
        dark_mode_label.setFixedWidth(150)

        self.dark_mode_toggle = QCheckBox()
        self.dark_mode_toggle.setChecked(self.dark_mode)
        self.dark_mode_toggle.setCursor(Qt.PointingHandCursor)
        self.dark_mode_toggle.stateChanged.connect(self.toggle_dark_mode)
        self.dark_mode_toggle.setStyleSheet("""
            QCheckBox::indicator {
                width: 40px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #ccc;
                border-radius: 10px;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-radius: 10px;
            }
        """)

        dark_mode_layout.addWidget(dark_mode_label)
        dark_mode_layout.addWidget(self.dark_mode_toggle)
        dark_mode_layout.addStretch()

        settings_layout.addLayout(dark_mode_layout)
        main_layout.addWidget(settings_section)

        # Divider
        divider2 = QFrame()
        divider2.setFrameShape(QFrame.HLine)
        divider2.setObjectName("divider")
        main_layout.addWidget(divider2)

        # ==================== SECTION 3: NOTES ====================
        notes_section = QFrame()
        notes_section.setObjectName("section")
        notes_layout = QVBoxLayout(notes_section)
        notes_layout.setSpacing(10)

        notes_title = QLabel("📝 Personal Notes")
        notes_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        notes_layout.addWidget(notes_title)

        self.notes_text = QTextEdit()
        self.notes_text.setPlaceholderText("Write your notes here...")
        self.notes_text.setMinimumHeight(150)
        self.notes_text.setText(self.notes_data.get("notes", ""))
        notes_layout.addWidget(self.notes_text)

        main_layout.addWidget(notes_section)

        # ==================== SAVE BUTTON ====================
        btn_save = QPushButton("💾 Save All Changes")
        btn_save.setObjectName("saveBtn")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setFixedHeight(45)
        btn_save.clicked.connect(self.save_data)
        main_layout.addWidget(btn_save, alignment=Qt.AlignCenter)

        main_layout.addStretch()
        
        scroll.setWidget(container)
        
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

    # ==================== THEME FUNCTIONS ====================
    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    color: #e0e0e0;
                    font-family: Arial;
                }
                QScrollArea {
                    background-color: #1e1e1e;
                    border: none;
                }
                QFrame#section {
                    background-color: #2d2d2d;
                    border-radius: 10px;
                    padding: 15px;
                }
                QFrame#divider {
                    background-color: #444;
                    min-height: 2px;
                    max-height: 2px;
                }
                QLabel {
                    font-size: 14px;
                    color: #e0e0e0;
                    font-weight: bold;
                    background-color: transparent;
                }
                QLineEdit {
                    padding: 10px;
                    border-radius: 5px;
                    border: 1px solid #555;
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                }
                QTextEdit {
                    padding: 10px;
                    border-radius: 5px;
                    border: 1px solid #555;
                    background-color: #3a3a3a;
                    color: #e0e0e0;
                }
                QPushButton#saveBtn {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 200px;
                }
                QPushButton#saveBtn:hover {
                    background-color: #45a049;
                }
                QPushButton#changeBtn {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton#changeBtn:hover {
                    background-color: #45a049;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #f0f0f0;
                    color: #000;
                    font-family: Arial;
                }
                QScrollArea {
                    background-color: #f0f0f0;
                    border: none;
                }
                QFrame#section {
                    background-color: #ffffff;
                    border-radius: 10px;
                    padding: 15px;
                    border: 1px solid #ddd;
                }
                QFrame#divider {
                    background-color: #ccc;
                    min-height: 2px;
                    max-height: 2px;
                }
                QLabel {
                    font-size: 14px;
                    color: black;
                    font-weight: bold;
                    background-color: transparent;
                }
                QLineEdit {
                    padding: 10px;
                    border-radius: 5px;
                    border: 1px solid #888;
                    background-color: white;
                    color: black;
                }
                QTextEdit {
                    padding: 10px;
                    border-radius: 5px;
                    border: 1px solid #888;
                    background-color: white;
                    color: black;
                }
                QPushButton#saveBtn {
                    background-color: #000;
                    color: white;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 200px;
                }
                QPushButton#saveBtn:hover {
                    background-color: #333;
                }
                QPushButton#changeBtn {
                    background-color: #000;
                    color: white;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 12px;
                }
                QPushButton#changeBtn:hover {
                    background-color: #333;
                }
            """)

    def toggle_dark_mode(self, state):
        self.dark_mode = bool(state)
        self.apply_theme()

    # ==================== ASSETS FOLDER HELPER ====================
    def get_assets_path(self):
        """Get the assets folder path relative to this file"""
        # Get the directory where this file (profile_update.py) is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to FYP folder, then into assets
        assets_dir = os.path.join(current_dir, "..", "assets")
        # Create assets folder if it doesn't exist
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
                # If no image is set, use default
                if "image" not in data or not data["image"]:
                    data["image"] = "Profile-Icon.png"  # Default image
                return data
        return {"image": "Profile-Icon.png"}  # Default for new users

    def load_notes(self):
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, "r") as f:
                return json.load(f)
        return {}

    def set_profile_picture(self, filename):
        """Load profile picture from assets folder"""
        if filename:
            # Get full path from assets folder
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
        
        # If image not found or no filename, show placeholder
        self.profile_pic.setPixmap(QPixmap())
        self.profile_pic.setStyleSheet("background: #999; border-radius: 60px;")

    def change_picture(self):
        """Let user select an image and copy it to assets folder"""
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file:
            try:
                # Get assets directory
                assets_dir = self.get_assets_path()
                
                # Generate unique filename or use fixed name
                # Option 1: Keep original filename
                # filename = os.path.basename(file)
                
                # Option 2: Always use "user_profile" (recommended)
                file_ext = os.path.splitext(file)[1]  # Get extension (.png, .jpg, etc)
                filename = f"user_profile{file_ext}"
                
                # Full destination path
                dest_path = os.path.join(assets_dir, filename)
                
                # Copy image to assets folder
                shutil.copy(file, dest_path)
                print(f"✅ Image copied to: {dest_path}")
                
                # Update user data with just the filename
                self.user_data["image"] = filename
                
                # Display the new image
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