#!/usr/bin/env python3
"""
Build a preset library on a live Eos console, as 5x5 DIRECT SELECT PAGES.

A preset stores EVERY parameter category at once - intensity, focus, colour,
beam - so one button recalls a complete look. That is what makes them the
busking tool: recall a preset, then layer FX submasters on top.

  PAGE 1  ( 1-25)  SIGNATURE - complete stage looks, ready to go
  PAGE 2  (26-50)  WASHES    - the whole rig in each of the 25 distinct colours
  PAGE 3  (51-75)  MOVERS    - position + gobo combinations

Groups:  1 Rig All  3 Pars All  5 Strips  6 SlimPars  7 Movers OH
         8 Movers Beam  11 Left All  12 Centre All  13 Right All
        16 Front Wash  19 Back Wash  20 Drums  51 Movers All
Focus:  OH 1-4 (up, ctr ceiling, ctr+up, side walls)
        BM 16-23 (ceiling, ctr ceiling, drum ceiling, side walls,
                  cross corners, cross up ctr, floor ctr, side cross ceil)
Beam:   OH 11-18 (eyeball, star broken, open, broken, spots, spiral, star,
                  flower);  BM 1-8 (spots big, spots small, windows, stars,
                  flowers skinny, x, zebra, flower fat)
"""
import argparse, sys, time
import eosdump as E

HAZE = "Chan 100 Thru 101"
ZERO = "Group 1 At 0"

# --- 25 distinct colours from page 1 of the colour library ------------------
COLOURS = [
    (1,"Red"),(2,"Orange"),(3,"Amber"),(4,"Yellow"),(5,"Lime"),
    (6,"Green"),(7,"Emerald"),(8,"Teal"),(9,"Cyan"),(10,"Sky"),
    (11,"Azure"),(12,"Blue"),(13,"Deep Blue"),(14,"Indigo"),(15,"Violet"),
    (16,"Purple"),(17,"Magenta"),(18,"Hot Pink"),(19,"Rose"),(20,"Blush"),
    (21,"White"),(22,"Warm White"),(23,"Cool White"),(24,"Lavender"),(25,"Peach"),
]

def wash(cp, wash_lvl=85, strip_lvl=65, mvr=True):
    """A full-rig wash in one colour, movers pointed neutral."""
    c = [f"Group 3 At {wash_lvl} Color_Palette {cp}",
         f"Group 6 At {wash_lvl} Color_Palette {cp}",
         f"Group 5 At {strip_lvl} Color_Palette {cp}"]
    if mvr:
        c += ["Group 7 At 100 Focus_Palette 2 Beam_Palette 13",
              "Group 8 At 100 Focus_Palette 16 Beam_Palette 1"]
    c.append(f"{HAZE} At 40")
    return c


# (number, label, record-scope group, [setup commands])
PRESETS = []

# ---------------- PAGE 1: SIGNATURE LOOKS ----------------
PRESETS += [
    ( 1, "Full Warm",     1, wash(22)),
    ( 2, "Full Cool",     1, wash(23)),
    ( 3, "Full White",    1, wash(21, 100, 85)),
    ( 4, "Deep Blue",     1, wash(13)),
    ( 5, "Deep Red",      1, wash(26)),
    ( 6, "Amber Glow",    1, wash(3, 55, 35)),
    ( 7, "Magenta Punch", 1, wash(17, 100, 85)),
    ( 8, "Green Wash",    1, wash(6)),
    ( 9, "Purple Wash",   1, wash(16)),
    (10, "Cyan Wash",     1, wash(9)),
    (11, "Front Warm",    1, ["Group 16 At 80 Color_Palette 22", f"{HAZE} At 35"]),
    (12, "Back Blue",     1, ["Group 19 At 80 Color_Palette 12", f"{HAZE} At 40"]),
    (13, "Sides Only",    1, ["Group 11 At 80 Color_Palette 21",
                              "Group 13 At 80 Color_Palette 21", f"{HAZE} At 35"]),
    (14, "Centre Special",1, ["Group 12 At 90 Color_Palette 22", f"{HAZE} At 35"]),
    (15, "Drums Feature", 1, ["Group 20 At 100 Color_Palette 17", f"{HAZE} At 40"]),
    (16, "Mvr Ceiling",   1, ["Group 7 At 100 Focus_Palette 2 Beam_Palette 13",
                              "Group 8 At 100 Focus_Palette 16 Beam_Palette 1",
                              f"{HAZE} At 50"]),
    (17, "Mvr Side Walls",1, ["Group 7 At 100 Focus_Palette 4 Beam_Palette 15",
                              "Group 8 At 100 Focus_Palette 19 Beam_Palette 2",
                              f"{HAZE} At 50"]),
    (18, "Mvr Centre",    1, ["Group 7 At 100 Focus_Palette 3 Beam_Palette 17",
                              "Group 8 At 100 Focus_Palette 17 Beam_Palette 4",
                              f"{HAZE} At 50"]),
    (19, "Beam Fan",      1, ["Group 8 At 100 Focus_Palette 20 Beam_Palette 3",
                              f"{HAZE} At 55"]),
    (20, "Strips Only",   1, ["Group 5 At 90 Color_Palette 12", f"{HAZE} At 35"]),
    (21, "Video Safe",    1, ["Group 5 At 15 Color_Palette 112", f"{HAZE} At 45"]),
    (22, "Speech",        1, ["Group 16 At 60 Color_Palette 22", f"{HAZE} At 30"]),
    (23, "Blackout",      1, []),
    (24, "Haze Only",     1, [f"{HAZE} At 50"]),
    (25, "Full Blast",    1, wash(21, 100, 100)),
]

