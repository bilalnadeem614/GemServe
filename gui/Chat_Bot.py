# Chat_Bot.py
import sys, os
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QFileDialog,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon


# ---------------------- MESSAGE BUBBLE -------------------------
class MessageBubble(QFrame):
    def __init__(self, text, is_user, dark_mode=False):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)

        badge = QLabel("U" if is_user else "AI")
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignCenter)

        if dark_mode:
            badge.setStyleSheet(
                """
                background: #4CAF50;
                color: white;
                border-radius: 14px;
                font-weight: bold;
            """
            )
        else:
            badge.setStyleSheet(
                """
                background: #2d2d2d;
                color: white;
                border-radius: 14px;
                font-weight: bold;
            """
            )

        if is_user:
            if dark_mode:
                bubble.setStyleSheet(
                    """
                    background: #2d2d2d;
                    border: 1px solid #444;
                    color: #e0e0e0;
                    padding: 10px;
                    border-radius: 8px;
                    max-width: 65%;
                """
                )
            else:
                bubble.setStyleSheet(
                    """
                    background: white;
                    border: 1px solid #c7c7c7;
                    padding: 10px;
                    border-radius: 8px;
                    max-width: 65%;
                """
                )
            layout = QHBoxLayout()
            layout.addStretch()
            layout.addWidget(bubble)
            layout.addWidget(badge)

        else:
            if dark_mode:
                bubble.setStyleSheet(
                    """
                    background: #3a3a3a;
                    border: 1px solid #555;
                    color: #e0e0e0;
                    padding: 10px;
                    border-radius: 8px;
                    max-width: 65%;
                """
                )
            else:
                bubble.setStyleSheet(
                    """
                    background: #ececec;
                    border: 1px solid #c5c5c5;
                    padding: 10px;
                    border-radius: 8px;
                    max-width: 65%;
                """
                )
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
        self.go_home = go_home_callback
        self.dark_mode = False
        self.setMinimumSize(450, 620)
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------- HEADER ----------------
        self.header = QFrame()
        self.header.setFixedHeight(55)

        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(10, 5, 10, 5)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.go_home)

        self.title = QLabel("Chatbot")
        self.title.setAlignment(Qt.AlignCenter)

        h_layout.addWidget(self.back_btn)
        h_layout.addStretch()
        h_layout.addWidget(self.title)
        h_layout.addStretch()
        root.addWidget(self.header)

        # ---------------- CHAT AREA ----------------
        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        self.chat_layout = QVBoxLayout(container)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(4)
        self.chat_layout.addStretch()

        self.chat_area.setWidget(container)
        root.addWidget(self.chat_area)
        self.scroll = self.chat_area

        # ---------------- INPUT AREA ----------------
        self.input_frame = QFrame()
        self.input_frame.setFixedHeight(70)

        i_layout = QHBoxLayout(self.input_frame)
        i_layout.setContentsMargins(10, 10, 10, 10)

        self.wrapper = QFrame()
        self.wrapper.setMinimumHeight(45)
        self.wrapper.setMaximumHeight(45)

        w_layout = QHBoxLayout(self.wrapper)
        w_layout.setContentsMargins(45, 0, 45, 0)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message...")
        self.input.returnPressed.connect(self.on_send)
        w_layout.addWidget(self.input)

        self.mic_btn = QPushButton("🎤", self.wrapper)
        self.mic_btn.setGeometry(8, 7, 30, 30)
        self.mic_btn.clicked.connect(self.on_mic_click)

        self.file_btn = QPushButton("📎", self.wrapper)
        self.file_btn.clicked.connect(self.on_file_upload)

        self.wrapper.resizeEvent = lambda e: self.file_btn.setGeometry(
            self.wrapper.width() - 38, 7, 30, 30
        )

        self.send_btn = QPushButton("Send")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.on_send)

        i_layout.addWidget(self.wrapper)
        i_layout.addWidget(self.send_btn)
        root.addWidget(self.input_frame)

    # -----------------------------------------
    # Dark Mode
    # -----------------------------------------
    def apply_dark_mode(self, enabled):
        self.dark_mode = enabled
        if enabled:
            self.header.setStyleSheet("background: #2d2d2d;")
            self.back_btn.setStyleSheet(
                """
                QPushButton {
                    background: #464646;
                    color: white;
                    padding: 6px 12px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover { background: #5a5a5a; }
            """
            )
            self.title.setStyleSheet("color: white; font-size: 18px; font-weight: 600;")
            self.chat_area.setStyleSheet("background: #1e1e1e;")
            self.input_frame.setStyleSheet("background: #1e1e1e;")
            self.wrapper.setStyleSheet(
                """
                QFrame {
                    background: #3a3a3a;
                    border-radius: 22px;
                    border: 1px solid #555;
                }
            """
            )
            self.input.setStyleSheet(
                """
                QLineEdit {
                    border: none;
                    background: #3a3a3a;
                    color: #e0e0e0;
                    font-size: 15px;
                }
            """
            )
            self.mic_btn.setStyleSheet("background: none; border: none;")
            self.file_btn.setStyleSheet("background: none; border: none;")
            self.send_btn.setStyleSheet(
                """
                QPushButton {
                    background: #4CAF50;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 8px;
                }
                QPushButton:hover { background: #45a049; }
            """
            )
        else:
            self.header.setStyleSheet("background: #2d2d2d;")
            self.back_btn.setStyleSheet(
                """
                QPushButton {
                    background: #464646;
                    color: white;
                    padding: 6px 12px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover { background: #5a5a5a; }
            """
            )
            self.title.setStyleSheet("color: white; font-size: 18px; font-weight: 600;")
            self.chat_area.setStyleSheet("background: #d3d3d3;")
            self.input_frame.setStyleSheet("background: #d3d3d3;")
            self.wrapper.setStyleSheet(
                """
                QFrame {
                    background: #ececec;
                    border-radius: 22px;
                    border: 1px solid #c5c5c5;
                }
            """
            )
            self.input.setStyleSheet(
                """
                QLineEdit {
                    border: none;
                    background: #ececec;
                    font-size: 15px;
                }
            """
            )
            self.mic_btn.setStyleSheet("background: none; border: none;")
            self.file_btn.setStyleSheet("background: none; border: none;")
            self.send_btn.setStyleSheet(
                """
                QPushButton {
                    background: #2d2d2d;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 8px;
                }
                QPushButton:hover { background: #3a3a3a; }
            """
            )

    # ---------------- FUNCTIONS ----------------
    def add_message(self, text, is_user):
        bubble = MessageBubble(text, is_user, self.dark_mode)
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
    w = ChatWindow(lambda: w.close())
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
