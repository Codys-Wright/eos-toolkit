#!/usr/bin/env python3
"""
A full stage look for each of the 18 song cues in list 1.

Each group of performers gets a colour identity; the three songs inside it move
through that identity so the stage changes without losing the group's look.
Every value is in the DESIGN table below - edit it and re-run to experiment.

  python3 build_song_looks.py --dry-run
  python3 build_song_looks.py --cues 110 120        # just these
"""
import argparse, sys, time
import eosdump as E

# --- zones ------------------------------------------------------------------
FRONT = "1 Thru 2 + 11 Thru 18"      # FOH trusses, over the audience
MID   = "3 Thru 10 + 20 Thru 31"     # stage lip and mid stage
BACK  = "32 Thru 48"                 # the 13 ft seam and upstage
OH    = "80 Thru 83"                 # gobo movers on the truss
BM    = "85 Thru 88"                 # beam movers at the seam
BARS  = "90 Thru 97"                 # TV uplights + footlights
SLIM  = "50 Thru 53"                 # column slimpars
HAZE  = "100 Thru 101"

# colour palettes 1-10: Red Orange Yellow Green Cyan Blue Purple Magenta WarmW ColdW
R,O,Y,G,C,B,P,M,WW,CW = range(1,11)
# focus palettes: 1-4 overhead movers, 5-10 beam movers
FP_OH_UP, FP_OH_CEIL, FP_OH_CTR, FP_OH_SIDE = 1,2,3,4
FP_BM_CEIL, FP_BM_CTR, FP_BM_DRUM, FP_BM_SIDE, FP_BM_CROSS, FP_BM_FLOOR = 5,6,7,8,9,10

# cue, label, front, mid, back, movers, bars, oh focus, bm focus, haze
DESIGN = [
 # --- GR: cool, building ------------------------------------------------
 (110,"GR Song 1",   B,  B,  C,  C,  B,  FP_OH_UP,   FP_BM_CEIL,  35),
 (120,"GR Song 2",   C,  C,  B,  B,  CW, FP_OH_CTR,  FP_BM_CROSS, 40),
 (130,"GR Song 3",   CW, C,  B,  C,  B,  FP_OH_CEIL, FP_BM_SIDE,  45),
 # --- AUB: warm ---------------------------------------------------------
 (210,"AUB Song 1",  O,  O,  R,  R,  O,  FP_OH_CTR,  FP_BM_DRUM,  35),
 (220,"AUB Song 2",  R,  O,  Y,  O,  R,  FP_OH_UP,   FP_BM_CROSS, 40),
 (230,"AUB Song 3",  WW, Y,  O,  R,  Y,  FP_OH_SIDE, FP_BM_CEIL,  45),
 # --- P3: jewel ---------------------------------------------------------
 (310,"P3 Song 1",   P,  P,  M,  M,  P,  FP_OH_UP,   FP_BM_CTR,   35),
 (320,"P3 Song 2",   M,  P,  B,  P,  M,  FP_OH_CEIL, FP_BM_CROSS, 40),
 (330,"P3 Song 3",   B,  M,  P,  C,  M,  FP_OH_CTR,  FP_BM_SIDE,  45),
 # --- TRI: fresh --------------------------------------------------------
 (410,"TRI Song 1",  G,  G,  C,  C,  G,  FP_OH_CTR,  FP_BM_FLOOR, 35),
 (420,"TRI Song 2",  C,  G,  Y,  G,  C,  FP_OH_UP,   FP_BM_DRUM,  40),
 (430,"TRI Song 3",  Y,  C,  G,  Y,  G,  FP_OH_SIDE, FP_BM_CROSS, 45),
 # --- KK: golden --------------------------------------------------------
 (510,"KK Song 1",   WW, WW, O,  O,  WW, FP_OH_CEIL, FP_BM_CEIL,  35),
 (520,"KK Song 2",   Y,  WW, R,  O,  Y,  FP_OH_CTR,  FP_BM_DRUM,  40),
 (530,"KK Song 3",   O,  Y,  WW, Y,  O,  FP_OH_UP,   FP_BM_CROSS, 45),
 # --- PS: pop, the finale group -----------------------------------------
 (610,"PS Song 1",   M,  C,  M,  M,  C,  FP_OH_UP,   FP_BM_CROSS, 40),
 (620,"PS Song 2",   C,  M,  P,  C,  M,  FP_OH_CTR,  FP_BM_SIDE,  45),
 (630,"PS Song 3",   CW, M,  C,  M,  CW, FP_OH_CEIL, FP_BM_FLOOR, 55),
]
# What each look is FOR. These display in a bar at the bottom of the PSD,
# including for the pending cue - so the operator reads the next vibe before
# taking it. Keep them plain: no quotes, slashes or brackets.
NOTES = {
110:"Cool open. Deep blue wash on cyan depth. Calm and wide, nothing moving - let the group arrive",
120:"Cyan lifts over blue, cold white bars. Brighter and colder - this is the step up into the chorus",
130:"Cold white front over blue depth. Peak of the cool set - crisp, open, the biggest of the three",
210:"Warm open. Orange wash on red depth. Golden hour, close and friendly - faces read easily here",
220:"Red front, yellow behind. Hotter and more urgent - the drive of the warm set",
230:"Warm white front on orange depth. Softest of the warm set - the landing, let it breathe",
310:"Purple wash, magenta depth. Rich and moody, low and close - the jewel set opens dark",
320:"Magenta front over blue back. Cooler jewel tone - the twist, colder than it looks on paper",
330:"Blue front, purple back, cyan movers. Deepest and coolest of the jewel set",
410:"Green wash on cyan depth. Fresh and open - the spring look, lots of air",
420:"Cyan front, yellow behind. Brighter and sharper - the contrast song",
430:"Yellow front on green depth. Warmest of the fresh set - sunlit, the payoff",
510:"Warm white wash, orange depth. Classic and clean - the safest look in the show, faces first",
520:"Yellow front, red behind. Golden and hot - the build of the warm set",
530:"Orange front on warm white depth. The glow - softest landing, good for a ballad",
610:"Magenta wash, cyan mid. Pop contrast, high energy from the very top - the finale group opens loud",
620:"Cyan front, purple back. The cool half of the finale - a breather before the last one",
630:"Cold white front, cyan back, magenta movers, haze up. Biggest look in the show - the finale",
}

