# services/file_service.py
import os
import json
import string
from pathlib import Path
from datetime import datetime


# Path to store user file cache
CACHE_DIR = Path("file_history")
CACHE_DIR.mkdir(exist_ok=True)


def get_user_cache_file(session_id):
    """Get the cache file path for a specific user/session"""
    return CACHE_DIR / f"user_{session_id}_files.json"


def load_file_cache(session_id):
    """Load cached file paths for a user"""
    cache_file = get_user_cache_file(session_id)
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
            return {"files": [], "last_updated": None}
    return {"files": [], "last_updated": None}


def save_file_cache(session_id, file_paths):
    """Save file paths to user's cache"""
    cache_file = get_user_cache_file(session_id)
    cache_data = {
        "files": file_paths[-15:],  # Keep only last 15
        "last_updated": datetime.now().isoformat()
    }
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving cache: {e}")


def add_to_cache(session_id, file_path):
    """Add a file path to user's cache"""
    cache = load_file_cache(session_id)
    files = cache.get("files", [])
    
    # Remove if already exists (to update position)
    if file_path in files:
        files.remove(file_path)
    
    files.append(file_path)
    save_file_cache(session_id, files)


def get_all_drives():
    """Get all available drives on Windows"""
    drives = []
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives


def initialize_file_mode():
    """Initialize file operation mode and return intro info"""
    drives = get_all_drives()
    drives_text = "\n".join(f"  • {d}" for d in drives) if drives else "  No drives found"
    
    intro_message = (
        "📁 File Operation Mode Activated\n\n"
        "🖥️ Available Drives:\n"
        f"{drives_text}\n\n"
        "📋 Available Commands:\n"
        "  • open <filename>   - Search and open file\n"
        "  • delete <filename> - Search and delete file\n"
        "  • new <filename>    - Create file (choose Desktop or custom path)\n\n"
        "💡 Tips:\n"
        "  • Use partial names: 'README' finds 'README.md', 'README.txt'\n"
        "  • First 15 recently opened files are cached for faster access\n"
        "  • When cache limit reached, you can search all drives or specific drive"
    )
    
    return {
        "status": "init",
        "message": intro_message,
        "drives": drives
    }


def search_in_cache(session_id, filename):
    """Search for file in user's cache first"""
    cache = load_file_cache(session_id)
    files = cache.get("files", [])
    
    user_name, user_ext = os.path.splitext(filename.lower())
    matches = []
    
    for file_path in files:
        if not os.path.exists(file_path):
            continue
        
        file_name = os.path.basename(file_path)
        name, ext = os.path.splitext(file_name.lower())
        
        if user_ext:
            if name.startswith(user_name) and ext == user_ext:
                matches.append(file_path)
        else:
            if name.startswith(user_name):
                matches.append(file_path)
    
    return matches


