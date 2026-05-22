# services/system_intent_service.py
"""
LLM-based intent router for system settings commands.

Detects phrases like:
  - "set volume to 60"
  - "turn off bluetooth"
  - "change brightness to 80%"
  - "set wallpaper to C:/pics/photo.jpg"
  - "enable dark mode"
  - "lock my screen"
  - "open calculator"
  - "what is my battery level"
  - "shutdown in 1 minute"

Returns a structured dict that Chat_Bot.py can act on directly.
"""

import re
import json
from services.llm_service import _call_ollama
from utils.config import OLLAMA_FAST_MODEL


# ─────────────────────────────────────────────────────────────
# LLM PROMPT
# ─────────────────────────────────────────────────────────────

_SYSTEM_INTENT_PROMPT = """You are a system settings intent extractor. Given a user message, extract the system action.

Return ONLY a JSON object with these fields:
- "action": one of the actions listed below, or "none"
- "value": numeric value if applicable (volume 0-100, brightness 0-100), or null
- "target": string value if applicable (app name, file path, wifi network), or null

Actions:
- "set_volume" → set volume to a specific level (value: 0-100)
- "increase_volume" → raise volume (value: amount to increase, default 10)
- "decrease_volume" → lower volume (value: amount to decrease, default 10)
- "mute" → mute audio
- "unmute" → unmute audio
- "get_volume" → ask current volume level
- "set_brightness" → set brightness to level (value: 0-100)
- "increase_brightness" → raise brightness (value: amount, default 10)
- "decrease_brightness" → lower brightness (value: amount, default 10)
- "get_brightness" → ask current brightness
- "enable_bluetooth" → turn on bluetooth
- "disable_bluetooth" → turn off bluetooth
- "get_bluetooth" → check bluetooth status
- "enable_wifi" → turn on wifi
- "disable_wifi" → turn off wifi
- "get_wifi" → check wifi status / what network am I on
- "list_wifi" → list available wifi networks
- "enable_dark_mode" → switch to dark mode / night mode
- "enable_light_mode" → switch to light mode / day mode
- "set_wallpaper" → change desktop wallpaper (target: file path)
- "get_wallpaper" → what is current wallpaper
- "lock_screen" → lock the computer
- "sleep" → put computer to sleep
- "shutdown" → shut down / turn off computer (value: delay seconds, default 30)
- "restart" → restart / reboot computer (value: delay seconds, default 30)
- "cancel_shutdown" → cancel pending shutdown or restart
- "get_battery" → check battery level or status
- "get_system_info" → system info, specs, RAM, CPU
# - "launch_app" → open or launch an application (target: app name)
- "enable_focus" → enable do not disturb / focus mode
- "disable_focus" → disable do not disturb / focus mode
- "none" → not a system settings command

Examples:
"set volume to 60" → {"action": "set_volume", "value": 60, "target": null}
"turn bluetooth off" → {"action": "disable_bluetooth", "value": null, "target": null}
"increase brightness by 20" → {"action": "increase_brightness", "value": 20, "target": null}
"what's my battery" → {"action": "get_battery", "value": null, "target": null}
"open notepad" → {"action": "launch_app", "value": null, "target": "notepad"}
"change wallpaper to C:\\Users\\user\\Pictures\\bg.jpg" → {"action": "set_wallpaper", "value": null, "target": "C:\\Users\\user\\Pictures\\bg.jpg"}
"enable dark mode" → {"action": "enable_dark_mode", "value": null, "target": null}
"lock my screen" → {"action": "lock_screen", "value": null, "target": null}
"shutdown in 1 minute" → {"action": "shutdown", "value": 60, "target": null}
"what wifi networks are nearby" → {"action": "list_wifi", "value": null, "target": null}
"hello how are you" → {"action": "none", "value": null, "target": null}

User message: "{message}"
JSON:"""


