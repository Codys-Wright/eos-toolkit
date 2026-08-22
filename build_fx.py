#!/usr/bin/env python3
"""
Build a full FX submaster library on a live Eos console, as 5x5 DIRECT SELECT
PAGES. Wipes subs 1-100 first (submasters are independent of cues, so this
cannot affect recorded cue data).

  PAGE 1  ( 1-25)  CORE       - the everyday reach-fors
  PAGE 2  (26-50)  MOVEMENT   - mover shapes, speed and size variants
  PAGE 3  (51-75)  COLOUR     - rainbows, smooth fades, colour-pair churns
  PAGE 4  (76-100) INTENSITY  - steps, strobes, ramps, and positional chases

Rate/Scale are overrides applied to the RUNNING effect then recorded into the
sub; Eos will not let the command line edit a stored effect definition.

Groups referenced (from the rebuilt 1-100 library):
   1 Rig All      3 Pars All    5 Strips      6 SlimPars   7 Movers OH
   8 Movers Beam 11 Left All   13 Right All  16 Front Wash 19 Back Wash
  21 Pars Odd    22 Pars Even  23 Pars 3rd   24 Pars 4th   25 Pars Split
  51 Movers All  66 Mvr Outer  67 Mvr Inner  87 Pars Qtr 1
"""
import argparse, sys, time
import eosdump as E

