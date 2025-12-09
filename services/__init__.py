# services/__init__.py
from .chat_service import get_chat_response, build_context_prompt
from .file_processor import process_file, extract_text_from_file
from .llm_service import ask_ollama

__all__ = [
    'get_chat_response',
    'build_context_prompt',
    'process_file',
    'extract_text_from_file',
    'ask_ollama'
]