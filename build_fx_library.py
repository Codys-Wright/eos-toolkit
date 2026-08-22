#!/usr/bin/env python3
"""
Build a show-ready step-based effect library on a live Eos console.

Fills the real gap in a stock Eos rig. Out of the box you already get colour
crossfades (100-159) and movement shapes (901-933); what is missing is the
intensity / chase / texture family that carries a live show.

Opens the Effect editor itself on macOS via eos_focus (Accessibility required).

  PAGE 301-325, five rows:
    301-305  chase family   - one channel order, five attributes
    306-310  organic        - sparkle, twinkle, lightning, fire, water
    311-315  strobes & hits
    316-320  spatial waves  - across and out from the rig
    321-325  movers

Attribute semantics (ETC docs):
  Reverse       steps run 5-4-3-2-1  (key is `reverse_steps`; the bare
                `reverse` key exists but errors here)
  Bounce        1-2-3-4-5-4-3-2-1, alternating each pass
  Build         each step ADDS to the previous; all on at the end, then reset
  Negative      inverted - channels sit ON and the active step goes OUT
  Random Group  step order continuously randomised
  Random Rate   per-step time randomised within a range, e.g. 50 Thru 200
"""
import argparse, sys, time
import eosdump as E
try:
    import eos_focus
except ImportError:
    eos_focus = None

# (num, label, group, steps, cycle_seconds, [attribute keys], random_rate_range)
LIBRARY = [
    # --- chase family: identical channels + steps, different attributes
    (301, "Chase Fwd",     203,  8, 1.2, [],                  None),
    (302, "Chase Rev",     203,  8, 1.2, ["reverse_steps"],   None),
    (303, "Chase Bounce",  203,  8, 1.2, ["bounce"],          None),
    (304, "Chase Build",   203,  8, 1.6, ["build"],           None),
    (305, "Chase Negativ", 203,  8, 1.2, ["negative"],        None),
    # --- organic / random
    (306, "Sparkle",         3, 16, 0.4, ["random_groups"],   None),
    (307, "Twinkle",         3, 16, 1.5, ["random_groups"],   None),
    (308, "Lightning",       3,  4, 0.25,["random_groups"],   "50 Thru 300"),
    (309, "Fire Flicker",    3, 10, 0.8, ["random_groups"],   "80 Thru 160"),
    (310, "Water Ripple",  205,  8, 1.6, ["bounce"],          "90 Thru 130"),
    # --- strobes and hits
    (311, "Strobe All",      3,  2, 0.15,[],                  None),
    (312, "Strobe Alt",     25,  2, 0.3, [],                  None),
    (313, "Strobe Build",    3,  5, 0.3, ["build"],           None),
    (314, "Stutter",         3,  3, 0.2, ["negative"],        None),
    (315, "Blinder Hit",     1,  2, 0.2, [],                  None),
    # --- spatial waves
    (316, "Wave L to R",   203,  8, 1.5, [],                  None),
    (317, "Wave R to L",   204,  8, 1.5, [],                  None),
    (318, "Wave Bounce",   203,  8, 1.5, ["bounce"],          None),
    (319, "Ripple Out",    205,  6, 1.2, [],                  None),
    (320, "Ripple In",     206,  6, 1.2, [],                  None),
    # --- movers
    (321, "Mvr Kick",      212,  8, 1.0, [],                  None),
    (322, "Mvr Stab",      212,  8, 0.3, [],                  None),
    (323, "Mvr Alt",       212,  2, 0.6, [],                  None),
    (324, "Mvr Build",     212,  8, 1.2, ["build"],           None),
    (325, "Mvr Random",    212,  8, 0.8, ["random_groups"],   None),
]


class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _rd(self, wait=1.3, idle=0.25):
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

    def newcmd(self, s, term=False):
        self.n += 1
        if self.dry:
            print(f"    newcmd {s!r}"); return ""
        self.conn.send("/eos/newcmd", s + ("#" if term else ""))
        return self._rd()

    def app(self, s):
        self.n += 1
        if self.dry:
            print(f"    append {s!r}"); return ""
        self.conn.send("/eos/cmd", s)
        return self._rd()

    def key(self, k):
        self.n += 1
        if self.dry:
            print(f"    key    {k}"); return ""
        self.conn.send(f"/eos/key/{k}", 1)
        self.conn.send(f"/eos/key/{k}", 0)
        return self._rd()

    def fx(self, n):
        if self.dry:
            return {"type": "StepBased"}
        coll = E.Collector()
        self.conn.send(f"/eos/get/fx/{n}")
        t = l = time.time()
        while time.time() - t < 5:
            m = self.conn.recv()
            if m:
                for a, g in m:
                    coll.feed(a, g)
                l = time.time()
            elif time.time() - l > 0.4:
                break
        r = E.build(coll).get("fx", {}).get(str(n))
        return r if r and r.get("type") else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", type=int, nargs="*")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    if conn and eos_focus and not eos_focus.editor_is_open(conn):
        print("opening the Effect editor via System Events")
        eos_focus.open_effect_editor()

    for num, label, grp, steps, cyc, attrs, rrate in LIBRARY:
        if a.only and num not in a.only:
            continue
        print(f"effect {num}  {label:<14} grp {grp:>3}  {steps:>2} steps  "
              f"{cyc}s  {'+'.join(attrs) or '-'}")

        b.newcmd(f"Delete Effect {num}", term=True)
        b.key("enter")

        b.newcmd(f"Effect {num}")
        e = b.key("enter")
        if "Does Not Exist" in e:
            b.errors.append((num, "Effect editor not focused"))
            print("\nABORTING - the Effect editor is not open.", file=sys.stderr)
            break
        b.key("stepbased")
        if not b.fx(num):
            b.errors.append((num, "not created"))
            continue

        b.key("step"); b.app(f"1 Thru {steps}"); b.key("enter"); b.key("enter")
        b.newcmd(f"Group {grp}"); b.key("enter")

        b.newcmd(f"Effect {num}"); b.key("cycletime"); b.app(str(cyc)); b.key("enter")

        for at in attrs:
            b.newcmd(f"Effect {num}")
            e = b.key(at)
            if "Error" in e:
                b.errors.append((num, f"attribute {at}: {e[-40:]}"))
        if rrate:
            b.newcmd(f"Effect {num}")
            b.key("random_rate"); b.app(rrate); b.key("enter")

        b.newcmd(f"Effect {num} Label {label}", term=True)

    if conn:
        conn.send("/eos/key/save_show", 1); conn.send("/eos/key/save_show", 0)
        end, saved = time.time() + 15, None
        while time.time() < end and not saved:
            for addr, args in conn.recv():
                if addr == "/eos/out/event/show/saved":
                    saved = args[0]
        print(f"\nsaved -> {saved or 'NOT SAVED'}")
        conn.close()
    print(f"{b.n} commands, {len(b.errors)} errors")
    for num, why in b.errors:
        print(f"  FAILED {num}: {why}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
