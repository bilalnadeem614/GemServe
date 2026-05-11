# gui/Chat_Bot.py
import sys, os
from services.system_intent_service import handle_system_command, is_system_command
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
    QLineEdit,
    QTextEdit,
)
from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QIcon
import shutil
from gui.speech_popup import open_speech_popup

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
from services import (
    get_chat_response,
    process_file,
    handle_llm_file_command,
    process_file_response,
    is_file_operation_request,
)
from services.file_service import (
    open_file,
    delete_file,
    create_file,
    find_files_by_name,
)
from utils.config import UPLOAD_DIR
from utils.helpers import sanitize_filename
from gui.Chat_Bot_styles import get_chat_styles
from services.chat_service import detect_todo_intent, handle_todo_intent
from services.app_service import handle_app_command
# ---------------------- MESSAGE BUBBLE -------------------------
class MessageBubble(QFrame):
    def __init__(self, text, is_user, dark_mode=False):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        cleaned_text = text.strip()

        bubble = QLabel(cleaned_text)
        bubble.setWordWrap(True)
        if "<a href=" in cleaned_text.lower():
            bubble.setTextFormat(Qt.RichText)
        else:
            bubble.setTextFormat(Qt.PlainText)
        bubble.setOpenExternalLinks(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)

        badge = QLabel("You" if is_user else "AI")
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignCenter)

        if dark_mode:
            badge.setStyleSheet(
                """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366F1, stop:1 #8B5CF6);
                color: #FFFFFF;
                border-radius: 18px;
                font-weight: 700;
                font-size: 11px;
            """
            )
        else:
            badge.setStyleSheet(
                """
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366F1, stop:1 #8B5CF6);
                color: #FFFFFF;
                border-radius: 18px;
                font-weight: 700;
                font-size: 11px;
            """
            )

        if is_user:
            if dark_mode:
                bubble.setStyleSheet(
                    """
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(139, 92, 246, 0.15), stop:1 rgba(30, 41, 59, 0.8));
                    border: 2px solid rgba(139, 92, 246, 0.3);
                    color: #E2E8F0;
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 15px;
                    font-weight: 500;
                """
                )
            else:
                bubble.setStyleSheet(
                    """
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(245, 243, 255, 0.9), stop:1 #FFFFFF);
                    border: 2px solid rgba(139, 92, 246, 0.25);
                    color: #1E293B;
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 15px;
                    font-weight: 500;
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
                    background: rgba(30, 41, 59, 0.6);
                    border: 2px solid rgba(71, 85, 105, 0.4);
                    color: #E2E8F0;
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 15px;
                    font-weight: 500;
                """
                )
            else:
                bubble.setStyleSheet(
                    """
                    background: #FFFFFF;
                    border: 2px solid rgba(226, 232, 240, 0.8);
                    color: #1E293B;
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 15px;
                    font-weight: 500;
                """
                )
            layout = QHBoxLayout()
            layout.addWidget(badge)
            layout.addWidget(bubble)
            layout.addStretch()

        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        self.setLayout(layout)


# ---------------------- LLM WORKER THREAD -------------------------
class LLMWorker(QThread):
    """Background thread for LLM processing to keep UI responsive"""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, session_id, user_query, mode="fast"):
        super().__init__()
        self.session_id = session_id
        self.user_query = user_query
        self.mode = mode

    def run(self):
        try:
            response = get_chat_response(self.session_id, self.user_query, self.mode)
            cleaned_response = response.strip()
            self.finished.emit(cleaned_response)
        except Exception as e:
            self.error.emit(str(e))


