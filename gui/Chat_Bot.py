# gui/Chat_Bot.py
import sys, os
import logging

# from GemServe.services.file_advanced_service import _normalise_location
from services.file_advanced_service import _normalise_location
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
from gui.speech_popup import open_speech_popup, SpeechPopup
from services.wake_word_detector import WakeWordDetector

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
from services.model_manager import ModelManager


logger = logging.getLogger(__name__)


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
        bubble.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse
        )

        badge = QLabel("You" if is_user else "AI")
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignCenter)

        if dark_mode:
            badge.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366F1, stop:1 #8B5CF6);
                color: #FFFFFF;
                border-radius: 18px;
                font-weight: 700;
                font-size: 11px;
            """)
        else:
            badge.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #6366F1, stop:1 #8B5CF6);
                color: #FFFFFF;
                border-radius: 18px;
                font-weight: 700;
                font-size: 11px;
            """)

        if is_user:
            if dark_mode:
                bubble.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(139, 92, 246, 0.15), stop:1 rgba(30, 41, 59, 0.8));
                    border: 2px solid rgba(139, 92, 246, 0.3);
                    color: #E2E8F0;
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 15px;
                    font-weight: 500;
                """)
            else:
                bubble.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(245, 243, 255, 0.9), stop:1 #FFFFFF);
                    border: 2px solid rgba(139, 92, 246, 0.25);
                    color: #1E293B;
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 15px;
                    font-weight: 500;
                """)
            layout = QHBoxLayout()
            layout.addStretch()
            layout.addWidget(bubble)
            layout.addWidget(badge)

        else:
            if dark_mode:
                bubble.setStyleSheet("""
                    background: rgba(30, 41, 59, 0.6);
                    border: 2px solid rgba(71, 85, 105, 0.4);
                    color: #E2E8F0;
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 15px;
                    font-weight: 500;
                """)
            else:
                bubble.setStyleSheet("""
                    background: #FFFFFF;
                    border: 2px solid rgba(226, 232, 240, 0.8);
                    color: #1E293B;
                    padding: 14px 18px;
                    border-radius: 18px;
                    font-size: 15px;
                    font-weight: 500;
                """)
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

            self.status_update.emit(
                f"🔄 Generating embeddings for {len(chunks)} chunks..."
            )
            self.progress.emit(30)

            def embedding_progress(current, total):
                percent = 30 + int((current / total) * 60)
                self.progress.emit(percent)

            success = add_document_chunks(
                self.session_id,
                file_id,
                self.filename,
                chunks,
                progress_callback=embedding_progress,
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
    error = Signal(str)

    def __init__(self, text: str, mode: str = "fast"):
        super().__init__()
        self.text = text
        self.mode = mode

    def run(self):
        try:
            from services.llm_file_service import is_file_operation_request
            from utils.config import OLLAMA_FAST_MODEL, OLLAMA_THINKING_MODEL

            model = (
                OLLAMA_THINKING_MODEL if self.mode == "thinking" else OLLAMA_FAST_MODEL
            )
            is_file, confidence = is_file_operation_request(self.text, model=model)
            self.finished.emit(is_file and confidence > 0.5)
        except Exception as e:
            self.error.emit(str(e))


# ----------------------- MAIN CHAT WINDOW ------------------------
class ChatWindow(QWidget):
    def __init__(self, go_home_callback, home_page_refresh_callback, model_manager=None):
        super().__init__()
        self.go_home = go_home_callback
        self.home_page_refresh = home_page_refresh_callback
        self.model_manager = model_manager or ModelManager()
        self.dark_mode = False
        self.current_session_id = None
        self.is_new_session = True
        self.llm_worker = None
        self.file_worker = None
        self._speech_popup = None
        self.router_worker = None
        self.wake_word_detector = None

        self.file_operation_mode = False
        self.pending_file_action = None

        self.setMinimumSize(450, 620)
        self.setup_ui()

    def setup_wake_word_detector(self, model_manager=None):
        """Create and wire the wake-word detector used by the chat window."""
        model_manager = model_manager or self.model_manager
        detector = WakeWordDetector(model_manager=model_manager, debug_mode=True)
        detector.wake_word_detected.connect(self._on_wake_word_detected)
        self.wake_word_detector = detector
        logger.info("Wake-word detector attached to ChatWindow.")
        return detector

    def start_wake_word_detection(self):
        """Start wake-word detection when the chat window becomes visible."""
        if self.wake_word_detector is None:
            logger.warning("Wake-word detector is not available on ChatWindow.")
            return

        worker_thread = getattr(self.wake_word_detector, "_worker_thread", None)
        if worker_thread is not None and worker_thread.isRunning():
            logger.info("Wake-word detector thread is already running.")
            return

        logger.info("Wake-word detection start requested from ChatWindow.")
        try:
            self.model_manager.get_tiny_model()
            logger.info("Tiny Whisper model primed for wake-word detection.")
        except Exception as exc:
            logger.warning("Could not prime tiny model before wake-word detection: %s", exc)

        if hasattr(self.wake_word_detector, "start_background_thread"):
            logger.info("Wake-word detector starting listening/transcribing from ChatWindow.")
            thread = self.wake_word_detector.start_background_thread()
            logger.info("Wake-word detector background thread started: %s", thread)

    def stop_wake_word_detection(self):
        """Stop wake-word detection when the chat window is hidden."""
        if self.wake_word_detector is None:
            logger.warning("stop_wake_word_detection() called but detector is unavailable.")
            return

        if hasattr(self.wake_word_detector, "stop_detector_gracefully"):
            logger.info("Wake-word detector stopping from ChatWindow.")
            self.wake_word_detector.stop_detector_gracefully()
        else:
            logger.info("Wake-word detector fallback stop_listening() from ChatWindow.")
            self.wake_word_detector.stop_listening()

    def _on_wake_word_detected(self, text: str):
        """Forward wake-word events to the active speech popup."""
        logger.info("Wake word detected in ChatWindow: %s", text)
        self._set_wake_word_detected_state(text)
        if self._speech_popup is None:
            self._speech_popup = SpeechPopup(
                self,
                model_manager=self.model_manager,
                whisper_model_dir="models/whisper",
                triggered_by_wake_word=True,
                wake_word_detector=self.wake_word_detector,
            )
            self._speech_popup.text_ready.connect(self._on_voice_text)
            self._speech_popup.finished.connect(self._on_speech_popup_finished)

        self._speech_popup.accept_wake_word_trigger(text)
        self._speech_popup.show()
        self._speech_popup.raise_()
        self._speech_popup.activateWindow()

    def _on_speech_popup_finished(self, result: int):
        """Restart wake-word listening after the popup completes a voice command."""
        logger.info("Speech popup finished with result=%s; scheduling wake-word restart.", result)
        self._set_wake_word_listening_state()
        QTimer.singleShot(250, self.start_wake_word_detection)

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------------- HEADER ----------------
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setFixedHeight(94)

        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(20, 12, 20, 12)
        h_layout.setSpacing(12)

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

        self._wake_indicator = QFrame()
        self._wake_indicator.setObjectName("wakeIndicator")
        self._wake_indicator.setFixedHeight(28)
        self._wake_indicator_layout = QHBoxLayout(self._wake_indicator)
        self._wake_indicator_layout.setContentsMargins(0, 0, 0, 0)
        self._wake_indicator_layout.setSpacing(8)

        self._wake_dot = QLabel("●")
        self._wake_dot.setObjectName("wakeIndicatorDot")
        self._wake_dot.setFixedWidth(14)
        self._wake_dot.setAlignment(Qt.AlignCenter)

        self._wake_indicator_label = QLabel("🎤 Listening for 'Hey' or 'Hello'")
        self._wake_indicator_label.setObjectName("wakeIndicatorLabel")

        self._wake_indicator_layout.addWidget(self._wake_dot)
        self._wake_indicator_layout.addWidget(self._wake_indicator_label)
        self._wake_indicator_layout.addStretch()

        self._wake_indicator_visible = True
        self._wake_pulse_on = False
        self._wake_indicator_timer = QTimer(self)
        self._wake_indicator_timer.setInterval(550)
        self._wake_indicator_timer.timeout.connect(self._pulse_wake_indicator)
        self._wake_indicator_timer.start()

        self._set_wake_word_listening_state()
        h_layout.addWidget(self._wake_indicator)

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
        self.input.setStyleSheet("font-size: 14px; padding: 6px;")
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
        if self.wake_word_detector is None:
            return
        if self._wake_indicator_visible:
            self._set_wake_word_listening_state()

    def showEvent(self, event):
        super().showEvent(event)
        self._wake_indicator_visible = True
        self._wake_indicator.setVisible(True)
        self._wake_indicator_timer.start()
        self._set_wake_word_listening_state()
        self.start_wake_word_detection()

    def hideEvent(self, event):
        QTimer.singleShot(0, self.stop_wake_word_detection)
        self._wake_indicator_timer.stop()
        self._wake_indicator.setVisible(False)
        self._wake_indicator_visible = False
        super().hideEvent(event)

    def _pulse_wake_indicator(self):
        """Animate the listening dot with a subtle pulse."""
        self._wake_pulse_on = not self._wake_pulse_on
        if self._wake_pulse_on:
            self._wake_dot.setStyleSheet(
                "color: #22C55E; font-size: 14px; font-weight: 700;"
            )
        else:
            self._wake_dot.setStyleSheet(
                "color: #86EFAC; font-size: 12px; font-weight: 700;"
            )

    def _set_wake_word_listening_state(self):
        """Show the default wake-word listening state."""
        self._wake_indicator_label.setText("🎤 Listening for 'Hi', 'Hey' or 'Hello'")
        self._wake_indicator_label.setStyleSheet("color: #16A34A; font-weight: 600;")
        self._wake_dot.setStyleSheet("color: #22C55E; font-size: 14px; font-weight: 700;")

    def _set_wake_word_detected_state(self, transcription: str = ""):
        """Update the indicator when a wake word has been detected."""
        label_text = "✅ Wake word detected"
        if transcription:
            label_text = f"✅ Wake word detected: {transcription}"
        self._wake_indicator_label.setText(label_text)
        self._wake_indicator_label.setStyleSheet("color: #0F766E; font-weight: 700;")
        self._wake_dot.setStyleSheet("color: #14B8A6; font-size: 14px; font-weight: 800;")

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
                file_to_delete = data.get("file") or (
                    data.get("files", [None])[0] if data.get("files") else None
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

        # ─────────────────────────────────────────────
        # 3. APP CONTROL
        # ─────────────────────────────────────────────
        app_response = handle_app_command(text)
        if app_response:
            self.add_message(app_response, False, save_to_db=False)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
            return

        # ─────────────────────────────────────────────
        # HANDLE PENDING FILE CREATION LOCATION
        # ─────────────────────────────────────────────
        if self.pending_file_action:
            action = self.pending_file_action.get("action")
            state = self.pending_file_action.get("state", "")

            # SAVE LOCATION SELECTION
            if action == "create_file" and state == "need_save_location":

                choice = text.strip()

                user_profile = os.environ.get("USERPROFILE", "")

                location_map = {
                    "1": os.path.join(user_profile, "Desktop"),
                    "2": os.path.join(user_profile, "Documents"),
                    "3": os.path.join(user_profile, "Downloads"),
                }

                if choice in location_map:
                    save_location = location_map[choice]
                else:
                    save_location = choice

                pending = self.pending_file_action

                from services.file_creator_service import (
                    create_csv,
                    create_xlsx,
                    create_docx,
                    create_pdf,
                )

                file_type = pending.get("file_type")
                filename = pending.get("filename")
                headers = pending.get("headers", [])
                rows = pending.get("rows", [])
                content = pending.get("content")
                title = pending.get("title")

                # CREATE FILE
                if file_type == "csv":
                    result = create_csv(
                        filename,
                        headers,
                        rows,
                        save_location,
                    )

                elif file_type == "xlsx":
                    result = create_xlsx(
                        filename,
                        headers,
                        rows,
                        title,
                        save_location,
                    )

                elif file_type == "docx":
                    result = create_docx(
                        filename,
                        content,
                        title,
                        headers,
                        rows,
                        save_location,
                    )

                elif file_type == "pdf":
                    result = create_pdf(
                        filename,
                        content,
                        title,
                        headers,
                        rows,
                        save_location,
                    )

                else:
                    result = {
                        "status": "error",
                        "message": f"❌ Unsupported file type: {file_type}"
                    }

                self.add_message(
                    result["message"],
                    False,
                    save_to_db=False,
                )

                self.pending_file_action = None
                self._re_enable()
                return
        # ─────────────────────────────────────────────
        # 4. STRUCTURED FILE CREATION (docx/xlsx/csv/pdf)
        # ─────────────────────────────────────────────
        from services.file_creator_service import (
            is_file_creation_request,
            handle_file_creation,
        )

        if is_file_creation_request(text):
            result = handle_file_creation(text)
            if result.get("status") == "need_save_location":
                pending = result.get("pending", {})
                pending["state"] = "need_save_location"
                self.pending_file_action = pending
            self.add_message(result["message"], False, save_to_db=False)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
            return

        # ─────────────────────────────────────────────
        # 5. ADVANCED FILE OPERATIONS (rename/move/search location)
        # ─────────────────────────────────────────────
        from services.file_advanced_service import (
            is_advanced_file_command,
            handle_advanced_file_command,
        )

        if is_advanced_file_command(text) or (
            self.pending_file_action
            and self.pending_file_action.get("action")
            in ("rename", "move", "search_location")
        ):
            self._handle_advanced_file(text)
            return

        # ─────────────────────────────────────────────
        # 6. WEB SEARCH
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
        # 7. FILE OPERATION MODE (pending actions)
        # ─────────────────────────────────────────────
        if self.file_operation_mode:
            if self.pending_file_action:
                self.handle_file_operation(text)
                self.input.setEnabled(True)
                self.send_btn.setEnabled(True)
                self.input.setFocus()
                return

        # ─────────────────────────────────────────────
        # 8. ROUTE via LLM (file op vs normal chat)
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

    def _handle_advanced_file(self, text: str):
        """Handle advanced file operations: rename, move, search in location."""
        from services.file_advanced_service import (
            handle_advanced_file_command,
            search_in_location,
            rename_file,
            rename_multiple_files,
            move_file,
            move_multiple_files,
            _normalise_location,
        )
        from services.llm_file_service import _smart_find
        from services.file_service import open_file
        from pathlib import Path
        import os

        def resolve_location(value: str):
            """Convert user shortcuts like Desktop, Documents, C, all into paths."""
            raw = (value or "").strip()
            key = raw.lower()
            user_profile = os.environ.get("USERPROFILE", "")
            shortcut_map = {
                "1": None,
                "all": None,
                "2": os.path.join(user_profile, "Desktop"),
                "desktop": os.path.join(user_profile, "Desktop"),
                "3": os.path.join(user_profile, "Documents"),
                "documents": os.path.join(user_profile, "Documents"),
                "4": os.path.join(user_profile, "Downloads"),
                "downloads": os.path.join(user_profile, "Downloads"),
            }
            return shortcut_map.get(key, _normalise_location(raw))

        def search_grouped(files_to_find, location=None, use_smart=False):
            """Return one result group per requested file instead of one flat list."""
            groups = []
            for fname in files_to_find:
                if use_smart:
                    result = search_in_location(fname, None, mode="regex")
                    found = result.get("files", [])
                else:
                    result = search_in_location(fname, location, mode="regex")
                    found = result.get("files", [])
                groups.append({"filename": fname, "files": found})
            return groups

        def build_ambiguous_message(groups, operation):
            """Build selection message for groups where one filename has many matches."""
            option_map = []
            lines = []
            idx = 1
            for group in groups:
                if len(group["files"]) > 1:
                    lines.append(f"\n📄 Matches for: {group['filename']}")
                    for path in group["files"]:
                        lines.append(f"  {idx}. {path}")
                        option_map.append({"filename": group["filename"], "path": path})
                        idx += 1
            return (
                f"📂 Multiple matches found. Choose the correct file number to {operation}:\n"
                + "\n".join(lines)
                + "\n\nEnter number or 'cancel':"
            ), option_map

        def finish_grouped_move(groups, destination):
            """Move all files when each requested filename has exactly one selected path."""
            missing = [g["filename"] for g in groups if len(g["files"]) == 0]
            ambiguous = [g for g in groups if len(g["files"]) > 1]

            if missing:
                self.add_message(
                    f"❌ Could not find: {', '.join(missing)}\n\n"
                    "📂 Where are these files located?\n\n"
                    "  • Desktop\n"
                    "  • Documents\n"
                    "  • Downloads\n"
                    "  • C drive / D drive\n"
                    "  • Full path\n"
                    "  • all",
                    False,
                    save_to_db=False,
                )
                return "need_location"

            if not ambiguous:
                paths = [g["files"][0] for g in groups]
                destination = _normalise_location(destination) or destination
                res = move_multiple_files(paths, destination)
                self.add_message(res["message"], False, save_to_db=False)
                self.pending_file_action = None
                return "done"

            message, option_map = build_ambiguous_message(ambiguous, "move")
            self.add_message(message, False, save_to_db=False)
            self.pending_file_action = {
                "action": "move",
                "state": "select_for_move",
                "files": option_map,
                "destination": destination,
                "remaining_files": [g for g in groups if len(g["files"]) == 1],
            }
            return "ambiguous"

        # ─────────────────────────────────────────────────────────────────────
        # HANDLE PENDING ADVANCED ACTION
        # ─────────────────────────────────────────────────────────────────────
        if self.pending_file_action:
            action = self.pending_file_action.get("action")
            state = self.pending_file_action.get("state", "")
            r = text.strip().lower()

            # ── User provided location for RENAME search ──────────────────────
            if action == "rename" and state == "need_rename_location":
                files_to_find = self.pending_file_action.get("files", [])
                new_names = self.pending_file_action.get("new_names", [])
                location = resolve_location(text)

                self.add_message("🔍 Searching for files…", False, save_to_db=False)
                groups = search_grouped(files_to_find, location, use_smart=False)
                self._remove_last_ai_bubble()

                missing = [g["filename"] for g in groups if len(g["files"]) == 0]
                ambiguous = [g for g in groups if len(g["files"]) > 1]

                if missing:
                    self.add_message(
                        f"❌ Could not find: {', '.join(missing)}\n\nCheck the filename and try again.",
                        False,
                        save_to_db=False,
                    )
                    self.pending_file_action = None
                elif not ambiguous:
                    pairs = []
                    for i, group in enumerate(groups):
                        if i < len(new_names):
                            pairs.append({"old_path": group["files"][0], "new_name": new_names[i]})
                    res = rename_file(pairs[0]["old_path"], pairs[0]["new_name"]) if len(pairs) == 1 else rename_multiple_files(pairs)
                    self.add_message(res["message"], False, save_to_db=False)
                    self.pending_file_action = None
                else:
                    message, option_map = build_ambiguous_message(ambiguous, "rename")
                    self.add_message(message, False, save_to_db=False)
                    self.pending_file_action = {
                        "action": "rename",
                        "state": "select_for_rename",
                        "files": option_map,
                        "new_names": new_names,
                        "remaining_files": [g for g in groups if len(g["files"]) == 1],
                    }

                self._re_enable()
                return

            # ── User provided location for MOVE search ────────────────────────
            if action == "move" and state == "need_move_location":
                files_to_find = self.pending_file_action.get("files", [])
                destination = self.pending_file_action.get("destination")
                location = resolve_location(text)

                self.add_message("🔍 Searching for files…", False, save_to_db=False)
                groups = search_grouped(files_to_find, location, use_smart=False)
                self._remove_last_ai_bubble()

                result_state = finish_grouped_move(groups, destination)
                if result_state == "need_location":
                    self.pending_file_action = {
                        "action": "move",
                        "state": "need_move_location",
                        "files": files_to_find,
                        "destination": destination,
                    }

                self._re_enable()
                return

            # ── User provided destination for MOVE ────────────────────────────
            if action == "move" and state == "need_destination":
                destination = _normalise_location(text.strip()) or text.strip()
                files_to_find = self.pending_file_action.get("files", [])

                self.add_message("🔍 Searching for files…", False, save_to_db=False)
                groups = search_grouped(files_to_find, use_smart=True)
                self._remove_last_ai_bubble()

                result_state = finish_grouped_move(groups, destination)
                if result_state == "need_location":
                    self.pending_file_action = {
                        "action": "move",
                        "state": "need_move_location",
                        "files": files_to_find,
                        "destination": destination,
                    }

                self._re_enable()
                return

            # ── User provided new name for RENAME ─────────────────────────────
            if action == "rename" and state == "need_new_name":
                new_name = text.strip()
                old_path = self.pending_file_action.get("file_path")
                res = rename_file(old_path, new_name)
                self.add_message(res["message"], False, save_to_db=False)
                self.pending_file_action = None
                self._re_enable()
                return

            # ── User selects from multiple files for RENAME ───────────────────
            if action == "rename" and state == "select_for_rename":
                files = self.pending_file_action.get("files", [])
                new_names = self.pending_file_action.get("new_names", [])
                remaining_files = self.pending_file_action.get("remaining_files", [])

                if r in ("cancel", "c"):
                    self.add_message("❌ Rename cancelled.", False, save_to_db=False)
                    self.pending_file_action = None
                    self._re_enable()
                    return

                try:
                    choice = int(r)
                    if 1 <= choice <= len(files):
                        selected_item = files[choice - 1]
                        selected_path = selected_item["path"] if isinstance(selected_item, dict) else selected_item

                        if len(new_names) == 1:
                            res = rename_file(selected_path, new_names[0])
                            self.add_message(res["message"], False, save_to_db=False)
                        else:
                            pairs = []
                            selected_filename = selected_item.get("filename") if isinstance(selected_item, dict) else None
                            for i, old_name in enumerate([g.get("filename") for g in remaining_files]):
                                if i < len(new_names) and remaining_files[i].get("files"):
                                    pairs.append({"old_path": remaining_files[i]["files"][0], "new_name": new_names[i]})
                            if selected_filename in self.pending_file_action.get("files", []):
                                idx = self.pending_file_action.get("files", []).index(selected_filename)
                                if idx < len(new_names):
                                    pairs.append({"old_path": selected_path, "new_name": new_names[idx]})
                            if not pairs:
                                self.pending_file_action = {"action": "rename", "state": "need_new_name", "file_path": selected_path}
                                self.add_message(f"📝 What should '{Path(selected_path).name}' be renamed to?", False, save_to_db=False)
                                self._re_enable()
                                return
                            res = rename_multiple_files(pairs)
                            self.add_message(res["message"], False, save_to_db=False)
                        self.pending_file_action = None
                    else:
                        self.add_message(f"❌ Enter a number between 1 and {len(files)}", False, save_to_db=False)
                except ValueError:
                    self.add_message("❌ Enter a number or 'cancel'", False, save_to_db=False)

                self._re_enable()
                return

            # ── User selects from multiple files for MOVE ─────────────────────
            if action == "move" and state == "select_for_move":
                files = self.pending_file_action.get("files", [])
                destination = self.pending_file_action.get("destination")
                remaining_files = self.pending_file_action.get("remaining_files", [])

                if r in ("cancel", "c"):
                    self.add_message("❌ Move cancelled.", False, save_to_db=False)
                    self.pending_file_action = None
                    self._re_enable()
                    return

                try:
                    choice = int(r)
                    if 1 <= choice <= len(files):
                        selected_item = files[choice - 1]
                        selected_path = selected_item["path"] if isinstance(selected_item, dict) else selected_item
                        paths = [selected_path]

                        for group in remaining_files:
                            if group.get("files"):
                                paths.append(group["files"][0])

                        destination = _normalise_location(destination) or destination
                        res = move_multiple_files(paths, destination)
                        self.add_message(res["message"], False, save_to_db=False)
                        self.pending_file_action = None
                    else:
                        self.add_message(f"❌ Enter a number between 1 and {len(files)}", False, save_to_db=False)
                except ValueError:
                    self.add_message("❌ Enter a number or 'cancel'", False, save_to_db=False)

                self._re_enable()
                return

            # ── User provided location for SEARCH ─────────────────────────────
            if action == "search_location" and state == "need_search_location":
                filename = self.pending_file_action.get("files", [None])[0]
                search_mode = self.pending_file_action.get("search_mode", "regex")
                location = resolve_location(text)

                result = search_in_location(filename, location, mode=search_mode)
                if result["status"] in ("error", "not_found"):
                    self.add_message(result["message"], False, save_to_db=False)
                    self.pending_file_action = None
                else:
                    files_list = "\n".join(f"  {i}. {f}" for i, f in enumerate(result["files"][:20], 1))
                    extra = f"\n  … and {result['count'] - 20} more" if result["count"] > 20 else ""
                    loc_str = location if location else "all drives"
                    self.add_message(
                        f"🔍 Found {result['count']} file(s) matching '{filename}' in {loc_str}:\n\n{files_list}{extra}\n\n"
                        "Enter a number to act on a file, or 'cancel':",
                        False,
                        save_to_db=False,
                    )
                    self.pending_file_action = {
                        "action": "search_location",
                        "state": "select_action",
                        "files": result["files"],
                    }
                self._re_enable()
                return

            if action == "search_location" and state == "select_action":
                files = self.pending_file_action.get("files", [])

                if r in ("cancel", "c"):
                    self.add_message("❌ Cancelled.", False, save_to_db=False)
                    self.pending_file_action = None
                    self._re_enable()
                    return

                try:
                    choice = int(r)

                    if 1 <= choice <= len(files):
                        selected = files[choice - 1]

                        # AUTO OPEN FILE
                        self.add_message(
                            f"📂 Opening file...\n\n{selected}",
                            False,
                            save_to_db=False,
                        )

                        res = open_file(selected)

                        self.add_message(
                            res.get("message", "✅ File opened."),
                            False,
                            save_to_db=False,
                        )

                        self.pending_file_action = None

                    else:
                        self.add_message(
                            f"❌ Enter a number between 1 and {len(files)}",
                            False,
                            save_to_db=False,
                        )

                except ValueError:
                    self.add_message(
                        "❌ Enter a number or 'cancel'",
                        False,
                        save_to_db=False,
                    )

                self._re_enable()
                return

            # ── User picks operation (open/rename/move) on selected file ──────
            if action == "search_location" and state == "select_operation":
                file_path = self.pending_file_action.get("file_path")
                if r == "open":
                    res = open_file(file_path)
                    self.add_message(res["message"], False, save_to_db=False)
                    self.pending_file_action = None
                elif r == "rename":
                    self.add_message("📝 Enter the new filename:", False, save_to_db=False)
                    self.pending_file_action = {
                        "action": "rename",
                        "state": "need_new_name",
                        "file_path": file_path,
                    }
                elif r == "move":
                    self.add_message("📁 Enter destination folder:", False, save_to_db=False)
                    self.pending_file_action = {
                        "action": "move",
                        "state": "need_destination",
                        "files": [file_path],
                    }
                elif r in ("cancel", "c"):
                    self.add_message("❌ Cancelled.", False, save_to_db=False)
                    self.pending_file_action = None
                else:
                    self.add_message("❌ Type open, rename, move, or cancel", False, save_to_db=False)
                self._re_enable()
                return


        # ─────────────────────────────────────────────────────────────────────
        # NEW ADVANCED COMMAND (no pending state)
        # ─────────────────────────────────────────────────────────────────────
        result = handle_advanced_file_command(text, self.current_session_id)
        status = result.get("status")

        if status == "success":
            self.add_message(result["message"], False, save_to_db=False)

            data = result.get("data", {})
            found_files = data.get("files", [])

            if found_files:
                self.pending_file_action = {
                    "action": "search_location",
                    "state": "select_action",
                    "files": found_files,
                }

                self.add_message(
                    "\nEnter file number to open it, or type 'cancel':",
                    False,
                    save_to_db=False,
                )

        elif status == "error":
            self.add_message(result["message"], False, save_to_db=False)

        elif status in ("need_info", "need_new_name", "need_search_info"):
            pending = result.get("pending", {})
            pending["state"] = status
            self.pending_file_action = pending
            self.add_message(result["message"], False, save_to_db=False)

        elif status == "need_rename_location":
            pending = result.get("pending", {})
            pending["state"] = "need_rename_location"
            self.pending_file_action = pending
            self.add_message(result["message"], False, save_to_db=False)

        elif status == "move_search":
            pending = result.get("pending", {})
            files_to_find = pending.get("files", [])
            destination = pending.get("destination")

            self.add_message("🔍 Searching for file(s) to move...", False, save_to_db=False)
            groups = search_grouped(files_to_find, use_smart=True)
            self._remove_last_ai_bubble()

            result_state = finish_grouped_move(groups, destination)
            if result_state == "need_location":
                pending["state"] = "need_move_location"
                self.pending_file_action = pending

        elif status == "need_destination":
            pending = result.get("pending", {})
            pending["state"] = "need_destination"
            self.pending_file_action = pending
            self.add_message(result["message"], False, save_to_db=False)

        elif status == "need_search_location":
            pending = result.get("pending", {})
            pending["state"] = "need_search_location"
            self.pending_file_action = pending
            self.add_message(result["message"], False, save_to_db=False)

        elif status == "not_advanced":
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
            return

        self._re_enable()

    def _remove_last_ai_bubble(self):
        """Remove the last AI message bubble (e.g. 'Searching…' placeholders)."""
        idx = self.chat_layout.count() - 2
        if idx >= 0:
            item = self.chat_layout.itemAt(idx)
            if item and item.widget():
                item.widget().deleteLater()

    def _re_enable(self):
        """Re-enable input after sync operations."""
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()

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
        Central entry point for any text input - typed OR spoken.
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
            self._speech_popup = SpeechPopup(
                self,
                model_manager=self.model_manager,
                whisper_model_dir="models/whisper",
                wake_word_detector=self.wake_word_detector,
            )
            self._speech_popup.text_ready.connect(self._on_voice_text)
        self._speech_popup.show()

    def _on_voice_text(self, text: str):
        self.input.setText(text)
        self.add_message(
            "🎤 Voice input coming soon! "
            "When ready, speech will route through the same pipeline as typed messages.",
            False,
            save_to_db=False,
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
                self.current_session_id, dest_path, file_type, filename
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

    def on_back(self, checked=False):
        logger.info("ChatWindow back button clicked; returning to home page.")
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
