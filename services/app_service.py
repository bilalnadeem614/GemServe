import os
import json
import glob
import time
import winreg
import subprocess
import psutil
import pygetwindow as gw
import pyautogui

# ──────────────────────────────────────────────
# PATH TO JSON REGISTRY
# ──────────────────────────────────────────────
REGISTRY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app_registry.json")


# ──────────────────────────────────────────────
# LOAD / SAVE JSON REGISTRY
# ──────────────────────────────────────────────
def load_registry() -> dict:
    """Load app registry from JSON file. Create if not exists."""
    if not os.path.exists(REGISTRY_FILE):
        default = {"apps": {}}
        save_registry(default)
        return default
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"apps": {}}


def save_registry(registry: dict):
    """Save updated app registry to JSON file."""
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        print(f"[AppController] Failed to save registry: {e}")


def add_to_registry(app_key: str, path: str, win_exe: str, tags: list):
    """Add a newly discovered app to the JSON registry."""
    registry = load_registry()
    registry["apps"][app_key] = {
        "tags": tags,
        "path": path,
        "win_exe": win_exe
    }
    save_registry(registry)
    print(f"[AppController] ✅ Saved '{app_key}' to registry.")


# ──────────────────────────────────────────────
# INTENT PARSER
# Detects: open / close / switch + app name
# ──────────────────────────────────────────────
# ──────────────────────────────────────────────
# INTENT PARSER — requires "app" keyword
# ──────────────────────────────────────────────
def parse_command(command: str):
    """
    Only triggers if user includes 'app' keyword.
    Examples:
      "open app chrome"     → intent=open,   app=chrome
      "close app spotify"   → intent=close,  app=spotify
      "switch app vs code"  → intent=switch, app=vs code
      "open chrome"         → returns (None, None) — goes to file/LLM
    """
    text = command.lower().strip()

    # ✅ MUST contain the word "app" to be treated as app command
    if "app" not in text.split():
        return None, None

    open_kws   = ["open app", "launch app", "start app", "run app"]
    close_kws  = ["close app", "quit app", "exit app", "kill app", "stop app", "terminate app"]
    switch_kws = ["switch to app", "switch app", "go to app", "focus on app", "bring up app"]

    intent    = None
    remaining = text

    for kw in open_kws:
        if text.startswith(kw):
            intent    = "open"
            remaining = text[len(kw):].strip()
            break

    if not intent:
        for kw in close_kws:
            if text.startswith(kw):
                intent    = "close"
                remaining = text[len(kw):].strip()
                break

    if not intent:
        for kw in switch_kws:
            if text.startswith(kw):
                intent    = "switch"
                remaining = text[len(kw):].strip()
                break

    if not intent:
        return None, None

    return intent, remaining if remaining else None

# ──────────────────────────────────────────────
# SEARCH JSON REGISTRY BY TAGS
# ──────────────────────────────────────────────
def search_in_registry(app_name: str):
    """
    Search the JSON registry using tags.
    Returns the app entry dict or None.
    """
    registry = load_registry()
    app_name_lower = app_name.lower().strip()

    for key, data in registry["apps"].items():
        # Direct key match
        if app_name_lower == key.lower():
            return key, data
        # Tag match
        for tag in data.get("tags", []):
            if app_name_lower in tag.lower() or tag.lower() in app_name_lower:
                return key, data

    return None, None


# ──────────────────────────────────────────────
# DYNAMIC SEARCH — START MENU
# ──────────────────────────────────────────────
def search_start_menu(app_name: str):
    start_menu_paths = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    matches = []
    for base_path in start_menu_paths:
        pattern = os.path.join(base_path, "**", "*.lnk")
        for shortcut in glob.glob(pattern, recursive=True):
            filename = os.path.splitext(os.path.basename(shortcut))[0]
            if app_name.lower() in filename.lower():
                matches.append({"name": filename, "path": shortcut, "type": "shortcut"})
    return matches


# ──────────────────────────────────────────────
# DYNAMIC SEARCH — COMMON DIRECTORIES
# ──────────────────────────────────────────────
def search_common_dirs(app_name: str):
    search_dirs = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
        os.path.expandvars(r"%APPDATA%"),
        os.path.expandvars(r"%LOCALAPPDATA%"),
    ]
    matches = []
    for base_dir in search_dirs:
        if not os.path.exists(base_dir):
            continue
        for root, dirs, files in os.walk(base_dir):
            depth = root.replace(base_dir, "").count(os.sep)
            if depth > 2:
                dirs.clear()
                continue
            for file in files:
                if file.endswith(".exe") and app_name.lower() in file.lower():
                    matches.append({
                        "name": file.replace(".exe", ""),
                        "path": os.path.join(root, file),
                        "type": "exe",
                        "win_exe": file
                    })
    return matches


# ──────────────────────────────────────────────
# DYNAMIC SEARCH — WINDOWS REGISTRY
# ──────────────────────────────────────────────
def search_registry_system(app_name: str):
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    results = []
    for reg_path in reg_paths:
        try:
            reg = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            for i in range(winreg.QueryInfoKey(reg)[0]):
                try:
                    sub_key = winreg.OpenKey(reg, winreg.EnumKey(reg, i))
                    try:
                        display_name    = winreg.QueryValueEx(sub_key, "DisplayName")[0]
                        install_location = winreg.QueryValueEx(sub_key, "InstallLocation")[0]
                        if app_name.lower() in display_name.lower() and install_location:
                            results.append({"name": display_name, "path": install_location})
                    except FileNotFoundError:
                        pass
                except Exception:
                    continue
        except Exception:
            continue
    return results


