# # services/file_advanced_service.py
# """
# Advanced file operations:
# - Rename single or multiple files
# - Move single or multiple files
# - Search with user-defined location (LLM + regex)
# """

# import os
# import re
# import json
# import string
# from pathlib import Path
# from services.llm_service import _call_ollama
# from utils.config import OLLAMA_FAST_MODEL

# # ─────────────────────────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────────────────────────


# def get_all_drives() -> list:
#     drives = []
#     for letter in string.ascii_uppercase:
#         drive = f"{letter}:\\"
#         if os.path.exists(drive):
#             drives.append(drive)
#     return drives


# def _skip_dirs() -> set:
#     return {
#         "Windows",
#         "System Volume Information",
#         "$Recycle.Bin",
#         "ProgramData",
#         "Program Files",
#         "Program Files (x86)",
#         "System32",
#         "SysWOW64",
#         "node_modules",
#         "venv",
#         ".git",
#         "AppData",
#     }


# # ─────────────────────────────────────────────────────────────
# # SEARCH WITH USER-DEFINED LOCATION
# # Supports both LLM-guided and regex search
# # ─────────────────────────────────────────────────────────────


# def search_in_location(
#     filename: str, location: str = None, max_depth: int = 15
# ) -> dict:
#     """
#     Search for files in a specific location or all drives.
#     location can be: drive letter (C:\\), folder path, or None (all drives).

#     Returns:
#         {"status": ..., "files": [...], "count": int, "message": str}
#     """
#     # Determine search roots
#     if location:
#         location = location.strip().strip('"').strip("'")
#         # Handle drive letter like "C" or "C:" or "C:\\"
#         if len(location) == 1 and location.isalpha():
#             location = f"{location}:\\"
#         elif len(location) == 2 and location.endswith(":"):
#             location = location + "\\"

#         if not os.path.exists(location):
#             return {
#                 "status": "error",
#                 "files": [],
#                 "count": 0,
#                 "message": f"❌ Location not found: {location}",
#             }
#         search_roots = [location]
#     else:
#         search_roots = get_all_drives()

#     user_name, user_ext = os.path.splitext(filename.lower())
#     user_norm = user_name.replace("_", " ").replace("-", " ")
#     skip = _skip_dirs()
#     matches = []

#     def file_matches(f: str) -> bool:
#         name, ext = os.path.splitext(f)
#         name_l = name.lower()
#         name_n = name_l.replace("_", " ").replace("-", " ")
#         if user_ext and ext.lower() != user_ext.lower():
#             return False
#         return (
#             name_l == user_name
#             or name_l.startswith(user_name)
#             or name_n.startswith(user_norm)
#             or user_name in name_l
#             or user_norm in name_n
#         )

#     for root_path in search_roots:
#         try:
#             for root, dirs, files in os.walk(root_path):
#                 depth = root.count(os.sep) - root_path.count(os.sep)
#                 if depth > max_depth:
#                     dirs[:] = []
#                     continue
#                 dirs[:] = [
#                     d
#                     for d in dirs
#                     if not d.startswith(".") and not d.startswith("$") and d not in skip
#                 ]
#                 for f in files:
#                     if file_matches(f):
#                         full = os.path.join(root, f)
#                         if full not in matches:
#                             matches.append(full)
#         except (PermissionError, OSError):
#             continue

#     if not matches:
#         loc_str = location if location else "all drives"
#         return {
#             "status": "not_found",
#             "files": [],
#             "count": 0,
#             "message": f"❌ '{filename}' not found in {loc_str}",
#         }

#     return {
#         "status": "found",
#         "files": matches,
#         "count": len(matches),
#         "message": f"🔍 Found {len(matches)} file(s)",
#     }


# # ─────────────────────────────────────────────────────────────
# # LLM INTENT PARSER FOR ADVANCED OPERATIONS
# # ─────────────────────────────────────────────────────────────

# _ADVANCED_INTENT_PROMPT = """You are a file operation intent extractor. Given a user message, extract the advanced file operation.

# Return ONLY a JSON object:
# {
#   "action": "rename" | "move" | "search_location" | "none",
#   "files": ["file1", "file2"],
#   "new_names": ["newname1", "newname2"],
#   "destination": "path or null",
#   "location": "search location or null"
# }

# Rules:
# - "rename" → user wants to rename file(s). files = original names, new_names = new names
# - "move" → user wants to move file(s). files = filenames, destination = target path
# - "search_location" → user wants to search in specific location. files = [filename], location = where to search
# - "none" → not an advanced file operation

