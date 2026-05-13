# services/file_tag_service.py
import os
import re
from pathlib import Path


def is_file_tag_command(text: str) -> bool:
    t = text.lower().strip()
    return (
        t.startswith("tag ")
        or t.startswith("add tag ")
        or t.startswith("show tags")
        or t.startswith("show files tagged")
        or t.startswith("auto tag ")
        or t.startswith("suggest tags")
    )


def _load_text_for_tagging(file_path: str) -> str:
    path = Path(file_path)
    ext = path.suffix.lower().replace(".", "")

    if not path.exists():
        return ""

    try:
        if ext in ("txt", "md"):
            return path.read_text(encoding="utf-8", errors="ignore")

        if ext == "pdf":
            try:
                import PyPDF2
                text = ""
                with open(path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text
            except Exception:
                return ""

        if ext == "docx":
            try:
                from docx import Document
                doc = Document(path)
                return "\n".join(p.text for p in doc.paragraphs if p.text)
            except Exception:
                return ""

        if ext == "csv":
            try:
                import csv
                rows = []
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.reader(f)
                    for i, row in enumerate(reader):
                        if i >= 5:
                            break
                        rows.append(" ".join(row))
                return "\n".join(rows)
            except Exception:
                return ""

        if ext == "xlsx":
            try:
                import openpyxl
                wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
                ws = wb.active
                rows = []
                for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
                    if i > 5:
                        break
                    rows.append(" ".join(str(cell) for cell in row if cell is not None))
                return "\n".join(rows)
            except Exception:
                return ""

    except Exception:
        return ""

    return ""


def _extract_text_tags(text: str) -> set:
    tags = set()
    if not text:
        return tags
    text_lower = text.lower()

    keywords = {
        "resume": "resume",
        "cv": "resume",
        "assignment": "assignment",
        "report": "report",
        "result": "result",
        "dmc": "certificate",
        "certificate": "certificate",
        "cheatsheet": "study",
        "complexity": "dsa",
        "budget": "finance",
        "student": "student-data",
        "students": "student-data",
        "invoice": "invoice",
        "proposal": "proposal",
        "minutes": "meeting-notes",
        "notes": "notes",
        "summary": "summary",
        "tutorial": "tutorial",
        "guide": "guide",
        "analysis": "analysis",
        "financial": "finance",
        "budget": "finance",
        "project": "project",
    }

    for key, tag in keywords.items():
        if re.search(rf"\b{re.escape(key)}\b", text_lower):
            tags.add(tag)

    # Add a few strong candidate tags from the first lines
    lines = [line.strip() for line in text_lower.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        header_tokens = [tok for tok in re.split(r"[\s,;|]+", first_line) if len(tok) > 3]
        stop_words = {
            "the", "and", "for", "with", "from", "this", "that", "your",
            "file", "text", "notes", "note", "data", "report", "document",
            "study", "project", "analysis"
        }
        for tok in header_tokens[:10]:
            if tok not in stop_words and re.match(r"^[a-z]+$", tok):
                tags.add(tok)

    return tags


def auto_generate_tags(file_path: str) -> list:
    path = Path(file_path)
    name = path.stem.lower()
    ext = path.suffix.lower().replace(".", "")

    tags = set()

    if ext:
        tags.add(ext)

    ext_map = {
        "pdf": "document",
        "docx": "word",
        "txt": "text",
        "csv": "data",
        "xlsx": "spreadsheet",
        "py": "python",
        "jpg": "image",
        "png": "image",
    }

    if ext in ext_map:
        tags.add(ext_map[ext])

    keywords = {
        "resume": "resume",
        "cv": "resume",
        "assignment": "assignment",
        "report": "report",
        "result": "result",
        "dmc": "certificate",
        "certificate": "certificate",
        "cheatsheet": "study",
        "complexity": "dsa",
        "budget": "finance",
        "students": "student-data",
    }

    for key, tag in keywords.items():
        if key in name:
            tags.add(tag)

    text = _load_text_for_tagging(file_path)
    if text:
        tags.update(_extract_text_tags(text))

    # For spreadsheet-like files, add headers and first rows as natural tags
    if ext in ("csv", "xlsx") and text:
        header_line = text.splitlines()[0] if text else ""
        for token in re.split(r"[\s,;|]+", header_line):
            tok = token.strip().lower()
            if tok and len(tok) > 2:
                tags.add(tok)

    if not tags:
        tags.add("untagged")

    return sorted(tags)


def parse_tag_command(text: str) -> dict:
    t = text.strip()

    # tag file.pdf as important, study
    m = re.search(r"tag\s+(.+?)\s+as\s+(.+)", t, re.I)
    if m:
        filename = m.group(1).strip()
        tags = [x.strip().lower() for x in re.split(r"[, ]+", m.group(2)) if x.strip()]
        return {
            "action": "manual_tag",
            "filename": filename,
            "tags": tags,
        }

    # auto tag file.pdf
    m = re.search(r"(?:auto tag|suggest tags)\s+(.+)", t, re.I)
    if m:
        return {
            "action": "auto_tag",
            "filename": m.group(1).strip(),
            "tags": [],
        }

    # show tags file.pdf
    m = re.search(r"show tags\s+(.+)", t, re.I)
    if m:
        return {
            "action": "show_tags",
            "filename": m.group(1).strip(),
            "tags": [],
        }

    # show files tagged <tag>
    m = re.search(r"show files tagged\s+(.+)", t, re.I)
    if m:
        return {
            "action": "show_files_by_tag",
            "filename": m.group(1).strip(),
            "tags": [],
        }

    return {
        "action": "unknown",
        "filename": None,
        "tags": [],
    }


def handle_file_tag_command(text: str, find_file_func, save_tags_func, get_tags_func) -> dict:
    parsed = parse_tag_command(text)
    action = parsed["action"]
    filename = parsed["filename"]

    if not filename:
        return {
            "status": "error",
            "message": "❌ Please provide filename.\nExample: tag report.pdf as important, study"
        }

    # For tag->file listing, we don't need to locate a specific file name
    if action != "show_files_by_tag":
        found_files = find_file_func(filename)

        if not found_files:
            return {
                "status": "error",
                "message": f"❌ File not found: {filename}"
            }

        # If there are multiple matches, ask the caller/UI to prompt the user
        if len(found_files) > 1:
            files_list = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(found_files))
            return {
                "status": "select",
                "message": (
                    f"📂 Multiple files found for '{filename}'.\n\n"
                    f"Reply with the file number to tag, or 'cancel':\n\n{files_list}"
                ),
                "data": {
                    "files": found_files,
                    "tags": parsed.get("tags", []),
                    "action": parsed.get("action", "manual_tag"),
                },
            }

        file_path = found_files[0]
    else:
        file_path = None

    if action == "manual_tag":
        tags = parsed["tags"]
        if tags:
            save_tags_func(file_path, tags, source="user")
        else:
            return {"status": "error", "message": "❌ No tags provided."}
        return {
            "status": "success",
            "message": (
                f"✅ Tags added!\n\n"
                f"📄 File: {os.path.basename(file_path)}\n"
                f"🏷️ Tags: {', '.join(tags)}"
            )
        }

    if action == "auto_tag":
        # ensure file still exists before attempting to read it
        try:
            if not Path(file_path).exists():
                return {"status": "error", "message": f"❌ File no longer exists: {file_path}"}
        except Exception:
            pass

        tags = auto_generate_tags(file_path)

        if not tags:
            return {"status": "error", "message": "⚠️ No tags could be generated for this file."}

        save_tags_func(file_path, tags, source="auto")
        return {
            "status": "success",
            "message": (
                f"✅ Auto tags generated!\n\n"
                f"📄 File: {os.path.basename(file_path)}\n"
                f"🏷️ Tags: {', '.join(tags)}"
            )
        }

    if action == "show_tags":
        tags = get_tags_func(file_path)
        return {
            "status": "success",
            "message": (
                f"🏷️ Tags for {os.path.basename(file_path)}:\n\n"
                f"{', '.join(tags) if tags else 'No tags found'}"
            )
        }

    if action == "show_files_by_tag":
        # Search the JSON tag DB for files with this tag
        try:
            from db.tag_db_json import search_by_tag

            tag = filename.lower()
            files = search_by_tag(tag)
            if not files:
                return {"status": "success", "message": f"🔎 No files found with tag: {tag}"}
            files_list = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(files))
            return {
                "status": "success",
                "message": (
                    f"🔎 Files tagged '{tag}':\n\n{files_list}"
                ),
            }
        except Exception:
            return {"status": "error", "message": "❌ Could not search tags."}

    return {
        "status": "error",
        "message": "❌ Invalid tag command."
    }