# ──────────────────────────────────────────────
# MASTER DYNAMIC FINDER
# Searches system and saves result to registry
# ──────────────────────────────────────────────
def find_app_on_system(app_name: str):
    """
    Search across Start Menu → Directories → Registry.
    If found, auto-saves to JSON registry.
    Returns: {"path": ..., "name": ..., "type": ..., "win_exe": ...} or None
    """
    print(f"[AppController] 🔍 '{app_name}' not in registry. Searching system...")

    # Layer 1: Start Menu
    sm = search_start_menu(app_name)
    if sm:
        result = sm[0]
        print(f"[AppController] ✅ Found in Start Menu: {result['name']}")
        add_to_registry(
            app_key  = app_name.lower(),
            path     = result["path"],
            win_exe  = result["name"] + ".exe",
            tags     = [app_name.lower(), result["name"].lower()]
        )
        return result

    # Layer 2: Common Directories
    dirs = search_common_dirs(app_name)
    if dirs:
        result = dirs[0]
        print(f"[AppController] ✅ Found in directories: {result['path']}")
        add_to_registry(
            app_key  = app_name.lower(),
            path     = result["path"],
            win_exe  = result["win_exe"],
            tags     = [app_name.lower(), result["name"].lower()]
        )
        return result

    # Layer 3: Windows Registry
    reg = search_registry_system(app_name)
    if reg:
        install_path = reg[0]["path"]
        exe_pattern  = os.path.join(install_path, "**", f"*{app_name}*.exe")
        exes = glob.glob(exe_pattern, recursive=True)
        if exes:
            result = {
                "name"    : reg[0]["name"],
                "path"    : exes[0],
                "type"    : "exe",
                "win_exe" : os.path.basename(exes[0])
            }
            print(f"[AppController] ✅ Found via Registry: {exes[0]}")
            add_to_registry(
                app_key  = app_name.lower(),
                path     = exes[0],
                win_exe  = result["win_exe"],
                tags     = [app_name.lower(), reg[0]["name"].lower()]
            )
            return result

    print(f"[AppController] ❌ '{app_name}' not found on system.")
    return None


# ──────────────────────────────────────────────
# CHECK IF APP IS RUNNING
# ──────────────────────────────────────────────
def is_running(win_exe: str) -> bool:
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == win_exe.lower():
                return True
        except Exception:
            pass
    return False


# ──────────────────────────────────────────────
# OPEN APP
# ──────────────────────────────────────────────
def open_app(app_name: str) -> str:
    # Step 1: Search JSON registry by tags
    key, data = search_in_registry(app_name)

    if data:
        path    = os.path.expandvars(data["path"])
        win_exe = data.get("win_exe", "")

        # Already running? Just switch to it
        if win_exe and is_running(win_exe):
            return switch_to_app(app_name)

        # Try to open from registry path
        try:
            if path.endswith(".lnk"):
                os.startfile(path)
            else:
                subprocess.Popen(path)
            time.sleep(1.5)
            return f"✅ '{data.get('tags', [app_name])[0].title()}' opened successfully."
        except FileNotFoundError:
            print(f"[AppController] ⚠️ Registry path failed ({path}). Falling back to system search.")

    # Step 2: Not in registry or path broken → search system
    result = find_app_on_system(app_name)
    if not result:
        return (
            f"❌ Could not find '{app_name}' on your system.\n"
            f"💡 Make sure it is installed, or try its exact name."
        )

    try:
        if result.get("type") == "shortcut":
            os.startfile(result["path"])
        else:
            subprocess.Popen(result["path"])
        time.sleep(1.5)
        return f"✅ '{result['name']}' opened successfully."
    except Exception as e:
        return f"❌ Found '{result['name']}' but failed to open it: {str(e)}"


# ──────────────────────────────────────────────
# CLOSE APP
# ──────────────────────────────────────────────
def close_app(app_name: str) -> str:
    key, data = search_in_registry(app_name)
    win_exe = data.get("win_exe", "").lower() if data else None

    closed = False
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            pname = proc.info["name"].lower()
            if (win_exe and pname == win_exe) or (app_name.lower() in pname):
                proc.terminate()
                closed = True
        except Exception:
            continue

    return f"✅ '{app_name.title()}' closed." if closed else f"ℹ️ '{app_name.title()}' is not running."


# ──────────────────────────────────────────────
# SWITCH TO APP
# ──────────────────────────────────────────────
def switch_to_app(app_name: str = None) -> str:
    if app_name:
        for title in gw.getAllTitles():
            if title.strip() and app_name.lower() in title.lower():
                try:
                    win = gw.getWindowsWithTitle(title)[0]
                    win.restore()
                    win.activate()
                    return f"✅ Switched to '{title}'."
                except Exception as e:
                    return f"❌ Could not switch: {str(e)}"
        return f"❌ No open window found for '{app_name}'. Try opening it first."

    pyautogui.hotkey("alt", "tab")
    return "✅ Switched to the next application."


# ──────────────────────────────────────────────
# MAIN HANDLER — Call this from Chat_Bot.py
# ──────────────────────────────────────────────
def handle_app_command(command: str):
    """
    Entry point. Returns response string, or None if not an app command.
    Call this BEFORE sending to your AI/LLM.
    """
    intent, app_name = parse_command(command)

    if not intent:
        return None  # Not an app command → let LLM handle it

    if intent == "open":
        return open_app(app_name) if app_name else "❓ Which app would you like to open?"

    elif intent == "close":
        return close_app(app_name) if app_name else "❓ Which app would you like to close?"

    elif intent == "switch":
        return switch_to_app(app_name)

    return None