# ─────────────────────────────────────────────────────────────
# ROUTING DETECTION (fast regex — used BEFORE the LLM parse)
# ─────────────────────────────────────────────────────────────

_SYSTEM_KEYWORDS = re.compile(
    r"\b("
    r"volume|mute|unmute|brightness|bluetooth|wifi|wi-fi|wireless|"
    r"dark mode|light mode|night mode|wallpaper|desktop background|"
    r"lock screen|lock my|sleep|shutdown|shut down|restart|reboot|"
    r"battery|charging|power|system info|ram|cpu|processor|"
    r"do not disturb|focus mode|focus assist|"
    # r"calculator|notepad|paint|chrome|firefox|edge|"
    # r"terminal|cmd|powershell|task manager|file explorer|"  
    # r"word|excel|powerpoint|outlook|vlc|spotify|"           
    # r"launch|open app|cancel shutdown"
    r")\b",
    re.IGNORECASE,
)

# Additional patterns that strongly suggest system commands
_SYSTEM_PATTERNS = [
    re.compile(r"\b(turn|switch|enable|disable)\b.{0,20}\b(volume|brightness|bluetooth|wifi|wi-fi|wireless|dark mode|light mode|focus|dnd)\b", re.I),
    re.compile(r"\bset\b.{0,10}\b(volume|brightness|wallpaper)\b", re.I),
    re.compile(r"\b(increase|decrease|raise|lower|bump up|turn up|turn down)\b.{0,15}\b(volume|brightness)\b", re.I),
    re.compile(r"\b(what.{0,10}(battery|wifi|bluetooth|volume|brightness))\b", re.I),
    re.compile(r"\b(lock|sleep|hibernate)\b.{0,10}\b(screen|computer|pc|laptop|system)\b", re.I),
    re.compile(r"\b(my|the)\b.{0,5}\b(battery|brightness|volume|wifi|bluetooth)\b", re.I),
]


def is_system_command(text: str) -> bool:
    """
    Fast pre-filter — returns True if message MIGHT be a system command.
    Used before calling the LLM to avoid unnecessary inference.
    """
    if _SYSTEM_KEYWORDS.search(text):
        return True
    for p in _SYSTEM_PATTERNS:
        if p.search(text):
            return True
    return False


# ─────────────────────────────────────────────────────────────
# LLM INTENT PARSER
# ─────────────────────────────────────────────────────────────


# def parse_system_intent(text: str) -> dict:
#     """
#     Use LLM to extract system command intent.
#     Falls back to regex parser on failure.

#     Returns:
#         {
#             "action": str,
#             "value": int | None,
#             "target": str | None,
#             "confidence": float,
#             "source": "llm" | "regex"
#         }
#     """
#     # Quick exit for clearly non-system messages
#     if not is_system_command(text):
#         return {
#             "action": "none",
#             "value": None,
#             "target": None,
#             "confidence": 0.0,
#             "source": "regex",
#         }

#     # Try LLM first
#     try:
#         prompt = _SYSTEM_INTENT_PROMPT.replace("{message}", text)
#         response = _call_ollama(prompt, OLLAMA_FAST_MODEL, timeout=15).strip()

#         # Parse JSON from response
#         try:
#             result = json.loads(response)
#         except Exception:
#             m = re.search(r"\{[^{}]+\}", response, re.DOTALL)
#             if m:
#                 result = json.loads(m.group())
#             else:
#                 raise ValueError("No JSON in response")

#         action = result.get("action", "none").lower().strip()
#         value = result.get("value")
#         target = result.get("target")

#         # Normalise value
#         if value is not None:
#             try:
#                 value = int(float(str(value)))
#             except Exception:
#                 value = None

#         if action != "none":
#             return {
#                 "action": action,
#                 "value": value,
#                 "target": target,
#                 "confidence": 0.9,
#                 "source": "llm",
#             }
#         return _regex_parse_system_intent(text)

