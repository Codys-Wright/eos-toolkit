#!/usr/bin/env python3
"""
Build a preset library on a live Eos console, as 5x5 DIRECT SELECT PAGES.

A preset stores EVERY parameter category at once - intensity, focus, colour,
beam - so one button recalls a complete look. That is what makes them the
busking tool: recall a preset, then layer FX submasters on top.

  PAGE 1  (  1-25)  POSITION + INTENSITY - no colour at all, so any of them
                    drops onto any song cue without fighting its colour
                    scheme (recorded with Record Only)
  PAGE 2  ( 26-50)  MOVER POSITIONS - also colour-free
  PAGES 3-6 (51-100) FIFTY COMPLETE LOOKS - colour, levels, mover position
                    and haze in one press. These DO carry colour.
  PAGE 2  (26-50)  WASHES    - the whole rig in each of the 25 distinct colours
  PAGE 3  (51-75)  MOVERS    - position + gobo combinations

Groups: 10 All  2 Pars  4 Strips  5 SlimPars  7 OH Movers
         8 Movers Beam  11 Left All  12 Centre All  13 Right All
        16 Front Wash  19 Back Wash  20 Drums  51 Movers All
Focus:  OH 1-4 = XYZ points Centre / DS Centre / Drums / Stage Left
        (see build_xyz_focus.py - these are Augment3d coordinates now)
        BM 16-23 (ceiling, ctr ceiling, drum ceiling, side walls,
                  cross corners, cross up ctr, floor ctr, side cross ceil)
Beam:   OH 11-18 (eyeball, star broken, open, broken, spots, spiral, star,
                  flower);  BM 1-8 (spots big, spots small, windows, stars,
                  flowers skinny, x, zebra, flower fat)
"""
import argparse, sys, time
import eosdump as E

HAZE = "Chan 100 Thru 101"
ZERO = "Group 10 At 0"
# Effects are stage state and a sneak does not clear them. The Chan form is
# required - "Group 10 Effect" is accepted and stops nothing (trap 29).
FX_STOP = "Chan 1 Thru 101 Effect"

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
    c = [f"Group 1 At {wash_lvl} Color_Palette {cp}",
         f"Group 5 At {wash_lvl} Color_Palette {cp}",
         f"Group 4 At {strip_lvl} Color_Palette {cp}"]
    if mvr:
        # Focus_Palette 3 = Fan Out, the neutral open-stage position for both
        # mover groups. Was FP 2 (OH) and FP 16 (the old pan/tilt Beam Ceiling),
        # which pointed the overheads left and the beams at the ceiling in
        # every single wash preset.
        c += ["Group 7 At 100 Focus_Palette 3 Beam_Palette 13",
              "Group 8 At 100 Focus_Palette 3 Beam_Palette 1"]
    c.append(f"{HAZE} At 40")
    return c


# (number, label, record-scope group, [setup commands])
PRESETS = []

# ---------------- PAGE 1: BUSKING LOOKS - NO COLOUR ----------------
# These carry POSITION and INTENSITY only, and are recorded with Record Only so
# no colour data is stored at all. That is the whole point: the song cue owns
# the colour scheme, and any of these can be dropped on top of any cue without
# fighting it. Recorded with Record they would bake in whatever colour happened
# to be on stage - which is exactly the bug that produced 25 pink presets.
#
# Groups:  1 Washers  4 Strips  5 SlimPars  7 OH Movers  8 Beam Movers
#         11 Left  12 Centre  13 Right  14 Downstage  15 Upstage
#         16 Front  17 Mid  19 Back  20 Drums
# Focus:   1 Centre  2 DS Centre  3 Drums  4 Stage Left  5 Stage Right
#          6 Audience  7 Straight  8 Crossed  9 Fan Out  10 Parallel Out