# Examples:
# "rename report.txt to summary.txt" → {"action":"rename","files":["report.txt"],"new_names":["summary.txt"],"destination":null,"location":null}
# "rename file1.txt to a.txt and file2.txt to b.txt" → {"action":"rename","files":["file1.txt","file2.txt"],"new_names":["a.txt","b.txt"],"destination":null,"location":null}
# "move resume.pdf to C:\\Documents" → {"action":"move","files":["resume.pdf"],"new_names":[],"destination":"C:\\Documents","location":null}
# "move file1.txt and file2.txt to D:\\Backup" → {"action":"move","files":["file1.txt","file2.txt"],"new_names":[],"destination":"D:\\Backup","location":null}
# "search for notes.txt in C drive" → {"action":"search_location","files":["notes.txt"],"new_names":[],"destination":null,"location":"C:\\"}
# "find resume in D:\\Projects" → {"action":"search_location","files":["resume"],"new_names":[],"destination":null,"location":"D:\\Projects"}
# "hello" → {"action":"none","files":[],"new_names":[],"destination":null,"location":null}

# User message: "{message}"
# JSON:"""


# def parse_advanced_intent(text: str) -> dict:
#     """Use LLM to parse advanced file operation intent, with regex fallback."""
#     try:
#         prompt = _ADVANCED_INTENT_PROMPT.replace("{message}", text)
#         response = _call_ollama(prompt, OLLAMA_FAST_MODEL, timeout=15).strip()

#         try:
#             result = json.loads(response)
#         except Exception:
#             m = re.search(r"\{.*\}", response, re.DOTALL)
#             if m:
#                 result = json.loads(m.group())
#             else:
#                 raise ValueError("No JSON found")

#         action = result.get("action", "none").lower()
#         if action in ("rename", "move", "search_location"):
#             return {
#                 "action": action,
#                 "files": result.get("files", []),
#                 "new_names": result.get("new_names", []),
#                 "destination": result.get("destination"),
#                 "location": result.get("location"),
#                 "source": "llm",
#             }
#     except Exception as e:
#         print(f"⚠️ Advanced intent LLM parse failed: {e} — using regex")

#     return _regex_parse_advanced(text)


# def _regex_parse_advanced(text: str) -> dict:
#     """Regex fallback for advanced file intent."""

#     t = text.lower().strip()

#     base = {
#         "action": "none",
#         "files": [],
#         "new_names": [],
#         "destination": None,
#         "location": None,
#         "source": "regex",
#     }

#     # ─────────────────────────────────────────
#     # RENAME DETECTION
#     # ─────────────────────────────────────────
#     if re.search(r"\b(rename|change name)\b", t):

#         # Pattern:
#         # rename old.txt to new.txt
#         pairs = re.findall(
#             r"(\S+\.\w+)\s+to\s+(\S+\.\w+)",
#             text,
#             re.I,
#         )

#         if pairs:
#             return {
#                 **base,
#                 "action": "rename",
#                 "files": [p[0] for p in pairs],
#                 "new_names": [p[1] for p in pairs],
#             }

#         return {
#             **base,
#             "action": "rename",
#         }

#     # ─────────────────────────────────────────
#     # MOVE DETECTION
#     # ─────────────────────────────────────────
#     if re.search(r"\b(move|transfer|copy to)\b", t):

#         # Extract destination
#         dest_match = re.search(
#             r'\b(?:to|into|in)\s+["\']?([A-Za-z]:\\[^\s"\']+)',
#             text,
#             re.I,
#         )

#         dest = dest_match.group(1).strip() if dest_match else None

#         # Extract files
#         file_matches = re.findall(
#             r"([\w\-. ]+\.\w{2,5})",
#             text,
#             re.I,
#         )

#         return {
#             **base,
#             "action": "move",
#             "files": file_matches,
#             "destination": dest,
#         }

#     # ─────────────────────────────────────────
#     # SEARCH LOCATION DETECTION
#     # ─────────────────────────────────────────
#     if re.search(r"\b(search|find|look for)\b", t):

#         # Extract filename
#         file_match = re.search(
#             r"(?:search|find|look for)\s+(?:for\s+)?([^\s]+(?:\.\w{2,5})?)",
#             text,
#             re.I,
#         )

#         fname = file_match.group(1).strip() if file_match else None

#         # Extract location
#         loc_match = re.search(
#             r"\b(?:in|inside|on|at)\s+([A-Za-z]:\\[^\n\r]*|[A-Za-z]\s*drive)",
#             text,
#             re.I,
#         )

#         loc = None

#         if loc_match:
#             raw = loc_match.group(1).strip()

#             # Convert "C drive" → "C:\\"
#             if "drive" in raw.lower():
#                 loc = f"{raw[0].upper()}:\\"
#             else:
#                 loc = raw

#         return {
#             **base,
#             "action": "search_location",
#             "files": [fname] if fname else [],
#             "location": loc,
#         }

#     return base


# def is_advanced_file_command(text: str) -> bool:
#     """Quick check if text is an advanced file command."""
#     t = text.lower()
#     if re.search(r"\b(rename|change name of)\b", t):
#         return True
#     if re.search(r"\b(move|transfer)\b.{0,20}\b(file|to|into)\b", t):
#         return True
#     if re.search(
#         r"\b(search|find|look for)\b.{0,30}\b(in|on|drive|folder|directory)\b", t
#     ):
#         return True
#     return False


# # ─────────────────────────────────────────────────────────────
# # RENAME OPERATIONS
# # ─────────────────────────────────────────────────────────────


# def rename_file(old_path: str, new_name: str) -> dict:
#     """Rename a single file."""
#     old = Path(old_path)
#     if not old.exists():
#         return {"status": "error", "message": f"❌ File not found: {old_path}"}

#     new_path = old.parent / new_name
#     if new_path.exists():
#         return {
#             "status": "confirm_overwrite",
#             "message": f"⚠️ '{new_name}' already exists in {old.parent}.\n\nType 'yes' to overwrite or 'no' to cancel.",
#             "old_path": str(old),
#             "new_path": str(new_path),
#         }

#     try:
#         old.rename(new_path)
#         return {"status": "success", "message": f"✅ Renamed: {old.name} → {new_name}"}
#     except Exception as e:
#         return {"status": "error", "message": f"❌ Rename failed: {str(e)}"}


# def rename_multiple_files(file_pairs: list) -> dict:
#     """
#     Rename multiple files.
#     file_pairs: [{"old_path": ..., "new_name": ...}, ...]
#     """
#     results = []
#     success_count = 0
#     fail_count = 0

#     for pair in file_pairs:
#         result = rename_file(pair["old_path"], pair["new_name"])
#         results.append(
#             f"{'✅' if result['status'] == 'success' else '❌'} {result['message']}"
#         )
#         if result["status"] == "success":
#             success_count += 1
#         else:
#             fail_count += 1

#     summary = f"📋 Rename Results: {success_count} succeeded, {fail_count} failed\n\n"
#     return {
#         "status": "success" if fail_count == 0 else "partial",
#         "message": summary + "\n".join(results),
#     }


# # ─────────────────────────────────────────────────────────────
# # MOVE OPERATIONS
# # ─────────────────────────────────────────────────────────────


# def move_file(src_path: str, dest_dir: str) -> dict:
#     """Move a single file to destination directory."""
#     src = Path(src_path)
#     if not src.exists():
#         return {"status": "error", "message": f"❌ File not found: {src_path}"}

#     dest = Path(dest_dir)
#     if not dest.exists():
#         return {"status": "error", "message": f"❌ Destination not found: {dest_dir}"}

#     if not dest.is_dir():
#         return {
#             "status": "error",
#             "message": f"❌ Destination must be a folder: {dest_dir}",
#         }

#     new_path = dest / src.name
#     if new_path.exists():
#         return {
#             "status": "confirm_overwrite",
#             "message": f"⚠️ '{src.name}' already exists in {dest_dir}.\n\nType 'yes' to overwrite or 'no' to cancel.",
#             "src_path": str(src),
#             "dest_path": str(new_path),
#         }

#     try:
#         import shutil

#         shutil.move(str(src), str(new_path))
#         return {"status": "success", "message": f"✅ Moved: {src.name} → {dest_dir}"}
#     except Exception as e:
#         return {"status": "error", "message": f"❌ Move failed: {str(e)}"}


# def move_multiple_files(src_paths: list, dest_dir: str) -> dict:
#     """Move multiple files to destination directory."""
#     results = []
#     success_count = 0
#     fail_count = 0

#     for src_path in src_paths:
#         result = move_file(src_path, dest_dir)
#         results.append(
#             f"{'✅' if result['status'] == 'success' else '❌'} {result['message']}"
#         )
#         if result["status"] == "success":
#             success_count += 1
#         else:
#             fail_count += 1

#     summary = f"📋 Move Results: {success_count} succeeded, {fail_count} failed\n\n"
#     return {
#         "status": "success" if fail_count == 0 else "partial",
#         "message": summary + "\n".join(results),
#     }


# # ─────────────────────────────────────────────────────────────
# # MAIN HANDLER
# # ─────────────────────────────────────────────────────────────


# def handle_advanced_file_command(user_prompt: str, session_id=None) -> dict:
#     """
#     Main handler for advanced file operations.
#     Returns dict with status and message for Chat_Bot.py.
#     """
#     intent = parse_advanced_intent(user_prompt)
#     action = intent.get("action", "none")

#     if action == "none":
#         return {"status": "not_advanced", "message": ""}

#     # ── SEARCH IN LOCATION ──
#     if action == "search_location":
#         files = intent.get("files", [])
#         location = intent.get("location")
#         filename = files[0] if files else None