# ---------------------- FILE PROCESSOR WORKER THREAD -------------------------
class FileProcessorWorker(QThread):
    """Background thread for file processing"""

    progress = Signal(int)
    status_update = Signal(str)
    finished = Signal(bool)
    error = Signal(str)

    def __init__(self, session_id, file_path, file_type, filename):
        super().__init__()
        self.session_id = session_id
        self.file_path = file_path
        self.file_type = file_type
        self.filename = filename

    def run(self):
        try:
            self.status_update.emit(f"📎 Processing: {self.filename}...")
            self.progress.emit(10)

            file_id = save_file_metadata(
                self.session_id, self.filename, self.file_path, self.file_type
            )

            self.status_update.emit(f"📖 Extracting text from {self.filename}...")
            self.progress.emit(20)
            chunks = process_file(self.file_path, self.file_type)

            if not chunks:
                self.error.emit(f"⚠️ Could not extract text from {self.filename}")
                self.finished.emit(False)
                return

            self.status_update.emit(f"🔄 Generating embeddings for {len(chunks)} chunks...")
            self.progress.emit(30)

            def embedding_progress(current, total):
                percent = 30 + int((current / total) * 60)
                self.progress.emit(percent)

            success = add_document_chunks(
                self.session_id,
                file_id,
                self.filename,
                chunks,
                progress_callback=embedding_progress
            )

            if not success:
                self.error.emit(f"❌ Failed to process embeddings for {self.filename}")
                self.finished.emit(False)
                return

            self.status_update.emit(f"✅ Finalizing...")
            self.progress.emit(95)
            mark_file_processed(file_id)

            self.progress.emit(100)
            self.finished.emit(True)

        except Exception as e:
            self.error.emit(f"❌ File processing error: {str(e)}")
            self.finished.emit(False)


# ---------------------- ROUTER WORKER THREAD -------------------------
class RouterWorker(QThread):
    """
    Runs is_file_operation_request() in a background thread so the LLM
    routing call never freezes the UI.
    """
    finished = Signal(bool)
    error    = Signal(str)

    def __init__(self, text: str, mode: str = "fast"):
        super().__init__()
        self.text = text
        self.mode = mode

    def run(self):
        try:
            from services.llm_file_service import is_file_operation_request
            from utils.config import OLLAMA_FAST_MODEL, OLLAMA_THINKING_MODEL
            model = OLLAMA_THINKING_MODEL if self.mode == "thinking" else OLLAMA_FAST_MODEL
            is_file, confidence = is_file_operation_request(self.text, model=model)
            self.finished.emit(is_file and confidence > 0.5)
        except Exception as e:
            self.error.emit(str(e))