def mv(fp, lvl=100):
    """Both mover groups on one XYZ focus point, shutter held open.

    Strobe Mode 25 is "no strobe" on these fixtures. Leave it unset and the
    profile's home value strobes, which made every mover preset unusable.
    """
    return [f"Group 7 At {lvl} Focus_Palette {fp}",
            f"Group 8 At {lvl} Focus_Palette {fp}",
            "Group 7 Strobe_Mode 25", "Group 8 Strobe_Mode 25"]

COLOUR_FREE = set(range(1, 26))     # recorded with Record Only

PRESETS += [
    # --- overall level, movers open on Fan Out ---
    ( 1, "Full Stage",    10, ["Group 1 At 100"] + mv(3)     + [f"{HAZE} At 40"]),
    ( 2, "Three Quarter", 10, ["Group 1 At 75"]  + mv(3)     + [f"{HAZE} At 35"]),
    ( 3, "Half",          10, ["Group 1 At 50"]  + mv(3)     + [f"{HAZE} At 35"]),
    ( 4, "Quarter",       10, ["Group 1 At 25"]  + mv(3, 70) + [f"{HAZE} At 30"]),
    ( 5, "Low Glow",      10, ["Group 1 At 10"]  + mv(3, 40) + [f"{HAZE} At 30"]),
    # --- depth ---
    ( 6, "Front Heavy",   10, ["Group 16 At 100", "Group 17 At 60",
                               "Group 19 At 25"] + mv(9) + [f"{HAZE} At 35"]),
    ( 7, "Mid Heavy",     10, ["Group 16 At 45", "Group 17 At 100",
                               "Group 19 At 45"] + mv(11) + [f"{HAZE} At 35"]),
    ( 8, "Back Heavy",    10, ["Group 16 At 25", "Group 17 At 60",
                               "Group 19 At 100"] + mv(10) + [f"{HAZE} At 40"]),
    ( 9, "Downstage",     10, ["Group 14 At 100"] + mv(9) + [f"{HAZE} At 35"]),
    (10, "Upstage",       10, ["Group 15 At 100"] + mv(10) + [f"{HAZE} At 40"]),
    # --- width ---
    (11, "Left Feature",  10, ["Group 11 At 100", "Group 12 At 45",
                               "Group 13 At 20"] + mv(13) + [f"{HAZE} At 35"]),
    (12, "Centre Feature",10, ["Group 12 At 100", "Group 11 At 35",
                               "Group 13 At 35"] + mv(11) + [f"{HAZE} At 35"]),
    (13, "Right Feature", 10, ["Group 13 At 100", "Group 12 At 45",
                               "Group 11 At 20"] + mv(14) + [f"{HAZE} At 35"]),
    (14, "Outside In",    10, ["Group 11 At 100", "Group 13 At 100",
                               "Group 12 At 30"] + mv(4) + [f"{HAZE} At 40"]),
    (15, "Inside Out",    10, ["Group 12 At 100", "Group 11 At 35",
                               "Group 13 At 35"] + mv(3) + [f"{HAZE} At 40"]),
    # --- features ---
    (16, "Drums Feature", 10, ["Group 20 At 100"] + mv(10) + [f"{HAZE} At 40"]),
    (17, "Vocal Centre",  10, ["Group 16 At 85", "Group 12 At 70"]
                              + mv(11) + [f"{HAZE} At 30"]),
    (18, "Band Wide",     10, ["Group 1 At 85"] + mv(3) + [f"{HAZE} At 40"]),
    # --- movers carrying the look on their own ---
    (19, "Movers Fan",    10, mv(3)  + [f"{HAZE} At 55"]),
    (20, "Movers Cross",  10, mv(4)  + [f"{HAZE} At 55"]),
    (21, "Movers Straight",10, mv(1) + [f"{HAZE} At 55"]),
    (22, "Audience Hit",  10, ["Group 1 At 30"] + mv(15) + [f"{HAZE} At 50"]),
    (23, "Beams Para",    10, ["Group 8 At 100 Focus_Palette 2",
                               f"{HAZE} At 55"]),
    # --- utility ---
    (24, "Preshow",       10, ["Group 5 At 20", f"{HAZE} At 40"]),
    (25, "Haze Only",     10, [f"{HAZE} At 50"]),
]

