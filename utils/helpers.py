# utils/helpers.py
import re
from datetime import datetime

def truncate_text(text, max_length=100):
    """Truncate text to max_length and add ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def estimate_tokens(text):
    """Rough estimation: 1 token ≈ 4 characters"""
    return len(text) // 4

def sanitize_filename(filename):
    """Remove special characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%b %d, %I:%M %p")
    except:
        return timestamp_str

def chunk_text_by_sentences(text, max_tokens=1800, overlap_tokens=200):
    """
    Split text into chunks based on sentences
    Args:
        text: Input text to chunk
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap between chunks
    Returns:
        List of text chunks
    """
    # Split by sentences (simple approach)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        
        if current_tokens + sentence_tokens > max_tokens and current_chunk:
            # Save current chunk
            chunks.append(' '.join(current_chunk))
            
            # Start new chunk with overlap
            overlap_text = ' '.join(current_chunk[-2:]) if len(current_chunk) >= 2 else ''
            current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
            current_tokens = estimate_tokens(' '.join(current_chunk))
        else:
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
    
    # Add remaining chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks