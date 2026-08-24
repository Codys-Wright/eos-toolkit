#!/usr/bin/env python3
"""
Build one-press FX macros on a live Eos console.

THE WORKFLOW PROBLEM
Applying an effect normally takes two steps: select channels, then choose the
effect. A macro collapses that to one button - and unlike a submaster it brings
no intensity of its own, so it sits on top of whatever the cue already has.
Set the colour palette in the cue, then fire an FX macro on top.

Each macro stops all running effects first, so the buttons REPLACE one another
instead of stacking. For layering two effects at once, use the FX submasters
(101-137) instead - those are additive by design.

WHY MACROS AND NOT PRESETS OR SUBS
  presets  - cannot hold an effect (the preset `fx` field stays empty whether
             you Record or Record Only - tested)
  subs     - hold an effect but bring their own level, which fights the cue
  macros   - run any command line, touch nothing else. Correct tool.

HOW TO AUTHOR ONE OVER OSC
Learn mode does NOT capture commands sent over OSC - they execute live instead.
The Macro Editor does work:

  1. [Macro] [Macro]           opens the editor - display navigation, so this
                               needs System Events (Mac hotkey: M, twice, ~80ms)
  2. <number> [Enter]          in this display a bare number IS a macro number;
                               an unused one creates an empty macro
  3. /eos/softkey/6  {Edit}    enters edit mode. /eos/key/edit does NOT.
                               Confirm it took: the softkeys change to
                               Loop Begin | Loop End | Wait | Delete | Done ...
  4. body via SYSTEM EVENTS    OSC key presses do NOT insert into a macro; the
                               editor captures real console keystrokes. Mac
                               hotkeys: Group=G  Effect=Alt+E  Enter=Return
                               At=@  Full=F  Thru=T
  5. Ctrl+Enter  [Select]      saves. {Done} exits edit mode WITHOUT saving the
                               keystrokes, and pressing softkeys while in edit
                               mode inserts them from the command palette
                               (that is where a stray "Clear_CmdLine" comes from).

Delete a macro before rebuilding it - entering edit mode on one that already
has content appends rather than replaces.
WARNING: this synthesises real keystrokes into the Eos window. Do not use the
computer while it runs - if another app takes focus, the keystrokes go there.
"""
import argparse, subprocess, sys, time
import eosdump as E

# (macro, group, effect, label) - group is the one the effect's steps were built on
FX_MACROS = [
    (101,203, 1,"FX Chase Fwd"),    (102,203, 2,"FX Chase Rev"),
    (103,203, 3,"FX Chase Bnce"),   (104,203, 4,"FX Chase Bld"),
    (105,203, 5,"FX Chase Neg"),    (106,  3, 6,"FX Sparkle"),
    (107,  3, 7,"FX Twinkle"),      (108,  3, 8,"FX Lightning"),
    (109,  3, 9,"FX Fire"),         (110,205,10,"FX Water"),
    (111,  3,11,"FX Strobe"),       (112, 25,12,"FX Strobe Alt"),
    (113,  3,13,"FX Strobe Bld"),   (114,  3,14,"FX Stutter"),
    (115,  1,15,"FX Blinder"),      (116,203,16,"FX Wave LR"),
    (117,204,17,"FX Wave RL"),      (118,203,18,"FX Wave Bnce"),
    (119,205,19,"FX Ripple Out"),   (120,206,20,"FX Ripple In"),
    (121,212,21,"FX Mvr Kick"),     (122,212,22,"FX Mvr Stab"),
    (123,212,23,"FX Mvr Alt"),      (124,212,24,"FX Mvr Build"),
    (125,212,25,"FX Mvr Random"),
    (126,201,26,"FX Ch Odd"),       (127,202,27,"FX Ch Even"),
    (128,203,28,"FX Ch L to R"),    (129,204,29,"FX Ch R to L"),
    (130,205,30,"FX Ch Ctr Out"),   (131,206,31,"FX Ch Out In"),
    (132,207,32,"FX Ch Frnt Bk"),   (133,208,33,"FX Ch Bk Frnt"),
    (134,209,34,"FX Ch Scatter"),   (135,210,35,"FX Ch Quarters"),
    (136,211,36,"FX Ch Strips"),    (137,212,37,"FX Ch Movers"),
]
STOP_MACRO = (140, "FX Stop All")     # Group 10 Effect Enter -> stop flag on all