# ---------------- PAGE 2 (26-50): MOVER POSITIONS ----------------
# Colour-free, like page 1: focus and intensity only, recorded with Record
# Only. Drop any of these onto any song cue and the cue keeps its colour.
#
# Focus palettes (build_xyz_focus.py):
#   1 Straight  2 Parallel Out  3 Fan Out  4 Crossed  5 Wall Split
#   6 Fan Audience  7 Split LR  8 Zigzag  9 DS Centre  10 Drums
#  11 Centre 12 US Centre 13 Stage Left 14 Stage Right 15 Audience
#  16 Lip Left 17 Lip Right 18 Aud Left 19 Aud Right 20 Upstage Wall
#
# The industry-standard six busking positions are Stage / Down / Up and Out /
# Down and Out / Cross / Crowd. Ours cover all six: Fan Out, Straight,
# Parallel Out, Fan Audience, Crossed and Audience.

def oh(fp, lvl=100):  return [f"Group 7 At {lvl} Focus_Palette {fp}"]
def bm(fp, lvl=100):  return [f"Group 8 At {lvl} Focus_Palette {fp}"]

MOVER_POS = [
    # --- the spread patterns, whole rig and split by group ---
    (26, "Straight All",   mv(1)),
    (27, "Straight OH",    oh(1)),
    (28, "Straight BM",    bm(1)),
    (29, "Parallel Out",   mv(2)),
    (30, "Parallel OH",    oh(2)),
    (31, "Fan Out",        mv(3)),
    (32, "Fan OH",         oh(3)),
    (33, "Fan BM",         bm(3)),
    (34, "Crossed",        mv(4)),
    (35, "Crossed OH",     oh(4)),
    (36, "Wall Split",     mv(5)),
    (37, "Fan Audience",   mv(6)),
    (38, "Split LR",       mv(7)),
    (39, "Zigzag",         mv(8)),
    # --- opposed pairs: the two groups doing different things ---
    (40, "OH Fan BM Cross",  oh(3) + bm(4)),
    (41, "OH Strght BM Fan", oh(1) + bm(3)),
    (42, "OH Cross BM Para", oh(4) + bm(2)),
    # --- convergence ---
    (43, "DS Centre",      mv(9)),
    (44, "Drums",          mv(10)),
    (45, "Centre",         mv(11)),
    (46, "US Centre",      mv(12)),
    (47, "Stage Left",     mv(13)),
    (48, "Stage Right",    mv(14)),
    (49, "Audience",       mv(15)),
    (50, "Upstage Wall",   mv(20)),
]
COLOUR_FREE |= {n for n, _l, _c in MOVER_POS}
for num, label, cmds in MOVER_POS:
    PRESETS.append((num, label, 51, cmds + [f"{HAZE} At 45"]))

# ---------------- 51-100: FIFTY COMPLETE LOOKS ----------------
# A complete look: colour, intensity distribution, mover position and haze,
# all in one press. These DO carry colour - that is the point of them. Recorded
# with plain Record, unlike 1-50.
#
# Colour palettes 1-25 (page 1 of the colour library):
#   1 Red      2 Orange   3 Amber    4 Yellow   5 Lime
#   6 Green    7 Emerald  8 Teal     9 Cyan    10 Sky
#  11 Azure   12 Blue    13 DeepBlue 14 Indigo 15 Violet
#  16 Purple  17 Magenta 18 HotPink 19 Rose    20 Blush
#  21 White   22 WarmWht 23 CoolWht 24 Lavender 25 Peach