#     except Exception as e:
#         print(f"⚠️ System intent LLM parse failed: {e} — using regex fallback")

#     # Fallback to regex
#     return _regex_parse_system_intent(text)
def parse_system_intent(text: str) -> dict:
    """
    Regex-first approach - LLM bypass.
    """
    if not is_system_command(text):
        return {
            "action": "none",
            "value": None,
            "target": None,
            "confidence": 0.0,
            "source": "regex",
        }

    # Direct regex - no LLM
    return _regex_parse_system_intent(text)

# ─────────────────────────────────────────────────────────────
# REGEX FALLBACK PARSER
# ─────────────────────────────────────────────────────────────


def _extract_number(text: str) -> int | None:
    """Extract the first integer from text."""
    m = re.search(r"\b(\d+)\b", text)
    return int(m.group(1)) if m else None


def _regex_parse_system_intent(text: str) -> dict:
    t = text.lower().strip()

    def _r(action, value=None, target=None):
        return {
            "action": action,
            "value": value,
            "target": target,
            "confidence": 0.8,
            "source": "regex",
        }
    # ── Bluetooth ────────────────────────────────
    if re.search(r"\b(turn on|enable|switch on|connect)\b.{0,10}bluetooth\b", t):
        return _r("enable_bluetooth")
    if re.search(r"\b(turn off|disable|switch off|disconnect)\b.{0,10}bluetooth\b", t):
        return _r("disable_bluetooth")
    if re.search(
        r"\bbluetooth\b.{0,15}\b(on|off|status|enabled|disabled)\b", t
    ) or re.search(r"\b(is|check).{0,10}bluetooth\b", t):
        return _r("get_bluetooth")

    # ── Brightness ───────────────────────────────
    if re.search(r"\b(set|change)\b.{0,10}brightness\b", t) or re.search(
        r"brightness.{0,10}\bto\b", t
    ):
        n = _extract_number(t)
        return _r("set_brightness", n or 70)
    if re.search(
        r"\b(increase|raise|turn up|higher|brighter)\b.{0,15}brightness\b", t
    ) or re.search(r"brightness.{0,10}\b(up|higher|brighter)\b", t):
        n = _extract_number(t)
        return _r("increase_brightness", n or 10)
    if re.search(
        r"\b(decrease|lower|turn down|reduce|dimmer|dim)\b.{0,15}brightness\b", t
    ) or re.search(r"brightness.{0,10}\b(down|lower|dim)\b", t):
        n = _extract_number(t)
        return _r("decrease_brightness", n or 10)
    if re.search(
        r"\b(what.{0,10}brightness|brightness\b.{0,10}(level|now|current))\b", t
    ):
        return _r("get_brightness")

    

    # ── Wi-Fi ─────────────────────────────────────
    if re.search(r"\b(turn on|enable|switch on)\b.{0,10}(wifi|wi-fi|wireless)\b", t):
        return _r("enable_wifi")
    if re.search(r"\b(turn off|disable|switch off)\b.{0,10}(wifi|wi-fi|wireless)\b", t):
        return _r("disable_wifi")
    if re.search(
        r"\b(list|show|nearby|available|what).{0,10}(wifi|wi-fi|network)\b", t
    ):
        return _r("list_wifi")
    if re.search(
        r"\b(wifi|wi-fi|internet).{0,15}(status|connected|on|off)\b", t
    ) or re.search(r"\b(am i|are we).{0,10}connected\b", t):
        return _r("get_wifi")

    # ── Dark / Light mode ────────────────────────
    if re.search(r"\b(dark mode|night mode|dark theme)\b", t) or re.search(
        r"\b(enable|turn on|switch to|use)\b.{0,10}dark\b", t
    ):
        return _r("enable_dark_mode")
    if re.search(r"\b(light mode|day mode|light theme)\b", t) or re.search(
        r"\b(enable|turn on|switch to|use)\b.{0,10}light\b", t
    ):
        return _r("enable_light_mode")

    # ── Wallpaper ────────────────────────────────
    if re.search(r"\b(set|change|update)\b.{0,10}wallpaper\b", t) or re.search(
        r"\bdesktop background\b", t
    ):
        # Try to extract a path
        m = re.search(r'["\']([^"\']+\.(jpg|jpeg|png|bmp))["\']', text, re.I)
        if not m:
            m = re.search(r"([A-Za-z]:\\[^\s]+\.(jpg|jpeg|png|bmp))", text, re.I)
        target = m.group(1) if m else None
        return _r("set_wallpaper", target=target)
    if re.search(r"\b(what.{0,10}wallpaper|current wallpaper)\b", t):
        return _r("get_wallpaper")

    # ── Lock / Sleep / Power ─────────────────────
    if re.search(r"\block.{0,10}(screen|computer|pc|laptop)\b", t) or re.search(
        r"\b(lock screen|lock my screen)\b", t
    ):
        return _r("lock_screen")
    if re.search(
        r"\b(sleep|hibernate|suspend)\b.{0,10}(computer|pc|laptop|system)\b", t
    ) or re.search(r"\b(put it to sleep|go to sleep)\b", t):
        return _r("sleep")
    if re.search(r"\b(cancel|abort).{0,10}(shutdown|restart|reboot)\b", t):
        return _r("cancel_shutdown")
    if re.search(
        r"\b(shutdown|shut down|turn off|power off)\b.{0,15}(computer|pc|laptop|system)?\b",
        t,
    ):
        n = _extract_number(t)
        # Convert minutes to seconds if "minute" in text
        if n and re.search(r"\bminute\b", t):
            n *= 60
        return _r("shutdown", n or 30)
    if re.search(r"\b(restart|reboot)\b", t):
        n = _extract_number(t)
        if n and re.search(r"\bminute\b", t):
            n *= 60
        return _r("restart", n or 30)

    # ── Battery / System info ────────────────────
    if re.search(r"\b(battery|charging|power level)\b", t):
        return _r("get_battery")
    if re.search(r"\b(system info|my specs|cpu|ram|processor|memory)\b", t):
        return _r("get_system_info")

    
    
    # ── Volume ────────────────────────────────────
    if re.search(r"\bmute\b", t) and not re.search(r"\bunmute\b", t):
        return _r("mute")
    if re.search(r"\bunmute\b", t):
        return _r("unmute")
    if re.search(r"\b(set|change)\b.{0,10}volume\b", t) or re.search(
        r"volume.{0,10}\bto\b", t
    ):
        n = _extract_number(t)
        return _r("set_volume", n or 50)
    if re.search(
        r"\b(increase|raise|turn up|bump up|louder|higher)\b.{0,15}volume\b", t
    ) or re.search(r"volume.{0,10}\b(up|higher|louder)\b", t):
        n = _extract_number(t)
        return _r("increase_volume", n or 10)
    if re.search(
        r"\b(decrease|lower|turn down|reduce|quieter|softer)\b.{0,15}volume\b", t
    ) or re.search(r"volume.{0,10}\b(down|lower|quieter)\b", t):
        n = _extract_number(t)
        return _r("decrease_volume", n or 10)
    if re.search(r"\b(what.{0,10}volume|volume\b.{0,10}(level|now|current))\b", t):
        return _r("get_volume")

    # ── App launch ───────────────────────────────
    app_match = re.search(
        r"\b(open|launch|start|run)\b.{0,5}"
        r"(calculator|notepad|paint|task manager|file explorer|"
        r"explorer|control panel|settings|camera|maps|store|"
        r"chrome|firefox|edge|browser|word|excel|powerpoint|"
        r"terminal|cmd|powershell|snipping tool|screenshot|calendar|mail|clock)\b",
        t,
    )
    if app_match:
        return _r("launch_app", target=app_match.group(2))

    # ── Focus Assist ─────────────────────────────
    if re.search(
        r"\b(enable|turn on|activate)\b.{0,15}(do not disturb|focus|dnd)\b", t
    ):
        return _r("enable_focus")
    if re.search(
        r"\b(disable|turn off|deactivate)\b.{0,15}(do not disturb|focus|dnd)\b", t
    ):
        return _r("disable_focus")

    return {
        "action": "none",
        "value": None,
        "target": None,
        "confidence": 0.0,
        "source": "regex",
    }