# levels are the same shape for every song - change here, not per cue
LVL = dict(front=80, mid=65, back=90, slim=75, oh=100, bm=100, bars=100)

class B_:
    def __init__(s, conn, dry): s.c, s.dry, s.n, s.errors = conn, dry, 0, []
    def send(s, cmd, confirm=False):
        s.n += 1
        if s.dry:
            print(f"      {cmd}"); return
        s.c.send("/eos/newcmd", cmd + "#"); time.sleep(0.17)
        echo = ""
        for a, g in s.c.recv():
            if a == "/eos/out/cmd" and g: echo = g[0]
        if "Please Confirm" in echo:
            s.c.send("/eos/key/enter",1); s.c.send("/eos/key/enter",0); time.sleep(0.25)
            echo = ""
            for a, g in s.c.recv():
                if a == "/eos/out/cmd" and g: echo = g[0]
        if "Error" in echo: s.errors.append((cmd, echo))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cues", type=int, nargs="*")
    a = ap.parse_args()
    rows = [r for r in DESIGN if not a.cues or r[0] in a.cues]
    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = B_(conn, a.dry_run)
    for cue,label,cf,cm,cb,cmv,cba,foh,fbm,haze in rows:
        print(f"  cue 1/{cue:<5} {label:<12} front={cf} mid={cm} back={cb} mvr={cmv} bars={cba} haze={haze}%")
        b.send("Sneak Time 0")
        # NEVER combine At <level> with Color_Palette in one command - the level
        # applies, the palette is silently dropped, and the echo reports success.
        for zone, lvl, cp in ((FRONT,LVL['front'],cf), (MID,LVL['mid'],cm),
                              (BACK,LVL['back'],cb),   (SLIM,LVL['slim'],cb),
                              (BARS,LVL['bars'],cba)):
            b.send(f"Chan {zone} At {lvl}")
            b.send(f"Chan {zone} Color_Palette {cp}")
        for zone, lvl, fp in ((OH,LVL['oh'],foh), (BM,LVL['bm'],fbm)):
            b.send(f"Chan {zone} At {lvl}")
            b.send(f"Chan {zone} Color_Palette {cmv}")
            b.send(f"Chan {zone} Focus_Palette {fp}")
        b.send(f"Chan {HAZE} At {haze}")
        b.send(f"Record Cue 1 / {cue} Label {label}", confirm=True)
        if cue in NOTES: b.send(f"Cue 1 / {cue} Notes {NOTES[cue]}")
    b.send("Sneak Time 0")
    if conn:
        conn.send("/eos/key/save_show",1); conn.send("/eos/key/save_show",0); time.sleep(1.0); conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for c,e in b.errors[:8]: print(f"  FAILED: {c}\n          {e[:70]}")
    return 1 if b.errors else 0

if __name__ == "__main__":
    sys.exit(main())
