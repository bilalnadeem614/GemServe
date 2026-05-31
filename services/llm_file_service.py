# services/llm_file_service.py
import os
import re
import json
from services.file_service import (
    open_file,
    delete_file,
    create_file,
    find_files_by_name,
    search_in_cache,
)
from services.llm_service import _call_ollama


# ---------------------------------------------------------------------------
# LLM-based intent parsing  (fast model, short prompt, 15s timeout)
# ---------------------------------------------------------------------------

_INTENT_PROMPT = """You are a file operation intent extractor. Given a user message, extract:
1. action: one of "open", "delete", "create", "search", or "none"
2. filename: the file or name mentioned (or null if none)

Rules:
- "open", "show", "view", "launch", "display", "load", "access" → action: "open"
- "delete", "remove", "trash", "erase", "get rid of", "wipe" → action: "delete"
- "create", "make", "new file", "generate", "touch" → action: "create"
- "find", "search", "locate", "look for", "where is", "list" → action: "search"
- For filename: extract ONLY the file/name part, no action words
- If no file operation is intended (e.g. "how are you", "write a poem"), use action: "none"

Respond ONLY with a JSON object, no explanation:
{"action": "open", "filename": "resume.pdf"}

Examples:
"Can you please open my resume?" → {"action": "open", "filename": "resume"}
"I need to see the DMC certificate" → {"action": "open", "filename": "DMC"}
"Get rid of that old notes file" → {"action": "delete", "filename": "notes"}
"Could you find Talha's resume?" → {"action": "search", "filename": "Talha resume"}
"Show me where my photos are" → {"action": "search", "filename": "photos"}
"Create a new file called report" → {"action": "create", "filename": "report"}
"What is the weather today?" → {"action": "none", "filename": null}

User message: "{message}"
JSON:"""


def _llm_parse_intent(text: str) -> dict:
    """
    Use the fast LLM (270m) to extract file operation intent.
    Falls back to regex if LLM fails or times out.
    """
    from utils.config import OLLAMA_FAST_MODEL

    try:
        prompt = _INTENT_PROMPT.replace("{message}", text)
        response = _call_ollama(prompt, OLLAMA_FAST_MODEL, timeout=15).strip()

        # Extract JSON from response
        # Try direct parse first
        try:
            result = json.loads(response)
        except Exception:
            # Find JSON object in response
            m = re.search(r"\{[^{}]+\}", response)
            if m:
                result = json.loads(m.group())
            else:
                raise ValueError("No JSON found")

        action = result.get("action", "none").lower().strip()
        filename = result.get("filename")
        filenames = result.get("filenames") or []

        # Normalise filename
        if filename and str(filename).lower() in ("null", "none", ""):
            filename = None
        filtered = [f for f in (filenames or []) if f and str(f).lower() not in ("null", "none", "")]
        if not filtered and filename:
            filtered = [filename]

        if action in ("open", "delete", "create", "search"):
            return {
                "action": action,
                "filename": filename,
                "filenames": filtered,
                "confidence": 0.9,
                "source": "llm",
            }

    except Exception as e:
        print(f"⚠️ LLM intent parse failed: {e} — falling back to regex")

    # Fallback to regex
    return _regex_parse_intent(text)


def _regex_parse_intent(text: str) -> dict:
    """Regex fallback for when LLM is unavailable or times out."""
    t = text.lower().strip()

    _DELETE_WORDS = r"\b(delete|remove|trash|erase|get rid of|wipe)\b"
    _OPEN_WORDS = r"\b(open|launch|start|show|view|display|run|access|load)\b"
    _CREATE_WORDS = r"\b(create|make|new|generate|touch|add)\b"
    _SEARCH_WORDS = r"\b(find|search|locate|look for|where is|where are|list)\b"

    if re.search(_DELETE_WORDS, t):
        action = "delete"
    elif re.search(_OPEN_WORDS, t):
        action = "open"
    elif re.search(_CREATE_WORDS, t):
        action = "create"
    elif re.search(_SEARCH_WORDS, t):
        action = "search"
    elif re.fullmatch(r"[\w\-. ]+\.\w{2,5}", t.strip()):
        action = "open"  # bare filename → open
    else:
        action = "unknown"

        # AFTER
    filenames = _extract_filenames(text)
    # If segment-based extraction missed files, try whole-text extraction as fallback
    if not filenames:
        single = _extract_filename(text)
        if single:
            filenames = [single]
    filename = filenames[0] if filenames else None
    
    confidence = (
        0.9
        if (action != "unknown" and filename)
        else 0.6 if action != "unknown" else 0.0
    )

    return {
        "action": action,
        "filename": filename,
        "filenames": filenames,
        "confidence": confidence,
        "source": "regex",
    }


