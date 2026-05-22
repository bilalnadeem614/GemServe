import json
import os
from pathlib import Path
import traceback
from datetime import datetime

DB_PATH = Path("data/tags.json")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_db():
    if not DB_PATH.exists():
        return {}

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # If file is corrupted or unreadable, return empty DB to avoid crashes
        return {}


def save_db(data):
    # Write atomically: write to temp file then replace
    tmp = DB_PATH.with_suffix(DB_PATH.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        # Use os.replace for atomic move which is reliable across platforms
        os.replace(str(tmp), str(DB_PATH))
    except Exception as e:  
        # Log the error for debugging and try direct write as a fallback
        try:
            log_file = DB_PATH.parent / "tags_save_errors.log"
            with open(log_file, "a", encoding="utf-8") as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] Save error: {str(e)}\n")
                lf.write(traceback.format_exc())
                lf.write("\n---\n")
        except Exception:
            pass

        try:
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            # If this also fails, log and give up (we avoid raising to not crash the app)
            try:
                log_file = DB_PATH.parent / "tags_save_errors.log"
                with open(log_file, "a", encoding="utf-8") as lf:
                    lf.write(f"[{datetime.utcnow().isoformat()}] Direct write failed.\n")
                    lf.write(traceback.format_exc())
                    lf.write("\n---\n")
            except Exception:
                pass


def add_tags(file_path, tags, source="user"):
    data = load_db()

    # normalize file path to absolute resolved string
    try:
        p = Path(str(file_path)).expanduser()
        # Use non-strict resolve to avoid errors when file not present
        abspath = str(p.resolve(strict=False))
    except Exception:
        abspath = os.path.abspath(str(file_path))

    if abspath not in data:
        data[abspath] = []

    for tag in tags:
        tag_text = str(tag).strip().lower()
        if not tag_text:
            continue

        entry = {
            "tag": tag_text,
            "source": source,
        }

        # avoid duplicate tag entries (same tag + source)
        if entry not in data[abspath]:
            data[abspath].append(entry)

    save_db(data)


def get_tags(file_path):
    data = load_db()

    try:
        p = Path(str(file_path)).expanduser()
        abspath = str(p.resolve(strict=False))
    except Exception:
        abspath = os.path.abspath(str(file_path))

    if abspath not in data:
        return []

    seen = set()
    result = []
    for t in data.get(abspath, []):
        tag = t.get("tag")
        if not tag:
            continue
        if tag in seen:
            continue
        seen.add(tag)
        result.append(tag)

    return result


def search_by_tag(tag):
    data = load_db()

    tag = tag.lower()

    result = []

    for file_path, tags in data.items():
        for t in tags:
            try:
                if t.get("tag") == tag:
                    result.append(file_path)
                    break
            except Exception:
                continue

    return result


def save_tags(file_path, tags, source="user"):
    """Compatibility wrapper used by other modules expecting `save_tags`."""
    add_tags(file_path, tags, source=source)


def get_tags_for_file(file_path):
    """Compatibility wrapper used by other modules expecting `get_tags`."""
    return get_tags(file_path)


def init_tag_db():
    """Ensure the tags JSON file exists."""
    if not DB_PATH.exists():
        save_db({})