#         if not filename:
#             return {
#                 "status": "need_info",
#                 "message": "❌ Please specify a filename to search for.\n\nExample: 'search for notes.txt in C drive'",
#                 "pending": {"action": "search_location", "location": location},
#             }

#         result = search_in_location(filename, location)
#         if result["status"] == "not_found":
#             return {"status": "error", "message": result["message"]}

#         files_list = "\n".join(
#             f"  {i}. {f}" for i, f in enumerate(result["files"][:20], 1)
#         )
#         extra = f"\n  … and {result['count'] - 20} more" if result["count"] > 20 else ""
#         loc_str = location if location else "all drives"
#         return {
#             "status": "success",
#             "message": f"🔍 Found {result['count']} file(s) matching '{filename}' in {loc_str}:\n\n{files_list}{extra}",
#             "data": {"files": result["files"]},
#         }

#     # ── RENAME ──
#     elif action == "rename":
#         files = intent.get("files", [])
#         new_names = intent.get("new_names", [])

#         if not files:
#             return {
#                 "status": "need_info",
#                 "message": "📝 Please specify:\n  • Which file to rename\n  • The new name\n\nExample: 'rename report.txt to summary.txt'",
#                 "pending": {"action": "rename"},
#             }

#         if not new_names:
#             return {
#                 "status": "need_info",
#                 "message": f"📝 What should '{files[0]}' be renamed to?\n\nType the new filename:",
#                 "pending": {"action": "rename", "files": files},
#             }

#         if len(files) != len(new_names):
#             return {
#                 "status": "error",
#                 "message": f"❌ Mismatch: {len(files)} file(s) but {len(new_names)} new name(s).",
#             }

#         # Need to find the files first
#         from services.llm_file_service import _smart_find

#         return {
#             "status": "rename_search",
#             "message": f"🔍 Searching for file(s) to rename...",
#             "pending": {"action": "rename", "files": files, "new_names": new_names},
#         }

#     # ── MOVE ──
#     elif action == "move":
#         files = intent.get("files", [])
#         destination = intent.get("destination")

#         if not files:
#             return {
#                 "status": "need_info",
#                 "message": "📁 Please specify which file(s) to move.\n\nExample: 'move report.txt to D:\\\\Documents'",
#                 "pending": {"action": "move"},
#             }

#         if not destination:
#             return {
#                 "status": "need_destination",
#                 "message": f"📁 Where should I move '{', '.join(files)}'?\n\nEnter destination path (e.g., D:\\\\Documents):",
#                 "pending": {"action": "move", "files": files},
#             }

#         return {
#             "status": "move_search",
#             "message": f"🔍 Searching for file(s) to move...",
#             "pending": {"action": "move", "files": files, "destination": destination},
#         }

#     return {"status": "not_advanced", "message": ""}

# services/file_advanced_service.py
"""
Advanced file operations:
- Rename single or multiple files (asks location compulsorily)
- Move single or multiple files
- Search with user-defined location (LLM + regex both supported)
"""

import os
import re
import json
import string
from pathlib import Path
# from services.llm_service import _call_ollama
# from utils.config import OLLAMA_FAST_MODEL

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────


def get_all_drives() -> list:
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives


def _skip_dirs() -> set:
    return {
        "Windows",
        "System Volume Information",
        "$Recycle.Bin",
        "ProgramData",
        "Program Files",
        "Program Files (x86)",
        "System32",
        "SysWOW64",
        "node_modules",
        "venv",
        ".git",
        "AppData",
    }


def _normalise_location(location: str) -> str | None:
    """Normalise user-provided location to a valid path. Returns None for 'all'."""
    if not location:
        return None
    loc = location.strip().strip('"').strip("'")
    if loc.lower() == "all":
        return None
    if len(loc) == 1 and loc.isalpha():
        return f"{loc.upper()}:\\"
    if len(loc) == 2 and loc[1] == ":":
        return f"{loc.upper()}\\"

    # Named folders
    user_profile = os.environ.get("USERPROFILE", "")
    folder_map = {
        "desktop": os.path.join(user_profile, "Desktop"),
        "documents": os.path.join(user_profile, "Documents"),
        "downloads": os.path.join(user_profile, "Downloads"),
        "pictures": os.path.join(user_profile, "Pictures"),
        "videos": os.path.join(user_profile, "Videos"),
        "music": os.path.join(user_profile, "Music"),
    }
    if loc.lower() in folder_map:
        return folder_map[loc.lower()]

    return loc


# ─────────────────────────────────────────────────────────────
# FILE MATCH HELPER
# ─────────────────────────────────────────────────────────────


