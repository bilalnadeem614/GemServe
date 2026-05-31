# gui/Chat_Bot.py
import sys, os
import logging
import re

from services.file_advanced_service import _normalise_location
from services.system_intent_service import handle_system_command, is_system_command
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QFileDialog,
    QMessageBox,
    QTextEdit,
)
from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QIcon
import shutil
import threading
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
        # Set when the last input came from voice so we can give a TTS ack
        self._last_input_was_voice = False
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
            pad = 18
            wrapper_h = max(54, new_h + pad)
            self.wrapper.setMinimumHeight(wrapper_h)
            self.wrapper.setMaximumHeight(wrapper_h)
            self.input_frame.setFixedHeight(wrapper_h + 36)
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
        mode = self.get_selected_mode()
        mode_name = "Fast Mode" if mode == "fast" else "Thinking Mode"
        self.add_message(f"🔄 Switched to {mode_name}", False, save_to_db=False)

    def get_selected_mode(self):
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
        self.current_session_id = None
        self.is_new_session = True
        self.pending_file_action = None
        self.title.setText("New Chat")
        self.clear_chat()
        self.files_container.setVisible(False)
        self.mode_combo.setCurrentIndex(0)
        print("✅ Ready for new session")

    def load_session(self, session_id):
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

    # ---------------- OVERWRITE CONFIRM HANDLER ----------------
    def _handle_overwrite_reply(self, text: str):
        """
        Handle y/n reply when a file-already-exists overwrite prompt is active.
        This is called from the earliest guard in on_send().
        """
        r = text.strip().lower()
        pending = self.pending_file_action

        if r not in ("y", "yes", "n", "no", "cancel"):
            self.add_message(
                "❌ Please type  y  to overwrite or  n  to cancel.",
                False, save_to_db=False,
            )
            # Keep pending_file_action intact so user can retry
            return

        filepath  = pending.get("filepath")
        filename  = pending.get("filename")
        save_path = pending.get("save_path")
        file_type = pending.get("file_type")
        headers   = pending.get("headers", [])
        rows      = pending.get("rows", [])
        content   = pending.get("content")
        title     = pending.get("title")
        filenames = pending.get("filenames", [])
        pending_messages = pending.get("messages", [])

        from services.file_service import create_file as create_simple_file

        def _process_remaining(remaining_files, base_path, messages=None):
            messages = messages or []
            for fname in remaining_files:
                next_result = create_simple_file(fname, custom_path=base_path)
                if (
                    next_result.get("status") == "confirm"
                    and next_result.get("action") == "overwrite"
                ):
                    return {
                        "status": "overwrite_confirm",
                        "message": next_result["message"],
                        "data": {
                            "filepath": next_result.get("path") or os.path.join(base_path, fname),
                            "filename": fname,
                            "save_path": base_path,
                            "filenames": remaining_files,
                            "operation": "create",
                        },
                        "messages": messages,
                    }
                messages.append(next_result["message"])
            return {"status": "success", "messages": messages}

        if r in ("n", "no", "cancel"):
            if not filenames or not filename:
                self.add_message(
                    "❌ Skipped - file was not overwritten.",
                    False, save_to_db=False,
                )
                self.pending_file_action = None
                return

            remaining = [f for f in filenames if f != filename]
            messages = pending_messages + [f"❌ Skipped existing file: {filename}"]
            if remaining:
                result = _process_remaining(remaining, save_path, messages)
                if result["status"] == "overwrite_confirm":
                    self.pending_file_action = {
                        "state":     "overwrite_confirm",
                        "filepath":  result["data"]["filepath"],
                        "filename":  result["data"]["filename"],
                        "save_path": result["data"]["save_path"],
                        "filenames": result["data"]["filenames"],
                        "messages":  result.get("messages", []),
                        "operation": "create",
                    }
                    self.add_message(result["message"], False, save_to_db=False)
                    return
                self.add_message("\n\n".join(result["messages"]), False, save_to_db=False)
            else:
                self.add_message("\n\n".join(messages), False, save_to_db=False)
            self.pending_file_action = None
            return

        try:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            self.add_message(
                f"❌ Could not remove existing file: {e}", False, save_to_db=False,
            )
            self.pending_file_action = None
            return

        if file_type:
            from services.file_creator_service import (
                create_csv, create_xlsx, create_docx, create_pdf, create_txt,
            )

            creators = {
                "csv":  lambda: create_csv(filename, headers, rows, save_path),
                "xlsx": lambda: create_xlsx(filename, headers, rows, title, save_path),
                "docx": lambda: create_docx(
                    filename, content, title,
                    headers if headers else None,
                    rows if rows else None,
                    save_path,
                ),
                "pdf":  lambda: create_pdf(
                    filename, content, title,
                    headers if headers else None,
                    rows if rows else None,
                    save_path,
                ),
                "txt":  lambda: create_txt(filename, content or "", save_path),
            }
            creator = creators.get(file_type)
            if creator:
                result = creator()
            else:
                result = {"status": "error", "message": f"❌ Unknown file type: {file_type}"}
        else:
            if not save_path and filepath:
                save_path = os.path.dirname(filepath)
            result = create_simple_file(filename, custom_path=save_path)

        remaining = [f for f in filenames if f != filename]
        messages = pending_messages + [result["message"]]
        if remaining:
            result = _process_remaining(remaining, save_path, messages)
            if result["status"] == "overwrite_confirm":
                self.pending_file_action = {
                    "state":     "overwrite_confirm",
                    "filepath":  result["data"]["filepath"],
                    "filename":  result["data"]["filename"],
                    "save_path": result["data"]["save_path"],
                    "filenames": result["data"]["filenames"],
                    "messages":  result.get("messages", []),
                    "operation": "create",
                }
                self.add_message(result["message"], False, save_to_db=False)
                return
            self.add_message("\n\n".join(result["messages"]), False, save_to_db=False)
            self.pending_file_action = None
            return

        self.add_message(result["message"], False, save_to_db=False)
        self.pending_file_action = None

    # ---------------- MULTI-FILE DELETE HANDLER ----------------
    def _handle_multi_delete(self, text: str):
        """
        Handle multi-file deletion: show numbered list, confirm each,
        then delete all confirmed files.
        state flow:
          "delete_select"  → user picks which files (or 'all')
          "delete_confirm" → user types yes/no
        """
        from services.file_service import delete_file as svc_delete_file
        from services.llm_file_service import _smart_find

        state   = self.pending_file_action.get("state", "")
        r       = text.strip().lower()

        # ── state: delete_select ─────────────────────────────────────────
        if state == "delete_select":
            files = self.pending_file_action.get("files", [])

            if r in ("cancel", "c", "no"):
                self.add_message("❌ Deletion cancelled.", False, save_to_db=False)
                self.pending_file_action = None
                return

            if r == "all":
                # Confirm deletion of every file in the list
                files_list = "\n".join(
                    f"  {i}. {f}" for i, f in enumerate(files, 1)
                )
                self.pending_file_action = {
                    "state":     "delete_confirm",
                    "files":     files,
                    "operation": "delete",
                }
                self.add_message(
                    f"🗑️ Delete ALL {len(files)} files?\n\n{files_list}\n\n"
                    "Type  yes  to confirm or  no  to cancel.",
                    False, save_to_db=False,
                )
                return

            # Parse comma-separated numbers like "1,3" or "1 3 2"
            try:
                indices = [
                    int(x.strip()) - 1
                    for x in re.split(r"[,\s]+", r)
                    if x.strip().isdigit()
                ]
            except Exception:
                indices = []

            if not indices:
                self.add_message(
                    "❌ Enter file numbers (e.g. 1,3), 'all', or 'cancel'.",
                    False, save_to_db=False,
                )
                return

            selected = []
            bad = []
            for idx in indices:
                if 0 <= idx < len(files):
                    selected.append(files[idx])
                else:
                    bad.append(idx + 1)

            if bad:
                self.add_message(
                    f"❌ Invalid number(s): {bad}. "
                    f"Choose between 1 and {len(files)}.",
                    False, save_to_db=False,
                )
                return

            files_list = "\n".join(f"  • {f}" for f in selected)
            self.pending_file_action = {
                "state":     "delete_confirm",
                "files":     selected,
                "operation": "delete",
            }
            self.add_message(
                f"🗑️ Delete {len(selected)} file(s)?\n\n{files_list}\n\n"
                "Type  yes  to confirm or  no  to cancel.",
                False, save_to_db=False,
            )
            return

        # ── state: delete_confirm ─────────────────────────────────────────
        if state == "delete_confirm":
            files = self.pending_file_action.get("files") or []
            if not files:
                single = self.pending_file_action.get("file")
                if single:
                    files = [single]
            if not files:
                self.add_message("❌ No files to delete.", False, save_to_db=False)
                self.pending_file_action = None
                return

            if r in ("yes", "y"):
                success_msgs = []
                fail_msgs    = []
                for fpath in files:
                    result = svc_delete_file(fpath)
                    if result.get("status") == "success":
                        success_msgs.append(f"✅ {os.path.basename(fpath)}")
                    else:
                        fail_msgs.append(
                            f"❌ {os.path.basename(fpath)}: {result.get('message','')}"
                        )

                parts = []
                if success_msgs:
                    parts.append(
                        f"🗑️ Deleted {len(success_msgs)} file(s):\n"
                        + "\n".join(success_msgs)
                    )
                if fail_msgs:
                    parts.append(
                        f"⚠️ Failed {len(fail_msgs)} file(s):\n"
                        + "\n".join(fail_msgs)
                    )
                self.add_message("\n\n".join(parts), False, save_to_db=False)

            elif r in ("no", "n", "cancel"):
                self.add_message("❌ Deletion cancelled.", False, save_to_db=False)
            else:
                self.add_message(
                    "❌ Please type  yes  to confirm or  no  to cancel.",
                    False, save_to_db=False,
                )
                return  # keep state

            self.pending_file_action = None

    # ---------------- MULTI-FILE RENAME HANDLER ----------------
    def _handle_multi_rename(self, text: str):
        """
        Handle multi-file rename with states:
          "rename_select"   → user picks which file from ambiguous list
          "rename_new_name" → user provides new name(s)
          "rename_confirm"  → user confirms the rename plan
        """
        from services.file_advanced_service import rename_file, rename_multiple_files
        from pathlib import Path

        state = self.pending_file_action.get("state", "")
        r     = text.strip().lower()

        # ── state: rename_select ──────────────────────────────────────────
        if state == "rename_select":
            files = self.pending_file_action.get("files", [])

            if r in ("cancel", "c"):
                self.add_message("❌ Rename cancelled.", False, save_to_db=False)
                self.pending_file_action = None
                return

            try:
                choice = int(r)
                if not (1 <= choice <= len(files)):
                    raise ValueError
            except ValueError:
                self.add_message(
                    f"❌ Enter a number between 1 and {len(files)}, or 'cancel'.",
                    False, save_to_db=False,
                )
                return

            selected_path = files[choice - 1]
            self.pending_file_action = {
                "state":     "rename_new_name",
                "file_path": selected_path,
                "operation": "rename",
            }
            self.add_message(
                f"📝 Rename  '{Path(selected_path).name}'  to what?\n"
                "(Type the new filename, or 'cancel')",
                False, save_to_db=False,
            )
            return

        # ── state: rename_new_name ────────────────────────────────────────
        if state == "rename_new_name":
            if r in ("cancel", "c"):
                self.add_message("❌ Rename cancelled.", False, save_to_db=False)
                self.pending_file_action = None
                return

            new_name  = text.strip()
            file_path = self.pending_file_action.get("file_path")

            # Ask for confirmation
            self.pending_file_action = {
                "state":     "rename_confirm",
                "file_path": file_path,
                "new_name":  new_name,
                "operation": "rename",
            }
            self.add_message(
                f"Rename  '{os.path.basename(file_path)}'  →  '{new_name}'?\n\n"
                "Type  yes  to confirm or  no  to cancel.",
                False, save_to_db=False,
            )
            return

        # ── state: rename_confirm ─────────────────────────────────────────
        if state == "rename_confirm":
            if r in ("no", "n", "cancel"):
                self.add_message("❌ Rename cancelled.", False, save_to_db=False)
                self.pending_file_action = None
                return

            if r in ("yes", "y"):
                file_path = self.pending_file_action.get("file_path")
                new_name  = self.pending_file_action.get("new_name")
                force     = self.pending_file_action.get("force_overwrite", False)
                result    = rename_file(file_path, new_name, overwrite=force)
                if result["status"] == "confirm_overwrite" and not force:
                    self.pending_file_action["force_overwrite"] = True
                    self.add_message(result["message"], False, save_to_db=False)
                    return
                self.add_message(result["message"], False, save_to_db=False)
                self.pending_file_action = None
                return

            self.add_message(
                "❌ Please type  yes  to confirm or  no  to cancel.",
                False, save_to_db=False,
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
                if result.get("action") == "overwrite":
                    filepath = result.get("path") or data.get("filepath")
                    filename = os.path.basename(filepath) if filepath else None
                    save_path = data.get("save_path") or (os.path.dirname(filepath) if filepath else None)
                    self.pending_file_action = {
                        "state":     "overwrite_confirm",
                        "filepath":  filepath,
                        "filename":  filename,
                        "save_path": save_path,
                        "filenames": data.get("filenames", [filename] if filename else []),
                        "operation": data.get("operation", "create"),
                    }
                    self.add_message(result["message"], False, save_to_db=False)
                else:
                    files = data.get("files", [])
                    file_to_delete = data.get("file") or (files[0] if files else None)
                    self.pending_file_action = {
                        "state":     "delete_confirm",
                        "file":      file_to_delete,
                        "files":     files,
                        "operation": "delete",
                    }
                    self.add_message(result["message"], False, save_to_db=False)

            # ── NEW: surface overwrite_confirm from process_file_response ──
            elif result["status"] == "overwrite_confirm":
                data = result.get("data", {})
                self.pending_file_action = {
                    "state":     "overwrite_confirm",
                    "filepath":  data.get("filepath"),
                    "filename":  data.get("filename"),
                    "save_path": data.get("save_path"),
                    "file_type": data.get("file_type"),
                    "headers":   data.get("headers", []),
                    "rows":      data.get("rows", []),
                    "content":   data.get("content"),
                    "title":     data.get("title"),
                    "filenames": data.get("filenames", []),
                    "operation": data.get("operation", "create"),
                }
                self.add_message(result["message"], False, save_to_db=False)

            elif result["status"] == "ask_location":
                self.pending_file_action = {
                    "state":     "location",
                    "filename":  self.pending_file_action.get("filename"),
                    "filenames": self.pending_file_action.get("filenames", []),
                    "operation": "create",
                }
                self.add_message(result["message"], False, save_to_db=False)

            elif result["status"] == "ask_custom_path":
                self.pending_file_action = {
                    "state":     "custom_path",
                    "filename":  self.pending_file_action.get("filename"),
                    "filenames": self.pending_file_action.get("filenames", []),
                    "operation": "create",
                }
                self.add_message(result["message"], False, save_to_db=False)

            elif result["status"] == "error" and not result.get("handled"):
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
            data      = result.get("data", {})
            operation = data.get("operation", "")

            # ── Multi-file DELETE: show a select-then-confirm flow ──────────
            if operation == "delete" and len(data.get("files", [])) > 1:
                files      = data["files"]
                files_list = "\n".join(
                    f"  {i}. {f}" for i, f in enumerate(files, 1)
                )
                self.pending_file_action = {
                    "state":     "delete_select",
                    "files":     files,
                    "operation": "delete",
                }
                self.add_message(
                    f"📂 Found {len(files)} file(s) matching "
                    f"'{data.get('filename', '')}':\n\n{files_list}\n\n"
                    "Enter file number(s) to delete (e.g. 1,3), 'all', or 'cancel':",
                    False, save_to_db=False,
                )

            # ── Multi-file RENAME: show a select flow ───────────────────────
            elif operation == "rename" and len(data.get("files", [])) > 1:
                files      = data["files"]
                files_list = "\n".join(
                    f"  {i}. {f}" for i, f in enumerate(files, 1)
                )
                self.pending_file_action = {
                    "state":     "rename_select",
                    "files":     files,
                    "operation": "rename",
                }
                self.add_message(
                    f"📂 Found {len(files)} file(s) matching "
                    f"'{data.get('filename', '')}':\n\n{files_list}\n\n"
                    "Enter the number of the file you want to rename, or 'cancel':",
                    False, save_to_db=False,
                )

            else:
                # Generic select (single-file open, etc.)
                self.pending_file_action = {
                    "state":     "select",
                    "files":     data.get("files", []),
                    "operation": operation,
                    "filename":  data.get("filename"),
                }
                self.add_message(result["message"], False, save_to_db=False)

        elif result["status"] == "confirm":
            data = result.get("data", {})
            files = data.get("files", [])

            # ── Multi-file DELETE confirm ───────────────────────────────────
            if len(files) > 1:
                files_list = "\n".join(
                    f"  {i}. {f}" for i, f in enumerate(files, 1)
                )
                self.pending_file_action = {
                    "state":     "delete_confirm",
                    "files":     files,
                    "operation": "delete",
                }
                self.add_message(
                    f"🗑️ Delete these {len(files)} file(s)?\n\n{files_list}\n\n"
                    "Type  yes  to confirm or  no  to cancel.",
                    False, save_to_db=False,
                )
            else:
                # Single-file delete
                self.pending_file_action = {
                    "state":     "delete_confirm",
                    "file":      files[0] if files else None,
                    "files":     files,
                    "operation": "delete",
                }
                self.add_message(result["message"], False, save_to_db=False)

        # ── NEW: overwrite_confirm from handle_llm_file_command ────────────
        elif result["status"] == "overwrite_confirm":
            data = result.get("data", {})
            self.pending_file_action = {
                "state":     "overwrite_confirm",
                "filepath":  data.get("filepath"),
                "filename":  data.get("filename"),
                "save_path": data.get("save_path"),
                "file_type": data.get("file_type"),
                "headers":   data.get("headers", []),
                "rows":      data.get("rows", []),
                "content":   data.get("content"),
                "title":     data.get("title"),
            }
            self.add_message(result["message"], False, save_to_db=False)

        elif result["status"] == "ask_location":
            data = result.get("data", {})
            self.pending_file_action = {
                "state":     "location",
                "filename":  data.get("filename"),
                "filenames": data.get("filenames", []),
                "operation": "create",
            }
            self.add_message(result["message"], False, save_to_db=False)

    # ---------------- SEND MESSAGE ----------------
    def on_send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return

        # If this input came from voice, give a brief TTS acknowledgement.
        if getattr(self, "_last_input_was_voice", False):
            try:
                self._speak_nonblocking("Working on it")
            finally:
                self._last_input_was_voice = False

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

        # ═══════════════════════════════════════════════════════════════════
        # EARLIEST GUARD — catch ALL pending dialog replies before any
        # routing or LLM calls.  This is what stops "y", "n", "1", "2" from
        # reaching the LLM router.
        # ═══════════════════════════════════════════════════════════════════
        if self.pending_file_action:
            _state  = self.pending_file_action.get("state", "")
            _action = self.pending_file_action.get("action", "")
            _op     = self.pending_file_action.get("operation", "")

            _DIALOG_STATES = {
                # overwrite
                "overwrite_confirm",
                # create-file location picking
                "location", "need_save_location", "custom_path", "ask_custom_path",
                # basic file ops
                "select", "delete_confirm",
                # multi-delete flow
                "delete_select",
                # multi-rename flow
                "rename_select", "rename_new_name", "rename_confirm",
            }

            if _state in _DIALOG_STATES:
                if _state == "overwrite_confirm":
                    self._handle_overwrite_reply(text)

                elif _state in ("delete_select", "delete_confirm") and _op == "delete":
                    self._handle_multi_delete(text)

                elif _state in ("rename_select", "rename_new_name", "rename_confirm"):
                    self._handle_multi_rename(text)

                elif _action in ("rename", "move", "search_location"):
                    self._handle_advanced_file(text)

                else:
                    self.handle_file_operation(text)

                self._re_enable()
                return

            # Advanced file ops that use their own state machine
            if _action in ("rename", "move", "search_location"):
                self._handle_advanced_file(text)
                return

            # Tag-select is handled below in its own block
            if _action == "tag_select" and _state == "await_choice":
                pass  # fall through to tag_select block

            # Pending create / generic file ops
            elif _op or _action == "create_file":
                self.handle_file_operation(text)
                self._re_enable()
                return
        # ═══════════════════════════════════════════════════════════════════
        # END EARLIEST GUARD
        # ═══════════════════════════════════════════════════════════════════

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
        # HANDLE PENDING FILE ACTIONS (tag_select etc.)
        # ─────────────────────────────────────────────
        if self.pending_file_action:
            action = self.pending_file_action.get("action")
            state  = self.pending_file_action.get("state", "")

            # TAG SELECTION FROM MULTIPLE MATCHES
            if action == "tag_select" and state == "await_choice":
                choice = text.strip().lower()
                if choice in ("cancel", "c"):
                    self.add_message("❌ Tagging cancelled.", False, save_to_db=False)
                    self.pending_file_action = None
                    self._re_enable()
                    return

                try:
                    idx   = int(choice) - 1
                    files = self.pending_file_action.get("files", [])
                    if idx < 0 or idx >= len(files):
                        raise ValueError

                    file_path  = files[idx]
                    tag_action = self.pending_file_action.get("tag_action")
                    tags       = self.pending_file_action.get("tags", [])

                    from db.tag_db_json import save_tags, get_tags
                    from services.file_tag_service import auto_generate_tags

                    if tag_action == "manual_tag":
                        if not tags:
                            self.add_message("❌ No tags to save.", False, save_to_db=False)
                        else:
                            save_tags(file_path, tags, source="user")
                            self.add_message(
                                f"✅ Tags added!\n\n"
                                f"📄 File: {os.path.basename(file_path)}\n"
                                f"🏷️ Tags: {', '.join(tags)}",
                                False, save_to_db=False,
                            )

                    elif tag_action == "auto_tag":
                        generated_tags = auto_generate_tags(file_path)
                        if not generated_tags:
                            self.add_message(
                                "⚠️ No tags could be generated for this file.",
                                False, save_to_db=False,
                            )
                        else:
                            save_tags(file_path, generated_tags, source="auto")
                            self.add_message(
                                f"✅ Auto tags generated!\n\n"
                                f"📄 File: {os.path.basename(file_path)}\n"
                                f"🏷️ Tags: {', '.join(generated_tags)}",
                                False, save_to_db=False,
                            )

                    elif tag_action == "show_tags":
                        current_tags = get_tags(file_path)
                        self.add_message(
                            f"🏷️ Tags for {os.path.basename(file_path)}:\n\n"
                            + (", ".join(current_tags) if current_tags else "No tags found"),
                            False, save_to_db=False,
                        )

                    else:
                        self.add_message("❌ Unknown tag action.", False, save_to_db=False)

                    self.pending_file_action = None
                    self._re_enable()
                    return

                except ValueError:
                    self.add_message(
                        "❌ Enter a valid number or 'cancel'",
                        False, save_to_db=False,
                    )
                    self._re_enable()
                    return

            # SAVE LOCATION SELECTION (create_file pending)
            if action == "create_file" and state == "need_save_location":
                choice       = text.strip()
                user_profile = os.environ.get("USERPROFILE", "")
                location_map = {
                    "1": os.path.join(user_profile, "Desktop"),
                    "2": os.path.join(user_profile, "Documents"),
                    "3": os.path.join(user_profile, "Downloads"),
                }
                save_location = location_map.get(choice, choice)

                pending = self.pending_file_action

                from services.file_creator_service import (
                    create_csv, create_xlsx, create_docx, create_pdf, create_txt,
                )

                file_type = pending.get("file_type")
                filename  = pending.get("filename")
                headers   = pending.get("headers", [])
                rows      = pending.get("rows", [])
                content   = pending.get("content")
                title     = pending.get("title")

                if file_type == "csv":
                    result = create_csv(filename, headers, rows, save_location)
                elif file_type == "xlsx":
                    result = create_xlsx(filename, headers, rows, title, save_location)
                elif file_type == "docx":
                    result = create_docx(filename, content, title, headers, rows, save_location)
                elif file_type == "pdf":
                    result = create_pdf(filename, content, title, headers, rows, save_location)
                elif file_type == "txt":
                    result = create_txt(filename, content, save_location)
                else:
                    result = {
                        "status":  "error",
                        "message": f"❌ Unsupported file type: {file_type}"
                    }

                # ── Surface overwrite prompt if file exists ─────────────────
                if result.get("status") == "exists":
                    self.pending_file_action = {
                        "state":     "overwrite_confirm",
                        "filepath":  result.get("filepath"),
                        "filename":  filename,
                        "save_path": save_location,
                        "file_type": file_type,
                        "headers":   headers,
                        "rows":      rows,
                        "content":   content,
                        "title":     title,
                    }
                    self.add_message(result["message"], False, save_to_db=False)
                else:
                    self.add_message(result["message"], False, save_to_db=False)
                    self.pending_file_action = None

                self._re_enable()
                return

        # ─────────────────────────────────────────────
        # 4. STRUCTURED FILE CREATION (docx/xlsx/csv/pdf/txt)
        # ─────────────────────────────────────────────
        from services.file_creator_service import (
            is_file_creation_request,
            handle_file_creation,
        )

        # Multi-file create → general file operation handler
        if re.search(r"\b(create|make|new)\b", text, re.I) and len(
            re.findall(r"\b[\w\-. ]+?\.(?:docx|xlsx|csv|pdf|txt)\b", text, re.I)
        ) > 1:
            self.handle_file_operation(text)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
            return

        if is_file_creation_request(text):
            result = handle_file_creation(text)
            if result.get("status") == "need_save_location":
                pending = result.get("pending", {})
                pending["state"] = "location"
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
        # FILE TAGGING
        # ─────────────────────────────────────────────
        from services.file_tag_service import (
            is_file_tag_command,
            handle_file_tag_command,
        )

        if is_file_tag_command(text):
            from services.file_advanced_service import search_in_location
            from db.tag_db_json import save_tags, get_tags

            def find_file_func(filename):
                result = search_in_location(filename, None, mode="regex")
                return result.get("files", [])

            def save_tags_func(file_path, tags, source="user"):
                save_tags(file_path, tags, source=source)

            def get_tags_func(file_path):
                return get_tags(file_path)

            result = handle_file_tag_command(
                text,
                find_file_func,
                save_tags_func,
                get_tags_func,
            )

            if result.get("status") == "select":
                self.pending_file_action = {
                    "action":     "tag_select",
                    "state":      "await_choice",
                    "files":      result["data"]["files"],
                    "tag_action": result["data"].get("action"),
                    "tags":       result["data"].get("tags", []),
                }

            self.add_message(result["message"], False, save_to_db=False)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
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
        # 7. LLM FILE OPERATION PENDING REPLY
        # ─────────────────────────────────────────────
        if self.pending_file_action and self.pending_file_action.get("operation"):
            self.handle_file_operation(text)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
            return

        # ─────────────────────────────────────────────
        # 8. ROUTE via regex (file op vs normal chat)
        # ─────────────────────────────────────────────
        mode = self.get_selected_mode()

        self.add_message("Routing...", False, save_to_db=False)
        self.router_worker = RouterWorker(text, mode)
        self.router_worker.finished.connect(
            lambda is_file: self._after_routing(text, mode, is_file)
        )
        self.router_worker.error.connect(
            lambda _: self._after_routing(text, mode, False)
        )
        self.router_worker.start()

    # ---------------- ADVANCED FILE HANDLER ----------------
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

        def resolve_location(value: str):
            raw = (value or "").strip()
            key = raw.lower()
            user_profile = os.environ.get("USERPROFILE", "")
            shortcut_map = {
                "1":         None,
                "all":       None,
                "2":         os.path.join(user_profile, "Desktop"),
                "desktop":   os.path.join(user_profile, "Desktop"),
                "3":         os.path.join(user_profile, "Documents"),
                "documents": os.path.join(user_profile, "Documents"),
                "4":         os.path.join(user_profile, "Downloads"),
                "downloads": os.path.join(user_profile, "Downloads"),
            }
            return shortcut_map.get(key, _normalise_location(raw))

        def search_grouped(files_to_find, location=None, use_smart=False):
            groups = []
            for fname in files_to_find:
                if use_smart:
                    result = search_in_location(fname, None, mode="regex")
                    found  = result.get("files", [])
                else:
                    result = search_in_location(fname, location, mode="regex")
                    found  = result.get("files", [])
                groups.append({"filename": fname, "files": found})
            return groups

        def build_ambiguous_message(groups, operation):
            option_map = []
            lines      = []
            idx        = 1
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
            missing   = [g["filename"] for g in groups if len(g["files"]) == 0]
            ambiguous = [g for g in groups if len(g["files"]) > 1]

            if missing:
                self.add_message(
                    f"❌ Could not find: {', '.join(missing)}\n\n"
                    "📂 Where are these files located?\n\n"
                    "  • Desktop\n  • Documents\n  • Downloads\n"
                    "  • C drive / D drive\n  • Full path\n  • all",
                    False, save_to_db=False,
                )
                return "need_location"

            if not ambiguous:
                paths       = [g["files"][0] for g in groups]
                destination = _normalise_location(destination) or destination
                res         = move_multiple_files(paths, destination)
                self.add_message(res["message"], False, save_to_db=False)
                self.pending_file_action = None
                return "done"

            message, option_map = build_ambiguous_message(ambiguous, "move")
            self.add_message(message, False, save_to_db=False)
            self.pending_file_action = {
                "action":            "move",
                "state":             "select_for_move",
                "files":             option_map,
                "destination":       destination,
                "remaining_files":   [g for g in groups if len(g["files"]) == 1],
                "ambiguous_names":   [g["filename"] for g in ambiguous],
                "resolved_paths":    [],
                "resolved_filenames": [],
            }
            return "ambiguous"

        # ─────────────────────────────────────────────────────────────────────
        # HANDLE PENDING ADVANCED ACTION
        # ─────────────────────────────────────────────────────────────────────
        if self.pending_file_action:
            action = self.pending_file_action.get("action")
            state  = self.pending_file_action.get("state", "")
            r      = text.strip().lower()

            # ── rename: user provided location ───────────────────────────────
            if action == "rename" and state == "need_rename_location":
                files_to_find = self.pending_file_action.get("files", [])
                new_names     = self.pending_file_action.get("new_names", [])
                location      = resolve_location(text)

                self.add_message("🔍 Searching for files…", False, save_to_db=False)
                groups = search_grouped(files_to_find, location, use_smart=False)
                self._remove_last_ai_bubble()

                missing   = [g["filename"] for g in groups if len(g["files"]) == 0]
                ambiguous = [g for g in groups if len(g["files"]) > 1]

                if missing:
                    self.add_message(
                        f"❌ Could not find: {', '.join(missing)}\n\nCheck the filename and try again.",
                        False, save_to_db=False,
                    )
                    self.pending_file_action = None
                elif not ambiguous:
                    pairs = []
                    for i, group in enumerate(groups):
                        if i < len(new_names):
                            pairs.append({"old_path": group["files"][0], "new_name": new_names[i]})
                    if len(pairs) == 1:
                        res = rename_file(pairs[0]["old_path"], pairs[0]["new_name"])
                    else:
                        res = rename_multiple_files(pairs)

                    if res["status"] == "confirm_overwrite":
                        new_name = pairs[0]["new_name"] if len(pairs) == 1 else os.path.basename(res.get("new_path", ""))
                        self.pending_file_action = {
                            "action":         "rename",
                            "state":          "rename_confirm",
                            "file_path":      res.get("old_path"),
                            "new_name":       new_name,
                            "force_overwrite": True,
                        }
                        self.add_message(res["message"], False, save_to_db=False)
                    else:
                        self.add_message(res["message"], False, save_to_db=False)
                        self.pending_file_action = None
                else:
                    message, option_map = build_ambiguous_message(ambiguous, "rename")
                    self.add_message(message, False, save_to_db=False)
                    self.pending_file_action = {
                        "action":          "rename",
                        "state":           "select_for_rename",
                        "files":           option_map,
                        "new_names":       new_names,
                        "remaining_files": [g for g in groups if len(g["files"]) == 1],
                        "original_files":  [g["filename"] for g in groups],
                    }

                self._re_enable()
                return

            # ── move: user provided location ──────────────────────────────────
            if action == "move" and state == "need_move_location":
                files_to_find = self.pending_file_action.get("files", [])
                destination   = self.pending_file_action.get("destination")
                location      = resolve_location(text)

                self.add_message("🔍 Searching for files…", False, save_to_db=False)
                groups = search_grouped(files_to_find, location, use_smart=False)
                self._remove_last_ai_bubble()

                result_state = finish_grouped_move(groups, destination)
                if result_state == "need_location":
                    self.pending_file_action = {
                        "action":      "move",
                        "state":       "need_move_location",
                        "files":       files_to_find,
                        "destination": destination,
                    }

                self._re_enable()
                return

            # ── move: user provided destination ───────────────────────────────
            if action == "move" and state == "need_destination":
                destination   = _normalise_location(text.strip()) or text.strip()
                files_to_find = self.pending_file_action.get("files", [])

                self.add_message("🔍 Searching for files…", False, save_to_db=False)
                groups = search_grouped(files_to_find, use_smart=True)
                self._remove_last_ai_bubble()

                result_state = finish_grouped_move(groups, destination)
                if result_state == "need_location":
                    self.pending_file_action = {
                        "action":      "move",
                        "state":       "need_move_location",
                        "files":       files_to_find,
                        "destination": destination,
                    }

                self._re_enable()
                return

            # ── rename: user provided new name ────────────────────────────────
            if action == "rename" and state == "need_new_name":
                new_name  = text.strip()
                old_path  = self.pending_file_action.get("file_path")
                res       = rename_file(old_path, new_name)
                self.add_message(res["message"], False, save_to_db=False)
                self.pending_file_action = None
                self._re_enable()
                return

            # ── rename: user selects from multiple matches ─────────────────────
            if action == "rename" and state == "select_for_rename":
                files            = self.pending_file_action.get("files", [])
                new_names        = self.pending_file_action.get("new_names", [])
                remaining_files  = self.pending_file_action.get("remaining_files", [])

                if r in ("cancel", "c"):
                    self.add_message("❌ Rename cancelled.", False, save_to_db=False)
                    self.pending_file_action = None
                    self._re_enable()
                    return

                try:
                    choice = int(r)
                    if 1 <= choice <= len(files):
                        selected_item = files[choice - 1]
                        selected_path = (
                            selected_item["path"]
                            if isinstance(selected_item, dict)
                            else selected_item
                        )

                        if len(new_names) == 1:
                            res = rename_file(selected_path, new_names[0])
                            if res["status"] == "confirm_overwrite":
                                self.pending_file_action = {
                                    "action":         "rename",
                                    "state":          "rename_confirm",
                                    "file_path":      res.get("old_path", selected_path),
                                    "new_name":       new_names[0],
                                    "force_overwrite": True,
                                }
                                self.add_message(res["message"], False, save_to_db=False)
                                self._re_enable()
                                return
                            self.add_message(res["message"], False, save_to_db=False)
                        else:
                            pairs = []
                            original_files  = self.pending_file_action.get("original_files", [])
                            selected_filename = (
                                selected_item.get("filename")
                                if isinstance(selected_item, dict)
                                else None
                            )
                            for group in remaining_files:
                                filename = group.get("filename")
                                if filename in original_files:
                                    idx = original_files.index(filename)
                                    if idx < len(new_names) and group.get("files"):
                                        pairs.append({
                                            "old_path": group["files"][0],
                                            "new_name": new_names[idx],
                                        })
                            if selected_filename and selected_filename in original_files:
                                idx = original_files.index(selected_filename)
                                if idx < len(new_names):
                                    pairs.append({
                                        "old_path": selected_path,
                                        "new_name": new_names[idx],
                                    })
                            if not pairs:
                                self.pending_file_action = {
                                    "action":    "rename",
                                    "state":     "need_new_name",
                                    "file_path": selected_path,
                                }
                                self.add_message(
                                    f"📝 What should '{Path(selected_path).name}' be renamed to?",
                                    False, save_to_db=False,
                                )
                                self._re_enable()
                                return
                            res = rename_multiple_files(pairs)
                            if res["status"] == "confirm_overwrite":
                                self.pending_file_action = {
                                    "action":         "rename",
                                    "state":          "rename_confirm",
                                    "file_path":      res.get("old_path", selected_path),
                                    "new_name":       Path(res.get("new_path", selected_path)).name,
                                    "force_overwrite": True,
                                }
                                self.add_message(res["message"], False, save_to_db=False)
                                self._re_enable()
                                return
                            self.add_message(res["message"], False, save_to_db=False)
                        self.pending_file_action = None
                    else:
                        self.add_message(
                            f"❌ Enter a number between 1 and {len(files)}",
                            False, save_to_db=False,
                        )
                except ValueError:
                    self.add_message(
                        "❌ Enter a number or 'cancel'", False, save_to_db=False,
                    )

                self._re_enable()
                return

            # ── move: user selects from multiple matches ───────────────────────
            if action == "move" and state == "select_for_move":
                files           = self.pending_file_action.get("files", [])
                destination     = self.pending_file_action.get("destination")
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
                        selected_path = (
                            selected_item["path"]
                            if isinstance(selected_item, dict)
                            else selected_item
                        )
                        selected_filename = (
                            selected_item["filename"]
                            if isinstance(selected_item, dict)
                            else Path(selected_path).name
                        )

                        resolved_paths = self.pending_file_action.get("resolved_paths", [])
                        resolved_filenames = self.pending_file_action.get(
                            "resolved_filenames", []
                        )
                        if selected_path not in resolved_paths:
                            resolved_paths.append(selected_path)
                        if selected_filename not in resolved_filenames:
                            resolved_filenames.append(selected_filename)

                        ambiguous_names = self.pending_file_action.get("ambiguous_names", [])
                        remaining_ambiguous = [
                            name for name in ambiguous_names if name not in resolved_filenames
                        ]

                        if remaining_ambiguous:
                            next_name = remaining_ambiguous[0]
                            next_options = [
                                item for item in files
                                if isinstance(item, dict) and item.get("filename") == next_name
                            ]
                            option_lines = [
                                f"  {idx + 1}. {item['path']}"
                                for idx, item in enumerate(next_options)
                            ]
                            self.add_message(
                                f"📂 Multiple locations found for '{next_name}'. Choose the correct file:\n"
                                + "\n".join(option_lines)
                                + "\n\nEnter number or 'cancel':",
                                False, save_to_db=False,
                            )
                            self.pending_file_action.update({
                                "files": next_options,
                                "resolved_paths": resolved_paths,
                                "resolved_filenames": resolved_filenames,
                            })
                            self._re_enable()
                            return

                        paths = resolved_paths[:]
                        for group in remaining_files:
                            if group.get("files"):
                                paths.append(group["files"][0])

                        destination = _normalise_location(destination) or destination
                        res = move_multiple_files(paths, destination)
                        self.add_message(res["message"], False, save_to_db=False)
                        self.pending_file_action = None
                    else:
                        self.add_message(
                            f"❌ Enter a number between 1 and {len(files)}",
                            False, save_to_db=False,
                        )
                except ValueError:
                    self.add_message(
                        "❌ Enter a number or 'cancel'", False, save_to_db=False,
                    )

                self._re_enable()
                return

            # ── search: user provided location ────────────────────────────────
            if action == "search_location" and state == "need_search_location":
                filename    = self.pending_file_action.get("files", [None])[0]
                search_mode = self.pending_file_action.get("search_mode", "regex")
                location    = resolve_location(text)

                result = search_in_location(filename, location, mode=search_mode)
                if result["status"] in ("error", "not_found"):
                    self.add_message(result["message"], False, save_to_db=False)
                    self.pending_file_action = None
                else:
                    files_list = "\n".join(
                        f"  {i}. {f}" for i, f in enumerate(result["files"][:20], 1)
                    )
                    extra   = f"\n  … and {result['count'] - 20} more" if result["count"] > 20 else ""
                    loc_str = location if location else "all drives"
                    self.add_message(
                        f"🔍 Found {result['count']} file(s) matching '{filename}' in {loc_str}:\n\n"
                        f"{files_list}{extra}\n\n"
                        "Enter a number to act on a file, or 'cancel':",
                        False, save_to_db=False,
                    )
                    self.pending_file_action = {
                        "action": "search_location",
                        "state":  "select_action",
                        "files":  result["files"],
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
                        self.add_message(
                            f"📂 Opening file...\n\n{selected}",
                            False, save_to_db=False,
                        )
                        res = open_file(selected)
                        self.add_message(
                            res.get("message", "✅ File opened."),
                            False, save_to_db=False,
                        )
                        self.pending_file_action = None
                    else:
                        self.add_message(
                            f"❌ Enter a number between 1 and {len(files)}",
                            False, save_to_db=False,
                        )
                except ValueError:
                    self.add_message(
                        "❌ Enter a number or 'cancel'", False, save_to_db=False,
                    )

                self._re_enable()
                return

            # ── search: user picks operation on selected file ──────────────────
            if action == "search_location" and state == "select_operation":
                file_path = self.pending_file_action.get("file_path")
                if r == "open":
                    res = open_file(file_path)
                    self.add_message(res["message"], False, save_to_db=False)
                    self.pending_file_action = None
                elif r == "rename":
                    self.add_message("📝 Enter the new filename:", False, save_to_db=False)
                    self.pending_file_action = {
                        "action":    "rename",
                        "state":     "need_new_name",
                        "file_path": file_path,
                    }
                elif r == "move":
                    self.add_message("📁 Enter destination folder:", False, save_to_db=False)
                    self.pending_file_action = {
                        "action": "move",
                        "state":  "need_destination",
                        "files":  [file_path],
                    }
                elif r in ("cancel", "c"):
                    self.add_message("❌ Cancelled.", False, save_to_db=False)
                    self.pending_file_action = None
                else:
                    self.add_message(
                        "❌ Type open, rename, move, or cancel", False, save_to_db=False,
                    )
                self._re_enable()
                return

        # ─────────────────────────────────────────────────────────────────────
        # NEW ADVANCED COMMAND (no pending state)
        # ─────────────────────────────────────────────────────────────────────
        result = handle_advanced_file_command(text, self.current_session_id)
        status = result.get("status")

        if status == "success":
            self.add_message(result["message"], False, save_to_db=False)

            data        = result.get("data", {})
            found_files = data.get("files", [])

            if found_files:
                self.pending_file_action = {
                    "action": "search_location",
                    "state":  "select_action",
                    "files":  found_files,
                }
                self.add_message(
                    "\nEnter file number to open it, or type 'cancel':",
                    False, save_to_db=False,
                )

        elif status == "error":
            self.add_message(result["message"], False, save_to_db=False)

        elif status in ("need_info", "need_new_name", "need_search_info"):
            pending        = result.get("pending", {})
            pending["state"] = status
            self.pending_file_action = pending
            self.add_message(result["message"], False, save_to_db=False)

        elif status == "need_rename_location":
            pending          = result.get("pending", {})
            pending["state"] = "need_rename_location"
            self.pending_file_action = pending
            self.add_message(result["message"], False, save_to_db=False)

        elif status == "move_search":
            pending       = result.get("pending", {})
            files_to_find = pending.get("files", [])
            destination   = pending.get("destination")

            self.add_message("🔍 Searching for file(s) to move...", False, save_to_db=False)
            groups = search_grouped(files_to_find, use_smart=True)
            self._remove_last_ai_bubble()

            result_state = finish_grouped_move(groups, destination)
            if result_state == "need_location":
                pending["state"] = "need_move_location"
                self.pending_file_action = pending

        elif status == "need_destination":
            pending          = result.get("pending", {})
            pending["state"] = "need_destination"
            self.pending_file_action = pending
            self.add_message(result["message"], False, save_to_db=False)

        elif status == "need_search_location":
            pending          = result.get("pending", {})
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
        idx = self.chat_layout.count() - 2
        if idx >= 0:
            item = self.chat_layout.itemAt(idx)
            if item and item.widget():
                item.widget().deleteLater()

    def _re_enable(self):
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.input.setFocus()

    def _after_routing(self, text: str, mode: str, is_file_op: bool):
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

    def _speak_nonblocking(self, msg: str):
        """Speak a short acknowledgement without blocking the UI."""
        # Allow disabling TTS via environment for headless/testing environments
        if os.environ.get("GEMSERVE_DISABLE_TTS", "0").lower() in ("1", "true", "yes"):
            return
        def _runner(message: str):
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(message)
                engine.runAndWait()
                return
            except Exception:
                logger.debug("pyttsx3 TTS failed, attempting fallback.")

            # Fallback: on Windows, use PowerShell System.Speech if available
            try:
                if sys.platform.startswith("win"):
                    import subprocess
                    powershell_cmd = (
                        "Add-Type -AssemblyName System.Speech;"
                        f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{message.replace("'", "\\'")}')"
                    )
                    subprocess.run(["powershell", "-Command", powershell_cmd], check=False)
                    return
            except Exception:
                logger.debug("Fallback TTS also failed.")

        threading.Thread(target=_runner, args=(msg,), daemon=True).start()

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
        # Mark that this input originated from voice so we can ack when processing
        self._last_input_was_voice = True
        self.input.setText(text)
        self.add_message(
            "🎤 Voice input coming soon! "
            "When ready, speech will route through the same pipeline as typed messages.",
            False, save_to_db=False,
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
                "✅ File uploaded successfully!\nFile is ready for questions.",
                False, save_to_db=False,
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
    w   = ChatWindow(lambda: w.close(), lambda: None)
    w.start_new_session()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()