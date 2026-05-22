# services/chat_service.py
import json
import os
import re
from html import escape
from datetime import datetime

from db.database import get_session_messages, check_session_has_files
from db.vector_store import query_relevant_chunks
from db.todo_db_helper import insert_task, get_all_tasks
from services.llm_service import (
    _call_ollama_chat,
    OLLAMA_FAST_MODEL,
    OLLAMA_THINKING_MODEL,
)
from utils.config import (
    MAX_HISTORY_MESSAGES_NO_FILES,
    MAX_HISTORY_MESSAGES_WITH_FILES,
    MAX_RAG_CHUNKS,
)
from utils.helpers import estimate_tokens
from utils.extract_info import extract_info

# ── System prompts ────────────────────────────────────────────────────────────

_SYSTEM_THINKING = """You are GemServe, an offline AI desktop assistant built for a Final Year Project.

Rules you must follow:
- Your name is GemServe. Never say you are Gemma, an AI language model, or any other name.
- Answer only what the user asks. Do not add unrequested information.
- If you don't know something, say "I don't know" — do not make up facts.
- Only greet the user on the very first message of a session.
- Be clear and concise."""

_SYSTEM_FAST = """You are GemServe, an offline AI desktop assistant.
Your name is GemServe. Never say you are Gemma.
Answer concisely. Do not make up facts."""

# Seed exchange so 270m model continues as GemServe from the start
_FAST_SEED = [
    {"role": "user", "content": "Who are you?"},
    {
        "role": "assistant",
        "content": "I'm GemServe, your offline AI desktop assistant. How can I help?",
    },
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_user_name() -> str | None:
    try:
        with open("user_data.json", "r") as f:
            return json.load(f).get("name")
    except Exception:
        return None


def _get_user_notes() -> str | None:
    try:
        with open("user_notes.json", "r") as f:
            return json.load(f).get("notes", "").strip() or None
    except Exception:
        return None


# ── Message builders ──────────────────────────────────────────────────────────


def build_messages_thinking(session_id: str, user_query: str) -> list:
    messages = []

    # System prompt
    system = _SYSTEM_THINKING
    name = _get_user_name()
    if name:
        system += f"\nThe user's name is {name}."
    notes = _get_user_notes()
    if notes:
        system += f"\nUser notes: {notes}"
    messages.append({"role": "system", "content": system})

    # RAG context
    if check_session_has_files(session_id):
        chunks = query_relevant_chunks(session_id, user_query, n_results=MAX_RAG_CHUNKS)
        if chunks and chunks["documents"][0]:
            rag_text = "\n\n".join(
                f"[From {chunks['metadatas'][0][i]['filename']}]\n{chunk}"
                for i, chunk in enumerate(chunks["documents"][0])
            )
            messages.append(
                {
                    "role": "system",
                    "content": f"Document context (use only if relevant):\n{rag_text}",
                }
            )

    # History
    limit = (
        MAX_HISTORY_MESSAGES_WITH_FILES
        if check_session_has_files(session_id)
        else MAX_HISTORY_MESSAGES_NO_FILES
    )
    for role, content, _ in get_session_messages(session_id, limit=limit):
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_query})

    print(
        f"📊 Thinking tokens: ~{estimate_tokens(' '.join(m['content'] for m in messages))}"
    )
    return messages


def build_messages_fast(session_id: str, user_query: str) -> list:
    # FIX: was mixing two implementations (messages list + prompt_parts list)
    # and referencing undefined variables. Rewritten to use messages list only.
    messages = []

    system = _SYSTEM_FAST
    name = _get_user_name()
    if name:
        system += f"\nThe user's name is {name}."
    messages.append({"role": "system", "content": system})

    history = get_session_messages(session_id, limit=4)
    if not history:
        messages.extend(_FAST_SEED)
    else:
        for role, content, _ in history:
            messages.append({"role": role, "content": content})

    # RAG context (if files exist)
    if check_session_has_files(session_id):
        chunks = query_relevant_chunks(session_id, user_query, n_results=MAX_RAG_CHUNKS)
        if chunks and chunks["documents"][0]:
            rag_text = "\n\n".join(
                f"[From {chunks['metadatas'][0][i]['filename']}]\n{chunk}"
                for i, chunk in enumerate(chunks["documents"][0])
            )
            messages.append(
                {
                    "role": "system",
                    "content": f"Document context (use only if relevant):\n{rag_text}",
                }
            )

    messages.append({"role": "user", "content": user_query})

    print(
        f"📊 Fast tokens: ~{estimate_tokens(' '.join(m['content'] for m in messages))}"
    )
    return messages


# ── Public API ────────────────────────────────────────────────────────────────


def get_chat_response(session_id: str, user_query: str, mode: str = "fast") -> str:
    # 1. Check for web search intent first.
    is_search, search_query = detect_search_intent(user_query)
    if is_search:
        return handle_search_intent(search_query)

    # 2. Existing todo intent check.
    is_todo, todo_text = detect_todo_intent(user_query)
    if is_todo:
        return handle_todo_intent(todo_text)

    # 3. Existing Ollama routing.
    if mode == "thinking":
        messages = build_messages_thinking(session_id, user_query)
        model, timeout = OLLAMA_THINKING_MODEL, 180
    else:
        messages = build_messages_fast(session_id, user_query)
        model, timeout = OLLAMA_FAST_MODEL, 60

    return _call_ollama_chat(messages, model, timeout)