def _extract_filenames(text: str) -> list[str]:
    """
    Extract all filenames (with extensions) from user text.
    Splits on conjunctions first, then extracts extension-bearing tokens.
    """
    # Split on 'and', 'or', commas, semicolons, newlines
    segments = re.split(r"\band\b|\bor\b|,|;|\n", text, flags=re.I)

    _ACTION_STRIP = re.compile(
        r"^\s*(?:please\s+)?(?:can\s+you\s+)?(?:could\s+you\s+)?"
        r"(?:open|delete|remove|trash|erase|create|make|find|search|locate|"
        r"look\s+for|where\s+is|where\s+are|show|view|display|launch|start|"
        r"access|load)\s+"
        r"(?:(?:the|my|a|an|file|document|called|named|titled)\s+)*",
        re.I,
    )
    _ARTICLE_STRIP = re.compile(
        r"^(?:(?:the|my|a|an|file|document|called|named|titled)\s+)+", re.I
    )
    # Match a strict filename: word chars/hyphens, a dot, 2-5 word-char extension
    _FNAME_RE = re.compile(r"\b([\w][\w\-]*(?:\.[\w\-]+)*\.\w{2,5})\b")

    results = []
    for segment in segments:
        seg = segment.strip()
        # Strip leading action words (only on first segment or if present)
        seg = _ACTION_STRIP.sub("", seg)
        seg = _ARTICLE_STRIP.sub("", seg).strip()

        for m in _FNAME_RE.finditer(seg):
            candidate = m.group(1).strip()
            if candidate.lower() in ("file", "document"):
                continue
            if candidate not in results:
                results.append(candidate)

    # Fallback: scan the whole original text if nothing found via segments
    if not results:
        for m in _FNAME_RE.finditer(text):
            candidate = m.group(1).strip()
            if candidate.lower() not in ("file", "document") and candidate not in results:
                results.append(candidate)

    return results


def _extract_filename(text: str) -> str | None:
    """Extract filename from text using regex strategies."""
    # Strip leading action verb
    # Strip leading action verb
    cleaned = re.sub(
        r"^(?:open|delete|remove|trash|erase|create|make|find|search|locate|"
        r"launch|show|view|look\s+for|get\s+rid\s+of|i\s+need\s+to\s+see|"
        r"can\s+you|please|could\s+you)\s+"
        r"(?:the\s+|my\s+|a\s+|me\s+)?(?:file\s+)?",
        "",
        text.strip(),
        flags=re.I,
    )

    # Has extension
    m = re.search(r"^([\w\-. ]+?\.\w{2,5})\b", cleaned)
    if m:
        return m.group(1).strip()

    # Quoted string
    m = re.search(r'["\']([^"\']+)["\']', text)
    if m:
        candidate = re.sub(
            r"^(?:open|delete|remove|create|make|find|search|launch|show|view)\s+",
            "",
            m.group(1).strip(),
            flags=re.I,
        )
        return candidate or None

    # "file/document called X"
    m = re.search(
        r'(?:file|document|folder)\s+(?:called|named|titled)\s+"?([^"]+?)"?\s*$',
        text,
        re.I,
    )
    if m:
        return m.group(1).strip()

    # Word after action verb
    m = re.search(
        r"(?:open|delete|remove|create|make|find|search|launch|show|view|see)\s+"
        r"(?:the\s+|my\s+|a\s+)?([A-Za-z0-9_\-. ]{2,60}?)(?:\s+file|\s+document|$)",
        text,
        re.I,
    )
    if m:
        candidate = m.group(1).strip()
        _SKIP = {"file", "document", "folder", "me", "it", "this", "that", ""}
        if candidate.lower() not in _SKIP:
            return candidate

    return None


# ---------------------------------------------------------------------------
# LLM-based routing  — uses the currently selected model to classify intent
# Falls back to regex if the model times out or returns garbage
# ---------------------------------------------------------------------------
import os

