#!/usr/bin/env python3
"""
Build one-press FX submasters for effects 1-37.

The workflow problem: applying an effect normally takes two steps - select the
channels, then choose the effect. A submaster collapses that to one, because it
stores the channel selection, a level, AND the effect together.

Presets cannot do this - tested, the preset `fx` field stays empty whether you
Record or Record Only. Macros cannot either, because Learn mode does not
capture commands sent over OSC. Submasters are the only container that holds an
effect and can be fired from a single button.

Each sub here pairs an effect with the group its steps were built from, so it
lands on the right fixtures with no selection needed.

  subs 101-125  effects 1-25   (the show library)
  subs 126-137  effects 26-37  (the ordered chases)

Level is intensity only - colour is untouched, so these LAYER on whatever the
cue already has. Set your colour palette in the cue, then bump an FX sub.
"""
import argparse, sys, time
import eosdump as E

# (sub, effect, group, level, label) - group = the one the effect was built on
BANK = [
    (101,  1, 203, 100, "Chase Fwd"),     (102,  2, 203, 100, "Chase Rev"),
    (103,  3, 203, 100, "Chase Bounce"),  (104,  4, 203, 100, "Chase Build"),
    (105,  5, 203, 100, "Chase Negativ"), (106,  6,   3, 100, "Sparkle"),
    (107,  7,   3, 100, "Twinkle"),       (108,  8,   3, 100, "Lightning"),
    (109,  9,   3, 100, "Fire Flicker"),  (110, 10, 205, 100, "Water Ripple"),
    (111, 11,   3, 100, "Strobe All"),    (112, 12,  25, 100, "Strobe Alt"),
    (113, 13,   3, 100, "Strobe Build"),  (114, 14,   3, 100, "Stutter"),
    (115, 15,   1, 100, "Blinder Hit"),   (116, 16, 203, 100, "Wave L to R"),
    (117, 17, 204, 100, "Wave R to L"),   (118, 18, 203, 100, "Wave Bounce"),
    (119, 19, 205, 100, "Ripple Out"),    (120, 20, 206, 100, "Ripple In"),
    (121, 21, 212, 100, "Mvr Kick"),      (122, 22, 212, 100, "Mvr Stab"),
    (123, 23, 212, 100, "Mvr Alt"),       (124, 24, 212, 100, "Mvr Build"),
    (125, 25, 212, 100, "Mvr Random"),
    (126, 26, 201, 100, "Chase Odd"),     (127, 27, 202, 100, "Chase Even"),
    (128, 28, 203, 100, "Chase L to R"),  (129, 29, 204, 100, "Chase R to L"),
    (130, 30, 205, 100, "Chase Ctr Out"), (131, 31, 206, 100, "Chase Out In"),
    (132, 32, 207, 100, "Chase Front Bk"),(133, 33, 208, 100, "Chase Back Fr"),
    (134, 34, 209, 100, "Chase Scatter"), (135, 35, 210, 100, "Chase Quarters"),
    (136, 36, 211, 100, "Chase Strips"),  (137, 37, 212, 100, "Chase Movers"),
]


class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _rd(self, wait=2.6, idle=0.25):
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

    def send(self, cmd, confirm=False, tolerate=()):
        self.n += 1
        if self.dry:
            print(f"    {cmd}")
            return ""
        self.conn.send("/eos/newcmd", cmd + "#")
        echo = self._rd()
        if "Please Confirm" in echo:
            if not confirm:
                self.conn.send("/eos/key/clear_cmd", 1)
                self.conn.send("/eos/key/clear_cmd", 0)
                self.errors.append((cmd, "unexpected confirm"))
                return echo
            self.conn.send("/eos/key/enter", 1)
            self.conn.send("/eos/key/enter", 0)
            echo = self._rd()
        if "Error" in echo and not any(t in echo for t in tolerate):
            self.errors.append((cmd, echo))
            print(f"  !! {cmd}\n     -> {echo[-50:]}", file=sys.stderr)
        return echo

    def save(self):
        if self.dry:
            return
        self.conn.send("/eos/key/save_show", 1)
        self.conn.send("/eos/key/save_show", 0)
        end = time.time() + 20
        while time.time() < end:
            for addr, args in self.conn.recv():
                if addr == "/eos/out/event/show/saved":
                    print(f"  saved -> {args[0]}")
                    return
        self.errors.append(("save", "not confirmed"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)
    if conn:
        conn.send("/eos/key/live", 1); conn.send("/eos/key/live", 0)
        time.sleep(0.5)

    lo, hi = BANK[0][0], BANK[-1][0]
    print(f"clearing subs {lo}-{hi}")
    b.send(f"Delete Sub {lo} Thru {hi}", confirm=True, tolerate=("Does Not Exist",))

    for sub, fx, grp, lvl, label in BANK:
        print(f"sub {sub:>3}  {label:<15} = Group {grp:>3} + Effect {fx}")
        b.send("Sneak Time 0")               # release manual AND running effects
        b.send(f"Group {grp} At {lvl}")
        b.send(f"Group {grp} Effect {fx}")   # Effect will not chain after At
        b.send(f"Record Sub {sub}")
        b.send(f"Sub {sub} Label {label}")

    b.send("Sneak Time 0")
    b.save()
    if conn:
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, why in b.errors:
        print(f"  FAILED: {cmd} -> {why[-50:]}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