# ─────────────────────────────────────────────────────────────
# EXECUTOR — maps intent → system_service call
# ─────────────────────────────────────────────────────────────


def execute_system_command(intent: dict) -> dict:
    """
    Execute the system command described by the intent dict.
    Returns {"status": ..., "message": ...}
    """
    from services import system_service as ss

    action = intent.get("action", "none")
    value = intent.get("value")
    target = intent.get("target")

    dispatch = {
        "set_volume": lambda: ss.set_volume(value if value is not None else 50),
        "increase_volume": lambda: ss.increase_volume(value or 10),
        "decrease_volume": lambda: ss.decrease_volume(value or 10),
        "mute": lambda: ss.mute_volume(),
        "unmute": lambda: ss.unmute_volume(),
        "get_volume": lambda: ss.get_volume(),
        "set_brightness": lambda: ss.set_brightness(value if value is not None else 70),
        "increase_brightness": lambda: ss.increase_brightness(value or 10),
        "decrease_brightness": lambda: ss.decrease_brightness(value or 10),
        "get_brightness": lambda: ss.get_brightness(),
        "enable_bluetooth": lambda: ss.enable_bluetooth(),
        "disable_bluetooth": lambda: ss.disable_bluetooth(),
        "get_bluetooth": lambda: ss.get_bluetooth_status(),
        "enable_wifi": lambda: ss.enable_wifi(),
        "disable_wifi": lambda: ss.disable_wifi(),
        "get_wifi": lambda: ss.get_wifi_status(),
        "list_wifi": lambda: ss.list_wifi_networks(),
        "enable_dark_mode": lambda: ss.set_dark_mode(True),
        "enable_light_mode": lambda: ss.set_dark_mode(False),
        "set_wallpaper": lambda: (
            ss.set_wallpaper(target)
            if target
            else {
                "status": "error",
                "message": "❌ Please provide the full path to an image file.\n"
                "Example: set wallpaper to C:\\Users\\You\\Pictures\\bg.jpg",
            }
        ),
        "get_wallpaper": lambda: ss.get_current_wallpaper(),
        "lock_screen": lambda: ss.lock_screen(),
        "sleep": lambda: ss.sleep_computer(),
        "shutdown": lambda: ss.shutdown_computer(value or 30),
        "restart": lambda: ss.restart_computer(value or 30),
        "cancel_shutdown": lambda: ss.cancel_shutdown(),
        "get_battery": lambda: ss.get_battery_status(),
        "get_system_info": lambda: ss.get_system_info(),
        "launch_app": lambda: ss.launch_app(target or "explorer"),
        "enable_focus": lambda: ss.set_focus_assist(True),
        "disable_focus": lambda: ss.set_focus_assist(False),
    }

    handler = dispatch.get(action)
    if handler:
        try:
            return handler()
        except Exception as e:
            return {"status": "error", "message": f"❌ System command failed: {str(e)}"}

    return {"status": "error", "message": f"❌ Unknown system action: {action}"}


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────


def handle_system_command(text: str) -> dict:
    """
    Full pipeline: detect → parse intent → execute.
    Returns {"status": ..., "message": ...} ready for display.
    """
    intent = parse_system_intent(text)

    if intent["action"] == "none":
        return {"status": "none", "message": ""}

    print(f"🖥️ System intent: {intent}")
    return execute_system_command(intent)