# ---------------- PAGE 2: COLOUR WASHES ----------------
for i, (cp, name) in enumerate(COLOURS):
    PRESETS.append((26 + i, f"Wash {name}"[:16], 1, wash(cp)))

# ---------------- PAGE 3: MOVER LOOKS ----------------
MOVERS = [
    ("OH Up Open",      7, 1, 13), ("OH Ceil Spots",   7, 2, 15),
    ("OH CtrUp Star",   7, 3, 17), ("OH Sides Flower", 7, 4, 18),
    ("OH Up Spiral",    7, 1, 16), ("OH Ceil Eyeball", 7, 2, 11),
    ("OH Sides Broken", 7, 4, 14), ("OH Ctr StarBrk",  7, 3, 12),
    ("BM Ceiling Big",  8, 16, 1), ("BM Ceil Small",   8, 17, 2),
    ("BM Drum Windows", 8, 18, 3), ("BM Sides Stars",  8, 19, 4),
    ("BM Cross Flower", 8, 20, 5), ("BM CrossUp X",    8, 21, 6),
    ("BM Floor Zebra",  8, 22, 7), ("BM SideCross Fat",8, 23, 8),
    ("BM Ceil Spiral",  8, 16, 16),
]
for i, (label, grp, fp, bp) in enumerate(MOVERS):
    PRESETS.append((51 + i, label[:16], 51,
                    [f"Group {grp} At 100 Focus_Palette {fp} Beam_Palette {bp}",
                     f"{HAZE} At 50"]))

COMBOS = [
    ("All Mvr Ceiling", 2, 16, 13, 1), ("All Mvr Sides",  4, 19, 15, 2),
    ("All Mvr Cross",   3, 20, 17, 5), ("All Mvr Up",     1, 21, 13, 6),
    ("All Mvr Drum",    2, 18, 15, 3), ("All Mvr Floor",  1, 22, 16, 7),
    ("All Mvr Spiral",  3, 16, 16, 16),("All Mvr Stars",  2, 19, 17, 4),
]
for i, (label, ohfp, bmfp, ohbp, bmbp) in enumerate(COMBOS):
    PRESETS.append((68 + i, label[:16], 51,
                    [f"Group 7 At 100 Focus_Palette {ohfp} Beam_Palette {ohbp}",
                     f"Group 8 At 100 Focus_Palette {bmfp} Beam_Palette {bmbp}",
                     f"{HAZE} At 50"]))


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
        self.errors.append(("save_show", "no confirmation event"))
        print("  !! SAVE NOT CONFIRMED", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pages", type=int, nargs="*", default=[1, 2, 3])
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)
    lo, hi = (min(a.pages) - 1) * 25 + 1, max(a.pages) * 25

    print(f"clearing presets {lo}-{hi}")
    b.send(f"Delete Preset {lo} Thru {hi}", confirm=True,
           tolerate=("Does Not Exist",))

    for num, label, scope, cmds in PRESETS:
        if not (lo <= num <= hi):
            continue
        print(f"preset {num:>3}  {label}")
        b.send("Sneak Time 0")
        b.send(ZERO)
        for c in cmds:
            b.send(c)
        b.send(f"Group {scope} Record Preset {num}")
        b.send(f"Preset {num} Label {label}")

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
