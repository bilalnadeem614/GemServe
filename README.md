# GemServe - Offline AI Desktop Assistant

![Status](https://img.shields.io/badge/status-Active%20Development-brightgreen)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

**GemServe** is a comprehensive offline AI desktop assistant that brings the power of modern AI to your local machine. Built with cutting-edge technologies, GemServe combines voice recognition, intelligent document processing, task management, and AI-powered conversations—all without requiring internet connectivity.

### Key Highlights

- **Voice-Activated Interface**: Wake word detection and speech-to-text powered by Whisper
- **Local LLM Integration**: Runs Ollama models locally for complete privacy
- **Smart Document Processing**: Upload files and ask questions with RAG (Retrieval Augmented Generation)
- **Task Management**: Built-in todo list with automatic scheduling and notifications
- **Session Memory**: Persistent chat history organized by topics
- **Smart Organization**: Tag system for notes, tasks, and files
- **Dark Mode Support**: Eye-friendly interface with theme customization
- **100% Offline**: No data leaves your machine—complete privacy guaranteed
- **App Management**: User can open, close apps already downloaded.

---

## Features

### 1. **AI-Powered Chat**
- Real-time conversations with local Ollama models
- Dual-mode LLM: Fast responses (Gemma 1B) and thinking-intensive queries (Gemma 4B)
- Context-aware conversations with memory of previous interactions
- Session management for organizing multiple conversation threads

### 2. **Voice Interaction**
- **Wake Word Detection**: Say the wake word to activate hands-free mode
- **Speech-to-Text**: Powered by OpenAI's Whisper model
- **Multi-size Models**: Choose between faster (tiny) or more accurate (base) models
- **Real-time Processing**: Convert speech to text instantly

### 3. **Document Intelligence (RAG)**
- Upload documents (PDF, Word, TXT, Code files, etc.)
- Automatic text extraction and chunking
- Semantic search using embeddings
- Ask questions about your documents and get precise answers
- Vector storage with ChromaDB for fast retrieval

### 4. **Smart File and App Management**
- File browser and search functionality
- Recently used file caching (last 15 files per session)
- File tagging and categorization
- Integration with uploaded documents for RAG
- App management like open, close apps.

### 5. **Task & Todo Management**
- Create, edit, and organize tasks
- Mark tasks as complete with progress tracking
- Automatic reminders and notifications
- Task prioritization and tagging

### 6. **Intelligent System Integration**
- Execute system commands through natural language
- Application discovery and registry
- Window management and automation
- System intent parsing

### 7. **User Preferences**
- Customizable dark/light theme
- User profile management
- Preference persistence
- Session-based settings

---

## System Requirements

### Hardware Requirements
- **CPU**: Intel/AMD processor (4+ cores recommended)
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 20GB free space for models and databases
- **Audio**: Microphone and speakers (optional, for voice features)

### Software Requirements
- **OS**: Windows 10+
- **Python**: 3.12.10
- **Ollama**: Latest version (for LLM capabilities)

---

## Installation & Setup

### Step 1: Prerequisites

1. **Install Python 3.12.10**
   ```bash
   python --version  # Verify installation
   ```

2. **Install Ollama**
   - Download from [ollama.ai](https://ollama.ai)
   - Run the installer
   - Start Ollama service: `ollama serve`

3. **Pull Required Models**
   ```bash
   ollama pull gemma3:1b      # Fast model (1.3 GB)
   ollama pull gemma3:4b      # Thinking model (4.2 GB)
   ollama pull embeddinggemma # Embedding model (~4 GB)
   ```

### Step 2: Clone & Setup Project

```bash
# Clone the repository
git clone <repository-url>
cd GemServe

# Create virtual environment
python -m venv venv312

# Activate virtual environment
# On Windows:
venv312\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download Whisper models (one-time setup)
python modeldownload.py
```

### Step 3: Configuration

Edit `utils/config.py` to customize:
- **LLM Models**: Change `OLLAMA_FAST_MODEL` and `OLLAMA_THINKING_MODEL`
- **Embedding Model**: Adjust `EMBEDDING_MODEL`
- **Context Limits**: Modify `MAX_HISTORY_MESSAGES` and `MAX_HISTORY_TOKENS`
- **API Keys**: Set `GEMINI_API_KEY` in `.env` (if using Gemini API as fallback)

### Step 4: Run Application

```bash
python main.py
```

The application will:
- Initialize the database
- Load the Whisper model (takes 30-60 seconds first time)
- Start the GUI
- Activate wake word detection

---

## Project Structure

```
GemServe/
├── main.py                    # Application entry point
├── modeldownload.py          # Model download utility
├── requirements.txt          # Python dependencies
│
├── gui/                      # User Interface (PySide6)
│   ├── Home_Page.py         # Dashboard & chat sessions
│   ├── Chat_Bot.py          # Chat interface & voice control
│   ├── todo_page.py         # Task management UI
│   ├── edit_task_page.py    # Task editor
│   ├── profile_update.py    # User settings
│   ├── speech_popup.py      # Voice recording popup
│   └── Chat_Bot_styles.py   # Stylesheet definitions
│
├── services/                 # Business Logic
│   ├── chat_service.py      # Chat response generation
│   ├── llm_service.py       # Ollama integration
│   ├── file_processor.py    # Document processing
│   ├── file_service.py      # File management & search
│   ├── file_tag_service.py  # File tagging system
│   ├── llm_file_service.py  # Document Q&A
│   ├── file_advanced_service.py # Advanced file ops
│   ├── file_creator_service.py  # File creation
│   ├── system_intent_service.py # Command parsing
│   ├── system_service.py    # System integration
│   ├── wake_word_detector.py # Voice activation
│   ├── notifier.py          # Notifications & reminders
│   ├── model_manager.py     # Model lifecycle
│   └── app_service.py       # Application registry
│
├── db/                       # Database Layer
│   ├── database.py          # SQLite operations
│   ├── vector_store.py      # ChromaDB integration
│   ├── tag_db_json.py       # JSON-based tag storage
│   ├── todo_db_helper.py    # Task database helpers
│   └── __init__.py          # Database initialization
│
├── utils/                    # Utilities
│   ├── config.py            # Configuration & settings
│   ├── logger.py            # Logging setup
│   ├── helpers.py           # Helper functions
│   └── extract_info.py      # Text extraction
│
├── data/                     # Runtime Data
│   ├── chroma_db/          # Vector database
│   ├── uploaded_files/     # User-uploaded documents
│   ├── chat.db             # SQLite database
│   ├── tags.json           # Tag definitions
│   └── app.log             # Application logs
│
├── models/                   # ML Models (Downloaded at runtime)
│   ├── whisper/            # Whisper models
│   ├── whisper-tiny/       # Tiny Whisper variant
│   └── [embeddings]/       # Embedding models
│
└── venv312/                 # Python virtual environment
    └── [site-packages]/    # Installed dependencies
```

---

## Usage Guide

### Starting a Conversation

1. **Launch the Application**
   ```bash
   python main.py
   ```

2. **From Home Page**
   - Click "New Chat" to start a conversation
   - Type messages or click the microphone icon for voice input

3. **Voice Activation**
   - Say the wake word when the app is running
   - Speak your query when the recording window opens
   - GemServe will transcribe and respond

### Uploading Documents

1. **In Chat Window**
   - Click the "Upload File" button
   - Select a document (PDF, DOCX, TXT, Python files, etc.)
   - Ask questions about the document content

2. **RAG Features**
   - GemServe chunks documents automatically
   - Creates embeddings for semantic search
   - Retrieves relevant sections when you ask questions

### Managing Tasks

1. **Open Todo List**
   - Click "Tasks" on the home page

2. **Create Task**
   - Click "New Task"
   - Set title, description, due date, and tags

3. **Track Progress**
   - Mark tasks as complete
   - View pending tasks on home page

### File and App Management

1. **File Management**
    ```bash
    open filename.ext (and filename.ext for multiple files)
    delete filename.ext
    create filename.ext (and filename.ext for multiple files)
    move filename.ext (and filename.ext  for multiple files) to folder
    rename filename.ext to filename.ext 
    search filename.ext
    ```
2. **App Managemet**
    ```bash

    open app app-name

    close app app-name
    ```
### Customization

1. **Theme Settings**
   - Click settings icon on home page
   - Toggle "Dark Mode" for eye comfort
   - Changes apply immediately

2. **Model Selection** (Advanced)
   - Edit `utils/config.py`
   - Change LLM or embedding models
   - Restart application

---

## Configuration Guide

### Key Configuration Files

#### `utils/config.py`
```python
# LLM Models
OLLAMA_FAST_MODEL = "gemma3:1b"          # For quick responses
OLLAMA_THINKING_MODEL = "gemma3:4b"      # For complex queries

# Embedding
EMBEDDING_MODEL = "embeddinggemma:latest"

# Context Management
MAX_HISTORY_MESSAGES_NO_FILES = 30       # Chat memory size
MAX_HISTORY_TOKENS_NO_FILES = 8000       # Token limit
MAX_RAG_CHUNKS = 8                       # Document chunks to consider

# Document Processing
CHUNK_SIZE = 1800                        # Tokens per chunk
CHUNK_OVERLAP = 200                      # Overlap between chunks
```

#### `.env` (Create if needed)
```
GEMINI_API_KEY=your_api_key_here  # Optional: Gemini fallback
```

---

## Integration Points

### Ollama Integration
- **URL**: `http://localhost:11434`
- **Models Used**:
  - `gemma3:1b` - Fast responses
  - `gemma3:4b` - Thinking mode
  - `embeddinggemma:latest` - Document embeddings

### ChromaDB Integration
- **Storage**: `data/chroma_db/`
- **Purpose**: Vector storage for RAG
- **Persistence**: SQLite backend

### Whisper Integration
- **Purpose**: Speech recognition
- **Models**: Tiny (~140MB) and Base (~74MB)
- **Inference**: CPU-based

---

## Database Schema

### SQLite (chat.db)
- **chat_sessions**: Stores conversation threads
- **messages**: Chat history with timestamps
- **file_metadata**: Uploaded file information
- **processed_files**: Processed document status

### JSON Storage
- **user_data.json**: User preferences (theme, settings)
- **user_notes.json**: Quick notes
- **data/tags.json**: Tag definitions and categorization

### Vector Store (ChromaDB)
- **Collections**: One per chat session
- **Embeddings**: Generated from document chunks
- **Metadata**: File source, page numbers, timestamps

---

## Troubleshooting

### Whisper Model Not Loading
```
Error: Tiny Whisper model could not be warmed at startup
```
**Solution**: 
- Re-run `python modeldownload.py`
- Check internet connection for first-time download

### Ollama Connection Failed
```
Error: Failed to connect to http://localhost:11434
```
**Solution**:
- Ensure Ollama is running: `ollama serve`
- Check Ollama is accessible on port 11434
- Verify firewall settings

### Wake Word Detection Not Working
```
Error: Wake word detector unavailable
```
**Solution**:
- Check microphone is connected and permissions granted
- Ensure `sounddevice` package is installed
- Run `pip install -r requirements.txt` again

### Out of Memory (OOM)
```
Error: CUDA out of memory
```
**Solution**:
- Reduce `MAX_HISTORY_MESSAGES` in config
- Use smaller models (Gemma 1B instead of 4B)

### Database Lock Error
```
Error: database is locked
```
**Solution**:
- Close all GemServe instances
- Restart the application
- Check `data/` folder permissions

---

## Privacy & Security

### Privacy Guarantees
- **100% Offline**: No data is sent to external servers
- **Local Storage**: All conversations stored locally
- **No Tracking**: No telemetry or analytics
- **Open-Source Models**: Uses transparent, open-source models
- **Your Control**: Full access to all data and models

### Data Storage
- Chat history: `data/chat.db`
- Uploaded files: `data/uploaded_files/`
- Embeddings: `data/chroma_db/`
- User data: `user_data.json`

---

## Development

### Project Dependencies

Key libraries:
- **PySide6**: GUI framework
- **Ollama**: LLM interface
- **ChromaDB**: Vector database
- **Faster-Whisper**: Speech recognition
- **PyTorch**: Deep learning backbone
- **NumPy/SciPy**: Numerical computing

### Adding New Features

1. **New Service**: Create file in `services/`
2. **Database Changes**: Update `db/database.py`
3. **GUI Changes**: Modify files in `gui/`
4. **Configuration**: Update `utils/config.py`

### Running Tests
```bash
# Test Ollama connection
python -c "from services.llm_service import ask_ollama; print(ask_ollama('Hi'))"

# Test Whisper
python modeldownload.py

# Check ChromaDB
python -c "from db.vector_store import get_vector_store; print(get_vector_store())"
```

---

## File History

The application automatically maintains user file history:
- `file_history/user_X_files.json` - Cache of last 15 accessed files
- Enables quick file search and autocomplete
- Automatically updated when files are accessed

---

## Roadmap

### Current Version (1.0)
- Chat interface with Ollama
- Voice activation & transcription
- Document upload & RAG
- Task management
- Dark mode

<!-- 
### Planned Features (v1.1+)
- [ ] Multi-user support with login
- [ ] Cloud backup option
- [ ] Plugin system for extensions
- [ ] Keyboard shortcuts & hotkeys
- [ ] Custom wake word training
- [ ] Voice output (Text-to-Speech)
- [ ] Web interface companion
- [ ] Mobile app integration -->

---

## License

MIT License - See LICENSE.txt for details

---

## Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with description

---

## Support & Contact

- **Issue Tracker**: Report bugs via GitHub Issues
- **Documentation**: Check docs/ folder for detailed guides
- **Community**: Join discussions for feature requests

---

## Acknowledgments

- **Ollama** - For local LLM capabilities
- **Whisper** - OpenAI's speech recognition model
- **ChromaDB** - Vector database solution
- **PySide6** - Python Qt framework
- **Open Source Community** - For all dependencies

---

## Quick Start Command

```bash
# Clone, setup, and run in one go
git clone <repository-url> && \
cd GemServe && \
python -m venv venv312 && \
venv312\Scripts\activate && \
pip install -r requirements.txt && \
python modeldownload.py && \
python main.py
```

---

**GemServe** - Your Personal AI Assistant. Offline. Private. Powerful.

*Last Updated: May 2026*
