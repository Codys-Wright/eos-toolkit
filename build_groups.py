#!/usr/bin/env python3
"""
Build an evergreen group library on a live Eos console, laid out as 5x5
DIRECT SELECT PAGES. Wipes every existing group first.

Safe to wipe: a cue stores channel values, not group references, so deleting
groups never alters recorded cues.

  PAGE 1  (1-25)   GLOBAL   - the everyday reach-for selections
  PAGE 2  (26-50)  PARS     - banks, patterns and splits across chans 1-48
  PAGE 3  (51-75)  MOVERS   - overhead (80-83) and beam (85-88)
  PAGE 4  (76-100) STRIPS   - strips, slimpars, haze, individual fixtures

  python3 build_groups.py --dry-run
  python3 build_groups.py --pages 1 2
"""
import argparse, sys, time
import eosdump as E

def P(nums):
    return " + ".join(str(n) for n in nums)

# ---------------------------------------------------------------------------
# Spatial map, read off the Augment3d / magic sheet plot. Screen-left = "Left".
#
#            80    [51 50 93]   81      82   [52 53 94]    83
#   HAZE  90    40 41                                47 48    92      HAZE
#                    42          43 44 45         46
#        95   32 33 34 35                       36 37 38 39   96
#           7  8   [SPKR]  20 21 22 23 | 28 29 30 31  [SPKR]  9 10
#              3  4     85    24 25 26 27    87        5  6
#                   86      97           88
#                     11 12 13 14   1 2   15 16 17 18
# ---------------------------------------------------------------------------
FRONT_C = "1 + 2"
FRONT_L = "11 Thru 14"
FRONT_R = "15 Thru 18"
MID_L   = "3 Thru 4 + 7 Thru 8"
MID_R   = "5 Thru 6 + 9 Thru 10"
MIDC_L  = "20 Thru 23"
MID_C   = "24 Thru 27"
MIDC_R  = "28 Thru 31"
WIDE_L  = "32 Thru 35"
WIDE_R  = "36 Thru 39"
BACK_L  = "40 Thru 42"
BACK_C  = "43 Thru 45"
BACK_R  = "46 Thru 48"

LEFT_ALL   = f"{MID_L} + {MIDC_L} + {FRONT_L} + {WIDE_L} + {BACK_L}"
RIGHT_ALL  = f"{MID_R} + {MIDC_R} + {FRONT_R} + {WIDE_R} + {BACK_R}"
CENTRE_ALL = f"{FRONT_C} + {MID_C} + {BACK_C}"
DOWNSTAGE  = f"{FRONT_C} + {FRONT_L} + {FRONT_R}"
UPSTAGE    = "40 Thru 48"

