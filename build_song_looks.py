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

FX_STOP = "Chan 1 Thru 101 Effect"   # the Chan form; Group does nothing (trap 29)

# colour palettes 1-10: Red Orange Yellow Green Cyan Blue Purple Magenta WarmW ColdW
R,O,Y,G,C,B,P,M,WW,CW = range(1,11)

# THE MOVERS HAVE A COLOUR WHEEL, NOT COLOUR MIXING, so an RGB colour palette
# is the wrong instrument for them - there is no cyan and no magenta slot to
# hit. Drive them by wheel position instead, at the slot centres from the OEM
# chart in docs/rig-model.md. Each design colour maps to its nearest real slot.
#   wheel: Open 3  Red 9  Pale Blue 16  Orange 22  Blue 28  Yellow 35
#          Green 41  Pink 47   (percent)
WHEEL = {R: 9, O: 22, Y: 35, G: 41, C: 16, B: 28, P: 47, M: 47, WW: 3, CW: 3}

# Focus palettes 1-10 are now Augment3d XYZ points and apply to ALL eight
# movers - see build_xyz_focus.py. The old FP_OH_* / FP_BM_* names pointed at
# palettes that no longer exist under those numbers.
# Renumbered when FP 1-8 became the SPREAD patterns and the convergence
# points moved to 9-20. The DESIGN table below uses the names, so it did not
# have to change - which is the entire reason for having the names.
FP_STRAIGHT, FP_PARA, FP_FAN, FP_CROSS = 1, 2, 3, 4
FP_WALLS, FP_FANAUD, FP_SPLIT, FP_ZIGZAG = 5, 6, 7, 8
FP_DS, FP_DRUMS = 9, 10
FP_CENTRE, FP_USC, FP_SL, FP_SR, FP_AUD = 11, 12, 13, 14, 15