def _file_matches(filename: str, user_name: str, user_ext: str, user_norm: str) -> bool:
    name, ext = os.path.splitext(filename)
    name_l = name.lower()
    name_n = name_l.replace("_", " ").replace("-", " ")
    if user_ext and ext.lower() != user_ext:
        return False
    return (
        name_l == user_name
        or name_l.startswith(user_name)
        or name_n.startswith(user_norm)
        or user_name in name_l
        or user_norm in name_n
    )


# ─────────────────────────────────────────────────────────────
# SEARCH — REGEX (fast, filesystem walk)
# ─────────────────────────────────────────────────────────────


def search_regex(filename: str, location: str = None, max_depth: int = 15) -> dict:
    """Pure regex/filesystem search."""
    norm_loc = _normalise_location(location) if location else None

    if norm_loc:
        if not os.path.exists(norm_loc):
            return {
                "status": "error",
                "files": [],
                "count": 0,
                "message": f"❌ Location not found: {norm_loc}",
            }
        search_roots = [norm_loc]
    else:
        search_roots = get_all_drives()

    user_name, user_ext = os.path.splitext(filename.lower())
    user_norm = user_name.replace("_", " ").replace("-", " ")
    skip = _skip_dirs()
    matches = []

    for root_path in search_roots:
        try:
            for root, dirs, files in os.walk(root_path):
                depth = root[len(root_path) :].count(os.sep)
                if depth > max_depth:
                    dirs[:] = []
                    continue
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".") and not d.startswith("$") and d not in skip
                ]
                for f in files:
                    if _file_matches(f, user_name, user_ext, user_norm):
                        full = os.path.join(root, f)
                        if full not in matches:
                            matches.append(full)
        except (PermissionError, OSError):
            continue

    loc_str = norm_loc if norm_loc else "all drives"
    if not matches:
        return {
            "status": "not_found",
            "files": [],
            "count": 0,
            "message": f"❌ '{filename}' not found in {loc_str}",
        }
    return {
        "status": "found",
        "files": matches,
        "count": len(matches),
        "message": f"🔍 Found {len(matches)} file(s) in {loc_str}",
    }


# ─────────────────────────────────────────────────────────────
# SEARCH — LLM GUIDED (asks LLM for likely paths, then walks)
# ─────────────────────────────────────────────────────────────


def parse_advanced_intent(text: str) -> dict:
    """Pure regex intent parser (NO LLM)."""

    t = text.lower().strip()

    base = {
        "action": "none",
        "files": [],
        "new_names": [],
        "destination": None,
        "location": None,
        "search_mode": "regex",
        "source": "regex",
    }

    # ───────── RENAME ─────────
    if re.search(r"\b(rename|change name)\b", t):
        pairs = re.findall(r"(\S+\.\w+)\s+to\s+(\S+\.\w+)", t)
        if pairs:
            return {
                **base,
                "action": "rename",
                "files": [p[0] for p in pairs],
                "new_names": [p[1] for p in pairs],
            }

        single = re.search(r"rename\s+(\S+)\s+to\s+(\S+)", t)
        if single:
            return {
                **base,
                "action": "rename",
                "files": [single.group(1)],
                "new_names": [single.group(2)],
            }

        return {**base, "action": "rename"}

    # ───────── MOVE ─────────
    if re.search(r"\b(move|transfer)\b", t):
        dest = None

        dest_match = re.search(
            r"\bto\s+([A-Za-z]:\\[^\s]+|desktop|documents|downloads)",
            t
        )
        if dest_match:
            dest = dest_match.group(1)

        files = re.findall(r"\b[\w\-]+\.\w+\b", t)

        return {
            **base,
            "action": "move",
            "files": files,
            "destination": dest,
        }

    # ───────── SEARCH ─────────
    if re.search(r"\b(search|find|locate|look for)\b", t):

        file_match = re.search(r"([\w\-. ]+\.\w+)", t)
        filename = file_match.group(1) if file_match else None

        loc = None

        drive_match = re.search(r"([a-z])\s*drive", t)
        if drive_match:
            loc = f"{drive_match.group(1).upper()}:\\"

        folder_match = re.search(r"(desktop|documents|downloads)", t)
        if folder_match:
            loc = folder_match.group(1)

        return {
            **base,
            "action": "search_location",
            "files": [filename] if filename else [],
            "location": loc,
        }

    return base

# ─────────────────────────────────────────────────────────────
# UNIFIED SEARCH ENTRY POINT
# ─────────────────────────────────────────────────────────────


def search_in_location(filename: str, location: str = None, mode: str = "regex") -> dict:
    """Only regex search allowed."""
    return search_regex(filename, location)


# ─────────────────────────────────────────────────────────────
# LLM INTENT PARSER
# ─────────────────────────────────────────────────────────────

