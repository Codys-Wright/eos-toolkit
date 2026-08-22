#!/usr/bin/env python3
"""
eos_focus - drive Eos display navigation on macOS, which OSC cannot reach.

OSC covers show DATA completely and the UI not at all. Display focus is the one
thing a script cannot do over OSC - and effect authoring requires it. This
module closes that gap using macOS System Events, which ships with the OS.

REQUIRES: System Settings > Privacy & Security > Accessibility -> enable the
app hosting this script (e.g. Claude, Terminal, iTerm). Without it osascript
fails with "not allowed to send keystrokes. (1002)".

Mac hotkeys differ from the published Windows table: the Effect key is
Option+E on macOS, not Ctrl+E.

The double-press gesture is timing sensitive. Two presses ~80ms apart open the
editor; a 1.2s gap registers as two separate Effect keypresses and does not.
"""
import subprocess
import time

APP = "Eos Family"
EFFECT_KEY = 'keystroke "e" using {option down}'


def _osa(script):
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "osascript failed")
    return r.stdout.strip()


def available():
    """True if System Events can drive Eos (Accessibility granted, app running)."""
    try:
        names = _osa('tell application "System Events" to get name of '
                     'every process whose background only is false')
        if APP not in names:
            return False
        _osa(f'tell application "System Events" to tell process "{APP}" '
             'to get name of window 1')
        return True
    except Exception:
        return False


def focus_app():
    _osa(f'tell application "System Events" to tell process "{APP}" '
         'to set frontmost to true')
    time.sleep(1.0)


def open_effect_editor():
    """Press [Effect] [Effect]. Both presses must land in one script - a gap
    over ~0.5s is read as two separate keypresses instead of the gesture."""
    focus_app()
    _osa(f'''tell application "System Events"
  {EFFECT_KEY}
  delay 0.08
  {EFFECT_KEY}
end tell''')
    time.sleep(1.5)


def editor_is_open(conn, wait=2.0):
    """Confirm via OSC. The editor publishes a distinctive softkey set."""
    seen, end = {}, time.time() + wait
    conn.send("/eos/ping", "focus")
    while time.time() < end:
        for addr, args in conn.recv():
            if "/softkey/" in addr and args:
                seen[addr] = args[0]
    labels = {v for v in seen.values() if v}
    return bool(labels & {"Step", "In Time", "On State", "InsrtBefore"})


if __name__ == "__main__":
    import sys
    if not available():
        print("System Events cannot reach Eos.\n"
              "  * Is Eos Family running?\n"
              "  * System Settings > Privacy & Security > Accessibility\n"
              "    -> enable the app running this script", file=sys.stderr)
        sys.exit(1)
    open_effect_editor()
    print("sent [Effect] [Effect]")