# cue, label, front, mid, back, movers, bars, OH focus, BM focus, haze
#
# Focus is the shape of the look, not just an aim. Fan Out is the neutral
# open-stage default; Drums pulls in for a feature; Crossed and Parallel are
# the big moments; Straight is eight vertical shafts, best with haze up.
DESIGN = [
 # --- GR: cool, building ------------------------------------------------
 (110,"GR Song 1",   B,  B,  C,  C,  B,  FP_FAN,      FP_STRAIGHT, 35),
 (120,"GR Song 2",   C,  C,  B,  B,  CW, FP_CENTRE,   FP_CROSS,    40),
 (130,"GR Song 3",   CW, C,  B,  C,  B,  FP_CROSS,    FP_FAN,      45),
 # --- AUB: warm ---------------------------------------------------------
 (210,"AUB Song 1",  O,  O,  R,  R,  O,  FP_CENTRE,   FP_DRUMS,    35),
 (220,"AUB Song 2",  R,  O,  Y,  O,  R,  FP_FAN,      FP_CROSS,    40),
 (230,"AUB Song 3",  WW, Y,  O,  R,  Y,  FP_DS,       FP_FAN,      45),
 # --- P3: jewel ---------------------------------------------------------
 (310,"P3 Song 1",   P,  P,  M,  M,  P,  FP_FAN,      FP_CENTRE,   35),
 (320,"P3 Song 2",   M,  P,  B,  P,  M,  FP_CROSS,    FP_CROSS,    40),
 (330,"P3 Song 3",   B,  M,  P,  C,  M,  FP_CENTRE,   FP_FAN,      45),
 # --- TRI: fresh --------------------------------------------------------
 (410,"TRI Song 1",  G,  G,  C,  C,  G,  FP_CENTRE,   FP_STRAIGHT, 35),
 (420,"TRI Song 2",  C,  G,  Y,  G,  C,  FP_FAN,      FP_DRUMS,    40),
 (430,"TRI Song 3",  Y,  C,  G,  Y,  G,  FP_DS,       FP_CROSS,    45),
 # --- KK: golden --------------------------------------------------------
 (510,"KK Song 1",   WW, WW, O,  O,  WW, FP_FAN,      FP_FAN,      35),
 (520,"KK Song 2",   Y,  WW, R,  O,  Y,  FP_CENTRE,   FP_DRUMS,    40),
 (530,"KK Song 3",   O,  Y,  WW, Y,  O,  FP_FAN,      FP_CROSS,    45),
 # --- PS: pop, the finale group -----------------------------------------
 (610,"PS Song 1",   M,  C,  M,  M,  C,  FP_FAN,      FP_CROSS,    40),
 (620,"PS Song 2",   C,  M,  P,  C,  M,  FP_CENTRE,   FP_FAN,      45),
 (630,"PS Song 3",   CW, M,  C,  M,  CW, FP_PARA,     FP_PARA,     55),
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
    def _echo(s, wait=3.0, idle=0.25):
        end, last, e = time.time()+wait, time.time(), ""
        while time.time() < end:
            m = s.c.recv()
            if m:
                last = time.time()
                for a, g in m:
                    if a == "/eos/out/cmd" and g: e = str(g[0])
            elif time.time()-last > idle: break
        return e

    def send(s, cmd, confirm=False):
        s.n += 1
        if s.dry:
            print(f"      {cmd}"); return
        s.c.send("/eos/newcmd", cmd + "#")
        echo = s._echo()
        if "Please Confirm" in echo:
            s.c.send("/eos/key/enter",1); s.c.send("/eos/key/enter",0)
            echo = s._echo()
        if "Error" in echo: s.errors.append((cmd, echo))

# STAGE STATE IS AN INPUT TO EVERY Record. "Sneak Time 0" sets a TIME - it
# clears nothing. Use "Group 10 Sneak Time 0", which actually sneaks the whole
# rig back to background, and release the cue list before building. Otherwise
# whatever is on stage when this runs gets recorded into the target.
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cues", type=int, nargs="*")
    a = ap.parse_args()
    rows = [r for r in DESIGN if not a.cues or r[0] in a.cues]
    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = B_(conn, a.dry_run)

    # Release the cue list first - Record captures the stage.
    b.send("Go_To_Cue Out")
    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")
    for cue,label,cf,cm,cb,cmv,cba,foh,fbm,haze in rows:
        print(f"  cue 1/{cue:<5} {label:<12} front={cf} mid={cm} back={cb} mvr={cmv} bars={cba} haze={haze}%")
        b.send(FX_STOP)
        b.send("Group 10 Sneak Time 0")
        # NEVER combine At <level> with Color_Palette in one command - the level
        # applies, the palette is silently dropped, and the echo reports success.
        for zone, lvl, cp in ((FRONT,LVL['front'],cf), (MID,LVL['mid'],cm),
                              (BACK,LVL['back'],cb),   (SLIM,LVL['slim'],cb),
                              (BARS,LVL['bars'],cba)):
            b.send(f"Chan {zone} At {lvl}")
            b.send(f"Chan {zone} Color_Palette {cp}")
        for zone, lvl, fp in ((OH,LVL['oh'],foh), (BM,LVL['bm'],fbm)):
            b.send(f"Chan {zone} At {lvl}")
            if zone == OH:
                # Colour WHEEL, not colour mixing - see WHEEL above.
                b.send(f"Chan {zone} Color_Select {WHEEL[cmv]}")
            else:
                # The Betoppers are a DIFFERENT wheel - 12 slots, chart unknown
                # - so the Riukoe percentages would land on arbitrary colours.
                # Open is slot 0 on essentially every wheel, so park them there
                # until someone reads the real chart off the fixture.
                b.send(f"Chan {zone} Color_Select 0")
            b.send(f"Chan {zone} Focus_Palette {fp}")
        b.send(f"Chan {HAZE} At {haze}")
        b.send(f"Record Cue 1 / {cue} Label {label}", confirm=True)
        if cue in NOTES: b.send(f"Cue 1 / {cue} Notes {NOTES[cue]}")
    b.send("Group 10 Sneak Time 0")
    if conn:
        conn.send("/eos/key/save_show",1); conn.send("/eos/key/save_show",0); time.sleep(1.0); conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for c,e in b.errors[:8]: print(f"  FAILED: {c}\n          {e[:70]}")
    return 1 if b.errors else 0

if __name__ == "__main__":
    sys.exit(main())
