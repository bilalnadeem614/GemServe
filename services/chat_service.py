# services/chat_service.py
from db.database import (
    get_session_messages, 
    check_session_has_files
)
from db.vector_store import query_relevant_chunks
from services.llm_service import ask_ollama
from utils.config import (
    SYSTEM_PROMPT,
    MAX_HISTORY_MESSAGES_NO_FILES,
    MAX_HISTORY_MESSAGES_WITH_FILES,
    MAX_RAG_CHUNKS,
    FAST_MODE_HISTORY_MESSAGES_NO_FILES,
    FAST_MODE_HISTORY_MESSAGES_WITH_FILES,
    THINKING_MODE_HISTORY_MESSAGES_NO_FILES,
    THINKING_MODE_HISTORY_MESSAGES_WITH_FILES,
    DEFAULT_MODE
)
from utils.helpers import estimate_tokens
import json
import os

def build_context_prompt(session_id, user_query, mode="fast"):
    """
    Build complete context prompt for LLM
    Includes: system prompt + user prefs + chat history + RAG context + current query
    Args:
        session_id: Chat session ID
        user_query: User's current query
        mode: "fast" (less context) or "thinking" (more context)
    """
    prompt_parts = []
    
    # 1. System Prompt
    prompt_parts.append(SYSTEM_PROMPT)
    
    # 2. User Preferences & Personalization
    user_data_file = "user_data.json"
    user_notes_file = "user_notes.json"
    
    # Load user data
    if os.path.exists(user_data_file):
        with open(user_data_file, 'r') as f:
            user_data = json.load(f)
            if user_data.get("name"):
                prompt_parts.append(f"\nUser's name: {user_data['name']}")
    
    # Load user notes for personalization
    if os.path.exists(user_notes_file):
        with open(user_notes_file, 'r') as f:
            user_notes = json.load(f)
            notes_content = user_notes.get("notes", "").strip()
            if notes_content:
                prompt_parts.append("\n--- User Personalization Notes ---")
                prompt_parts.append(notes_content)
                prompt_parts.append("(Use this information to personalize responses and understand the user's preferences, context, and needs.)")
    
    # 3. Check if session has files
    has_files = check_session_has_files(session_id)
    
    # 4. Chat History (limited based on file presence and mode)
    # Get appropriate history limits based on mode
    if mode == "thinking":
        history_limit = THINKING_MODE_HISTORY_MESSAGES_WITH_FILES if has_files else THINKING_MODE_HISTORY_MESSAGES_NO_FILES
    else:  # fast mode or default
        history_limit = FAST_MODE_HISTORY_MESSAGES_NO_FILES if not has_files else FAST_MODE_HISTORY_MESSAGES_WITH_FILES
    
    history = get_session_messages(session_id, limit=history_limit)
    
    if history:
        prompt_parts.append("\n--- Previous Conversation ---")
        for role, content, _ in history:
            prompt_parts.append(f"{role.capitalize()}: {content}")
    
    # 5. RAG Context (if files exist)
    if has_files:
        relevant_chunks = query_relevant_chunks(session_id, user_query, n_results=MAX_RAG_CHUNKS)
        
        if relevant_chunks and relevant_chunks['documents'][0]:
            prompt_parts.append("\n--- Relevant Document Context ---")
            for i, chunk in enumerate(relevant_chunks['documents'][0], 1):
                metadata = relevant_chunks['metadatas'][0][i-1]
                prompt_parts.append(f"\n[From {metadata['filename']}]")
                prompt_parts.append(chunk)
    
    # 6. Current Query
    prompt_parts.append(f"\n--- Current Query ---")
    prompt_parts.append(f"User: {user_query}")
    prompt_parts.append("Assistant:")
    
    final_prompt = "\n".join(prompt_parts)
    
    # Token estimation for debugging
    total_tokens = estimate_tokens(final_prompt)
    print(f"📊 Context tokens: ~{total_tokens}")
    
    return final_prompt

def get_chat_response(session_id, user_query, mode="fast"):
    """
    Main function to get LLM response with full context
    Args:
        session_id: Chat session ID
        user_query: User's current query
        mode: "fast" (gemma3:270m) or "thinking" (gemma3n:e2b)
    """
    # Build context-aware prompt
    prompt = build_context_prompt(session_id, user_query, mode=mode)
    
    # Get response from LLM with selected model
    response = ask_ollama(prompt, mode=mode)
    
    return response