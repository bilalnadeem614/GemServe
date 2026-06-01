import os
import json
import glob
import time
import winreg
import subprocess
import psutil
import pygetwindow as gw
import pyautogui
import shutil

# ──────────────────────────────────────────────
# REGISTRY FILE — same folder as this script
# ──────────────────────────────────────────────
REGISTRY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_registry.json")


# ──────────────────────────────────────────────
# HELPER
# ──────────────────────────────────────────────
def clean_path(path: str) -> str:
    if not path:
        return ""
    return os.path.expandvars(path).strip().strip('"').strip("'")


# ──────────────────────────────────────────────
# CACHE — LOAD
# ──────────────────────────────────────────────
def load_registry() -> dict:
    if not os.path.exists(REGISTRY_FILE):
        return {"apps": {}}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"apps": {}}


# ──────────────────────────────────────────────
# CACHE — SAVE ONE APP
# ──────────────────────────────────────────────
def save_to_cache(app_key: str, path: str, win_exe: str, tags: list,
                  args: list = None, uwp_id: str = None):
    registry = load_registry()
    registry["apps"][app_key] = {
        "tags"         : tags,
        "path"         : path,
        "win_exe"      : win_exe,
        "args"         : args or [],
        "uwp_id"       : uwp_id or "",
        "last_verified": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        print(f"[Cache] ✅ Saved '{app_key}' → {REGISTRY_FILE}")
    except Exception as e:
        print(f"[Cache] ❌ Failed to save '{app_key}': {e}")


# ──────────────────────────────────────────────
# FIRST RUN    — write Chrome + Edge into JSON on first run
# Called once at module load. Skips if already present.
# ──────────────────────────────────────────────
def first_registry():
    """
    Pre-populate app_registry.json with Chrome, Edge and Excel.
    These are hardcoded because their paths are confirmed.
    All other apps are discovered at runtime and saved to cache then.
    """
    registry = load_registry()
    changed  = False

    # ── Chrome ────────────────────────────────
    if "chrome" not in registry["apps"]:
        chrome_candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            clean_path(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for candidate in chrome_candidates:
            if os.path.exists(candidate):
                registry["apps"]["chrome"] = {
                    "tags"         : ["chrom", "chrome", "google chrome", "googlechrome"],
                    "path"         : candidate,
                    "win_exe"      : "chrome.exe",
                    "args"         : ["--new-window"],
                    "uwp_id"       : "",
                    "last_verified": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                print(f"[Bootstrap] ✅ Chrome registered: {candidate}")
                changed = True
                break

    # ── Edge ──────────────────────────────────
    if "edge" not in registry["apps"]:
        edge_candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            clean_path(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        ]
        edge_saved = False
        for candidate in edge_candidates:
            if os.path.exists(candidate):
                registry["apps"]["edge"] = {
                    "tags"         : ["edgee", "edge", "microsoft edge", "msedge"],
                    "path"         : candidate,
                    "win_exe"      : "msedge.exe",
                    "args"         : ["--new-window"],
                    "uwp_id"       : "",
                    "last_verified": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                print(f"[Bootstrap] ✅ Edge registered: {candidate}")
                changed = True
                edge_saved = True
                break

        # Edge UWP fallback (some Windows 11 machines)
        if not edge_saved:
            registry["apps"]["edge"] = {
                "tags"         : ["edgee", "edge", "microsoft edge", "msedge"],
                "path"         : "",
                "win_exe"      : "msedge.exe",
                "args"         : [],
                "uwp_id"       : "Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!App",
                "last_verified": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            print("[Bootstrap] ✅ Edge registered as UWP fallback.")
            changed = True

    # ── Excel ─────────────────────────────────
    if "excel" not in registry["apps"]:
        excel_candidates = [
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files\Microsoft Office\Office16\EXCEL.EXE",
        ]
        for candidate in excel_candidates:
            if os.path.exists(candidate):
                registry["apps"]["excel"] = {
                    "tags"         : ["excel", "excell", "microsoft excel", "ms excel"],
                    "path"         : candidate,
                    "win_exe"      : "EXCEL.EXE",
                    "args"         : [],
                    "uwp_id"       : "",
                    "last_verified": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                print(f"[Bootstrap] ✅ Excel registered: {candidate}")
                changed = True
                break
    
    # ── WhatsApp ──────────────────────────────
    if "whatsapp" not in registry["apps"]:
        whatsapp_candidates = [
            clean_path(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
            clean_path(r"%APPDATA%\WhatsApp\WhatsApp.exe"),
        ]
        whatsapp_saved = False
        for candidate in whatsapp_candidates:
            if os.path.exists(candidate):
                registry["apps"]["whatsapp"] = {
                    "tags"         : ["whatsapp", "whats app"],
                    "path"         : candidate,
                    "win_exe"      : "WhatsApp.exe",
                    "args"         : [],
                    "uwp_id"       : "",
                    "last_verified": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                print(f"[Bootstrap] ✅ WhatsApp registered: {candidate}")
                changed = True
                whatsapp_saved = True
                break

        # WhatsApp UWP fallback (Store version)
        if not whatsapp_saved:
            registry["apps"]["whatsapp"] = {
                "tags"         : ["whatsapp", "whats app"],
                "path"         : "",
                "win_exe"      : "WhatsApp.exe",
                "args"         : [],
                "uwp_id"       : "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
                "last_verified": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            print("[Bootstrap] ✅ WhatsApp registered as UWP fallback.")
            changed = True
            
    # Save if anything was added
    if changed:
        try:
            os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            print(f"[Bootstrap] ✅ app_registry.json updated.")
        except Exception as e:
            print(f"[Bootstrap] ❌ Could not write registry: {e}")

# Run when module loads
first_registry()


# ──────────────────────────────────────────────
# CACHE — SEARCH BY NAME OR TAG
# ──────────────────────────────────────────────
def load_from_cache(app_name: str):
    registry  = load_registry()
    app_lower = app_name.lower().strip()

    for key, data in registry["apps"].items():
        if app_lower == key.lower():
            print(f"[Cache] ✅ Hit (key): '{key}'")
            return key, data
        for tag in data.get("tags", []):
            if app_lower in tag.lower() or tag.lower() in app_lower:
                print(f"[Cache] ✅ Hit (tag '{tag}'): '{key}'")
                return key, data

    print(f"[Cache] ℹ️ '{app_name}' not in cache — will search system.")
    return None, None


# ──────────────────────────────────────────────
# CACHE — VALIDATE (auto-remove broken paths)
# ──────────────────────────────────────────────
def validate_cache_entry(key: str, data: dict) -> bool:
    path = clean_path(data.get("path", ""))
    if not path:
        return True   # UWP app, no path to check
    if os.path.exists(path):
        return True
    print(f"[Cache] ⚠️ Broken path for '{key}': {path} — removing.")
    registry = load_registry()
    registry["apps"].pop(key, None)
    try:
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
    except Exception:
        pass
    return False


# ──────────────────────────────────────────────
# INTENT PARSER
# ──────────────────────────────────────────────
def parse_command(command: str):
    text = command.lower().strip()

    if "app" not in text.split():
        return None, None

    open_kws   = ["open app", "launch app", "start app", "run app"]
    close_kws  = ["close app", "quit app", "exit app", "kill app", "stop app", "terminate app"]
    switch_kws = ["switch to app", "switch app", "go to app", "focus on app", "bring up app"]

    intent = None
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
# RUNTIME SEARCH FUNCTIONS
# (used for all apps except Chrome & Edge)
# ──────────────────────────────────────────────

def search_start_menu(app_name: str):
    bases = [
        clean_path(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]
    for base in bases:
        for lnk in glob.glob(os.path.join(base, "**", "*.lnk"), recursive=True):
            name = os.path.splitext(os.path.basename(lnk))[0]
            if app_name.lower() in name.lower():
                print(f"[Search] ✅ Start Menu: {lnk}")
                return {"name": name, "path": lnk,
                        "win_exe": name + ".exe", "args": [], "uwp_id": ""}
    return None


def search_app_paths_registry(app_name: str):
    reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
    for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        try:
            reg = winreg.OpenKey(hive, reg_path)
            for i in range(winreg.QueryInfoKey(reg)[0]):
                try:
                    key_name = winreg.EnumKey(reg, i)
                    if app_name.lower() in key_name.lower():
                        sub  = winreg.OpenKey(reg, key_name)
                        path = clean_path(winreg.QueryValueEx(sub, "")[0])
                        if os.path.exists(path):
                            print(f"[Search] ✅ App Paths registry: {path}")
                            return {
                                "name"   : key_name.replace(".exe", "").replace(".EXE", ""),
                                "path"   : path,
                                "win_exe": os.path.basename(path),
                                "args"   : [],
                                "uwp_id" : "",
                            }
                except Exception:
                    continue
        except Exception:
            continue
    return None


def search_common_dirs(app_name: str):
    dirs = [
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        clean_path(r"%LOCALAPPDATA%\Programs"),
        clean_path(r"%APPDATA%"),
        clean_path(r"%LOCALAPPDATA%"),
    ]
    for base in dirs:
        if not os.path.exists(base):
            continue
        for root, subdirs, files in os.walk(base):
            if root.replace(base, "").count(os.sep) > 4:
                subdirs.clear()
                continue
            for f in files:
                if f.lower().endswith(".exe") and app_name.lower() in f.lower():
                    path = os.path.join(root, f)
                    print(f"[Search] ✅ Directory scan: {path}")
                    return {"name": f[:-4], "path": path,
                            "win_exe": f, "args": [], "uwp_id": ""}
    return None


def search_registry_uninstall(app_name: str):
    hive_pairs = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, reg_path in hive_pairs:
        try:
            reg = winreg.OpenKey(hive, reg_path)
            for i in range(winreg.QueryInfoKey(reg)[0]):
                try:
                    sub = winreg.OpenKey(reg, winreg.EnumKey(reg, i))
                    try:
                        name     = winreg.QueryValueEx(sub, "DisplayName")[0]
                        location = clean_path(winreg.QueryValueEx(sub, "InstallLocation")[0])
                        if app_name.lower() in name.lower() and location:
                            exes = glob.glob(
                                os.path.join(location, "**", f"*{app_name}*.exe"),
                                recursive=True
                            )
                            if exes:
                                print(f"[Search] ✅ Registry uninstall: {exes[0]}")
                                return {
                                    "name"   : name,
                                    "path"   : exes[0],
                                    "win_exe": os.path.basename(exes[0]),
                                    "args"   : [],
                                    "uwp_id" : "",
                                }
                    except FileNotFoundError:
                        pass
                except Exception:
                    continue
        except Exception:
            continue
    return None


def search_system_path(app_name: str):
    for name in [app_name + ".exe", app_name]:
        found = shutil.which(name)
        if found:
            found = clean_path(found)
            print(f"[Search] ✅ System PATH: {found}")
            return {"name": app_name, "path": found,
                    "win_exe": os.path.basename(found), "args": [], "uwp_id": ""}
    return None


# ──────────────────────────────────────────────
# MASTER FINDER
# Runs 4 runtime search layers, saves result to cache
# ──────────────────────────────────────────────
def find_app_on_system(app_name: str):
    """
    Called only when app is NOT in cache.
    Searches system across 4 layers and saves result to app_registry.json.
    """
    print(f"[Search] 🔍 Searching system for '{app_name}'...")

    for fn in [
        search_start_menu,
        search_app_paths_registry,
        search_common_dirs,
        search_registry_uninstall,
        search_system_path,
    ]:
        result = fn(app_name)
        if result:
            # Save to cache so next request is instant
            save_to_cache(
                app_key = app_name.lower(),
                path    = result.get("path", ""),
                win_exe = result.get("win_exe", ""),
                tags    = [app_name.lower(), result.get("name", app_name).lower()],
                args    = result.get("args", []),
                uwp_id  = result.get("uwp_id", ""),
            )
            return result

    print(f"[Search] ❌ '{app_name}' not found anywhere.")
    return None


# ──────────────────────────────────────────────
# SAFE LAUNCHER
# ──────────────────────────────────────────────
def launch_app(path: str, args: list = None, uwp_id: str = None) -> bool:
    # UWP Store app
    if uwp_id:
        try:
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{uwp_id}"], shell=False)
            print(f"[Launch] ✅ UWP: {uwp_id}")
            return True
        except Exception as e:
            print(f"[Launch] ❌ UWP failed: {e}")
            return False

    path = clean_path(path)
    if not path or not os.path.exists(path):
        print(f"[Launch] ❌ Path not found: {path}")
        return False

    try:
        if path.lower().endswith(".lnk") or os.path.isdir(path):
            os.startfile(path)
        else:
            subprocess.Popen([path] + (args or []), shell=False)
        print(f"[Launch] ✅ Launched: {path}")
        return True
    except PermissionError:
        try:
            subprocess.Popen([path] + (args or []), shell=True)
            print(f"[Launch] ✅ Launched (shell=True): {path}")
            return True
        except Exception as e:
            print(f"[Launch] ❌ PermissionError: {e}")
            return False
    except Exception as e:
        print(f"[Launch] ❌ Failed: {e}")
        return False


# ──────────────────────────────────────────────
# IS RUNNING
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
    # Step 1 — load from cache (Chrome & Edge always here after bootstrap)
    key, data = load_from_cache(app_name)

    if data:
        if not validate_cache_entry(key, data):
            data = None   # path broken → re-search

    if data:
        path    = clean_path(data.get("path", ""))
        win_exe = data.get("win_exe", "")
        args    = data.get("args", [])
        uwp_id  = data.get("uwp_id", "") or None

        if win_exe and is_running(win_exe):
            return switch_to_app(app_name)

        if launch_app(path, args, uwp_id):
            time.sleep(1.5)
            return f"✅ '{data['tags'][0].title()}' opened successfully."

        print(f"[Open] ⚠️ Cache launch failed — re-searching system.")

    # Step 2 — runtime search + auto-save to cache
    result = find_app_on_system(app_name)

    if not result:
        return (
            f"❌ Could not find '{app_name}' on your system.\n"
            f"💡 Make sure it is installed. Try exact name e.g. 'open app chrome'."
        )

    if launch_app(result.get("path", ""), result.get("args", []), result.get("uwp_id") or None):
        time.sleep(1.5)
        return f"✅ '{result['name']}' opened successfully."

    return f"❌ Found '{result['name']}' but could not open it. Try running as Administrator."


# ──────────────────────────────────────────────
# CLOSE APP
# ──────────────────────────────────────────────
def close_app(app_name: str) -> str:
    _, data = load_from_cache(app_name)
    win_exe = data.get("win_exe", "").lower() if data else app_name.lower()

    targets = []
    for proc in psutil.process_iter(["name", "pid", "ppid"]):
        try:
            pname = proc.info["name"].lower()
            if pname == win_exe or app_name.lower() in pname:
                targets.append(proc)
        except Exception:
            continue

    if not targets:
        return f"ℹ️ '{app_name.title()}' is not running."

    # Kill parent only for multi-process apps (Chrome, Edge)
    all_pids = {p.pid for p in targets}
    parents  = [p for p in targets if p.info["ppid"] not in all_pids]
    to_kill  = parents if parents else targets

    for proc in to_kill:
        try:
            proc.terminate()
        except Exception:
            continue

    return f"✅ '{app_name.title()}' closed."


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
        return f"❌ No open window found for '{app_name}'."

    pyautogui.hotkey("alt", "tab")
    return "✅ Switched to next application."


# ──────────────────────────────────────────────
# MAIN HANDLER — call from Chat_Bot.py
# ──────────────────────────────────────────────
def handle_app_command(command: str):
    intent, app_name = parse_command(command)
    if not intent:
        return None
    if intent == "open":
        return open_app(app_name)  if app_name else "❓ Which app to open?"
    elif intent == "close":
        return close_app(app_name) if app_name else "❓ Which app to close?"
    elif intent == "switch":
        return switch_to_app(app_name)
    return None