_ADVANCED_INTENT_PROMPT = """You are a file operation intent extractor.

Return ONLY a JSON object:
{
  "action": "rename" | "move" | "search_location" | "none",
  "files": ["file1"],
  "new_names": ["newname1"],
  "destination": "path or null",
  "location": "search location or null",
  "search_mode": "regex" | "llm"
}

- rename: user wants to rename file(s)
- move: user wants to move file(s) to another folder
- search_location: user wants to search in a specific place
- search_mode: "llm" if user says "smart search" or "AI search", else "regex"

Examples:
"rename report.txt to summary.txt" -> {"action":"rename","files":["report.txt"],"new_names":["summary.txt"],"destination":null,"location":null,"search_mode":"regex"}
"rename file1.txt to a.txt and file2.txt to b.txt" -> {"action":"rename","files":["file1.txt","file2.txt"],"new_names":["a.txt","b.txt"],"destination":null,"location":null,"search_mode":"regex"}
"move resume.pdf to C:\\Documents" -> {"action":"move","files":["resume.pdf"],"new_names":[],"destination":"C:\\Documents","location":null,"search_mode":"regex"}
"search for notes.txt in C drive" -> {"action":"search_location","files":["notes.txt"],"new_names":[],"destination":null,"location":"C:\\","search_mode":"regex"}
"smart search for resume in D drive" -> {"action":"search_location","files":["resume"],"new_names":[],"destination":null,"location":"D:\\","search_mode":"llm"}
"find budget.xlsx in Documents" -> {"action":"search_location","files":["budget.xlsx"],"new_names":[],"destination":null,"location":"Documents","search_mode":"regex"}
"hello" -> {"action":"none","files":[],"new_names":[],"destination":null,"location":null,"search_mode":"regex"}

User message: "{message}"
JSON:"""


# def parse_advanced_intent(text: str) -> dict:
#     """Pure regex intent parser (NO LLM)."""

#     t = text.lower().strip()

#     base = {
#         "action": "none",
#         "files": [],
#         "new_names": [],
#         "destination": None,
#         "location": None,
#         "search_mode": "regex",
#         "source": "regex",
#     }

#     # ───────── RENAME ─────────
#     if re.search(r"\b(rename|change name)\b", t):
#         pairs = re.findall(r"(\S+\.\w+)\s+to\s+(\S+\.\w+)", t)

#         if pairs:
#             return {
#                 **base,
#                 "action": "rename",
#                 "files": [p[0] for p in pairs],
#                 "new_names": [p[1] for p in pairs],
#             }

#         single = re.search(r"rename\s+(\S+)\s+to\s+(\S+)", t)
#         if single:
#             return {
#                 **base,
#                 "action": "rename",
#                 "files": [single.group(1)],
#                 "new_names": [single.group(2)],
#             }

#         return {**base, "action": "rename"}

#     # ───────── MOVE ─────────
#     if re.search(r"\b(move|transfer)\b", t):
#         dest = None

#         dest_match = re.search(
#             r"\bto\s+([A-Za-z]:\\[^\s]+|desktop|documents|downloads)",
#             t
#         )
#         if dest_match:
#             dest = dest_match.group(1)

#         files = re.findall(r"[\w\-. ]+\.\w+", t)

#         return {
#             **base,
#             "action": "move",
#             "files": files,
#             "destination": dest,
#         }

#     # ───────── SEARCH ─────────
#     if re.search(r"\b(search|find|locate|look for)\b", t):

#         file_match = re.search(r"([\w\-. ]+\.\w+)", t)
#         filename = file_match.group(1) if file_match else None

#         loc = None

#         # Drive (C drive → C:\)
#         drive_match = re.search(r"([a-z])\s*drive", t)
#         if drive_match:
#             loc = f"{drive_match.group(1).upper()}:\\"

#         # Folder names
#         folder_match = re.search(r"(desktop|documents|downloads)", t)
#         if folder_match:
#             loc = folder_match.group(1)

#         return {
#             **base,
#             "action": "search_location",
#             "files": [filename] if filename else [],
#             "location": loc,
#         }

#     return base