# RIG CAPABILITY MATRIX (measured, not assumed):
#   RGB colour fx (910/912/913/917)  -> pars, strips, slimpars ONLY
#   Absolute colour fx (800-859,4xx) -> everything, incl. movers (colour WHEELS)
#   Focus fx (901-933)               -> movers ONLY (no pan/tilt on the wash)
#   Intensity fx (936-941)           -> everything
#   CMY (918) and Hue-Sat (914)      -> NOTHING on this rig has those params
#
# (sub, group, effect, level, rate, scale, label)
BANK = [
    # ---------------- PAGE 1: CORE ----------------
    ( 1,  7, 927, 100, 100, 100, "OH Fig8"),
    ( 2,  7, 928, 100, 100, 100, "OH Circle"),
    ( 3,  7, 929, 100, 100, 100, "OH Square"),
    ( 4,  7, 933, 100, 100, 100, "OH Spiral"),
    ( 5,  7, 932, 100, 100, 100, "OH Triangle"),
    ( 6,  8, 909, 100, 100, 100, "BM Ballyhoo"),
    ( 7,  8, 934, 100, 100, 100, "BM Search"),
    ( 8,  8, 940, 100, 100, 100, "BM Pan"),
    ( 9,  8, 931, 100, 100, 100, "BM Can Can"),
    (10,  8, 926, 100, 100, 100, "BM Sweep"),
    (11,  3, 917,  90, 100, 100, "Rainbow Pars"),
    (12,  3, 910,  90, 100, 100, "Col Smooth"),
    (13,  3, 911,  90, 100, 100, "Col Fade Lin"),
    (14,  3, 913,  90, 100, 100, "Bump Colour"),
    (15,  3, 912,  90,  50, 100, "Rainbow Slow"),
    (16,  3, 937, 100, 100, 100, "Par Step"),
    (17,  3, 936, 100, 100, 100, "Par Fade"),
    (18,  3, 939, 100, 100, 100, "Par Strobe"),
    (19,  3, 941, 100, 100, 100, "Par Fast Strb"),
    (20,  3, 915, 100, 100, 100, "Par Ramp"),
    (21,  1, 917,  90, 100, 100, "Rig Rainbow"),
    (22,  1, 939, 100, 100, 100, "Rig Strobe"),
    (23,  1, 937, 100, 100, 100, "Rig Step"),
    (24, 21, 937, 100, 150, 100, "Odd Chase"),
    (25,  1, 910,  90, 100, 100, "Rig Col Smooth"),
    # ---------------- PAGE 2: MOVEMENT ----------------
    (26,  7, 927, 100, 100, 100, "OH Fig8 Slow"),
    (27,  7, 927, 100, 250, 100, "OH Fig8 Fast"),
    (28,  7, 930, 100, 100, 200, "OH Fig8 Big"),
    (29,  7, 928, 100, 100, 100, "OH Circ Slow"),
    (30,  7, 928, 100, 250, 100, "OH Circ Fast"),
    (31,  7, 928, 100, 100, 200, "OH Circ Big"),
    (32,  7, 929, 100, 100, 150, "OH Square Big"),
    (33,  7, 933, 100, 150, 100, "OH Spiral Fst"),
    (34,  7, 905, 100, 100, 100, "OH Tri Wide"),
    (35,  7, 908, 100, 100, 100, "OH Rev Circle"),
    (36,  8, 909, 100, 100, 100, "BM Ballyhoo"),
    (37,  8, 909, 100, 250, 100, "BM Bally Fast"),
    (38,  8, 934, 100, 100, 100, "BM Search"),
    (39,  8, 934, 100, 100, 200, "BM Search Wide"),
    (40,  8, 940, 100, 100, 100, "BM Pan"),
    (41,  8, 940, 100, 250, 100, "BM Pan Fast"),
    (42,  8, 931, 100, 100, 100, "BM Can Can"),
    (43,  8, 926, 100, 250, 100, "BM Sweep Fast"),
    (44,  8, 901, 100, 100, 100, "BM Circle Big"),
    (45,  8, 903, 100, 100, 100, "BM Fig8 Big"),
    (46, 51, 930, 100, 100, 100, "All Mvr Fig8"),
    (47, 51, 928, 100, 100, 100, "All Mvr Circle"),
    (48, 66, 930, 100, 100, 100, "Outer Fig8"),
    (49, 67, 928, 100, 100, 100, "Inner Circle"),
    (50, 51, 909, 100, 100, 100, "All Ballyhoo"),
    # ---------------- PAGE 3: COLOUR ----------------
    (51,  3, 917,  90, 100, 100, "Rainbow RGB"),
    (52,  3, 919,  90, 100, 100, "Rainbow Wide"),
    (53,  3, 910,  90, 100, 100, "Col Smooth"),
    (54,  3, 911,  90, 100, 100, "Col Fade Lin"),
    (55,  3, 913,  90, 100, 100, "Bump Colour"),
    (56,  3, 525,  90, 100, 100, "Red Pink Yel"),
    (57,  3, 800,  90, 100, 100, "Red Blue"),
    (58,  3, 801,  90, 100, 100, "Red Green"),
    (59,  3, 804,  90, 100, 100, "Red Magenta"),
    (60,  3, 807,  90, 100, 100, "Red Yellow"),
    (61,  3, 809,  90, 100, 100, "Red White"),
    (62,  3, 810,  90, 100, 100, "Green Blue"),
    (63,  3, 813,  90, 100, 100, "Green Cyan"),
    (64,  3, 814,  90, 100, 100, "Green Magenta"),
    (65,  3, 824,  90, 100, 100, "Blue Magenta"),
    (66,  3, 828,  90, 100, 100, "Blue Orange"),
    (67,  3, 844,  90, 100, 100, "Cyan Magenta"),
    (68,  3, 856,  90, 100, 100, "Mag Yellow"),
    (69,  3, 413,  90, 100, 100, "RYB Step"),
    (70,  3, 405,  90, 100, 100, "RB White Step"),
    (71,  3, 400,  90, 100, 100, "Grn Orng Step"),
    (72,  3, 500,  90, 100, 100, "RGB Cycle"),
    (73,  3, 501,  90, 100, 100, "Magenta Pop"),
    (74,  1, 917,  90, 100, 100, "Rig Rainbow"),
    (75, 51, 412,  90, 100, 100, "Mvr Colours"),
    # ---------------- PAGE 4: INTENSITY & CHASE ----------------
    (76,  3, 937, 100, 100, 100, "Step"),
    (77,  3, 937, 100, 250, 100, "Step Fast"),
    (78,  3, 937, 100,  50, 100, "Step Slow"),
    (79,  3, 936, 100, 100, 100, "Fade In Out"),
    (80,  3, 938, 100, 100, 100, "Fade Alt"),
    (81,  3, 939, 100, 100, 100, "Strobe"),
    (82,  3, 941, 100, 100, 100, "Strobe Fast"),
    (83,  3, 915, 100, 100, 100, "Ramp"),
    (84,  3, 916, 100, 100, 100, "Ramp Inverted"),
    (85, 21, 937, 100, 150, 100, "Odd Chase"),
    (86, 22, 937, 100, 150, 100, "Even Chase"),
    (87, 87, 937, 100, 150, 100, "Qtr 1 Chase"),
    (88, 23, 937, 100, 150, 100, "Third Chase"),
    (89, 24, 937, 100, 150, 100, "Fourth Chase"),
    (90, 25, 937, 100, 150, 100, "Split Chase"),
    (91, 16, 937, 100, 150, 100, "Front Chase"),
    (92, 19, 937, 100, 150, 100, "Back Chase"),
    (93, 11, 937, 100, 150, 100, "Left Chase"),
    (94, 13, 937, 100, 150, 100, "Right Chase"),
    (95,  5, 937, 100, 150, 100, "Strip Chase"),
    (96,  5, 915, 100, 100, 100, "Strip Ramp"),
    (97,  6, 937, 100, 150, 100, "Slim Step"),
    (98,  1, 915, 100, 100, 100, "Rig Ramp"),
    (99,  1, 936, 100, 100, 100, "Rig Fade"),
    (100, 1, 939, 100, 100, 100, "Rig Strobe"),
]


