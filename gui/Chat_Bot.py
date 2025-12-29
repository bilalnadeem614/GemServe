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
from PySide6.QtWidgets import QComboBox
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
from services.file_service import (
    initialize_file_mode, 
    handle_file_command, 
    open_file, 
    delete_file,
    find_files_by_name
)
from utils.config import UPLOAD_DIR
from utils.helpers import sanitize_filename
from gui.Chat_Bot_styles import get_chat_styles


# ---------------------- MESSAGE BUBBLE -------------------------
class MessageBubble(QFrame):
    def __init__(self, text, is_user, dark_mode=False):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Clean up text - remove leading/trailing whitespace and extra newlines
        cleaned_text = text.strip()

        bubble = QLabel(cleaned_text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)

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

    def __init__(self, session_id, user_query):
        super().__init__()
        self.session_id = session_id
        self.user_query = user_query

    def run(self):
        try:
            response = get_chat_response(self.session_id, self.user_query)
            # Clean response - remove extra whitespace and newlines
            cleaned_response = response.strip()
            self.finished.emit(cleaned_response)
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
        
        # File operation mode state
        self.file_operation_mode = False
        self.pending_file_action = None  # Store pending actions (delete, overwrite, create location, etc.)

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
        w_layout.setContentsMargins(55, 0, 55, 0)

        self.input = QLineEdit()
        self.input.setObjectName("messageInput")
        self.input.setPlaceholderText("Type your message...")
        self.input.returnPressed.connect(self.on_send)
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
        self.mode_combo.addItem("📁 File Operation")
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
        """Handle mode change in dropdown"""
        mode = self.get_selected_mode()
        
        if mode == "file_operation" and not self.file_operation_mode:
            # Entering file operation mode
            self.file_operation_mode = True
            result = initialize_file_mode()
            self.add_message(result["message"], False, save_to_db=False)
            self.input.setPlaceholderText("Enter file command (e.g., open README.md)...")
            
        elif mode != "file_operation" and self.file_operation_mode:
            # Exiting file operation mode
            self.file_operation_mode = False
            self.pending_file_action = None
            self.add_message("📁 File Operation Mode Deactivated", False, save_to_db=False)
            self.input.setPlaceholderText("Type your message...")

    def get_selected_mode(self):
        """Get current selected mode"""
        mode_text = self.mode_combo.currentText()
        if "Fast" in mode_text:
            return "fast"
        elif "Thinking" in mode_text:
            return "thinking"
        elif "File Operation" in mode_text:
            return "file_operation"
        return "fast"

    # -----------------------------------------
    # Session Management
    # -----------------------------------------
    def start_new_session(self):
        """Start a new chat session"""
        self.current_session_id = None
        self.is_new_session = True
        self.file_operation_mode = False
        self.pending_file_action = None
        self.title.setText("New Chat")
        self.clear_chat()
        self.files_container.setVisible(False)
        self.mode_combo.setCurrentIndex(0)  # Reset to Fast mode
        print("✅ Ready for new session")

    def load_session(self, session_id):
        """Load an existing chat session"""
        self.current_session_id = session_id
        self.is_new_session = False
        self.file_operation_mode = False
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
        """Handle file operation commands"""
        # Check if this is a response to a pending action
        if self.pending_file_action:
            action_type = self.pending_file_action.get("action")
            
            # Handle CACHE LIMIT response
            if action_type in ["cache_limit_open", "cache_limit_delete"]:
                user_response = text.strip().lower()
                files = self.pending_file_action.get("files", [])
                operation = "open" if action_type == "cache_limit_open" else "delete"
                
                # Check if user wants full search
                if user_response == "all":
                    self.add_message("🔍 Searching all drives...", False, save_to_db=False)
                    filename = self.pending_file_action.get("filename")
                    result = find_files_by_name(filename, session_id=None)
                    
                    if result["count"] == 0:
                        self.add_message(f"❌ File '{filename}' not found in any drive", False, save_to_db=False)
                        self.pending_file_action = None
                    elif result["count"] == 1:
                        if operation == "open":
                            res = open_file(result["files"][0], self.current_session_id)
                            self.add_message(res["message"], False, save_to_db=False)
                        else:
                            self.pending_file_action = {
                                "action": "delete",
                                "files": [result["files"][0]]
                            }
                            self.add_message(f"⚠️ Are you sure you want to delete:\n📂 {result['files'][0]}\n\nType 'y' to confirm or 'n' to cancel", False, save_to_db=False)
                            return
                        self.pending_file_action = None
                    else:
                        self.show_file_selection(result["files"], operation)
                    return
                
                # Check if user specified a drive
                elif user_response.endswith(":\\") or (len(user_response) == 1 and user_response.isalpha()):
                    drive = user_response.upper()
                    if not drive.endswith(":\\"):
                        drive += ":\\"
                    
                    if not os.path.exists(drive):
                        self.add_message(f"❌ Drive '{drive}' not found", False, save_to_db=False)
                        return
                    
                    self.add_message(f"🔍 Searching {drive}...", False, save_to_db=False)
                    filename = self.pending_file_action.get("filename")
                    result = find_files_by_name(filename, session_id=self.current_session_id, specific_drive=drive)
                    
                    if result["count"] == 0:
                        self.add_message(f"❌ File '{filename}' not found in {drive}", False, save_to_db=False)
                        self.pending_file_action = None
                    elif result["count"] == 1:
                        if operation == "open":
                            res = open_file(result["files"][0], self.current_session_id)
                            self.add_message(res["message"], False, save_to_db=False)
                        else:
                            self.pending_file_action = {
                                "action": "delete",
                                "files": [result["files"][0]]
                            }
                            self.add_message(f"⚠️ Are you sure you want to delete:\n📂 {result['files'][0]}\n\nType 'y' to confirm or 'n' to cancel", False, save_to_db=False)
                            return
                        self.pending_file_action = None
                    else:
                        self.show_file_selection(result["files"], operation)
                    return
                
                # Check if user selected a number from cache
                else:
                    try:
                        choice = int(user_response)
                        if 1 <= choice <= len(files):
                            selected_file = files[choice - 1]
                            
                            if operation == "open":
                                result = open_file(selected_file, self.current_session_id)
                                self.add_message(result["message"], False, save_to_db=False)
                            else:
                                self.pending_file_action = {
                                    "action": "delete",
                                    "files": [selected_file]
                                }
                                self.add_message(f"⚠️ Are you sure you want to delete:\n📂 {selected_file}\n\nType 'y' to confirm or 'n' to cancel", False, save_to_db=False)
                                return
                            
                            self.pending_file_action = None
                        else:
                            self.add_message(f"❌ Please enter a number between 1 and {len(files)}, 'all', or a drive letter", False, save_to_db=False)
                            return
                    except ValueError:
                        self.add_message("❌ Invalid input. Enter a number, 'all', or drive letter (e.g., 'C:\\')", False, save_to_db=False)
                    return
            
            # Handle DELETE confirmation
            if action_type == "delete":
                user_response = text.strip().lower()
                
                if user_response in ["y", "yes"]:
                    files = self.pending_file_action.get("files", [])
                    
                    if len(files) == 1:
                        result = delete_file(files[0], self.current_session_id)
                        self.add_message(result["message"], False, save_to_db=False)
                    else:
                        # Ask user to select which file
                        self.show_file_selection(files, "delete")
                        return
                        
                    self.pending_file_action = None
                    
                elif user_response in ["n", "no", "c", "cancel"]:
                    self.add_message("❌ Deletion cancelled", False, save_to_db=False)
                    self.pending_file_action = None
                else:
                    self.add_message("❌ Invalid response. Please enter 'y' for yes or 'n' for no", False, save_to_db=False)
                return
                
            # Handle OVERWRITE confirmation
            elif action_type == "overwrite":
                user_response = text.strip().lower()
                
                if user_response in ["y", "yes"]:
                    path = self.pending_file_action.get("path")
                    try:
                        os.remove(path)
                        from pathlib import Path
                        Path(path).touch()
                        self.add_message(f"✅ File overwritten: {os.path.basename(path)}", False, save_to_db=False)
                    except Exception as e:
                        self.add_message(f"❌ Failed to overwrite: {str(e)}", False, save_to_db=False)
                    self.pending_file_action = None
                    
                elif user_response in ["n", "no", "c", "cancel"]:
                    self.add_message("❌ File creation cancelled", False, save_to_db=False)
                    self.pending_file_action = None
                else:
                    self.add_message("❌ Invalid response. Please enter 'y' for yes or 'n' for no", False, save_to_db=False)
                return
            
            # Handle CREATE LOCATION selection
            elif action_type == "create_location":
                user_response = text.strip().lower()
                filename = self.pending_file_action.get("filename")
                
                if user_response in ["1", "desktop"]:
                    # Create on Desktop
                    from services.file_service import create_file
                    result = create_file(filename, custom_path=None)
                    
                    if result["status"] == "success":
                        self.add_message(result["message"], False, save_to_db=False)
                        self.pending_file_action = None
                    elif result["status"] == "confirm":
                        # File exists, ask to overwrite
                        self.pending_file_action = {"action": "overwrite", "path": result["path"]}
                        self.add_message(result["message"], False, save_to_db=False)
                    else:
                        self.add_message(result["message"], False, save_to_db=False)
                        self.pending_file_action = None
                    return
                    
                elif user_response in ["2", "custom"]:
                    # Ask for custom path
                    self.pending_file_action = {
                        "action": "custom_path",
                        "filename": filename
                    }
                    self.add_message("📂 Enter the full path where you want to create the file:\n(e.g., C:\\Users\\Me\\Documents or T:\\Projects)", False, save_to_db=False)
                    return
                    
                elif user_response in ["c", "cancel", "q", "quit"]:
                    self.add_message("❌ File creation cancelled", False, save_to_db=False)
                    self.pending_file_action = None
                else:
                    self.add_message("❌ Invalid choice. Type '1' for Desktop, '2' for custom path, or 'cancel'", False, save_to_db=False)
                return
            
            # Handle CUSTOM PATH input
            elif action_type == "custom_path":
                custom_path = text.strip()
                filename = self.pending_file_action.get("filename")
                
                # Remove quotes if user added them
                custom_path = custom_path.strip('"').strip("'")
                
                if custom_path.lower() in ["c", "cancel", "q", "quit"]:
                    self.add_message("❌ File creation cancelled", False, save_to_db=False)
                    self.pending_file_action = None
                    return
                
                from services.file_service import create_file
                result = create_file(filename, custom_path=custom_path)
                
                if result["status"] == "success":
                    self.add_message(result["message"], False, save_to_db=False)
                    self.pending_file_action = None
                elif result["status"] == "confirm":
                    # File exists, ask to overwrite
                    self.pending_file_action = {"action": "overwrite", "path": result["path"]}
                    self.add_message(result["message"], False, save_to_db=False)
                else:
                    self.add_message(result["message"], False, save_to_db=False)
                    self.pending_file_action = None
                return
                
            # Handle FILE SELECTION (by number)
            elif action_type == "select_file":
                files = self.pending_file_action.get("files", [])
                operation = self.pending_file_action.get("operation")
                
                try:
                    choice = int(text.strip())
                    if 1 <= choice <= len(files):
                        selected_file = files[choice - 1]
                        
                        if operation == "open":
                            result = open_file(selected_file, self.current_session_id)
                            self.add_message(result["message"], False, save_to_db=False)
                        elif operation == "delete":
                            # Confirm deletion
                            self.pending_file_action = {
                                "action": "delete",
                                "files": [selected_file]
                            }
                            self.add_message(f"⚠️ Are you sure you want to delete:\n📂 {selected_file}\n\nType 'y' to confirm or 'n' to cancel", False, save_to_db=False)
                            return
                            
                        self.pending_file_action = None
                    else:
                        self.add_message(f"❌ Please enter a number between 1 and {len(files)}", False, save_to_db=False)
                        return
                except ValueError:
                    if text.strip().lower() in ["c", "cancel", "q", "quit"]:
                        self.add_message("❌ Operation cancelled", False, save_to_db=False)
                        self.pending_file_action = None
                    else:
                        self.add_message("❌ Invalid input. Enter a number or 'c' to cancel", False, save_to_db=False)
                return
        
        # Process new file command
        result = handle_file_command(text, self.current_session_id)
        
        if result["status"] == "success":
            self.add_message(result["message"], False, save_to_db=False)
            
        elif result["status"] == "error":
            self.add_message(result["message"], False, save_to_db=False)
        
        elif result["status"] == "single_file":
            # Single file found, open directly
            file_path = result["file"]
            if result["action"] == "open":
                res = open_file(file_path, self.current_session_id)
                self.add_message(res["message"], False, save_to_db=False)
        
        elif result["status"] == "cache_limit":
            # Cache found but under 15, ask user
            self.pending_file_action = {
                "action": f"cache_limit_{result['action']}",
                "files": result["files"],
                "filename": text.split(maxsplit=1)[1].strip()  # Extract filename
            }
            self.add_message(result["message"], False, save_to_db=False)
        
        elif result["status"] == "ask_location":
            # Ask where to create file (Desktop or custom path)
            self.pending_file_action = {
                "action": "create_location",
                "filename": result["filename"]
            }
            self.add_message(result["message"], False, save_to_db=False)
            
        elif result["status"] == "multiple":
            # Multiple files found - ask user to select
            self.show_file_selection(result["files"], result["action"])
            
        elif result["status"] == "confirm":
            action = result["action"]
            
            if action == "delete":
                # Ask for delete confirmation
                files = result["files"]
                if len(files) == 1:
                    self.pending_file_action = {"action": "delete", "files": files}
                    self.add_message(f"⚠️ Are you sure you want to delete:\n📂 {files[0]}\n\nType 'y' to confirm or 'n' to cancel", False, save_to_db=False)
                else:
                    self.show_file_selection(files, "delete")
                    
            elif action == "overwrite":
                # Ask for overwrite confirmation
                self.pending_file_action = {"action": "overwrite", "path": result["path"]}
                self.add_message(result["message"], False, save_to_db=False)
                
        elif result["status"] == "warning":
            # System file warning
            self.pending_file_action = {"action": "delete", "files": [result["path"]]}
            self.add_message(result["message"] + "\n\nType 'y' to confirm or 'n' to cancel", False, save_to_db=False)

    def show_file_selection(self, files, operation):
        """Show file selection menu"""
        message = f"📊 Found {len(files)} file(s). Select one:\n\n"
        for i, file in enumerate(files, 1):
            message += f"{i}. {file}\n"
        message += "\nEnter the number or 'c' to cancel"
        
        self.pending_file_action = {
            "action": "select_file",
            "files": files,
            "operation": operation
        }
        
        self.add_message(message, False, save_to_db=False)

    # ---------------- SEND MESSAGE ----------------
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

        # FILE OPERATION MODE
        if self.file_operation_mode:
            self.handle_file_operation(text)
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.input.setFocus()
            return

        # NORMAL CHAT MODE
        self.add_message("Thinking...", False, save_to_db=False)

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
        self.add_message(f"📎 Uploading: {filename}...", False, save_to_db=False)

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
                success = add_document_chunks(
                    self.current_session_id, file_id, filename, chunks
                )

                if success:
                    mark_file_processed(file_id)
                    self.add_file_to_ui(filename)

                    last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
                    if last_item and last_item.widget():
                        last_item.widget().deleteLater()

                    self.add_message(
                        f"✅ File uploaded successfully!\n{filename} is ready for questions ({len(chunks)} chunks processed)",
                        False,
                        save_to_db=False,
                    )
                else:
                    self.add_message(
                        f"❌ Failed to process embeddings for {filename}",
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

    def add_file_to_ui(self, filename):
        """Add file badge to the files container"""
        file_badge = QLabel(f"📄 {filename}")
        file_badge.setObjectName("fileBadge")
        file_badge.setFixedHeight(32)
        self.files_list_layout.addWidget(file_badge)
        self.files_container.setVisible(True)

    def load_uploaded_files_ui(self):
        """Load uploaded files for current session into UI"""
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