def _regex_parse_advanced(text: str) -> dict:
    t = text.lower().strip()
    base = {
        "action": "none",
        "files": [],
        "new_names": [],
        "destination": None,
        "location": None,
        "search_mode": "regex",
        "source": "regex",
    }

    if re.search(r"\b(smart search|intelligent search|ai search)\b", t):
        base["search_mode"] = "llm"

    # Rename
    if re.search(r"\b(rename|change name)\b", t):
        pairs = re.findall(r"(\S+\.\w+)\s+to\s+(\S+\.\w+)", t)
        if pairs:
            return {
                **base,
                "action": "rename",
                "files": [p[0] for p in pairs],
                "new_names": [p[1] for p in pairs],
            }
        no_ext = re.findall(r"rename\s+(\S+)\s+to\s+(\S+)", t)
        if no_ext:
            return {
                **base,
                "action": "rename",
                "files": [no_ext[0][0]],
                "new_names": [no_ext[0][1]],
            }
        return {**base, "action": "rename"}

    
    # ───────── MOVE ─────────
    if re.search(r"\b(move|transfer)\b", t):
        dest = None

        # Detect destination (supports Desktop, Documents, Downloads, paths)
        dest_match = re.search(
            r"\bto\s+([A-Za-z]:\\[^\s]+|desktop|documents|downloads|pictures|videos|music)",
            t
        )

        if dest_match:
            dest = dest_match.group(1)

        files = re.findall(r"[\w\-. ]+\.\w+", t)

        return {
            **base,
            "action": "move",
            "files": files,
            "destination": dest,
        }


def is_advanced_file_command(text: str) -> bool:
    """Quick check if text is an advanced file command."""
    t = text.lower().strip()

    # Rename commands
    if re.search(r"\b(rename|change name of|change name)\b", t):
        return True

    # Move commands:
    # Examples:
    # move file.pdf to Downloads
    # move Complexity_Cheatsheet.pdf to Downloads
    # move a.txt and b.txt to Desktop
    # transfer report.docx into D:\Backup
    if re.search(r"\b(move|transfer)\b", t) and re.search(r"\b(to|into|in)\b", t):
        return True

    # Search commands with location
    if re.search(r"\b(search|find|locate|look for)\b", t) and re.search(
        r"\b(in|on|at|inside|within)\b.{0,80}"
        r"\b(drive|folder|directory|desktop|documents|downloads|pictures|videos|music|[a-z]:\\)\b",
        t,
    ):
        return True

    return False


# ─────────────────────────────────────────────────────────────
# RENAME OPERATIONS
# ─────────────────────────────────────────────────────────────


def rename_file(old_path: str, new_name: str) -> dict:
    old = Path(old_path)
    if not old.exists():
        return {"status": "error", "message": f"❌ File not found: {old_path}"}
    new_path = old.parent / new_name
    if new_path.exists():
        return {
            "status": "confirm_overwrite",
            "message": f"⚠️ '{new_name}' already exists.\n\nType 'yes' to overwrite or 'no' to cancel.",
            "old_path": str(old),
            "new_path": str(new_path),
        }
    try:
        old.rename(new_path)
        return {
            "status": "success",
            "message": (
                f"✅ Renamed!\n\n"
                f"📄 Old: {old.name}\n"
                f"📄 New: {new_name}\n"
                f"📂 Location: {old.parent}"
            ),
        }
    except Exception as e:
        return {"status": "error", "message": f"❌ Rename failed: {str(e)}"}


def rename_multiple_files(file_pairs: list) -> dict:
    results = []
    success = fail = 0
    for pair in file_pairs:
        r = rename_file(pair["old_path"], pair["new_name"])
        results.append(f"{'✅' if r['status'] == 'success' else '❌'} {r['message']}")
        if r["status"] == "success":
            success += 1
        else:
            fail += 1
    return {
        "status": "success" if fail == 0 else "partial",
        "message": f"📋 Rename: {success} succeeded, {fail} failed\n\n"
        + "\n".join(results),
    }


# ─────────────────────────────────────────────────────────────
# MOVE OPERATIONS
# ─────────────────────────────────────────────────────────────


def move_file(src_path: str, dest_dir: str) -> dict:
    """Move one file to destination folder. Creates destination folder if missing."""
    import shutil

    try:
        src = Path(src_path)

        if not src.exists():
            return {"status": "error", "message": f"❌ File not found: {src_path}"}

        if not src.is_file():
            return {
                "status": "error",
                "message": f"❌ Source is not a file: {src_path}",
            }

        dest_dir = _normalise_location(dest_dir) or dest_dir
        dest = Path(dest_dir)

        # Create destination folder automatically
        dest.mkdir(parents=True, exist_ok=True)

        if not dest.is_dir():
            return {
                "status": "error",
                "message": f"❌ Destination must be a folder: {dest_dir}",
            }

        new_path = dest / src.name

        if new_path.exists():
            return {
                "status": "error",
                "message": f"⚠️ File already exists at destination: {new_path}",
            }

        old_parent = src.parent
        shutil.move(str(src), str(new_path))

        return {
            "status": "success",
            "message": (
                f"✅ Moved!\n\n"
                f"📄 File: {src.name}\n"
                f"📂 From: {old_parent}\n"
                f"📂 To: {dest}"
            ),
        }

    except Exception as e:
        return {"status": "error", "message": f"❌ Move failed: {str(e)}"}


