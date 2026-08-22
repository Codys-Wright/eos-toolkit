#!/usr/bin/env python3
"""
Build a professional colour-palette and group library on a live Eos console.

NUMBERING SCHEME (fresh 100+ range; nothing existing is overwritten)
  Colour palettes
    101-126  full rig  (Group 5 = chans 1-99, every colour-capable fixture)
  Groups
    101-108  by fixture type   (derived from patch, physically accurate)
    111-118  par structure     (odd/even, quarters - for chases and splits)
    121-124  useful combos

  python3 build_library.py --dry-run
  python3 build_library.py --only colors
  python3 build_library.py --only groups
"""
import argparse, sys, time
import eosdump as E

# --- colour library: (number, label, r, g, b) with r/g/b as 0.0-1.0 ----------
COLORS = [
    (101, "Red",          1.00, 0.00, 0.00),
    (102, "Deep Red",     0.55, 0.00, 0.02),
    (103, "Orange",       1.00, 0.35, 0.00),
    (104, "Amber",        1.00, 0.50, 0.05),
    (105, "Gold",         1.00, 0.70, 0.15),
    (106, "Straw",        1.00, 0.85, 0.45),
    (107, "Yellow",       1.00, 1.00, 0.00),
    (108, "Lime",         0.60, 1.00, 0.00),
    (109, "Green",        0.00, 1.00, 0.00),
    (110, "Deep Green",   0.00, 0.45, 0.10),
    (111, "Teal",         0.00, 0.80, 0.60),
    (112, "Cyan",         0.00, 1.00, 1.00),
    (113, "Sky Blue",     0.35, 0.75, 1.00),
    (114, "Blue",         0.00, 0.30, 1.00),
    (115, "Deep Blue",    0.00, 0.05, 0.80),
    (116, "Indigo",       0.25, 0.00, 0.80),
    (117, "Violet",       0.55, 0.00, 1.00),
    (118, "Purple",       0.70, 0.00, 0.90),
    (119, "Magenta",      1.00, 0.00, 1.00),
    (120, "Hot Pink",     1.00, 0.00, 0.45),
    (121, "Pink",         1.00, 0.45, 0.65),
    (122, "Lavender",     0.75, 0.60, 1.00),
    (123, "Peach",        1.00, 0.65, 0.50),
    (124, "White",        1.00, 1.00, 1.00),
    (125, "Warm White",   1.00, 0.85, 0.65),
    (126, "Cool White",   0.80, 0.90, 1.00),
]

def _plus(nums):
    return " + ".join(str(n) for n in nums)

# --- group library laid out as a 5x5 DIRECT SELECT GRID ---------------------
# Row = category, and each row reads broad -> specific left to right, so the
# grid is navigable by muscle memory:
#
#   101 Rig All      102 Pars All   103 SlimPars    104 Strips      105 Haze
#   106 Movers All   107 Mvr OH     108 Mvr Beam    109 Wash All    110 Mvr+Strip
#   111 Zone Left    112 Zone Ctr   113 Zone Right  114 Front Wash  115 Drums
#   116 Pars Qtr 1   117 Pars Qtr 2 118 Pars Qtr 3  119 Pars Qtr 4  120 Pars Upstg
#   121 Pars Odd     122 Pars Even  123 Pars 3rd    124 Pars 4th    125 Pars Split
#
# Zone rows reuse the reference show's 501/502/503 channel lists, which are the
# only left/centre/right division actually derived from the physical rig.
GROUPS = [
    # row 1 - whole rig, by fixture type
    (101, "Rig All",      "1 Thru 98"),
    (102, "Pars All",     "1 Thru 48"),
    (103, "SlimPars",     "50 Thru 53"),
    (104, "Strips",       "90 Thru 97"),
    (105, "Haze",         "100 Thru 101"),
    # row 2 - movers and big combos
    (106, "Movers All",   "80 Thru 83 + 85 Thru 88 + 98"),
    (107, "Movers OH",    "80 Thru 83"),
    (108, "Movers Beam",  "85 Thru 88 + 98"),
    (109, "Wash All",     "1 Thru 48 + 50 Thru 53"),
    (110, "Mvr + Strip",  "80 Thru 83 + 85 Thru 88 + 90 Thru 97 + 98"),
    # row 3 - stage zones
    (111, "Zone Left",    "3 Thru 4 + 7 Thru 8 + 20 Thru 21 + 32 Thru 35 + 41 + 50"),
    (112, "Zone Centre",  "22 Thru 29 + 42 Thru 46 + 51 Thru 52"),
    (113, "Zone Right",   "2 + 5 Thru 6 + 9 Thru 10 + 15 Thru 18 + 30 Thru 31 "
                          "+ 36 Thru 39 + 47 Thru 48 + 53"),
    (114, "Front Wash",   "1 Thru 6 + 11 Thru 18"),
    (115, "Drums",        "42 Thru 46 + 50 Thru 53"),
    # row 4 - par depth, for building layers upstage to down
    (116, "Pars Qtr 1",   "1 Thru 12"),
    (117, "Pars Qtr 2",   "13 Thru 24"),
    (118, "Pars Qtr 3",   "25 Thru 36"),
    (119, "Pars Qtr 4",   "37 Thru 48"),
    (120, "Pars Upstage", "32 Thru 41 + 47 Thru 48"),
    # row 5 - patterns, for chases and texture
    (121, "Pars Odd",     _plus(range(1, 49, 2))),
    (122, "Pars Even",    _plus(range(2, 49, 2))),
    (123, "Pars 3rd",     _plus(range(1, 49, 3))),
    (124, "Pars 4th",     _plus(range(1, 49, 4))),
    (125, "Pars Split",   "2 + 4 Thru 5 + 11 + 13 + 16 + 18 + 21 + 23 + 25 "
                          "+ 27 Thru 28 + 30 + 32 + 34 + 37 + 39 + 41 "
                          "+ 43 Thru 45 + 47"),
]

