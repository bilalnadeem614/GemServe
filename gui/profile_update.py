# settings_page.py
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
)
from PySide6.QtGui import QPixmap, Qt, QPainter
import json
import os

DATA_FILE = "user_data.json"


class SettingsPage(QWidget):
    def __init__(self, on_saved):
        super().__init__()
        self.on_saved = on_saved

        self.user_data = self.load_user_data()
        # -------------------- STYLE --------------------
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial;
            }

            QLabel {
                font-size: 16px;
                color: black;
                font-weight: bold;
            }

            QLineEdit {
                padding: 12px 6px;
                border-radius: 5px;
                border: 1px solid #888;
                background-color: white;
                color: black;
            }

            QPushButton {
                background-color: black;
                color: white;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #444;
                color: white;
            }

            QLabel#profile_pic_label {
                border-radius: 70px;
                background-color: gray;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # -------- PROFILE PICTURE ----------
        self.profile_pic = QLabel()
        self.profile_pic.setObjectName("profile_pic_label")
        self.profile_pic.setFixedSize(140, 140)
        
        self.set_profile_picture(self.user_data.get("image", ""))

        btn_change_img = QPushButton("Change Profile Picture")
        btn_change_img.setCursor(Qt.PointingHandCursor)
        btn_change_img.setStyleSheet("background-color: black; color: white;")
        btn_change_img.clicked.connect(self.change_picture)

        layout.addWidget(self.profile_pic, alignment=Qt.AlignCenter)
        layout.addWidget(btn_change_img, alignment=Qt.AlignCenter)
        
        # -------- USER FIELDS ----------
        # Name
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        self.name_input = QLineEdit(self.user_data.get("name", ""))
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        self.email_input = QLineEdit(self.user_data.get("email", ""))
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)

        # -------- SAVE BUTTON ----------
        btn_save = QPushButton("Save")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("background-color: black; color: white;")
        btn_save.clicked.connect(self.save_data)
        layout.addWidget(btn_save, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def load_user_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        return {}

    def set_profile_picture(self, path):
        if path and os.path.exists(path):
            pix = QPixmap(path).scaled(140, 140)
            mask = QPixmap(140, 140)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(Qt.white)
            painter.drawEllipse(0, 0, 140, 140)
            painter.end()
            
            pix.setMask(mask.createMaskFromColor(Qt.transparent))
            self.profile_pic.setPixmap(pix)
        else:
            self.profile_pic.setStyleSheet("sbackground: #999; border-radius: 70px;")

    def change_picture(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file:
            self.user_data["image"] = file
            self.set_profile_picture(file)

    def save_data(self):
       
        self.user_data["name"] = self.name_input.text()
        self.user_data["email"] = self.email_input.text()

        with open(DATA_FILE, "w") as f:
            json.dump(self.user_data, f, indent=4)

        self.on_saved(self.user_data)