PAGES = {
1: [  # ---- GLOBAL: whole rig, types, sides, depth, quick splits
    ( 1, "Rig All",      "1 Thru 98"),
    ( 2, "Wash All",     "1 Thru 48 + 50 Thru 53"),
    ( 3, "Pars All",     "1 Thru 48"),
    ( 4, "Movers All",   "80 Thru 83 + 85 Thru 88"),
    ( 5, "Strips",       "90 Thru 97"),
    ( 6, "SlimPars",     "50 Thru 53"),
    ( 7, "Movers OH",    "80 Thru 83"),
    ( 8, "Movers Beam",  "85 Thru 88"),
    ( 9, "Haze",         "100 Thru 101"),
    (10, "Mvr + Strip",  "80 Thru 83 + 85 Thru 88 + 90 Thru 97"),
    (11, "Left All",     LEFT_ALL),
    (12, "Centre All",   CENTRE_ALL),
    (13, "Right All",    RIGHT_ALL),
    (14, "Downstage",    DOWNSTAGE),
    (15, "Upstage",      UPSTAGE),
    (16, "Front Wash",   f"{FRONT_C} + {FRONT_L} + {FRONT_R}"),
    (17, "Mid Wash",     f"{MID_L} + {MIDC_L} + {MID_C} + {MIDC_R} + {MID_R}"),
    (18, "Wide Wash",    f"{WIDE_L} + {WIDE_R}"),
    (19, "Back Wash",    f"{BACK_L} + {BACK_C} + {BACK_R}"),
    (20, "Drums",        "42 Thru 46 + 50 Thru 53"),
    (21, "Pars Odd",     P(range(1, 49, 2))),
    (22, "Pars Even",    P(range(2, 49, 2))),
    (23, "Pars 3rd",     P(range(1, 49, 3))),
    (24, "Pars 4th",     P(range(1, 49, 4))),
    (25, "Pars Split",   "2 + 4 Thru 5 + 11 + 13 + 16 + 18 + 21 + 23 + 25 "
                         "+ 27 Thru 28 + 30 + 32 + 34 + 37 + 39 + 41 "
                         "+ 43 Thru 45 + 47"),
],
2: [  # ---- PARS BY POSITION: row = depth, column = left -> right
    (26, "Front Left",   FRONT_L),
    (27, "Front Centre", FRONT_C),
    (28, "Front Right",  FRONT_R),
    (29, "Front L+C",    f"{FRONT_L} + {FRONT_C}"),
    (30, "Front C+R",    f"{FRONT_C} + {FRONT_R}"),
    (31, "Mid Left",     MID_L),
    (32, "Mid Ctr Left", MIDC_L),
    (33, "Mid Centre",   MID_C),
    (34, "Mid Ctr Right",MIDC_R),
    (35, "Mid Right",    MID_R),
    (36, "Wide Left",    WIDE_L),
    (37, "Wide Right",   WIDE_R),
    (38, "Wide Both",    f"{WIDE_L} + {WIDE_R}"),
    (39, "Wide + Mid L", f"{WIDE_L} + {MID_L}"),
    (40, "Wide + Mid R", f"{WIDE_R} + {MID_R}"),
    (41, "Back Left",    BACK_L),
    (42, "Back Centre",  BACK_C),
    (43, "Back Right",   BACK_R),
    (44, "Back L+C",     f"{BACK_L} + {BACK_C}"),
    (45, "Back C+R",     f"{BACK_C} + {BACK_R}"),
    (46, "Left Deep",    f"{FRONT_L} + {MID_L} + {WIDE_L} + {BACK_L}"),
    (47, "Right Deep",   f"{FRONT_R} + {MID_R} + {WIDE_R} + {BACK_R}"),
    (48, "Centre Deep",  CENTRE_ALL),
    (49, "Outer Ring",   f"{WIDE_L} + {WIDE_R} + {BACK_L} + {BACK_R}"),
    (50, "Inner Core",   f"{FRONT_C} + {MID_C} + {MIDC_L} + {MIDC_R}"),
],
3: [  # ---- MOVERS / STRIPS / SLIMPARS - multi-fixture selections only.
      # Single fixtures are reachable by typing the channel; a group would
      # just take up a tile.
    (51, "Movers All",    "80 Thru 83 + 85 Thru 88"),
    (52, "Movers OH",     "80 Thru 83"),
    (53, "Movers Beam",   "85 Thru 88"),
    (54, "Mvr Left",      "80 + 85"),
    (55, "Mvr Right",     "83 + 88"),
    (56, "OH Outer",      "80 + 83"),
    (57, "OH Inner",      "81 Thru 82"),
    (58, "OH Left Pair",  "80 Thru 81"),
    (59, "OH Right Pair", "82 Thru 83"),
    (60, "OH Odd",        "80 + 82"),
    (61, "OH Even",       "81 + 83"),
    (62, "BM Outer",      "85 + 88"),
    (63, "BM Inner",      "86 Thru 87"),
    (64, "BM Left Pair",  "85 Thru 86"),
    (65, "BM Right Pair", "87 Thru 88"),
    (66, "Mvr Outer All", "80 + 83 + 85 + 88"),
    (67, "Mvr Inner All", "81 Thru 82 + 86 Thru 87"),
    (68, "Mvr Left All",  "80 Thru 81 + 85 Thru 86"),
    (69, "Mvr Right All", "82 Thru 83 + 87 Thru 88"),
    (70, "Mvr + Strip",   "80 Thru 83 + 85 Thru 88 + 90 Thru 97"),
    (71, "Strips All",    "90 Thru 97"),
    (72, "Strips Back",   "90 Thru 94"),
    (73, "Strips Left",   "90 + 93 + 95"),
    (74, "Strips Right",  "92 + 94 + 96"),
    (75, "SlimPars All",  "50 Thru 53"),
],
4: [  # ---- PAR PATTERNS & SPLITS - the chase / texture page
    (76, "Pars Odd",      P(range(1, 49, 2))),
    (77, "Pars Even",     P(range(2, 49, 2))),
    (78, "Pars 3rd",      P(range(1, 49, 3))),
    (79, "Pars 4th",      P(range(1, 49, 4))),
    (80, "Pars 5th",      P(range(1, 49, 5))),
    (81, "Pars 6th",      P(range(1, 49, 6))),
    (82, "Pars 8th",      P(range(1, 49, 8))),
    (83, "Pars Split A",  "2 + 4 Thru 5 + 11 + 13 + 16 + 18 + 21 + 23 + 25 "
                          "+ 27 Thru 28 + 30 + 32 + 34 + 37 + 39 + 41 "
                          "+ 43 Thru 45 + 47"),
    (84, "Pars Split B",  "1 + 3 + 6 + 12 + 14 Thru 15 + 17 + 20 + 22 + 24 "
                          "+ 26 + 29 + 31 + 33 + 35 Thru 36 + 38 + 40 + 42 "
                          "+ 46 + 48"),
    (85, "Pars 1st Half", "1 Thru 24"),
    (86, "Pars 2nd Half", "25 Thru 48"),
    (87, "Pars Qtr 1",    "1 Thru 12"),
    (88, "Pars Qtr 2",    "13 Thru 24"),
    (89, "Pars Qtr 3",    "25 Thru 36"),
    (90, "Pars Qtr 4",    "37 Thru 48"),
    (91, "Pars Qtr 1+3",  "1 Thru 12 + 25 Thru 36"),
    (92, "Pars Qtr 2+4",  "13 Thru 24 + 37 Thru 48"),
    (93, "Pars Ends",     "1 Thru 6 + 43 Thru 48"),
    (94, "Pars Middle",   "19 Thru 30"),
    (95, "Slim Left",     "50 Thru 51"),
    (96, "Slim Right",    "52 Thru 53"),
    (97, "Strips Odd",    "91 + 93 + 95 + 97"),
    (98, "Strips Even",   "90 + 92 + 94 + 96"),
    (99, "Drums",         "42 Thru 46 + 50 Thru 53"),
    (100, "Rig No Haze",  "1 Thru 98"),
],
}


class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _echo(self, wait=3.0, idle=0.30):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pages", type=int, nargs="*", default=[1, 2, 3, 4])
    ap.add_argument("--no-wipe", action="store_true")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    if not a.no_wipe:
        print("wiping every existing group (cues are unaffected)")
        for rng in ("1 Thru 200", "501 Thru 503"):
            b.send(f"Delete Group {rng}", confirm=True,
                   tolerate=("Does Not Exist",))

    for pg in a.pages:
        print(f"\n--- PAGE {pg}")
        for num, label, sel in PAGES[pg]:
            print(f"group {num}  {label}")
            b.send(f"Chan {sel} Record Group {num}")
            b.send(f"Group {num} Label {label}")

    if conn:
        b.send("Sneak Time 0")
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors:
        print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