def find_files_by_name(filename, session_id=None, specific_drive=None, max_depth=15):
    """Find files across all drives with partial matching and caching"""
    
    # First check cache if session_id provided
    cache_matches = []
    if session_id:
        cache_matches = search_in_cache(session_id, filename)
        if cache_matches:
            # If we found files in cache and it's under 15 items, check if user wants full search
            if len(cache_matches) <= 15:
                return {
                    "status": "cache_found",
                    "files": cache_matches,
                    "count": len(cache_matches)
                }
    
    matches = []
    user_filename = filename.strip()
    user_name, user_ext = os.path.splitext(user_filename)
    user_name, user_ext = user_name.lower(), user_ext.lower()

    skip_folders = {
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

    user_profile = os.environ.get("USERPROFILE", "")

    # Priority search paths
    priority_paths = [
        os.getcwd(),
        os.path.join(user_profile, "Desktop"),
        os.path.join(user_profile, "Documents"),
        os.path.join(user_profile, "Downloads"),
    ]

    # Get drives to search
    if specific_drive:
        all_drives = [specific_drive] if os.path.exists(specific_drive) else []
    else:
        all_drives = get_all_drives()

    def file_matches(file):
        """Check if file matches search criteria with partial matching"""
        name, ext = os.path.splitext(file)
        name, ext = name.lower(), ext.lower()
        
        if user_ext:
            if user_name and name.startswith(user_name) and ext == user_ext:
                return True
            return file.lower() == user_filename.lower()
        
        return name.startswith(user_name)

    # Search priority paths first (unless specific drive specified)
    if not specific_drive:
        for base in priority_paths:
            if not os.path.exists(base):
                continue

            try:
                for root, dirs, files in os.walk(base):
                    depth = root[len(base):].count(os.sep)
                    if depth > max_depth:
                        dirs[:] = []
                        continue

                    dirs[:] = [
                        d for d in dirs
                        if not d.startswith(".") and not d.startswith("$") and d not in skip_folders
                    ]

                    for file in files:
                        if file_matches(file):
                            full_path = os.path.join(root, file)
                            if full_path not in matches:
                                matches.append(full_path)
            except (PermissionError, OSError):
                continue

    # Search all drives or specific drive
    if len(matches) < 50:
        searched_paths = set()
        if not specific_drive:
            for path in priority_paths:
                if os.path.exists(path):
                    searched_paths.add(os.path.normpath(path))
        
        for drive in all_drives:
            try:
                for root, dirs, files in os.walk(drive):
                    norm_root = os.path.normpath(root)
                    if norm_root in searched_paths:
                        continue
                    
                    depth = root[len(drive):].count(os.sep)
                    if depth > max_depth:
                        dirs[:] = []
                        continue

                    dirs[:] = [
                        d for d in dirs
                        if not d.startswith(".") and not d.startswith("$") and d not in skip_folders
                    ]

                    for file in files:
                        if file_matches(file):
                            full_path = os.path.join(root, file)
                            if full_path not in matches:
                                matches.append(full_path)
                                
            except (PermissionError, OSError):
                continue

    return {
        "status": "found",
        "files": matches,
        "count": len(matches)
    }


def open_file(path, session_id=None):
    """Open a file using default application and cache it"""
    try:
        os.startfile(path)
        
        # Add to cache if session_id provided
        if session_id:
            add_to_cache(session_id, path)
        
        return {
            "status": "success",
            "message": f"✅ Opened: {Path(path).name}\n📂 Location: {path}"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": "❌ File no longer exists at this location"
        }
    except PermissionError:
        return {
            "status": "error",
            "message": "❌ Permission denied. Cannot open this file"
        }
    except OSError:
        return {
            "status": "error",
            "message": "❌ Cannot open file: No associated application found"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Failed to open: {str(e)}"
        }


def delete_file(path, session_id=None):
    """Delete a file and remove from cache"""
    try:
        # Check if it's a system file
        system_indicators = ["Windows", "Program Files", "System32", "SysWOW64"]
        if any(indicator in path for indicator in system_indicators):
            return {
                "status": "warning",
                "message": f"⚠️ WARNING: This appears to be a system file!\n📂 {path}\n\nDeleting system files can damage your Windows installation.",
                "path": path
            }
        
        os.remove(path)
        
        # Remove from cache if session_id provided
        if session_id:
            cache = load_file_cache(session_id)
            files = cache.get("files", [])
            if path in files:
                files.remove(path)
                save_file_cache(session_id, files)
        
        return {
            "status": "success",
            "message": f"✅ Deleted: {Path(path).name}"
        }
    except PermissionError:
        return {
            "status": "error",
            "message": "❌ Permission denied. File may be in use or protected"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Failed to delete: {str(e)}"
        }


def create_file(filename, custom_path=None):
    """Create a new file on Desktop or custom path"""
    # Validate filename (only if no custom path - custom path can have separators)
    if not custom_path:
        if ".." in filename or "/" in filename or "\\" in filename:
            return {
                "status": "error",
                "message": "❌ Invalid filename. Cannot contain path separators"
            }
    
    invalid_chars = '<>:"|?*'
    base_filename = os.path.basename(filename) if custom_path else filename
    if any(char in base_filename for char in invalid_chars):
        return {
            "status": "error",
            "message": f"❌ Invalid filename. Cannot contain: {invalid_chars}"
        }
    
    # If custom path provided, use it
    if custom_path:
        # Validate custom path exists
        if not os.path.exists(custom_path):
            return {
                "status": "error",
                "message": f"❌ Path does not exist: {custom_path}"
            }
        
        if not os.path.isdir(custom_path):
            return {
                "status": "error",
                "message": f"❌ Path is not a directory: {custom_path}"
            }
        
        target_dir = custom_path
    else:
        # Use Desktop
        user_profile = os.environ.get("USERPROFILE", "")
        
        # Try multiple Desktop locations
        possible_desktops = [
            os.path.join(user_profile, "Desktop"),
            os.path.join(user_profile, "OneDrive", "Desktop"),
            os.path.join(user_profile, "OneDrive - Personal", "Desktop"),
        ]
        
        target_dir = None
        for path in possible_desktops:
            if os.path.exists(path):
                target_dir = path
                break
        
        # Fallback to current directory
        if not target_dir:
            target_dir = os.getcwd()
    
    path = Path(target_dir) / base_filename

    # Check if file exists
    if path.exists():
        return {
            "status": "confirm",
            "action": "overwrite",
            "path": str(path),
            "message": f"⚠️ File already exists: {base_filename}\n📂 Location: {target_dir}\n\nType 'y' to overwrite or 'n' to cancel"
        }

    try:
        path.touch()
        return {
            "status": "success",
            "message": f"✅ File created: {base_filename}\n📂 Location: {target_dir}"
        }
    except PermissionError:
        return {
            "status": "error",
            "message": "❌ Permission denied. Cannot create file"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Failed to create file: {str(e)}"
        }


def handle_file_command(text, session_id=None):
    """Main handler for file operation commands"""
    text = text.strip()
    
    if not text:
        return {
            "status": "error",
            "message": "❌ Please enter a command\n\n📋 Usage:\n  • open <filename>\n  • delete <filename>\n  • new <filename>"
        }
    
    parts = text.split(maxsplit=1)
    
    if len(parts) < 2:
        return {
            "status": "error",
            "message": "❌ Please provide a filename\n\n📋 Usage:\n  • open <filename>\n  • delete <filename>\n  • new <filename>"
        }

    cmd = parts[0].lower()
    filename = parts[1].strip()
    
    if not filename:
        return {
            "status": "error",
            "message": "❌ Filename cannot be empty"
        }

    # OPEN command
    if cmd == "open":
        # First check cache
        cache_matches = []
        if session_id:
            cache_matches = search_in_cache(session_id, filename)
        
        # If cache has results and <= 15 files, ask user
        if cache_matches and len(cache_matches) <= 15:
            return {
                "status": "cache_limit",
                "action": "open",
                "files": cache_matches,
                "count": len(cache_matches),
                "filename": filename,
                "message": f"📦 Found {len(cache_matches)} file(s) in recent cache.\n\nSelect an option:\n  • Number (1-{len(cache_matches)}) - Open that file\n  • 'all' - Search all drives\n  • Drive letter (e.g., 'C:\\') - Search specific drive"
            }
        
        # No cache or cache empty - do full search
        result = find_files_by_name(filename, session_id=None)
        
        if result["count"] == 0:
            return {
                "status": "error",
                "message": f"❌ File '{filename}' not found in any drive"
            }
        
        if result["count"] == 1:
            return {
                "status": "single_file",
                "action": "open",
                "file": result["files"][0]
            }
        
        # Multiple files found
        return {
            "status": "multiple",
            "action": "open",
            "files": result["files"],
            "message": f"📊 Found {result['count']} file(s) matching '{filename}'"
        }

    # DELETE command
    elif cmd == "delete":
        # First check cache
        cache_matches = []
        if session_id:
            cache_matches = search_in_cache(session_id, filename)
        
        # If cache has results and <= 15 files, ask user
        if cache_matches and len(cache_matches) <= 15:
            return {
                "status": "cache_limit",
                "action": "delete",
                "files": cache_matches,
                "count": len(cache_matches),
                "filename": filename,
                "message": f"📦 Found {len(cache_matches)} file(s) in recent cache.\n\nSelect an option:\n  • Number (1-{len(cache_matches)}) - Delete that file\n  • 'all' - Search all drives\n  • Drive letter (e.g., 'C:\\') - Search specific drive"
            }
        
        # No cache or cache empty - do full search
        result = find_files_by_name(filename, session_id=None)
        
        if result["count"] == 0:
            return {
                "status": "error",
                "message": f"❌ File '{filename}' not found in any drive"
            }
        
        # Return files for confirmation
        return {
            "status": "confirm",
            "action": "delete",
            "files": result["files"],
            "message": f"📊 Found {result['count']} file(s) matching '{filename}'"
        }

    # NEW command
    elif cmd == "new":
        return {
            "status": "ask_location",
            "action": "create",
            "filename": filename,
            "message": f"📝 Create '{filename}' at:\n\n  1. Desktop (default)\n  2. Custom path\n\nType '1', '2', or 'cancel'"
        }

    # Unknown command
    else:
        return {
            "status": "error",
            "message": f"❌ Unknown command: '{cmd}'\n\n📋 Valid commands:\n  • open <filename>\n  • delete <filename>\n  • new <filename>"
        }