# --- relabel existing targets so the old library is at least legible ---------
RELABEL = {
    "Color_Palette": {
        1:"Legacy Red", 2:"Legacy Green", 3:"Legacy Blue", 4:"Legacy Lime",
        5:"Legacy Cyan", 6:"Legacy Magenta", 7:"Legacy Pink", 8:"Legacy Purple",
        9:"Legacy Yellow", 10:"Legacy Orange", 11:"Legacy Sky Blue",
        12:"Legacy White", 13:"Legacy OH Mixed", 15:"Legacy Par Warm",
        18:"Legacy Cyan Alt", 20:"Legacy Mixed", 22:"Legacy Strip",
        30:"OH White", 31:"OH Cyan", 32:"OH Blue", 33:"OH Magenta",
        34:"OH White Red", 35:"OH Orange Cyan", 36:"OH Blue Orange",
        37:"OH Green Yellow", 38:"OH Magenta Green",
        41:"Beam White", 42:"Beam Red", 43:"Beam Yellow", 44:"Beam Blue",
        45:"Beam Green", 46:"Beam Orange", 47:"Beam Purple",
    },
    "Focus_Palette": {
        1:"OH Up", 2:"OH Centre Ceiling", 3:"OH Centre Up", 4:"OH Side Walls",
        16:"Beam Ceiling", 17:"Beam Centre Ceiling", 18:"Beam Drum Ceiling",
        19:"Beam Side Walls", 20:"Beam Cross Corners",
        21:"Beam Cross Up Centre", 22:"Beam Floor Centre",
        23:"Beam Side Cross Ceiling",
    },
    "Group": {
        1:"Pars All Legacy", 2:"SlimPars Legacy", 3:"Foot Lights",
        4:"Movers Overhead Legacy", 5:"Rig All Legacy", 6:"Movers Beam Legacy",
        8:"Pars Upstage Block", 11:"Pars Stage Right", 12:"Pars Stage Left",
        13:"Drums Legacy", 14:"Pars Centre", 15:"Pars Split A",
        16:"Pars Split B", 21:"Pars Front Legacy",
        501:"Zone Left", 502:"Zone Centre", 503:"Zone Right",
    },
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

    def send(self, cmd, confirm=False):
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
        if "Error" in echo:
            self.errors.append((cmd, echo))
            print(f"  !! {cmd}\n     -> {echo}", file=sys.stderr)

    def rgb(self, r, g, b):
        self.n += 1
        if self.dry:
            print(f"  /eos/color/rgb {r} {g} {b}")
            return
        self.conn.send("/eos/color/rgb", float(r), float(g), float(b))
        time.sleep(0.35)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=["colors", "groups", "relabel"])
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)
    todo = a.only

    if todo in (None, "colors"):
        print(f"--- {len(COLORS)} colour palettes (101-126)")
        for num, label, r, g, bl in COLORS:
            print(f"cp {num}  {label}")
            b.send("Sneak Time 0")
            b.send("Group 5 At 100")        # every colour-capable fixture
            b.rgb(r, g, bl)
            b.send(f"Group 5 Record Color_Palette {num}")
            b.send(f"Color_Palette {num} Label {label}")
        b.send("Sneak Time 0")

    if todo in (None, "groups"):
        print(f"\n--- {len(GROUPS)} groups as a 5x5 grid (101-125)")
        b.send(f"Delete Group {GROUPS[0][0]} Thru {GROUPS[-1][0]}", confirm=True)
        for num, label, sel in GROUPS:
            print(f"group {num}  {label}")
            b.send(f"Chan {sel} Record Group {num}")
            b.send(f"Group {num} Label {label}")

    if todo in (None, "relabel"):
        print(f"\n--- relabelling existing targets")
        for kind, mapping in RELABEL.items():
            for num, label in sorted(mapping.items()):
                b.send(f"{kind} {num} Label {label}")

    if conn:
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors:
        print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
