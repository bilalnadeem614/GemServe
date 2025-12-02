import sys, os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QScrollArea, QFrame, QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon


# --------- Load Icon Safely ----------
def load_icon(name):
    base_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_path, "assets/icons", name)

    if os.path.exists(icon_path):
        return QIcon(icon_path)
    else:
        print(f"[ERROR] Icon not found: {icon_path}")
        return QIcon()


# ---------------------- MESSAGE BUBBLE -------------------------
class MessageBubble(QFrame):
    def __init__(self, text, is_user):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)

        badge = QLabel("U" if is_user else "AI")
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet("""
            background: #2d2d2d;
            color: white;
            border-radius: 14px;
            font-weight: bold;
        """)

        if is_user:
            bubble.setStyleSheet("""
                background: white;
                border: 1px solid #c7c7c7;
                padding: 10px;
                border-radius: 8px;
                max-width: 65%;
            """)
            layout = QHBoxLayout()
            layout.addStretch()
            layout.addWidget(bubble)
            layout.addWidget(badge)

        else:
            bubble.setStyleSheet("""
                background: #ececec;
                border: 1px solid #c5c5c5;
                padding: 10px;
                border-radius: 8px;
                max-width: 65%;
            """)
            layout = QHBoxLayout()
            layout.addWidget(badge)
            layout.addWidget(bubble)
            layout.addStretch()

        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        self.setLayout(layout)


# ----------------------- MAIN CHAT WINDOW ------------------------
class ChatWindow(QWidget):
    def __init__(self, go_home_callback):
        super().__init__()
        self.go_home = go_home_callback     # <-- Back button handler
        self.setMinimumSize(450, 620)
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------- HEADER ----------------
        header = QFrame()
        header.setFixedHeight(55)
        header.setStyleSheet("background: #2d2d2d;")

        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(10, 5, 10, 5)

        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("""
            QPushButton {
                background: #464646;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover { background: #5a5a5a; }
        """)
        back_btn.clicked.connect(self.go_home)  # <-- Important

        title = QLabel("Chatbot")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)

        h_layout.addWidget(back_btn)
        h_layout.addStretch()
        h_layout.addWidget(title)
        h_layout.addStretch()
        root.addWidget(header)

        # ---------------- CHAT AREA ----------------
        chat_area = QScrollArea()
        chat_area.setWidgetResizable(True)
        chat_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        self.chat_layout = QVBoxLayout(container)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(4)
        self.chat_layout.addStretch()

        chat_area.setWidget(container)
        chat_area.setStyleSheet("background: #d3d3d3;")

        root.addWidget(chat_area)
        self.scroll = chat_area

        # ---------------- INPUT AREA ----------------
        input_frame = QFrame()
        input_frame.setFixedHeight(70)
        input_frame.setStyleSheet("background: #d3d3d3;")

        i_layout = QHBoxLayout(input_frame)
        i_layout.setContentsMargins(10, 10, 10, 10)

        wrapper = QFrame()
        wrapper.setStyleSheet("""
            QFrame {
                background: #ececec;
                border-radius: 22px;
                border: 1px solid #c5c5c5;
            }
        """)
        wrapper.setMinimumHeight(45)
        wrapper.setMaximumHeight(45)

        w_layout = QHBoxLayout(wrapper)
        w_layout.setContentsMargins(45, 0, 45, 0)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message...")
        self.input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: #ececec;
                font-size: 15px;
            }
        """)
        self.input.returnPressed.connect(self.on_send)
        w_layout.addWidget(self.input)

        self.mic_btn = QPushButton("🎤", wrapper)
        self.mic_btn.setGeometry(8, 7, 30, 30)
        self.mic_btn.setStyleSheet("background: none; border: none;")
        self.mic_btn.clicked.connect(self.on_mic_click)

        self.file_btn = QPushButton("📎", wrapper)
        self.file_btn.setStyleSheet("background: none; border: none;")
        self.file_btn.clicked.connect(self.on_file_upload)

        wrapper.resizeEvent = lambda e: self.file_btn.setGeometry(
            wrapper.width() - 38, 7, 30, 30
        )

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("""
            QPushButton {
                background: #2d2d2d;
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
            }
            QPushButton:hover { background: #3a3a3a; }
        """)
        send_btn.clicked.connect(self.on_send)

        i_layout.addWidget(wrapper)
        i_layout.addWidget(send_btn)
        root.addWidget(input_frame)

    # ---------------- FUNCTIONS ----------------
    def add_message(self, text, is_user):
        bubble = MessageBubble(text, is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(50, self.scroll_bottom)

    def scroll_bottom(self):
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )

    def on_send(self):
        text = self.input.text().strip()
        if not text:
            return

        self.add_message(text, True)
        self.input.clear()

        QTimer.singleShot(200, lambda: self.add_message("AI: " + text, False))

    def on_mic_click(self):
        self.add_message("[Listening from mic…]", True)

    def on_file_upload(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file:
            self.add_message(f"📎 File Selected:\n{file}", True)


# ---------------- MAIN (Not used in main app) ----------------
def main():
    app = QApplication(sys.argv)
    w = ChatWindow(lambda: w.close())  # For standalone testing
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
