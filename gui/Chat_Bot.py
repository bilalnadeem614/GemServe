# gui/Chat_Bot.py
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
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QIcon
import shutil

# Import database and services
from db import (
    create_session,
    save_message,
    get_session_messages,
    save_file_metadata,
    mark_file_processed,
    get_session_files,
)
from db.vector_store import add_document_chunks
from services import get_chat_response, process_file
from utils.config import UPLOAD_DIR
from utils.helpers import sanitize_filename


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
                color: #ffffff;
                border-radius: 14px;
                font-weight: bold;
            """
            )
        else:
            badge.setStyleSheet(
                """
                background: #2d2d2d;
                color: #ffffff;
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
                    background: #ffffff;
                    border: 1px solid #c7c7c7;
                    color: #000000;
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
                    color: #000000;
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


# ---------------------- LLM WORKER THREAD -------------------------
class LLMWorker(QThread):
    """Background thread for LLM processing to keep UI responsive"""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, session_id, user_query):
        super().__init__()
        self.session_id = session_id
        self.user_query = user_query

    def run(self):
        try:
            response = get_chat_response(self.session_id, self.user_query)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))


# ----------------------- MAIN CHAT WINDOW ------------------------
class ChatWindow(QWidget):
    def __init__(self, go_home_callback, home_page_refresh_callback):
        super().__init__()
        self.go_home = go_home_callback
        self.home_page_refresh = home_page_refresh_callback  # To refresh home page sessions
        self.dark_mode = False
        self.current_session_id = None
        self.is_new_session = True
        self.llm_worker = None

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
        self.back_btn.clicked.connect(self.on_back)

        self.title = QLabel("New Chat")
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
    # Session Management
    # -----------------------------------------
    def start_new_session(self):
        """Start a new chat session"""
        self.current_session_id = None
        self.is_new_session = True
        self.title.setText("New Chat")
        self.clear_chat()
        print("✅ Ready for new session")

    def load_session(self, session_id):
        """Load an existing chat session"""
        self.current_session_id = session_id
        self.is_new_session = False
        self.clear_chat()

        messages = get_session_messages(session_id)

        for role, content, timestamp in messages:
            is_user = role == "user"
            self.add_message(content, is_user, save_to_db=False)

        if messages:
            first_message = messages[0][1]
            title = first_message[:30] + "..." if len(first_message) > 30 else first_message
            self.title.setText(title)

        print(f"✅ Loaded session {session_id}")

    def clear_chat(self):
        """Clear all messages from chat area"""
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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
                    color: #ffffff;
                    padding: 6px 12px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:hover { background: #5a5a5a; }
            """
            )
            self.title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: 600;")
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
                    color: #ffffff;
                    padding: 8px 16px;
                    border-radius: 8px;
                }
                QPushButton:hover { background: #45a049; }
            """
            )
        else:
            self.header.setStyleSheet("background: #f0f0f0;")
            self.back_btn.setStyleSheet(
                """
                QPushButton {
                    background: #ffffff;
                    color: #000000;
                    padding: 6px 12px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
                QPushButton:hover { background: #e8e8e8; }
            """
            )
            self.title.setStyleSheet("color: #000000; font-size: 18px; font-weight: 600;")
            self.chat_area.setStyleSheet("background: #f0f0f0;")
            self.input_frame.setStyleSheet("background: #f0f0f0;")
            self.wrapper.setStyleSheet(
                """
                QFrame {
                    background: #ffffff;
                    border-radius: 22px;
                    border: 1px solid #ccc;
                }
            """
            )
            self.input.setStyleSheet(
                """
                QLineEdit {
                    border: none;
                    background: #ffffff;
                    color: #000000;
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
                    color: #ffffff;
                    padding: 8px 16px;
                    border-radius: 8px;
                }
                QPushButton:hover { background: #45a049; }
            """
            )

    # ---------------- MESSAGE FUNCTIONS ----------------
    def add_message(self, text, is_user, save_to_db=True):
        bubble = MessageBubble(text, is_user, self.dark_mode)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(50, self.scroll_bottom)

        if save_to_db and self.current_session_id:
            role = "user" if is_user else "assistant"
            save_message(self.current_session_id, role, text)

    def scroll_bottom(self):
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )

    def on_send(self):
        text = self.input.text().strip()
        if not text:
            return

        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)

        if self.is_new_session:
            self.current_session_id = create_session(text)
            self.is_new_session = False

            title = text[:30] + "..." if len(text) > 30 else text
            self.title.setText(title)

            self.home_page_refresh()

        self.add_message(text, True, save_to_db=True)
        self.input.clear()

        self.add_message("🤔 Thinking...", False, save_to_db=False)

        self.llm_worker = LLMWorker(self.current_session_id, text)
        self.llm_worker.finished.connect(self.on_llm_response)
        self.llm_worker.error.connect(self.on_llm_error)
        self.llm_worker.start()

    def on_llm_response(self, response):
        last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
        if last_item and last_item.widget():
            last_item.widget().deleteLater()

        self.add_message(response, False, save_to_db=True)

        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()

    def on_llm_error(self, error_msg):
        last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
        if last_item and last_item.widget():
            last_item.widget().deleteLater()

        self.add_message(f"❌ Error: {error_msg}", False, save_to_db=False)

        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()

    def on_mic_click(self):
        self.add_message("🎤 Voice input coming soon...", False, save_to_db=False)

    def on_file_upload(self):
        if not self.current_session_id:
            QMessageBox.warning(
                self,
                "No Active Session",
                "Please send a message first to start a session before uploading files.",
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "Supported Files (*.txt *.md *.pdf);;Text Files (*.txt);;Markdown (*.md);;PDF Files (*.pdf);;All Files (*.*)",
        )

        if not file_path:
            return

        filename = os.path.basename(file_path)
        self.add_message(f"📎Uploading: {filename}...", True, save_to_db=False)

        try:
            safe_filename = sanitize_filename(filename)
            dest_path = os.path.join(
                UPLOAD_DIR, f"session_{self.current_session_id}_{safe_filename}"
            )
            shutil.copy(file_path, dest_path)

            file_type = safe_filename.split(".")[-1].lower()

            file_id = save_file_metadata(
                self.current_session_id, filename, dest_path, file_type
            )

            chunks = process_file(dest_path, file_type)

            if chunks:
                add_document_chunks(self.current_session_id, file_id, filename, chunks)
                mark_file_processed(file_id)

                self.add_message(
                    f"✅ File uploaded successfully!\n{filename} ({len(chunks)} chunks)",
                    False,
                    save_to_db=False,
                )
            else:
                self.add_message(
                    f"⚠️ Could not extract text from {filename}",
                    False,
                    save_to_db=False,
                )

        except Exception as e:
            self.add_message(f"❌ Upload failed: {str(e)}", False, save_to_db=False)
            print(f"File upload error: {e}")

    def on_back(self):
        self.home_page_refresh()
        self.go_home()


# ---------------- MAIN (Not used in main app) ----------------
def main():
    app = QApplication(sys.argv)
    w = ChatWindow(lambda: w.close(), lambda: None)
    w.start_new_session()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