class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _echo(self, wait=3.0, idle=0.25):
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
            print(f"  {cmd}")
            return
        self.conn.send("/eos/newcmd", cmd + "#")
        echo = self._echo()
        if "Please Confirm" in echo:
            if not confirm:
                self.errors.append((cmd, "unexpected confirm prompt"))
                self.conn.send("/eos/key/clear_cmd", 1)
                self.conn.send("/eos/key/clear_cmd", 0)
                return
            self.conn.send("/eos/key/enter", 1)
            self.conn.send("/eos/key/enter", 0)
            echo = self._echo()
        if "Error" in echo and not any(t in echo for t in tolerate):
            self.errors.append((cmd, echo))
            print(f"  !! {cmd}\n     -> {echo}", file=sys.stderr)

    def save(self):
        """Save is a KEY. Typing 'Save_Show' is silently ignored by Eos."""
        if self.dry:
            print("  <key save_show>")
            return
        self.conn.send("/eos/key/save_show", 1)
        self.conn.send("/eos/key/save_show", 0)
        end = time.time() + 15
        while time.time() < end:
            for addr, args in self.conn.recv():
                if addr == "/eos/out/event/show/saved":
                    print(f"  saved -> {args[0]}")
                    return
        print("  !! SAVE NOT CONFIRMED", file=sys.stderr)
        self.errors.append(("save_show", "no confirmation event"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pages", type=int, nargs="*", default=[1, 2, 3, 4])
    ap.add_argument("--subs", type=int, nargs="*",
                    help="rebuild only these sub numbers")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)
    lo = (min(a.pages) - 1) * 25 + 1
    hi = max(a.pages) * 25

    if a.subs:
        for n in a.subs:
            b.send(f"Delete Sub {n}", confirm=True, tolerate=("Does Not Exist",))
    else:
        print(f"clearing subs {lo}-{hi}")
        b.send(f"Delete Sub {lo} Thru {hi}", confirm=True,
               tolerate=("Does Not Exist",))

    for sub, grp, fx, lvl, rate, scale, label in BANK:
        if a.subs:
            if sub not in a.subs:
                continue
        elif not (lo <= sub <= hi):
            continue
        print(f"sub {sub:>3}  {label}")
        b.send("Sneak Time 0")            # release manual AND running effects
        b.send(f"Group {grp} At {lvl}")
        b.send(f"Group {grp} Effect {fx}")
        if rate != 100:
            b.send(f"Effect {fx} Rate {rate}")
        if scale != 100:
            b.send(f"Effect {fx} Scale {scale}")
        b.send(f"Record Sub {sub}")
        b.send(f"Sub {sub} Label {label}")

    b.send("Sneak Time 0")
    b.save()
    if conn:
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors:
        print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
