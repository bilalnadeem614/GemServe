# utils/config.py
import os

# ==================== PATHS ====================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "chat.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploaded_files")
LOG_FILE = os.path.join(DATA_DIR, "app.log")

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ==================== LLM SETTINGS ====================
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma3:270m"  # Default model (for backward compatibility)

# Model configuration for different modes
MODEL_CONFIG = {
    "fast": {
        "model": "gemma3:270m",
        "description": "Fast responses - optimized for quick answers",
        "timeout": 120,  # Increased timeout for fast model (270M can be slow)
    },
    "thinking": {
        "model": "gemma3n:e2b",
        "description": "Thinking mode - optimized for detailed analysis",
        "timeout": 180,  # More time for thinking model
    }
}
DEFAULT_MODE = "fast"

# ==================== REQUEST SETTINGS ====================
DEFAULT_REQUEST_TIMEOUT = 120  # seconds, fallback timeout
MAX_RETRIES = 2  # Number of retries for failed requests
RETRY_DELAY = 1  # Seconds to wait between retries
EMBEDDING_BATCH_SIZE = 4  # Number of chunks to batch per embedding request

# ==================== EMBEDDING SETTINGS ====================
EMBEDDING_MODEL = "embeddinggemma:latest"  # For document embeddings

# ==================== CONTEXT WINDOW SETTINGS ====================
# Token limits for Gemma models (32k total context)
MAX_TOTAL_TOKENS = 32000
SYSTEM_PROMPT_TOKENS = 500
USER_PREFS_TOKENS = 200
RESERVED_RESPONSE_TOKENS = 8000

# Fast Mode: Less context window
FAST_MODE_HISTORY_MESSAGES_NO_FILES = 20
FAST_MODE_HISTORY_TOKENS_NO_FILES = 5000
FAST_MODE_HISTORY_MESSAGES_WITH_FILES = 10
FAST_MODE_HISTORY_TOKENS_WITH_FILES = 3000

# Thinking Mode: More context window
THINKING_MODE_HISTORY_MESSAGES_NO_FILES = 30
THINKING_MODE_HISTORY_TOKENS_NO_FILES = 10000
THINKING_MODE_HISTORY_MESSAGES_WITH_FILES = 20
THINKING_MODE_HISTORY_TOKENS_WITH_FILES = 6000

# Default context limits (backward compatibility)
MAX_HISTORY_MESSAGES_NO_FILES = FAST_MODE_HISTORY_MESSAGES_NO_FILES
MAX_HISTORY_TOKENS_NO_FILES = FAST_MODE_HISTORY_TOKENS_NO_FILES
MAX_HISTORY_MESSAGES_WITH_FILES = FAST_MODE_HISTORY_MESSAGES_WITH_FILES
MAX_HISTORY_TOKENS_WITH_FILES = FAST_MODE_HISTORY_TOKENS_WITH_FILES
MAX_RAG_CHUNKS = 8
MAX_CHUNK_TOKENS = 1800  # ~15k / 8 chunks

# ==================== CHUNKING SETTINGS ====================
CHUNK_SIZE = 1800  # tokens per chunk
CHUNK_OVERLAP = 200  # overlap between chunks

# ==================== CHROMADB SETTINGS ====================
CHROMA_PERSIST_DIR = os.path.join(DATA_DIR, "chroma_db")
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

# ==================== SYSTEM PROMPT ====================
SYSTEM_PROMPT = """You are an offline AI desktop assistant named GemServe.
You help users with file management, tasks, reminders, and general queries.
Be concise, helpful, and friendly in your responses.
When answering questions about uploaded documents, reference the specific information provided in the context."""

# ==================== THEME COLORS ====================
# Light Mode Colors
LIGHT_MODE = {
    "bg_primary": "#f0f0f0",
    "bg_secondary": "#ffffff",
    "text_primary": "#000000",
    "text_secondary": "#333333",
    "button_text": "#000000",
    "border": "#ccc",
    "user_bubble_bg": "#ffffff",
    "user_bubble_border": "#c7c7c7",
    "bot_bubble_bg": "#ececec",
    "bot_bubble_border": "#c5c5c5",
    "badge_bg": "#2d2d2d",
    "badge_text": "#ffffff",
    "accent_green": "#4CAF50",
}

# Dark Mode Colors
DARK_MODE = {
    "bg_primary": "#1e1e1e",
    "bg_secondary": "#2d2d2d",
    "text_primary": "#ffffff",
    "text_secondary": "#e0e0e0",
    "button_text": "#ffffff",
    "border": "#444",
    "user_bubble_bg": "#2d2d2d",
    "user_bubble_border": "#444",
    "bot_bubble_bg": "#3a3a3a",
    "bot_bubble_border": "#555",
    "badge_bg": "#4CAF50",
    "badge_text": "#ffffff",
    "accent_green": "#4CAF50",
}