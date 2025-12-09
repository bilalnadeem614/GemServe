# services/file_processor.py
import os
from utils.helpers import chunk_text_by_sentences
from utils.config import CHUNK_SIZE, CHUNK_OVERLAP

def extract_text_from_file(file_path, file_type):
    """
    Extract text from different file types
    Currently supports: txt, md, pdf
    """
    file_type = file_type.lower()
    
    if file_type in ['txt', 'md']:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    elif file_type == 'pdf':
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            print("⚠️ PyPDF2 not installed. Install with: pip install PyPDF2")
            return ""
        except Exception as e:
            print(f"❌ Error extracting PDF: {e}")
            return ""
    
    else:
        print(f"⚠️ Unsupported file type: {file_type}")
        return ""

def process_file(file_path, file_type):
    """
    Process a file: extract text and chunk it
    Returns list of text chunks
    """
    # Extract text
    text = extract_text_from_file(file_path, file_type)
    
    if not text.strip():
        print("⚠️ No text extracted from file")
        return []
    
    # Chunk the text
    chunks = chunk_text_by_sentences(
        text, 
        max_tokens=CHUNK_SIZE, 
        overlap_tokens=CHUNK_OVERLAP
    )
    
    print(f"✅ Processed file into {len(chunks)} chunks")
    return chunks