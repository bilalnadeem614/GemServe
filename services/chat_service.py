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
    MAX_RAG_CHUNKS
)
from utils.helpers import estimate_tokens
import json
import os

def build_context_prompt(session_id, user_query):
    """
    Build complete context prompt for LLM
    Includes: system prompt + user prefs + chat history + RAG context + current query
    """
    prompt_parts = []
    
    # 1. System Prompt
    prompt_parts.append(SYSTEM_PROMPT)
    
    # 2. User Preferences
    user_data_file = "user_data.json"
    if os.path.exists(user_data_file):
        with open(user_data_file, 'r') as f:
            user_data = json.load(f)
            if user_data.get("name"):
                prompt_parts.append(f"\nUser's name: {user_data['name']}")
    
    # 3. Check if session has files
    has_files = check_session_has_files(session_id)
    
    # 4. Chat History (limited based on file presence)
    history_limit = MAX_HISTORY_MESSAGES_WITH_FILES if has_files else MAX_HISTORY_MESSAGES_NO_FILES
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

def get_chat_response(session_id, user_query):
    """
    Main function to get LLM response with full context
    """
    # Build context-aware prompt
    prompt = build_context_prompt(session_id, user_query)
    
    # Get response from LLM
    response = ask_ollama(prompt)
    
    return response