_ROUTE_PROMPT = """Classify this message. Reply with ONLY one word: FILE or CHAT.

FILE = user wants to open, delete, create, find, or search for a specific file by name on their computer.
CHAT = anything else — questions, summarizing/reading an uploaded file, general conversation, writing tasks.

IMPORTANT: If the message says "this file", "the file", "uploaded file", or refers to content already in the conversation, that is CHAT not FILE.

Examples:
"open my resume" → FILE
"delete notes.txt" → FILE
"find Talha DMC" → FILE
"create report.docx" → FILE
"open the file called budget" → FILE
"who are you" → CHAT
"summarize this file" → CHAT
"can you summarize this file?" → CHAT
"what does this document say?" → CHAT
"what is in the uploaded file?" → CHAT
"explain the file I uploaded" → CHAT
"write a poem" → CHAT
"what is the weather" → CHAT
"hello" → CHAT
"I need to see my certificate" → FILE

Message: "{message}"
Answer:"""


def is_file_operation_request(text: str, model: str = None) -> tuple[bool, float]:
    """
    Classify whether the message is a file operation using regex only.
    Fast, deterministic, no LLM calls.

    Args:
        text  : user message
        model : (ignored) kept for backward compatibility

    Returns (is_file_op: bool, confidence: float)
    """
    return _regex_is_file_op(text)


def _regex_is_file_op(text: str) -> tuple[bool, float]:
    """Instant regex fallback for routing when LLM is unavailable."""
    t = text.strip().lower()

    # If message clearly refers to already-uploaded/context file → always CHAT
    _CONTEXT_RE = r"\b(this\s+file|the\s+file|uploaded\s+file|this\s+document|the\s+document|this\s+pdf|the\s+pdf|my\s+upload)\b"
    if re.search(_CONTEXT_RE, t):
        return False, 0.0

    _ACTION_RE = (
        r"\b(?:open|launch|start|delete|remove|trash|erase|create|make|"
        r"find|search|locate|look\s+for|where\s+is|get\s+rid\s+of|"
        r"show\s+me|i\s+need\s+to\s+see|can\s+you\s+(?:open|find|delete|show))\b"
    )
    has_action = bool(re.search(_ACTION_RE, t))
    has_extension = bool(re.search(r"\.\w{2,5}\b", t))
    has_file_noun = bool(
        re.search(
            r"\b(?:file|document|folder|photo|image|video|certificate|resume|cv)\b", t
        )
    )
    has_quotes = bool(re.search(r'["\'\']', t))

    if has_action and (has_extension or has_file_noun or has_quotes):
        return True, 0.9
    if has_extension and re.fullmatch(r"[\w\-. ]+\.\w{2,5}", t.strip()):
        return True, 0.85

    _CHAT_WORDS = {
        "me",
        "something",
        "anything",
        "that",
        "this",
        "it",
        "one",
        "some",
        "any",
        "more",
        "all",
        "new",
        "good",
        "best",
        "great",
        "a",
        "an",
        "the",
        "poem",
        "story",
        "joke",
        "recipe",
        "idea",
        "example",
        "way",
        "help",
        "info",
        "you",
    }
    if has_action:
        m = re.search(
            r"\b(?:open|delete|remove|find|search|create|make|launch|start|show)\s+"
            r"(?:the\s+|my\s+|a\s+)?(\w[\w\-. ]{1,40})",
            t,
        )
        if m:
            target = m.group(1).strip().split()[0]
            if target not in _CHAT_WORDS and len(target) >= 3:
                return True, 0.75

    return False, 0.0


# ---------------------------------------------------------------------------
# Smart file finder
# ---------------------------------------------------------------------------


def _smart_find(filename: str, session_id=None) -> list:
    """
    Search using multiple strategies so partial names and no-extension
    queries still find the right file.
    """
    seen = set()
    found = []

    def _add(paths):
        for p in paths:
            if p not in seen:
                seen.add(p)
                found.append(p)

    if "." in filename:
        dot_idx = filename.rfind(".")
        name_part = filename[:dot_idx]
        ext_part = filename[dot_idx:]
    else:
        name_part = filename
        ext_part = ""

    # Strategy 1: exact + space/underscore variants
    for v in {
        filename,
        name_part.replace(" ", "_") + ext_part,
        name_part.replace("_", " ") + ext_part,
    }:
        _add(find_files_by_name(v, session_id=None)["files"])

    if found:
        return found

    # Strategy 2: word fragments (with and without extension)
    words = re.split(r"[\s_\-]+", name_part)
    for word in words:
        if len(word) >= 3:
            for query in {word + ext_part, word}:
                _add(find_files_by_name(query, session_id=None)["files"])

    if found:
        return found

    # Strategy 3: bare name_part (no extension) — catches "resume" → "resume.pdf"
    _add(find_files_by_name(name_part, session_id=None)["files"])

    return found


# Public alias — kept for backwards compatibility with services/__init__.py
def parse_user_intent(text: str) -> dict:
    """Public wrapper around the LLM intent parser with regex fallback."""
    return _llm_parse_intent(text)


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


def handle_llm_file_command(user_prompt: str, session_id=None) -> dict:
    """
    Interpret a natural language file request and execute the appropriate
    file_service function. Uses regex-only for deterministic intent parsing.
    """
    intent = _regex_parse_intent(user_prompt)
    action = intent["action"]
    filename = intent["filename"]
    filenames = intent.get("filenames") or ([filename] if filename else [])

    if action == "none" or (intent["confidence"] < 0.6 and action == "unknown"):
        return {
            "status": "clarify",
            "message": (
                "🤔 I'm not sure which file operation you want.\n\n"
                "Try saying:\n"
                "  • 'Open my resume'\n"
                "  • 'Delete notes.txt'\n"
                "  • 'Create report.docx'\n"
                "  • 'Find my DMC certificate'"
            ),
            "action": None,
            "confidence": intent["confidence"],
        }

    if not filenames:
        return {
            "status": "error",
            "message": (
                f"❌ I understand you want to {action} a file, "
                "but I couldn't work out the filename.\n\n"
                f"Try: '{action.capitalize()} [filename]'"
            ),
            "action": action,
        }

    # ---- OPEN ----
    if action == "open":
        if len(filenames) > 1:
            messages = []
            ambiguous = []
            missing = []
            for name in filenames:
                cache_matches = search_in_cache(session_id, name) if session_id else []
                if cache_matches:
                    if len(cache_matches) == 1:
                        result = open_file(cache_matches[0], session_id)
                        messages.append(result["message"])
                        continue
                    ambiguous.append((name, cache_matches))
                    continue

                files = _smart_find(name, session_id)
                if not files:
                    missing.append(name)
                elif len(files) == 1:
                    result = open_file(files[0], session_id)
                    messages.append(result["message"])
                else:
                    ambiguous.append((name, files))

            if missing:
                return {
                    "status": "error",
                    "message": f"❌ Could not find: {', '.join(missing)}",
                    "action": "open",
                }
            if ambiguous:
                name, files = ambiguous[0]
                return _multi_select_response(files[:20], "open", name)

            return {
                "status": "success",
                "message": "\n\n".join(messages),
                "action": "open",
            }

        cache_matches = search_in_cache(session_id, filename) if session_id else []
        if cache_matches:
            if len(cache_matches) == 1:
                result = open_file(cache_matches[0], session_id)
                return {
                    "status": result["status"],
                    "message": result["message"],
                    "action": "open",
                }
            return _multi_select_response(cache_matches, "open", filename)

        files = _smart_find(filename, session_id)
        if not files:
            return {
                "status": "error",
                "message": f"❌ '{filename}' not found on any drive.",
                "action": "open",
            }
        if len(files) == 1:
            result = open_file(files[0], session_id)
            return {
                "status": result["status"],
                "message": result["message"],
                "action": "open",
            }
        return _multi_select_response(files[:20], "open", filename)

    # ---- DELETE ----
    elif action == "delete":
        if len(filenames) > 1:
            resolved = []
            ambiguous = []
            missing = []
            for name in filenames:
                files = _smart_find(name, session_id)
                if not files:
                    missing.append(name)
                elif len(files) == 1:
                    resolved.append(files[0])
                else:
                    ambiguous.append((name, files))

            # In the DELETE branch, multi-file path — REPLACE the missing check:
            if missing:
                return {
                    "status": "error",
                    "message": (
                        f"❌ Could not find: {', '.join(missing)}\n\n"
                        f"✅ Found: {', '.join(os.path.basename(p) for p in resolved)}"
                        if resolved else
                        f"❌ Could not find any of: {', '.join(missing)}"
                    ),
                    "action": "delete",
                }
            if ambiguous:
                name, files = ambiguous[0]
                return _multi_select_response(files[:20], "delete", name)

            return _delete_multi_confirm(resolved)

        cache_matches = search_in_cache(session_id, filename) if session_id else []
        if cache_matches:
            if len(cache_matches) == 1:
                return _delete_confirm(cache_matches[0])
            return _multi_select_response(cache_matches, "delete", filename)

        files = _smart_find(filename, session_id)
        if not files:
            return {
                "status": "error",
                "message": f"❌ '{filename}' not found on any drive.",
                "action": "delete",
            }
        if len(files) == 1:
            return _delete_confirm(files[0])
        return _multi_select_response(files[:20], "delete", filename)

    # ---- CREATE ----
    elif action == "create":
        label = filenames[0] if len(filenames) == 1 else f"{len(filenames)} files"
        return {
            "status": "ask_location",
            "message": (
                f"📂 Where should I create {label}?\n\n"
                "Options:\n"
                "  1. Desktop (default)\n"
                "  2. Documents\n"
                "  3. Downloads\n"
                "  4. Custom path (e.g., D:\\Projects)\n\n"
                "Type 1, 2, 3, or a full path:"
            ),
            "action": "create",
            "data": {"filenames": filenames, "operation": "create"},
        }

    # ---- SEARCH ----
    elif action == "search":
        if len(filenames) > 1:
            messages = []
            for name in filenames:
                files = _smart_find(name, session_id)
                if not files:
                    messages.append(f"❌ No files matching '{name}' found.")
                    continue
                files_list = "\n".join(f"  {i}. {f}" for i, f in enumerate(files[:20], 1))
                extra = f"\n  … and {len(files) - 20} more" if len(files) > 20 else ""
                messages.append(
                    f"🔍 Found {len(files)} file(s) matching '{name}':\n\n{files_list}{extra}"
                )
            return {
                "status": "success",
                "message": "\n\n".join(messages),
                "action": "search",
            }

        files = _smart_find(filename, session_id)
        if not files:
            return {
                "status": "error",
                "message": f"❌ No files matching '{filename}' found.",
                "action": "search",
            }
        files_list = "\n".join(f"  {i}. {f}" for i, f in enumerate(files[:20], 1))
        extra = f"\n  … and {len(files) - 20} more" if len(files) > 20 else ""
        return {
            "status": "success",
            "message": f"🔍 Found {len(files)} file(s) matching '{filename}':\n\n{files_list}{extra}",
            "action": "search",
            "data": {"files": files, "count": len(files)},
        }

    return {
        "status": "error",
        "message": f"❌ Unknown action: {action}",
        "action": action,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _delete_confirm(filepath: str) -> dict:
    return {
        "status": "confirm",
        "message": f"🗑️ Delete this file?\n📂 {filepath}\n\nType yes to confirm or no to cancel",
        "action": "delete",
        "data": {"files": [filepath], "operation": "delete"},
    }


def _delete_multi_confirm(filepaths: list) -> dict:
    files_list = "\n".join(f"  {i}. {p}" for i, p in enumerate(filepaths, 1))
    return {
        "status": "confirm",
        "message": (
            f"🗑️ Delete these files?\n{files_list}\n\nType yes to confirm or no to cancel"
        ),
        "action": "delete",
        "data": {"files": filepaths, "operation": "delete"},
    }


def _multi_select_response(files: list, operation: str, filename: str) -> dict:
    numbered = "\n".join(f"  {i}. {f}" for i, f in enumerate(files, 1))
    return {
        "status": "select",
        "message": (
            f"📂 Found {len(files)} file(s) matching '{filename}'.\n\n"
            f"{numbered}\n\nEnter the number to {operation}, or cancel"
        ),
        "action": operation,
        "data": {"files": files, "operation": operation, "filename": filename},
    }


# ---------------------------------------------------------------------------
# Follow-up response processor
# ---------------------------------------------------------------------------


def process_file_response(response_text: str, pending_action: dict) -> dict:
    """Handle user reply to multi-step file prompts."""
    state = pending_action.get("state", "select")
    files = pending_action.get("files", [])
    operation = pending_action.get("operation", "")
    r = response_text.strip().lower()

    def _create_files_with_overwrite_check(filenames, custom_path):
        results = []
        for fname in filenames:
            result = create_file(fname, custom_path=custom_path)
            if result.get("status") == "confirm" and result.get("action") == "overwrite":
                filepath = result.get("path") or os.path.join(custom_path, fname)
                return {
                    "status": "overwrite_confirm",
                    "message": result["message"],
                    "data": {
                        "filepath": filepath,
                        "filename": os.path.basename(filepath),
                        "save_path": custom_path,
                        "filenames": filenames,
                        "operation": "create",
                    },
                    "handled": True,
                }
            results.append(result)
        return results

    if state == "select":
        if r in ("cancel", "c", "no"):
            return {
                "status": "success",
                "message": "❌ Operation cancelled.",
                "handled": True,
            }
        try:
            choice = int(r)
            if 1 <= choice <= len(files):
                selected = files[choice - 1]
                if operation == "open":
                    result = open_file(selected)
                    return {
                        "status": result["status"],
                        "message": result["message"],
                        "action": "open",
                        "handled": True,
                    }
                elif operation == "delete":
                    return {
                        "status": "confirm",
                        "message": f"🗑️ Delete this file?\n📂 {selected}\n\nType yes to confirm or no to cancel",
                        "action": "delete_confirm",
                        "data": {"file": selected},
                        "handled": True,
                    }
            return {
                "status": "error",
                "message": f"❌ Please enter a number between 1 and {len(files)}.",
                "handled": False,
            }
        except ValueError:
            return {
                "status": "error",
                "message": "❌ Invalid input — please enter a number or 'cancel'.",
                "handled": False,
            }

    elif state == "delete_confirm":
        
        if r in ("yes", "y"):
            
            
            # Normalize both key styles
            files = pending_action.get("files") or []
            if not files:
                single = pending_action.get("file")
                if single:
                    files = [single]
            
            if not files:
                return {"status": "error", "message": "❌ No file to delete.", "handled": True}
            
            if len(files) > 1:
                results = []
                success = 0
                fail = 0
                for fpath in files:
                    result = delete_file(fpath)
                    if result["status"] == "success":
                        success += 1
                    else:
                        fail += 1
                    results.append(
                        f"{'✅' if result['status'] == 'success' else '❌'} {result['message']}"
                    )
                return {
                    "status": "success",
                    "message": (
                        f"📋 Delete results:\n\n✅ Success: {success}\n❌ Failed: {fail}\n\n"
                        + "\n".join(results)
                    ),
                    "action": "delete",
                    "handled": True,
                }
            result = delete_file(files[0])
            return {
                "status": result["status"],
                "message": result["message"],
                "action": "delete",
                "handled": True,
            }
           
        elif r in ("no", "n", "cancel"):
            return {
                "status": "success",
                "message": "❌ Delete cancelled.",
                "handled": True,
            }
        return {
            "status": "error",
            "message": "❌ Please type yes or no.",
            "handled": False,
        }

    elif state == "location":
        filenames = pending_action.get("filenames") or [pending_action.get("filename", "")]
        if r in ("1", "desktop"):
            save_path = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
            results = _create_files_with_overwrite_check(filenames, save_path)
        elif r in ("2", "documents"):
            save_path = os.path.join(os.environ.get("USERPROFILE", ""), "Documents")
            results = _create_files_with_overwrite_check(filenames, save_path)
        elif r in ("3", "downloads"):
            save_path = os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
            results = _create_files_with_overwrite_check(filenames, save_path)
        elif r in ("4", "custom", "custom path", "path"):
            return {
                "status": "ask_custom_path",
                "message": "📁 Enter the full path (or cancel):",
                "action": "create_custom",
                "handled": True,
            }
        elif r in ("cancel", "c"):
            return {
                "status": "success",
                "message": "❌ Creation cancelled.",
                "handled": True,
            }
        else:
            # Accept direct full path input too
            save_path = response_text.strip()
            results = _create_files_with_overwrite_check(filenames, save_path)

        if isinstance(results, dict):
            return results

        messages = [result["message"] for result in results]
        return {
            "status": "success",
            "message": "\n\n".join(messages),
            "action": "create",
            "handled": True,
        }

    elif state == "custom_path":
        if r in ("cancel", "c"):
            return {
                "status": "success",
                "message": "❌ Creation cancelled.",
                "handled": True,
            }
        filenames = pending_action.get("filenames") or [pending_action.get("filename", "")]
        results = _create_files_with_overwrite_check(filenames, response_text.strip())
        if isinstance(results, dict):
            return results
        messages = [result["message"] for result in results]
        return {
            "status": "success",
            "message": "\n\n".join(messages),
            "action": "create",
            "handled": True,
        }

    return {
        "status": "error",
        "message": "❌ Unexpected state. Please try again.",
        "handled": False,
    }
