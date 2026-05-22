# services/system_service.py
"""
Windows system settings controller.
Handles: wallpaper, volume, brightness, Bluetooth, Wi-Fi, dark/light mode,
         screen lock, sleep, restart, shutdown, app launch.

All functions return:
    {"status": "success"|"error"|"info", "message": str}
"""

import os
import re
import subprocess
import ctypes
from pathlib import Path


# ─────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────

def _run_ps(script: str, timeout: int = 15) -> tuple:
    """Run a PowerShell script and return (success, output)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=timeout
        )
        out = (result.stdout + result.stderr).strip()
        return result.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "Command timed out."
    except FileNotFoundError:
        return False, "PowerShell not found."
    except Exception as e:
        return False, str(e)


def _run_cmd(command: list, timeout: int = 10) -> tuple:
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, shell=False
        )
        out = (result.stdout + result.stderr).strip()
        return result.returncode == 0, out
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────────────────────
# VOLUME
# C# source stored as a plain string — no f-string so Python
# never touches the braces inside the C# class definition.
# PowerShell does NOT support the C# "f" float suffix — use
# [float] casting instead: [float]0.60  not  0.60f
# ─────────────────────────────────────────────────────────────

_AUDIO_CS = """\
using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {
    int NotImpl1();
    int NotImpl2();
    int NotImpl3();
    int NotImpl4();
    int SetMasterVolumeLevelScalar(float fLevel, Guid pguidEventContext);
    int NotImpl6();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int NotImpl8();
    int NotImpl9();
    int NotImpl10();
    int NotImpl11();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, Guid pguidEventContext);
    int GetMute(out bool pbMute);
}

[Guid("D666063F-1587-4E43-81F1-B948E807363F")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {
    int Activate([MarshalAs(UnmanagedType.LPStruct)] Guid iid, int dwClsCtx,
                 IntPtr pActivationParams,
                 [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface);
    int OpenPropertyStore(int stgmAccess, out IntPtr ppProperties);
    int GetId([MarshalAs(UnmanagedType.LPWStr)] out string ppstrId);
    int GetState(out int pdwState);
}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
    int EnumAudioEndpoints(int dataFlow, int dwStateMask, out IntPtr ppDevices);
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppEndpoint);
}

