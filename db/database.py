# db/database.py
import sqlite3
from datetime import datetime
from utils.config import DB_PATH
from utils.helpers import truncate_text

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Chat Sessions Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Messages Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
        )
    """)
    
    # Uploaded Files Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_processed BOOLEAN DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_files_session ON uploaded_files(session_id)")
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

# ==================== SESSION OPERATIONS ====================

def create_session(first_message):
    """Create a new chat session with first message as title"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    title = truncate_text(first_message, 100)
    
    c.execute("INSERT INTO chat_sessions (title) VALUES (?)", (title,))
    session_id = c.lastrowid
    
    # Save first message
    c.execute("""
        INSERT INTO messages (session_id, role, content) 
        VALUES (?, 'user', ?)
    """, (session_id, first_message))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Created session {session_id}: {title}")
    return session_id

def get_all_sessions():
    """Get all chat sessions ordered by most recent"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT session_id, title, updated_at 
        FROM chat_sessions 
        ORDER BY updated_at DESC
    """)
    
    sessions = c.fetchall()
    conn.close()
    
    return sessions

def update_session_timestamp(session_id):
    """Update the last modified timestamp of a session"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        UPDATE chat_sessions 
        SET updated_at = CURRENT_TIMESTAMP 
        WHERE session_id = ?
    """, (session_id,))
    
    conn.commit()
    conn.close()

def delete_session(session_id):
    """Delete a session and all associated data"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Deleted session {session_id}")

# ==================== MESSAGE OPERATIONS ====================

def save_message(session_id, role, content):
    """Save a message to the database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO messages (session_id, role, content) 
        VALUES (?, ?, ?)
    """, (session_id, role, content))
    
    conn.commit()
    conn.close()
    
    # Update session timestamp
    update_session_timestamp(session_id)

def get_session_messages(session_id, limit=None):
    """Get messages for a specific session"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    if limit:
        c.execute("""
            SELECT role, content, timestamp 
            FROM messages 
            WHERE session_id = ? 
            ORDER BY message_id DESC 
            LIMIT ?
        """, (session_id, limit))
        messages = c.fetchall()[::-1]  # Reverse to chronological
    else:
        c.execute("""
            SELECT role, content, timestamp 
            FROM messages 
            WHERE session_id = ? 
            ORDER BY message_id ASC
        """, (session_id,))
        messages = c.fetchall()
    
    conn.close()
    return messages

# ==================== FILE OPERATIONS ====================

def save_file_metadata(session_id, filename, file_path, file_type):
    """Save uploaded file metadata"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        INSERT INTO uploaded_files 
        (session_id, filename, file_path, file_type) 
        VALUES (?, ?, ?, ?)
    """, (session_id, filename, file_path, file_type))
    
    file_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return file_id

def mark_file_processed(file_id):
    """Mark file as processed (embeddings created)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        UPDATE uploaded_files 
        SET is_processed = 1 
        WHERE file_id = ?
    """, (file_id,))
    
    conn.commit()
    conn.close()

def get_session_files(session_id):
    """Get all files for a session"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT file_id, filename, upload_date, is_processed 
        FROM uploaded_files 
        WHERE session_id = ? 
        ORDER BY upload_date ASC
    """, (session_id,))
    
    files = c.fetchall()
    conn.close()
    
    return files

def check_session_has_files(session_id):
    """Check if session has any processed files"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT COUNT(*) 
        FROM uploaded_files 
        WHERE session_id = ? AND is_processed = 1
    """, (session_id,))
    
    count = c.fetchone()[0]
    conn.close()
    
    return count > 0