EDIT_SOFTKEY = 6      # {Edit} in the list view; reads {Done} once in edit mode


# Mac hotkeys for the console keys a macro body needs
HOTKEY = {"group": '"g"', "effect": '"e" using {option down}',
          "at": '"@"', "full": '"f"', "thru": '"t"'}


def osa(script):
    subprocess.run(["osascript", "-e", script], capture_output=True)


def osa_keys(seq):
    """seq of 'group'/'effect'/digits/'enter' -> one AppleScript of keystrokes.

    Re-focuses Eos FIRST, every time. System Events types into whatever app is
    frontmost - if focus drifts mid-run the keystrokes land in someone's text
    editor. Focusing per batch means drift costs one batch, not the run.
    """
    osa('tell application "System Events" to tell process "Eos Family" '
        'to set frontmost to true')
    time.sleep(0.35)
    lines = ['tell application "System Events"']
    for k in seq:
        if k == "enter":
            lines.append("  key code 36")
        elif k in HOTKEY:
            lines.append(f"  keystroke {HOTKEY[k]}")
        elif len(k) == 1:
            lines.append(f'  keystroke "{k}"')
        else:
            # An unmapped multi-character token would be typed one letter at a
            # time, and in the Macro Editor every letter is a hotkey. That is
            # silent corruption, so refuse it instead.
            raise ValueError(
                f"key {k!r} is not in HOTKEY and is not a single character. "
                f"Add it to HOTKEY or express it as separate keys.")
        lines.append("  delay 0.12")
    lines.append("end tell")
    osa("\n".join(lines))


def digits(n):
    return [ch for ch in str(n)]


class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _rd(self, wait=0.9, idle=0.2):
        end, last, echo = time.time() + wait, time.time(), ""
        while time.time() < end:
            msgs = self.conn.recv()
            if msgs:
                last = time.time()
                for addr, args in msgs:
                    if addr == "/eos/out/cmd" and args:
                        echo = str(args[0])
            elif time.time() - last > idle:
                break
        return echo

    def cmd(self, s, term=True):
        self.n += 1
        if self.dry:
            print(f"    cmd  {s}"); return ""
        self.conn.send("/eos/newcmd", s + ("#" if term else ""))
        return self._rd()

    def key(self, k, w=0.5):
        self.n += 1
        if self.dry:
            print(f"    key  {k}"); return ""
        self.conn.send(f"/eos/key/{k}", 1)
        self.conn.send(f"/eos/key/{k}", 0)
        return self._rd(w)

    def softkey(self, i, w=1.1):
        self.n += 1
        if self.dry:
            print(f"    soft {i}"); return ""
        self.conn.send(f"/eos/softkey/{i}", 1.0)
        return self._rd(w)

    def macro(self, n):
        if self.dry:
            return {"text": "?"}
        coll = E.Collector()
        self.conn.send(f"/eos/get/macro/{n}")
        t = l = time.time()
        while time.time() - t < 5:
            m = self.conn.recv()
            if m:
                for a, g in m:
                    coll.feed(a, g)
                l = time.time()
            elif time.time() - l > 0.35:
                break
        r = E.build(coll).get("macro", {}).get(str(n))
        if not r:
            return None
        return {"label": r.get("label", ""),
                "text": " ".join(str(x) for x in r.get("text", []))}

    def write(self, num, keystrokes, label):
        """Select macro `num`, enter edit mode, type the body, save."""
        self.cmd(str(num))                       # bare number = macro number here
        self.softkey(EDIT_SOFTKEY, 1.2)          # {Edit}
        if not self.dry:
            osa_keys(keystrokes)                 # real keystrokes, not OSC
            time.sleep(0.4)
            osa('tell application "System Events" to '
                'key code 36 using {control down}')   # [Select] = save
            time.sleep(1.0)
        self.cmd(f"Macro {num} Label {label}")
        got = self.macro(num)
        if not got or not got.get("text"):
            self.errors.append((num, "body empty after save"))
            print(f"  !! macro {num} came back empty", file=sys.stderr)
        return got