[ComImport]
[Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject { }

public class AudioManager {
    private static IAudioEndpointVolume GetVol() {
        var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
        IMMDevice dev;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        object volObj;
        dev.Activate(typeof(IAudioEndpointVolume).GUID, 0, IntPtr.Zero, out volObj);
        return (IAudioEndpointVolume)volObj;
    }
    public static void SetVolume(float level) {
        GetVol().SetMasterVolumeLevelScalar(level, Guid.Empty);
    }
    public static float GetVolume() {
        float v;
        GetVol().GetMasterVolumeLevelScalar(out v);
        return v;
    }
    public static void SetMute(bool mute) {
        GetVol().SetMute(mute, Guid.Empty);
    }
    public static bool GetMute() {
        bool m;
        GetVol().GetMute(out m);
        return m;
    }
}
"""


def _audio_script(ps_commands: str) -> str:
    """
    Build a PowerShell script that compiles AudioManager then runs ps_commands.
    The C# is embedded via a here-string so no Python string formatting
    ever touches the C# braces.
    """
    cs_safe = _AUDIO_CS.replace("'", "''")   # escape PS here-string single quotes
    return "@'\n" + cs_safe + "\n'@\n" + \
           "| Set-Variable -Name cs\n" \
           "Add-Type -TypeDefinition $cs -PassThru | Out-Null\n" + \
           ps_commands


def _audio_script2(ps_commands: str) -> str:
    """
    Alternative builder that avoids the pipeline assignment
    (more compatible across PS versions).
    """
    cs_safe = _AUDIO_CS.replace("'", "''")
    lines = [
        "$cs = @'",
        cs_safe,
        "'@",
        "Add-Type -TypeDefinition $cs -PassThru | Out-Null",
        ps_commands,
    ]
    return "\n".join(lines)


def set_volume(level: int) -> dict:
    """Set master volume (0-100)."""
    level = max(0, min(100, int(level)))
    # Use [float] cast — NOT the C# 'f' suffix which PowerShell doesn't understand
    fval = f"{level / 100.0:.4f}"
    ps = f"[AudioManager]::SetVolume([float]{fval})"
    script = _audio_script2(ps)
    ok, out = _run_ps(script, timeout=20)
    if "error" not in out.lower() and "exception" not in out.lower():
        return {"status": "success", "message": f"🔊 Volume set to {level}%"}
    return {"status": "error", "message": f"❌ Could not set volume: {out}"}


def get_volume() -> dict:
    """Get current master volume level."""
    ps = "[int]([AudioManager]::GetVolume() * 100)"
    script = _audio_script2(ps)
    ok, out = _run_ps(script, timeout=20)
    lines = [l.strip() for l in out.splitlines() if l.strip().isdigit()]
    if lines:
        return {"status": "info", "message": f"🔊 Current volume: {lines[-1]}%"}
    return {"status": "info", "message": "🔊 Could not read volume level."}


def mute_volume() -> dict:
    """Mute system audio."""
    script = _audio_script2("[AudioManager]::SetMute($true)")
    _run_ps(script, timeout=20)
    return {"status": "success", "message": "🔇 Audio muted."}


def unmute_volume() -> dict:
    """Unmute system audio."""
    script = _audio_script2("[AudioManager]::SetMute($false)")
    _run_ps(script, timeout=20)
    return {"status": "success", "message": "🔊 Audio unmuted."}


def increase_volume(amount: int = 10) -> dict:
    """Increase volume by amount percent."""
    amount = max(1, min(100, int(amount)))
    famt = f"{amount / 100.0:.4f}"
    ps = "\n".join([
        "$cur = [AudioManager]::GetVolume()",
        f"$new = [Math]::Min([float]1.0, $cur + [float]{famt})",
        "[AudioManager]::SetVolume([float]$new)",
        "[int]($new * 100)",
    ])
    script = _audio_script2(ps)
    ok, out = _run_ps(script, timeout=20)
    lines = [l.strip() for l in out.splitlines() if l.strip().isdigit()]
    level = lines[-1] if lines else "?"
    return {"status": "success", "message": f"🔊 Volume increased to {level}%"}


def decrease_volume(amount: int = 10) -> dict:
    """Decrease volume by amount percent."""
    amount = max(1, min(100, int(amount)))
    famt = f"{amount / 100.0:.4f}"
    ps = "\n".join([
        "$cur = [AudioManager]::GetVolume()",
        f"$new = [Math]::Max([float]0.0, $cur - [float]{famt})",
        "[AudioManager]::SetVolume([float]$new)",
        "[int]($new * 100)",
    ])
    script = _audio_script2(ps)
    ok, out = _run_ps(script, timeout=20)
    lines = [l.strip() for l in out.splitlines() if l.strip().isdigit()]
    level = lines[-1] if lines else "?"
    return {"status": "success", "message": f"🔉 Volume decreased to {level}%"}


# ─────────────────────────────────────────────────────────────
# WALLPAPER
# ─────────────────────────────────────────────────────────────

def set_wallpaper(image_path: str) -> dict:
    path = Path(image_path)
    if not path.exists():
        return {"status": "error", "message": f"❌ File not found: {image_path}"}
    if path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
        return {"status": "error", "message": "❌ Unsupported format. Use JPG, PNG, or BMP."}
    target = str(path.resolve())
    SPI_SETDESKWALLPAPER = 20
    ok = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, target, 3)
    if ok:
        return {"status": "success", "message": f"✅ Wallpaper set to: {path.name}"}
    return {"status": "error", "message": "❌ Failed to set wallpaper. Try a JPG or BMP file."}


def get_current_wallpaper() -> dict:
    buf = ctypes.create_unicode_buffer(512)
    ctypes.windll.user32.SystemParametersInfoW(0x0073, 512, buf, 0)
    path = buf.value
    if path:
        return {"status": "info", "message": f"🖼️ Current wallpaper: {path}"}
    return {"status": "info", "message": "🖼️ No wallpaper is currently set."}


# ─────────────────────────────────────────────────────────────
# BRIGHTNESS
# ─────────────────────────────────────────────────────────────

def set_brightness(level: int) -> dict:
    level = max(0, min(100, int(level)))
    script = "\n".join([
        "$m = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods -ErrorAction SilentlyContinue",
        "if ($m) {",
        f"    $m.WmiSetBrightness(1, {level})",
        "    Write-Output 'ok'",
        "} else { Write-Output 'no_wmi' }",
    ])
    ok, out = _run_ps(script)
    if "ok" in out:
        return {"status": "success", "message": f"☀️ Brightness set to {level}%"}
    return {"status": "error", "message": "❌ Brightness control not supported on this display (laptop screens only)."}


def get_brightness() -> dict:
    script = "\n".join([
        "$b = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness -ErrorAction SilentlyContinue",
        "if ($b) { Write-Output $b.CurrentBrightness } else { Write-Output 'unsupported' }",
    ])
    ok, out = _run_ps(script)
    out = out.strip()
    if out.isdigit():
        return {"status": "info", "message": f"☀️ Current brightness: {out}%"}
    return {"status": "info", "message": "☀️ Brightness level unavailable (external monitor?)."}


def increase_brightness(amount: int = 10) -> dict:
    amount = max(1, min(100, int(amount)))
    script = "\n".join([
        "$b = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness -ErrorAction SilentlyContinue",
        "if ($b) {",
        "    $cur = $b.CurrentBrightness",
        f"    $new = [Math]::Min(100, $cur + {amount})",
        "    $m = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods",
        "    $m.WmiSetBrightness(1, $new)",
        "    Write-Output $new",
        "} else { Write-Output 'unsupported' }",
    ])
    ok, out = _run_ps(script)
    out = out.strip()
    if out.isdigit():
        return {"status": "success", "message": f"☀️ Brightness increased to {out}%"}
    return {"status": "error", "message": "❌ Could not adjust brightness (laptop screen only)."}


def decrease_brightness(amount: int = 10) -> dict:
    amount = max(1, min(100, int(amount)))
    script = "\n".join([
        "$b = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness -ErrorAction SilentlyContinue",
        "if ($b) {",
        "    $cur = $b.CurrentBrightness",
        f"    $new = [Math]::Max(0, $cur - {amount})",
        "    $m = Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods",
        "    $m.WmiSetBrightness(1, $new)",
        "    Write-Output $new",
        "} else { Write-Output 'unsupported' }",
    ])
    ok, out = _run_ps(script)
    out = out.strip()
    if out.isdigit():
        return {"status": "success", "message": f"🌙 Brightness decreased to {out}%"}
    return {"status": "error", "message": "❌ Could not adjust brightness (laptop screen only)."}


# ─────────────────────────────────────────────────────────────
# BLUETOOTH
# ─────────────────────────────────────────────────────────────

# Bluetooth script built with plain string concatenation — no f-string
# heredocs so PowerShell curly braces are never mangled by Python.
_BT_PREAMBLE = (
    "Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null\n"
    "$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | "
    "Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and "
    "$_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]\n"
    "function Await($WinRtTask, $ResultType) {\n"
    "    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)\n"
    "    $netTask = $asTask.Invoke($null, @($WinRtTask))\n"
    "    $netTask.Wait(-1) | Out-Null\n"
    "    $netTask.Result\n"
    "}\n"
    "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null\n"
    "[Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null\n"
    "[Windows.Devices.Radios.RadioState,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null\n"
    "$radios = Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) "
    "([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]])\n"
    "$bt = $radios | Where-Object { $_.Kind -eq [Windows.Devices.Radios.RadioKind]::Bluetooth } "
    "| Select-Object -First 1\n"
)


def _bluetooth_toggle(enable: bool) -> dict:
    state_word = "On" if enable else "Off"
    emoji = "🔵" if enable else "⭕"
    label = "enabled" if enable else "disabled"

    script = (
        _BT_PREAMBLE
        + "if ($bt) {\n"
        + f"    $targetState = [Windows.Devices.Radios.RadioState]::{state_word}\n"
        + "    $result = Await ($bt.SetStateAsync($targetState)) ([Windows.Devices.Radios.RadioAccessStatus])\n"
        + '    Write-Output "ok:$result"\n'
        + "} else {\n"
        + "    Write-Output 'no_radio'\n"
        + "}"
    )
    ok, out = _run_ps(script, timeout=20)

    if "ok:" in out.lower():
        return {"status": "success", "message": f"{emoji} Bluetooth {label}."}
    if "no_radio" in out:
        return {"status": "error", "message": "❌ No Bluetooth adapter found on this device."}

    # Fallback: PnpDevice toggle (requires admin)
    ps_cmd = "Enable" if enable else "Disable"
    script2 = (
        "$bt = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue "
        "| Where-Object { $_.Status -ne 'Unknown' } | Select-Object -First 1\n"
        "if ($bt) {\n"
        f"    {ps_cmd}-PnpDevice -InstanceId $bt.InstanceId -Confirm:$false -ErrorAction Stop\n"
        "    Write-Output 'ok'\n"
        "} else {\n"
        "    Write-Output 'not_found'\n"
        "}"
    )
    ok2, out2 = _run_ps(script2, timeout=15)
    if "ok" in out2:
        return {"status": "success", "message": f"{emoji} Bluetooth {label}."}
    if "not_found" in out2:
        return {"status": "error", "message": "❌ No Bluetooth adapter found."}

    return {
        "status": "error",
        "message": (
            f"❌ Could not {'enable' if enable else 'disable'} Bluetooth automatically.\n"
            "Try: Settings → Bluetooth & devices → toggle Bluetooth manually."
        )
    }


def enable_bluetooth() -> dict:
    return _bluetooth_toggle(True)


def disable_bluetooth() -> dict:
    return _bluetooth_toggle(False)


def get_bluetooth_status() -> dict:
    script = (
        _BT_PREAMBLE
        + "if ($bt) { Write-Output $bt.State } else { Write-Output 'not_found' }"
    )
    ok, out = _run_ps(script, timeout=15)
    out = out.strip()
    if "On" in out:
        return {"status": "info", "message": "🔵 Bluetooth is ON."}
    if "Off" in out:
        return {"status": "info", "message": "⭕ Bluetooth is OFF."}
    if "not_found" in out:
        return {"status": "info", "message": "⭕ No Bluetooth adapter found."}
    return {"status": "info", "message": f"🔵 Bluetooth status: {out}"}


# ─────────────────────────────────────────────────────────────
# WI-FI
# ─────────────────────────────────────────────────────────────

def _get_wifi_adapter_name() -> str:
    ok, out = _run_cmd(["netsh", "interface", "show", "interface"])
    if ok and out:
        for line in out.splitlines():
            for keyword in ("wi-fi", "wifi", "wireless", "wlan"):
                if keyword in line.lower():
                    parts = line.split()
                    if parts:
                        return parts[-1]
    return "Wi-Fi"


def enable_wifi() -> dict:
    adapter = _get_wifi_adapter_name()
    ok, out = _run_cmd(["netsh", "interface", "set", "interface", adapter, "admin=enable"])
    if ok:
        return {"status": "success", "message": "📶 Wi-Fi enabled."}
    return {"status": "error", "message": f"❌ Could not enable Wi-Fi: {out}"}


def disable_wifi() -> dict:
    adapter = _get_wifi_adapter_name()
    ok, out = _run_cmd(["netsh", "interface", "set", "interface", adapter, "admin=disable"])
    if ok:
        return {"status": "success", "message": "📵 Wi-Fi disabled."}
    return {"status": "error", "message": f"❌ Could not disable Wi-Fi: {out}"}


def get_wifi_status() -> dict:
    ok, out = _run_cmd(["netsh", "wlan", "show", "interfaces"])
    if ok and out:
        if "connected" in out.lower():
            m = re.search(r"SSID\s*:\s*(.+)", out)
            ssid = m.group(1).strip() if m else "unknown"
            return {"status": "info", "message": f"📶 Wi-Fi connected to: {ssid}"}
        if "disconnected" in out.lower():
            return {"status": "info", "message": "📵 Wi-Fi is disconnected."}
    return {"status": "info", "message": "📵 Wi-Fi is off or not available."}


def list_wifi_networks() -> dict:
    ok, out = _run_cmd(["netsh", "wlan", "show", "networks"])
    if ok and out:
        networks = re.findall(r"SSID\s+\d+\s*:\s*(.+)", out)
        if networks:
            net_list = "\n".join(f"  • {n.strip()}" for n in networks[:15])
            return {"status": "info", "message": f"📶 Available Wi-Fi networks:\n{net_list}"}
    return {"status": "info", "message": "📵 No Wi-Fi networks found or Wi-Fi is off."}


# ─────────────────────────────────────────────────────────────
# DARK / LIGHT MODE
# ─────────────────────────────────────────────────────────────

def set_dark_mode(enable: bool) -> dict:
    value = 0 if enable else 1
    label = "Dark" if enable else "Light"
    emoji = "🌙" if enable else "☀️"
    reg_path = r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    script = "\n".join([
        f'Set-ItemProperty -Path "{reg_path}" -Name AppsUseLightTheme -Value {value} -ErrorAction SilentlyContinue',
        f'Set-ItemProperty -Path "{reg_path}" -Name SystemUsesLightTheme -Value {value} -ErrorAction SilentlyContinue',
        "Write-Output 'ok'",
    ])
    _run_ps(script)
    return {
        "status": "success",
        "message": f"{emoji} Windows switched to {label} Mode.\n(Reopen apps to see the change.)"
    }


# ─────────────────────────────────────────────────────────────
# SCREEN LOCK / SLEEP / POWER
# ─────────────────────────────────────────────────────────────

def lock_screen() -> dict:
    _run_cmd(["rundll32", "user32.dll,LockWorkStation"])
    return {"status": "success", "message": "🔒 Screen locked."}


def sleep_computer() -> dict:
    script = "\n".join([
        "Add-Type -Assembly System.Windows.Forms",
        "[System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)",
    ])
    ok, out = _run_ps(script)
    if ok:
        return {"status": "success", "message": "💤 Computer going to sleep."}
    return {"status": "error", "message": f"❌ Could not sleep: {out}"}


def shutdown_computer(delay_seconds: int = 30) -> dict:
    delay_seconds = max(0, int(delay_seconds))
    ok, out = _run_cmd(["shutdown", "/s", "/t", str(delay_seconds)])
    if ok:
        return {
            "status": "success",
            "message": f"⚠️ Shutting down in {delay_seconds} seconds.\nType 'cancel shutdown' to abort."
        }
    return {"status": "error", "message": f"❌ Shutdown failed: {out}"}


def cancel_shutdown() -> dict:
    ok, out = _run_cmd(["shutdown", "/a"])
    if ok:
        return {"status": "success", "message": "✅ Shutdown cancelled."}
    return {"status": "info", "message": "ℹ️ No pending shutdown to cancel."}


def restart_computer(delay_seconds: int = 30) -> dict:
    delay_seconds = max(0, int(delay_seconds))
    ok, out = _run_cmd(["shutdown", "/r", "/t", str(delay_seconds)])
    if ok:
        return {
            "status": "success",
            "message": f"🔄 Restarting in {delay_seconds} seconds.\nType 'cancel shutdown' to abort."
        }
    return {"status": "error", "message": f"❌ Restart failed: {out}"}


# ─────────────────────────────────────────────────────────────
# BATTERY / SYSTEM INFO
# ─────────────────────────────────────────────────────────────

def get_battery_status() -> dict:
    script = "\n".join([
        "$b = Get-WmiObject Win32_Battery -ErrorAction SilentlyContinue",
        "if ($b) {",
        "    $s = switch ($b.BatteryStatus) {",
        "        1 { 'Discharging' } 2 { 'AC Connected' } 3 { 'Fully Charged' }",
        "        4 { 'Low' } 5 { 'Critical' } default { 'Unknown' }",
        "    }",
        '    Write-Output "$($b.EstimatedChargeRemaining)% - $s"',
        "} else { Write-Output 'no_battery' }",
    ])
    ok, out = _run_ps(script)
    out = out.strip()
    if "no_battery" in out:
        return {"status": "info", "message": "🔌 No battery detected (desktop PC)."}
    if out:
        return {"status": "info", "message": f"🔋 Battery: {out}"}
    return {"status": "info", "message": "🔋 Battery info unavailable."}


def get_system_info() -> dict:
    script = "\n".join([
        "$cpu = (Get-WmiObject Win32_Processor | Select-Object -First 1).Name",
        "$ram = [Math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)",
        "$free = [Math]::Round((Get-WmiObject Win32_OperatingSystem).FreePhysicalMemory / 1MB, 1)",
        "$os = (Get-WmiObject Win32_OperatingSystem).Caption",
        'Write-Output "OS: $os"',
        'Write-Output "CPU: $cpu"',
        'Write-Output "RAM: $($ram) GB total, $free GB free"',
    ])
    ok, out = _run_ps(script)
    if ok and out:
        return {"status": "info", "message": f"💻 System Info:\n{out.strip()}"}
    return {"status": "info", "message": "💻 Could not retrieve system info."}


# ─────────────────────────────────────────────────────────────
# APP LAUNCH
# ─────────────────────────────────────────────────────────────

# _APP_MAP = {
#     "calculator":    "calc",
#     "notepad":       "notepad",
#     "paint":         "mspaint",
#     "task manager":  "taskmgr",
#     "file explorer": "explorer",
#     "explorer":      "explorer",
#     "control panel": "control",
#     "snipping tool": "snippingtool",
#     "screenshot":    "snippingtool",
#     "cmd":           "cmd",
#     "terminal":      "wt",
#     "powershell":    "powershell",
#     "chrome":        "chrome",
#     "firefox":       "firefox",
#     "edge":          "msedge",
#     "word":          "winword",
#     "excel":         "excel",
#     "powerpoint":    "powerpnt",
# }


_APP_MAP = {
    "notepad": "notepad",
    "paint": "mspaint",
    "task manager": "taskmgr",
    "file explorer": "explorer",
    "explorer": "explorer",
    "control panel": "control",
    "snipping tool": "snippingtool",
    "screenshot": "snippingtool",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
}

_MS_URI_MAP = {
    "settings": "ms-settings:",
    "camera": "microsoft.windows.camera:",
    "calendar": "outlookcal:",
    "mail": "outlookmail:",
    "clock": "ms-clock:",
    "maps": "bingmaps:",
    "store": "ms-windows-store:",
    "browser": "microsoft-edge:",
}


def launch_app(app_name: str) -> dict:
    """Attempt to launch a named app or command.

    Returns a dict with `status` and `message` suitable for UI display.
    """
    if not app_name:
        return {"status": "error", "message": "❌ No app name provided."}

    key = app_name.lower().strip()

    # MS URI scheme (open Settings, Camera, etc.)
    if key in _MS_URI_MAP:
        try:
            os.startfile(_MS_URI_MAP[key])
            return {"status": "success", "message": f"🚀 Launching {app_name}..."}
        except Exception as e:
            return {"status": "error", "message": f"❌ Could not launch {app_name}: {e}"}

    # map friendly name to executable
    cmd = _APP_MAP.get(key, app_name)
    try:
        # If a simple executable name, let Popen handle it; otherwise use shell for full commands
        if isinstance(cmd, str):
            subprocess.Popen(cmd, shell=True)
        else:
            subprocess.Popen(cmd)
        return {"status": "success", "message": f"🚀 Launching {app_name}..."}
    except Exception as e:
        return {"status": "error", "message": f"❌ Could not launch {app_name}: {e}"}


# ─────────────────────────────────────────────────────────────
# FOCUS ASSIST
# ─────────────────────────────────────────────────────────────

def set_focus_assist(enable: bool) -> dict:
    label = "enabled" if enable else "disabled"
    emoji = "🔕" if enable else "🔔"
    val = 0 if enable else 1
    reg_path = r"HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings"
    script = "\n".join([
        f'$p = "{reg_path}"',
        "if (-not (Test-Path $p)) { New-Item -Path $p -Force | Out-Null }",
        f'Set-ItemProperty -Path $p -Name "NOC_GLOBAL_SETTING_TOASTS_ENABLED" -Value {val} -Type DWORD',
        "Write-Output 'ok'",
    ])
    _run_ps(script)
    return {"status": "success", "message": f"{emoji} Focus Assist {label}."}