def look(fcp, bcp, fp, fl=85, bl=90, sl=70, hz=40):
    """front colour, back colour, mover focus, and the levels around them."""
    return [f"Group 16 At {fl}",  f"Group 16 Color_Palette {fcp}",
            f"Group 17 At {fl-15}", f"Group 17 Color_Palette {fcp}",
            f"Group 19 At {bl}",  f"Group 19 Color_Palette {bcp}",
            f"Group 5 At {sl}",   f"Group 5 Color_Palette {bcp}",
            f"Group 4 At {sl}",   f"Group 4 Color_Palette {fcp}",
            f"Group 7 At 100 Focus_Palette {fp}",
            f"Group 8 At 100 Focus_Palette {fp}",
            f"{HAZE} At {hz}"]

#  num  label             front  back  focus  levels / haze
LOOKS = [
    # --- 51-60 single-colour states, the bread and butter ---
    (51, "Deep Blue",       12, 13,  3),
    (52, "Cold Open",       23, 11,  1, 70, 80, 60, 35),
    (53, "Warm Wash",       22,  2,  3),
    (54, "Golden Hour",      3,  2,  3, 90, 80, 70, 45),
    (55, "Blood Red",        1,  1,  4, 95,100, 80, 50),
    (56, "Forest",           6,  7,  3),
    (57, "Ocean",            9, 11,  2),
    (58, "Violet Haze",     15, 16,  3, 80, 90, 70, 55),
    (59, "Hot Pink",        18, 17,  6, 95, 95, 80, 45),
    (60, "Clean White",     21, 21,  3,100, 90, 80, 30),
    # --- 61-70 two-colour contrast, the ones that read from the back row ---
    (61, "Blue Amber",      12,  3,  4),
    (62, "Magenta Cyan",    17,  9,  4, 90, 95, 75, 50),
    (63, "Red Blue",         1, 12,  4, 90, 95, 75, 45),
    (64, "Green Magenta",    6, 17,  7),
    (65, "Orange Teal",      2,  8,  3),
    (66, "Purple Lime",     16,  5,  8),
    (67, "Rose Azure",      19, 11,  3),
    (68, "Yellow Indigo",    4, 14,  7),
    (69, "Peach Deep",      25, 13,  6),
    (70, "Lavender Sky",    24, 10,  2, 75, 80, 65, 45),
    # --- 71-80 features: one thing gets the stage ---
    (71, "Drums Feature",    2,  1, 10, 40,100, 60, 45),
    (72, "Vocal Centre",    22, 13, 11, 95, 45, 50, 30),
    (73, "Guitar SL",       17, 16, 13, 60, 60, 55, 40),
    (74, "Guitar SR",        9, 11, 14, 60, 60, 55, 40),
    (75, "Solo Spot",       21, 13, 11,100, 30, 40, 35),
    (76, "Band Wide",       22,  2,  3, 85, 90, 75, 40),
    (77, "Upstage Feature", 13, 12, 12, 35, 95, 60, 50),
    (78, "Downstage Punch",  1,  2,  9,100, 50, 70, 40),
    (79, "Duet",            19, 16,  7, 80, 70, 60, 40),
    (80, "Full Band Hit",   21,  1,  4,100,100, 90, 55),
    # --- 81-90 high energy ---
    (81, "Rave Blue",       12, 14,  6, 95,100, 85, 60),
    (82, "Rave Magenta",    17, 15,  6, 95,100, 85, 60),
    (83, "Strobe Base",     21, 21,  1,100,100, 90, 55),
    (84, "Audience Blast",  21, 12,  6, 90, 90, 80, 60),
    (85, "Beam Storm",      13, 12,  8, 60, 90, 70, 65),
    (86, "Chase Base",       2,  1,  3, 90, 90, 80, 45),
    (87, "Big Finish",      17,  9,  2,100,100, 90, 60),
    (88, "Wall of Light",   21, 23,  5,100,100, 90, 50),
    (89, "Split Stage",      1,  9,  7, 90, 90, 75, 50),
    (90, "Anthem",          22, 12,  3,100, 95, 85, 50),
    # --- 91-100 low, ambient and utility ---
    (91, "Preshow",         13, 14,  3, 25, 30, 20, 40),
    (92, "Interval",        22,  3,  3, 40, 40, 35, 30),
    (93, "Ballad",          24, 13, 11, 55, 60, 45, 45),
    (94, "Smoke Room",      11, 12,  1, 20, 35, 25, 60),
    (95, "Silhouette",      13, 21,  1, 10, 95, 30, 55),
    (96, "Low Amber",        3,  2,  3, 30, 35, 25, 35),
    (97, "Night",           14, 13,  2, 20, 30, 20, 45),
    (98, "Speech",          22, 22, 11, 70, 40, 40, 25),
    (99, "Video Safe",      23, 23, 11, 15, 15, 15, 45),
    (100,"House Warm",       2, 22,  3, 45, 45, 40, 30),
]
for row in LOOKS:
    num, label, fcp, bcp, fp = row[:5]
    PRESETS.append((num, label[:16], 10, look(fcp, bcp, fp, *row[5:])))