def open_macro_editor():
    osa('tell application "System Events" to tell process "Eos Family" '
        'to set frontmost to true')
    time.sleep(1.0)
    osa('tell application "System Events"\nkeystroke "m"\ndelay 0.08\n'
        'keystroke "m"\nend tell')
    time.sleep(1.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", type=int, nargs="*")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    if conn:
        b.key("live")
        b.cmd("Sneak Time 0")
        lo, hi = FX_MACROS[0][0], STOP_MACRO[0]
        print(f"clearing macros {lo}-{hi} (edit mode appends, so start clean)")
        b.cmd(f"Delete Macro {lo} Thru {hi}")
        b.key("enter")
        print("opening the Macro Editor ([Macro][Macro] via System Events)")
        open_macro_editor()

    # Each FX macro STOPS every running effect before starting its own, so the
    # buttons are mutually exclusive - pressing one replaces the last rather
    # than stacking. "Chan 1 Thru 101 Effect [Enter]" with no effect number is Eos's
    # stop flag; it kills effects without touching levels or colour.
    # THE STOP MUST USE A CHANNEL RANGE. The group form ("group 10 effect")
    # is accepted and stops nothing, so every FX macro built with it stacked
    # its effect on top of the previous one instead of replacing it. Verified
    # with probe subs; see trap 29. Keystrokes, so digits are separate keys.
    # NO "Chan" KEYWORD. A bare number on the Eos command line is already a
    # channel selection, and "chan" is not in HOTKEY - it got typed as the
    # letters c,h,a,n, which inside the Macro Editor are the hotkeys
    # Copy_To / Rem_Dim / @ / Sneak. Every macro came out starting
    # "Copy_To Rem_Dim @ Sneak" and the build still reported 0 errors.
    STOP = ["1", "thru", "1", "0", "1", "effect", "enter"]
    jobs = [(num, STOP + ["group"] + digits(grp) + ["effect"] + digits(fx) + ["enter"], lab)
            for num, grp, fx, lab in FX_MACROS]
    jobs.append((STOP_MACRO[0], list(STOP), STOP_MACRO[1]))

    for num, keys, label in jobs:
        if a.only and num not in a.only:
            continue
        got = b.write(num, keys, label)
        body = (got or {}).get("text", "")
        # A macro that reads back is not a macro that is CORRECT. Compare the
        # body to what we meant to type - the "0 errors" run that produced
        # "Copy_To Rem_Dim @ Sneak ..." printed these and nobody looked.
        ok = ("Copy_To" not in body and "Rem_Dim" not in body
              and "Sneak" not in body and "Thru" in body and "Effect" in body)
        flag = "" if ok else "   <-- BODY WRONG"
        if not ok:
            b.errors.append((num, f"unexpected macro body: {body!r}"))
        print(f"macro {num:>4}  {label:<15} -> {body!r}{flag}")

    if conn:
        b.key("live")
        conn.send("/eos/key/save_show", 1); conn.send("/eos/key/save_show", 0)
        end, saved = time.time() + 20, None
        while time.time() < end and not saved:
            for addr, args in conn.recv():
                if addr == "/eos/out/event/show/saved":
                    saved = args[0]
        print(f"\nsaved -> {saved or 'NOT SAVED'}")
        conn.close()
    print(f"{b.n} commands, {len(b.errors)} errors")
    for n, why in b.errors:
        print(f"  FAILED {n}: {why}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