def move_multiple_files(src_paths: list, dest_dir: str) -> dict:
    """Move multiple files to destination folder."""
    if not src_paths:
        return {"status": "error", "message": "❌ No files provided to move."}

    results = []
    success = 0
    fail = 0

    dest_dir = _normalise_location(dest_dir) or dest_dir

    for src_path in src_paths:
        result = move_file(src_path, dest_dir)

        if result["status"] == "success":
            success += 1
            results.append(result["message"])
        else:
            fail += 1
            results.append(result["message"])

    return {
        "status": "success" if fail == 0 else "partial",
        "message": (
            f"📋 Move Results\n\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {fail}\n\n" + "\n\n".join(results)
        ),
    }


# ─────────────────────────────────────────────────────────────
# MAIN HANDLER
# ─────────────────────────────────────────────────────────────


def handle_advanced_file_command(user_prompt: str, session_id=None) -> dict:
    intent = parse_advanced_intent(user_prompt)
    action = intent.get("action", "none")

    if action == "none":
        return {"status": "not_advanced", "message": ""}

    # ── SEARCH IN LOCATION ──
    if action == "search_location":
        files = intent.get("files", [])
        location = intent.get("location")
        search_mode = intent.get("search_mode", "regex")
        filename = files[0] if files else None

        if not filename:
            return {
                "status": "need_search_info",
                "message": (
                    "🔍 Please specify what to search for.\n\n"
                    "Example:\n"
                    "search for notes.txt in Desktop"
                ),
                "pending": {
                    "action": "search_location",
                    "location": location,
                    "search_mode": search_mode,
                },
            }

        if not location:
            return {
                "status": "need_search_location",
                "message": (
                    f"📂 Where should I search for '{filename}'?\n\n"
                    "Options:\n"
                    "  • Desktop\n"
                    "  • Documents\n"
                    "  • Downloads\n"
                    "  • C drive / D drive\n"
                    "  • Full path\n"
                    "  • all"
                ),
                "pending": {
                    "action": "search_location",
                    "files": [filename],
                    "search_mode": search_mode,
                },
            }

        location = None if str(location).lower() == "all" else location
        result = search_in_location(filename, location, mode=search_mode)

        if result["status"] in ("error", "not_found"):
            return {"status": "error", "message": result["message"]}

        files_list = "\n".join(
            f"  {i}. {f}" for i, f in enumerate(result["files"][:20], 1)
        )
        extra = f"\n  … and {result['count'] - 20} more" if result["count"] > 20 else ""
        loc_str = location if location else "all drives"

        return {
            "status": "success",
            "message": (
                f"🔍 Found {result['count']} file(s) matching '{filename}' in {loc_str}:\n\n"
                f"{files_list}{extra}"
            ),
            "data": {"files": result["files"]},
        }

    # ── RENAME ──
    if action == "rename":
        files = intent.get("files", [])
        new_names = intent.get("new_names", [])

        if not files:
            return {
                "status": "need_info",
                "message": (
                    "📝 Please specify file name and new name.\n\n"
                    "Example:\n"
                    "rename old.txt to new.txt"
                ),
                "pending": {"action": "rename"},
            }

        if not new_names:
            return {
                "status": "need_info",
                "message": f"📝 What should '{files[0]}' be renamed to?",
                "pending": {"action": "rename", "files": files},
            }

        if len(files) != len(new_names):
            return {
                "status": "error",
                "message": f"❌ Mismatch: {len(files)} file(s), but {len(new_names)} new name(s).",
            }

        return {
            "status": "need_rename_location",
            "message": (
                f"📂 Where should I search for file(s) to rename?\n\n"
                f"Files: {', '.join(files)}\n\n"
                "Options:\n"
                "  • Desktop\n"
                "  • Documents\n"
                "  • Downloads\n"
                "  • C drive / D drive\n"
                "  • Full path\n"
                "  • all"
            ),
            "pending": {"action": "rename", "files": files, "new_names": new_names},
        }

    # ── MOVE ──
    if action == "move":
        files = intent.get("files", [])
        destination = intent.get("destination")

        if not files:
            return {
                "status": "need_info",
                "message": (
                    "📁 Please specify which file(s) to move.\n\n"
                    "Example:\n"
                    "move a.txt and b.txt to Desktop"
                ),
                "pending": {"action": "move"},
            }

        if not destination:
            return {
                "status": "need_destination",
                "message": (
                    f"📁 Where should I move these file(s)?\n\n"
                    f"Files: {', '.join(files)}\n\n"
                    "Enter destination folder:"
                ),
                "pending": {"action": "move", "files": files},
            }

        return {
            "status": "move_search",
            "message": "🔍 Searching for file(s) to move...",
            "pending": {"action": "move", "files": files, "destination": destination},
        }

    return {"status": "not_advanced", "message": ""}