import re as _re

_AT_PAL = _re.compile(
    r"^(?P<sel>.+?) At (?P<lvl>\S+) (?P<pal>(?:Color|Focus|Beam|Intensity)_Palette .*)$")

def split_level_and_palette(cmd):
    """TRAP 21: 'Group 7 At 100 Focus_Palette 3' applies the LEVEL and silently
    DROPS the palette. The echo reports success and the movers never move.

    Every mover line in this file was written that way, so no preset moved a
    mover - confirmed by read-back: combined gave pan/tilt (0,0), split gave
    (-29.7, -69.6).

    Splitting here rather than at each call site means a future edit cannot
    reintroduce it.
    """
    m = _AT_PAL.match(cmd)
    if not m:
        return [cmd]
    return [f"{m['sel']} At {m['lvl']}", f"{m['sel']} {m['pal']}"]


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
    # Pages are 25 presets each: 1 = position+intensity, 2 = mover
    # positions, 3-6 = the fifty complete looks (51-100).
    ap.add_argument("--pages", type=int, nargs="*", default=[1, 2, 3, 4, 5, 6])
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)
    lo, hi = (min(a.pages) - 1) * 25 + 1, max(a.pages) * 25

    print(f"clearing presets {lo}-{hi}")
    # RECORD CAPTURES THE STAGE, and a running cue is part of the stage.
    # Build against an empty background or the show's current look bleeds into
    # every preset. "Go_To_Cue Out Time 0" is a syntax error - Eos accepts
    # "Go_To_Cue Out" and silently appends "Preset" to the version with Time.
    b.send("Go_To_Cue Out")
    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")

    b.send(f"Delete Preset {lo} Thru {hi}", confirm=True,
           tolerate=("Does Not Exist",))

    for num, label, scope, cmds in PRESETS:
        if not (lo <= num <= hi):
            continue
        print(f"preset {num:>3}  {label}")
        # Clear to a known state. "Sneak Time 0" only sets a TIME - it clears
        # nothing. Without a real sneak, any parameter this preset does not set
        # keeps whatever the last preset (or the running cue) left on stage,
        # and Record bakes it in. That is how show colour ends up inside a
        # preset that never mentions colour.
        b.send(FX_STOP)
        b.send("Group 10 Sneak Time 0")
        b.send(ZERO)
        for c in cmds:
            for part in split_level_and_palette(c):
                b.send(part)
        # Record Only for the colour-free bank: it stores ONLY manual data, so
        # colour - which we never touch for these - is simply absent from the
        # preset and the song cue keeps its own. Record would store the whole
        # parameter category for every non-default channel instead.
        # Record Only MERGES into an existing target, so the Delete above is
        # load-bearing, not hygiene. See trap 26.
        verb = "Record_Only" if num in COLOUR_FREE else "Record"
        b.send(f"Group {scope} {verb} Preset {num}")
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