# ----------------------- MAIN CHAT WINDOW ------------------------
class ChatWindow(QWidget):
    def __init__(self, go_home_callback, home_page_refresh_callback):
        super().__init__()
        self.go_home = go_home_callback
        self.home_page_refresh = home_page_refresh_callback
        self.dark_mode = False
        self.current_session_id = None
        self.is_new_session = True
        self.llm_worker = None
        self.file_worker = None
        self._speech_popup = None
        self.router_worker = None

        self.file_operation_mode = False
        self.pending_file_action = None

        self.setMinimumSize(450, 620)
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------- HEADER ----------------
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setFixedHeight(70)

        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(20, 15, 20, 15)

        self.back_btn = QPushButton("←")
        self.back_btn.setObjectName("backButton")
        self.back_btn.setFixedSize(40, 40)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.on_back)

        self.title = QLabel("New Chat")
        self.title.setObjectName("headerTitle")
        self.title.setAlignment(Qt.AlignCenter)

        h_layout.addWidget(self.back_btn)
        h_layout.addStretch()
        h_layout.addWidget(self.title)
        h_layout.addStretch()

        root.addWidget(self.header)

        # ============= UPLOADED FILES SECTION =============
        self.files_container = QFrame()
        self.files_container.setObjectName("filesContainer")
        self.files_container.setVisible(False)

        files_layout = QVBoxLayout(self.files_container)
        files_layout.setContentsMargins(20, 10, 20, 10)
        files_layout.setSpacing(8)

        files_title = QLabel("📎 Uploaded Files:")
        files_title.setObjectName("filesTitle")
        files_layout.addWidget(files_title)

        self.files_list_layout = QVBoxLayout()
        self.files_list_layout.setSpacing(6)
        files_layout.addLayout(self.files_list_layout)

        root.addWidget(self.files_container)

        # ---------------- CHAT AREA ----------------
        self.chat_area = QScrollArea()
        self.chat_area.setObjectName("chatArea")
        self.chat_area.setWidgetResizable(True)
        self.chat_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("chatContainer")
        self.chat_layout = QVBoxLayout(container)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()

        self.chat_area.setWidget(container)
        root.addWidget(self.chat_area)
        self.scroll = self.chat_area

        # ---------------- INPUT AREA ----------------
        self.input_frame = QFrame()
        self.input_frame.setObjectName("inputFrame")
        self.input_frame.setFixedHeight(90)

        i_layout = QHBoxLayout(self.input_frame)
        i_layout.setContentsMargins(20, 18, 20, 18)
        i_layout.setSpacing(12)

        self.wrapper = QFrame()
        self.wrapper.setObjectName("inputWrapper")
        self.wrapper.setMinimumHeight(54)
        self.wrapper.setMaximumHeight(54)

        w_layout = QHBoxLayout(self.wrapper)
        w_layout.setContentsMargins(55, 0, 215, 0)

        self.input = QTextEdit()
        self.input.setObjectName("messageInput")
        self.input.setPlaceholderText("Type your message...")
        self.input.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input.setFixedHeight(36)
        self.input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        def _adjust_height():
            doc_h = int(self.input.document().size().height())
            new_h = max(36, min(doc_h + 10, 160))
            self.input.setFixedHeight(new_h)
            # grow wrapper and frame to match
            pad = 18  # top+bottom padding inside wrapper
            wrapper_h = max(54, new_h + pad)
            self.wrapper.setMinimumHeight(wrapper_h)
            self.wrapper.setMaximumHeight(wrapper_h)
            self.input_frame.setFixedHeight(wrapper_h + 36)
            # keep overlay buttons vertically centred
            btn_y = (wrapper_h - 36) // 2
            self.mic_btn.setGeometry(9, btn_y, 36, 36)
            self.mode_combo.setGeometry(self.wrapper.width() - 210, btn_y, 150, 36)
            self.file_btn.setGeometry(self.wrapper.width() - 45, btn_y, 36, 36)

        self.input.document().contentsChanged.connect(_adjust_height)

        def _key_press(event):
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                self.on_send()
            else:
                QTextEdit.keyPressEvent(self.input, event)

        self.input.keyPressEvent = _key_press
        w_layout.addWidget(self.input)

        self.mic_btn = QPushButton("🎤", self.wrapper)
        self.mic_btn.setObjectName("iconButton")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setGeometry(9, 9, 36, 36)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.clicked.connect(self.on_mic_click)

        self.mode_combo = QComboBox(self.wrapper)
        self.mode_combo.setObjectName("modeCombo")
        self.mode_combo.addItem("⚡ Fast")
        self.mode_combo.addItem("🧠 Thinking")
        self.mode_combo.setFixedSize(150, 36)
        self.mode_combo.setGeometry(50, 9, 150, 36)
        self.mode_combo.setCursor(Qt.PointingHandCursor)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)

        self.file_btn = QPushButton("📎", self.wrapper)
        self.file_btn.setObjectName("iconButton")
        self.file_btn.setFixedSize(36, 36)
        self.file_btn.setCursor(Qt.PointingHandCursor)
        self.file_btn.clicked.connect(self.on_file_upload)

        def on_wrapper_resize(e):
            self.mode_combo.setGeometry(self.wrapper.width() - 210, 9, 150, 36)
            self.file_btn.setGeometry(self.wrapper.width() - 45, 9, 36, 36)

        self.wrapper.resizeEvent = on_wrapper_resize

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setFixedHeight(54)
        self.send_btn.setFixedWidth(100)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.on_send)

        i_layout.addWidget(self.wrapper)
        i_layout.addWidget(self.send_btn)
        root.addWidget(self.input_frame)

    # -----------------------------------------
    # Mode Management
    # -----------------------------------------
    def on_mode_changed(self):
        """Handle mode change (notification only)"""
        mode = self.get_selected_mode()
        mode_name = "Fast Mode" if mode == "fast" else "Thinking Mode"
        self.add_message(f"🔄 Switched to {mode_name}", False, save_to_db=False)

    def get_selected_mode(self):
        """Get current selected mode"""
        mode_text = self.mode_combo.currentText()
        if "Fast" in mode_text:
            return "fast"
        elif "Thinking" in mode_text:
            return "thinking"
        return "fast"

    # -----------------------------------------
    # Session Management
    # -----------------------------------------
    def start_new_session(self):
        """Start a new chat session"""
        self.current_session_id = None
        self.is_new_session = True
        self.pending_file_action = None
        self.title.setText("New Chat")
        self.clear_chat()
        self.files_container.setVisible(False)
        self.mode_combo.setCurrentIndex(0)
        print("✅ Ready for new session")

    def load_session(self, session_id):
        """Load an existing chat session"""
        self.current_session_id = session_id
        self.is_new_session = False
        self.pending_file_action = None
        self.clear_chat()

        messages = get_session_messages(session_id)

        for role, content, timestamp in messages:
            is_user = role == "user"
            self.add_message(content, is_user, save_to_db=False)

        if messages:
            first_message = messages[0][1]
            title = (
                first_message[:30] + "..." if len(first_message) > 30 else first_message
            )
            self.title.setText(title)

        self.load_uploaded_files_ui()
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
        self.setStyleSheet(get_chat_styles(enabled))

    # ---------------- MESSAGE FUNCTIONS ----------------
    def add_message(self, text, is_user, save_to_db=True):
        bubble = MessageBubble(text, is_user, self.dark_mode)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(50, self.scroll_bottom)

        if save_to_db and self.current_session_id:
            role = "user" if is_user else "assistant"
            cleaned_text = text.strip()
            save_message(self.current_session_id, role, cleaned_text)

    def scroll_bottom(self):
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )

    # ---------------- FILE OPERATION HANDLER ----------------
    def handle_file_operation(self, text):
        """Handle file operation commands using LLM for intent recognition"""
        if self.pending_file_action:
            result = process_file_response(text, self.pending_file_action)

            if result["status"] == "success":
                self.add_message(result["message"], False, save_to_db=False)
                self.pending_file_action = None

            elif result["status"] == "confirm":
                data = result.get("data", {})
                file_to_delete = (
                    data.get("file") or
                    (data.get("files", [None])[0] if data.get("files") else None)
                )
                self.pending_file_action = {
                    "state": "delete_confirm",
                    "file": file_to_delete,
                    "operation": "delete",
                }
                self.add_message(result["message"], False, save_to_db=False)

            elif result["status"] == "ask_location":
                self.pending_file_action = {
                    "state": "location",
                    "filename": self.pending_file_action.get("filename"),
                    "operation": "create",
                }
                self.add_message(result["message"], False, save_to_db=False)

            elif result["status"] == "ask_custom_path":
                self.pending_file_action = {
                    "state": "custom_path",
                    "filename": self.pending_file_action.get("filename"),
                    "operation": "create",
                }
                self.add_message(result["message"], False, save_to_db=False)

            elif result["status"] == "error" and not result["handled"]:
                self.add_message(result["message"], False, save_to_db=False)

            return

        result = handle_llm_file_command(text, self.current_session_id)

        if result["status"] == "success":
            self.add_message(result["message"], False, save_to_db=False)

        elif result["status"] == "error":
            self.add_message(result["message"], False, save_to_db=False)

        elif result["status"] == "clarify":
            self.add_message(result["message"], False, save_to_db=False)

        elif result["status"] == "select":
            self.pending_file_action = {
                "state": "select",
                "files": result["data"]["files"],
                "operation": result["data"]["operation"],
                "filename": result["data"]["filename"],
            }
            self.add_message(result["message"], False, save_to_db=False)

        elif result["status"] == "confirm":
            self.pending_file_action = {
                "state": "delete_confirm",
                "file": result["data"]["files"][0] if result["data"]["files"] else None,
                "operation": result["action"],
            }
            self.add_message(result["message"], False, save_to_db=False)

        elif result["status"] == "ask_location":
            self.pending_file_action = {
                "state": "location",
                "filename": result["data"]["filename"],
                "operation": "create",
            }
            self.add_message(result["message"], False, save_to_db=False)

    # ---------------- SEND MESSAGE ----------------
    def on_send(self):
        text = self.input.toPlainText().strip()
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

        # ─────────────────────────────────────────────
        # 1. TODO INTENT CHECK
        # ─────────────────────────────────────────────
        is_todo, task_text = detect_todo_intent(text)
        if is_todo:
            response = handle_todo_intent(task_text)
            self.add_message(response, False, save_to_db=True)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
            self.home_page_refresh()
            return

        # ─────────────────────────────────────────────
        # 2. SYSTEM COMMAND CHECK
        # ─────────────────────────────────────────────
        if is_system_command(text):
            result = handle_system_command(text)
            if result["status"] != "none":
                self.add_message(result["message"], False, save_to_db=True)
                self.input.setEnabled(True)
                self.send_btn.setEnabled(True)
                self.input.setFocus()
                return
        # ✅ APP CONTROL — open app / close app / switch app
        app_response = handle_app_command(text)
        if app_response:
            self.add_message(app_response, False, save_to_db=False)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
            return

        # ─────────────────────────────────────────────
        # 3. WEB SEARCH CHECK
        # Route 'search web ...' directly to chat so it bypasses file intent.
        # ─────────────────────────────────────────────
        if text.lower().strip().startswith("search web "):
            mode = self.get_selected_mode()
            self.add_message("Thinking...", False, save_to_db=False)
            self.llm_worker = LLMWorker(self.current_session_id, text, mode)
            self.llm_worker.finished.connect(self.on_llm_response)
            self.llm_worker.error.connect(self.on_llm_error)
            self.llm_worker.start()
            return

        # ─────────────────────────────────────────────
        # 4. FILE OPERATION MODE
        # If mid-way through a file operation always route back to file handler
        # ─────────────────────────────────────────────
        if self.file_operation_mode:
            if self.pending_file_action:
                self.handle_file_operation(text)
                self.input.setEnabled(True)
                self.send_btn.setEnabled(True)
                self.input.setFocus()
                return

        # ─────────────────────────────────────────────
        # 5. ROUTE via LLM (file op vs normal chat)
        # ─────────────────────────────────────────────
        mode = self.get_selected_mode()

        self.add_message("🔍 Routing...", False, save_to_db=False)
        self.router_worker = RouterWorker(text, mode)
        self.router_worker.finished.connect(
            lambda is_file: self._after_routing(text, mode, is_file)
        )
        self.router_worker.error.connect(
            lambda _: self._after_routing(text, mode, False)
        )
        self.router_worker.start()

    def _after_routing(self, text: str, mode: str, is_file_op: bool):
        """Called by RouterWorker once intent is classified."""
        # Remove the "Routing..." bubble
        last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
        if last_item and last_item.widget():
            last_item.widget().deleteLater()

        if is_file_op:
            self.handle_file_operation(text)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
            return

        # Normal chat
        self.add_message("Thinking...", False, save_to_db=False)
        self.llm_worker = LLMWorker(self.current_session_id, text, mode)
        self.llm_worker.finished.connect(self.on_llm_response)
        self.llm_worker.error.connect(self.on_llm_error)
        self.llm_worker.start()

    def process_text_input(self, text: str):
        """
        Central entry point for any text input — typed OR spoken.
        Voice just calls this after speech-to-text.
        """
        self.input.setPlainText(text)
        self.on_send()

    def on_llm_response(self, response):
        last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
        if last_item and last_item.widget():
            last_item.widget().deleteLater()

        if not response or not response.strip():
            response = "⚠️ The model returned an empty response. Please try again."

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
        from gui.speech_popup import SpeechPopup
        if self._speech_popup is None:
            self._speech_popup = SpeechPopup(self, whisper_model_dir="models/whisper")
            self._speech_popup.text_ready.connect(self._on_voice_text)
        self._speech_popup.show()

    def _on_voice_text(self, text: str):
        self.input.setText(text)
        self.add_message(
            "🎤 Voice input coming soon! "
            "When ready, speech will route through the same pipeline as typed messages.",
            False, save_to_db=False
        )

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
            "Supported Files (*.txt *.md *.pdf);;Text Files (*.txt);;Markdown (*.md);;PDF Files (*.pdf)",
        )

        if not file_path:
            return

        filename = os.path.basename(file_path)

        self.file_btn.setEnabled(False)
        self.send_btn.setEnabled(False)

        self.add_message(f"📎 Uploading: {filename}...", False, save_to_db=False)

        try:
            safe_filename = sanitize_filename(filename)
            dest_path = os.path.join(
                UPLOAD_DIR, f"session_{self.current_session_id}_{safe_filename}"
            )
            shutil.copy(file_path, dest_path)

            file_type = safe_filename.split(".")[-1].lower()

            self.file_worker = FileProcessorWorker(
                self.current_session_id,
                dest_path,
                file_type,
                filename
            )
            self.file_worker.progress.connect(self.on_file_progress)
            self.file_worker.status_update.connect(self.on_file_status_update)
            self.file_worker.finished.connect(self.on_file_upload_finished)
            self.file_worker.error.connect(self.on_file_upload_error)
            self.file_worker.start()

        except Exception as e:
            self.add_message(f"❌ Upload failed: {str(e)}", False, save_to_db=False)
            self.file_btn.setEnabled(True)
            self.send_btn.setEnabled(True)

    def on_file_progress(self, percent):
        pass

    def on_file_status_update(self, status):
        if self.chat_layout.count() > 1:
            last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
            if last_item and last_item.widget():
                last_item.widget().deleteLater()
        self.add_message(status, False, save_to_db=False)

    def on_file_upload_finished(self, success):
        if self.chat_layout.count() > 1:
            last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
            if last_item and last_item.widget():
                last_item.widget().deleteLater()

        if success:
            self.add_message(
                f"✅ File uploaded successfully!\nFile is ready for questions.",
                False,
                save_to_db=False,
            )
            self.load_uploaded_files_ui()

        self.file_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()

    def on_file_upload_error(self, error_msg):
        if self.chat_layout.count() > 1:
            last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
            if last_item and last_item.widget():
                last_item.widget().deleteLater()

        self.add_message(error_msg, False, save_to_db=False)

        self.file_btn.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()

    def add_file_to_ui(self, filename):
        file_badge = QLabel(f"📄 {filename}")
        file_badge.setObjectName("fileBadge")
        file_badge.setFixedHeight(32)
        self.files_list_layout.addWidget(file_badge)
        self.files_container.setVisible(True)

    def load_uploaded_files_ui(self):
        if not self.current_session_id:
            return

        while self.files_list_layout.count():
            item = self.files_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        files = get_session_files(self.current_session_id)

        if files:
            for file_id, filename, upload_date, is_processed in files:
                if is_processed:
                    self.add_file_to_ui(filename)

    def on_back(self):
        self.home_page_refresh()
        self.go_home()


# ---------------- MAIN ----------------
def main():
    app = QApplication(sys.argv)
    w = ChatWindow(lambda: w.close(), lambda: None)
    w.start_new_session()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()