# Backward-compat alias
def build_context_prompt(session_id: str, user_query: str) -> str:
    # FIX: was defined twice; second definition called undefined symbols.
    messages = build_messages_thinking(session_id, user_query)
    return "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in messages)


# ── Search helpers ───────────────────────────────────────────────────────────


def detect_search_intent(user_query: str):
    """Detects if user wants to search the web using 'search web <query>'."""
    pattern = r'^search web\s+(.+)'
    match = re.match(pattern, user_query.lower().strip())
    if match:
        return True, match.group(1).strip()
    return False, None


def handle_search_intent(query: str) -> str:
    """Calls Gemini Search and formats the answer with references."""
    from services.llm_service import call_gemini_search

    result = call_gemini_search(query)
    answer = result["answer"]
    sources = result["sources"]

    if not sources:
        return answer

    safe_answer = escape(str(answer)).replace("\n", "<br>")
    ref_text = "<br><br><b style=\"font-size: 14px; color: #6366F1;\">[Refrences:]</b><br><br>"
    for i, src in enumerate(sources, 1):
        title = escape(str(src.get("title") or f"Refrence-{i}"))
        uri = escape(str(src.get("uri") or ""))
        if uri:
            ref_text += f"&nbsp;&nbsp;<b>[Refrence-{i}]</b> <a href=\"{uri}\" style=\"color: #06B6D4; text-decoration: underline;\">{title}</a><br>"
        else:
            ref_text += f"&nbsp;&nbsp;<b>[Refrence-{i}]</b> {title}<br>"

    return f"{safe_answer}{ref_text}"


# ── Todo helpers ──────────────────────────────────────────────────────────────


def detect_todo_intent(user_query: str):
    query_lower = user_query.lower().strip()

    todo_patterns = [
        r'^yes add task\s+(.+)',
        r'^add task\s+(.+)',
        r'^add to(?: my)? (?:todo|to-do|task list)\s+(.+)',
        r'^remind me to\s+(.+)',
        r'^create task\s+(.+)',
        r'^new task\s+(.+)',
        r'^schedule\s+(.+)',
        r'^todo\s+(.+)',
        r'^task\s+(.+)',
        r'^don\'t forget to\s+(.+)',
        r'^dont forget to\s+(.+)',
        r'^i need to\s+(.+)',
        r'^make sure to\s+(.+)',
    ]

    for pattern in todo_patterns:
        match = re.match(pattern, query_lower)
        if match:
            return True, match.group(1).strip()

    return False, None


def validate_task_datetime(task_date: str, task_time: str):
    """
    Validate that task date/time is not in the past.
    Returns (is_valid, error_message).
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    try:
        task_date_obj = datetime.strptime(task_date, "%Y-%m-%d").date()
    except ValueError:
        return False, (
            f"❌ Invalid date format: '{task_date}'. "
            "Please use format like '2025-03-10' or say 'tomorrow'."
        )

    if task_date_obj < now.date():
        return False, (
            f"❌ Cannot add task in the past!\n\n"
            f"📅 You entered: {task_date}\n"
            f"📅 Today is: {today_str}\n\n"
            "Please provide a current or future date."
        )

    if task_date_obj == now.date() and task_time:
        try:
            task_time_clean = task_time.strip()
            if "am" in task_time_clean.lower() or "pm" in task_time_clean.lower():
                task_time_obj = datetime.strptime(task_time_clean, "%I:%M %p").time()
            else:
                task_time_obj = datetime.strptime(task_time_clean, "%H:%M").time()

            if task_time_obj < now.time():
                current_time_str = now.strftime("%I:%M %p")
                return False, (
                    f"❌ Cannot add task in the past!\n\n"
                    f"⏰ You entered: {task_time}\n"
                    f"⏰ Current time: {current_time_str}\n\n"
                    "Please provide a future time for today, or specify a future date."
                )
        except ValueError:
            pass  # Skip time validation if parsing fails

    return True, None


def handle_todo_intent(task_text: str) -> str:
    """
    Extract info, validate datetime, check for duplicates, and insert task into DB.
    Returns a confirmation message string.
    """
    title, task_date, task_time = extract_info(task_text)

    if not title:
        return (
            "❌ Could not understand the task.\n\n"
            "💡 Try like:\n"
            "  • 'add task buy groceries tomorrow at 5pm'\n"
            "  • 'remind me to call doctor on 2026-03-10 at 10am'\n"
            "  • 'todo finish report'"
        )

    is_valid, error_msg = validate_task_datetime(task_date, task_time)
    if not is_valid:
        return error_msg

    existing_tasks = get_all_tasks()
    for task in existing_tasks:
        existing_title = str(task[1]).lower().strip()
        existing_date = str(task[2]).strip()

        if existing_title == title.lower().strip() and existing_date == task_date:
            return (
                f"⚠️ Task already exists!\n\n"
                f"📝 Title: {task[1]}\n"
                f"📅 Date: {existing_date}\n"
                f"⏰ Time: {task[3] if task[3] else '(no time set)'}\n\n"
                f"Add anyway? Type 'yes add task {task_text}' to force add."
            )

    try:
        insert_task(title, task_date, task_time)
        time_str = f"{task_time}" if task_time else "(no time set)"
        return (
            f"✅ Task added to your Todo List!\n\n"
            f"📝 Title: {title}\n"
            f"📅 Date: {task_date}\n"
            f"⏰ Time: {time_str}"
        )
    except Exception as e:
        return f"❌ Failed to add task: {str(e)}"