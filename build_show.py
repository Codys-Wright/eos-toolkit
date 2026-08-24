#!/usr/bin/env python3
"""
Build cue list 1 for the PopStars concert, from the run sheet.

  Order of Show _ PopStars Concert 2026-08.txt

STRUCTURE. Acts are numbered by IDENTITY and sequenced by LINKS, so adding a
song or reordering an act never means renumbering anything:

    act base   100 200 300 400 500 600      one per group, video cue blocked
    song       base + 10, 20, 30, 40...     room for ten songs per act
    sub-cue    base + song + 1..9           blackouts, builds, holds
    act out    base + 90                    links to the next act's base

Every cue carries a LINK to the next one. To insert a song, record it in a gap
and re-point two links. To move an act, change one link. Nothing renumbers.

LIGHTING NOTES from the run sheet are encoded as sub-cues, not as busking:
  GR1  lights black out, back on when V1 starts
  AUB1 lights down, back on when V1 starts
  P31  lights down while they get stools, back on once the song starts
  P32  lights dim until the song starts
  TRI1 STROBE during "mwahhh"  -> busked on fader 1, noted in the cue
  TRI2 lots of red
  KK1  lots of pink
  PS1  lots of red, then BLACKOUT held until the next song
  PS2  lots of blue, soft, builds at the end
  PS3  last song - big

  python3 build_show.py --host 10.0.0.5 --dry-run
  python3 build_show.py --host 10.0.0.5 --cues 110 111
"""
import argparse, sys, time
import eosdump as E

# --- zones (groups) ---------------------------------------------------------
WASH, CANS, STRIP, SLIM = 1, 2, 4, 5
OH, BM = 7, 8
FRONT, MID, BACK = 16, 17, 19
HAZE = "Chan 100 Thru 101"

# colour palettes 1-25
RED,ORANGE,AMBER,YELLOW,LIME,GREEN,EMERALD,TEAL,CYAN,SKY = range(1, 11)
AZURE,BLUE,DEEPBLUE,INDIGO,VIOLET,PURPLE,MAGENTA,HOTPINK,ROSE,BLUSH = range(11, 21)
WHITE,WARMWHITE,COOLWHITE,LAVENDER,PEACH = range(21, 26)

# focus palettes 1-20
F_STRAIGHT,F_PARA,F_FAN,F_CROSS,F_WALLS = 1,2,3,4,5
F_FANAUD,F_SPLIT,F_ZIGZAG,F_DS,F_DRUMS = 6,7,8,9,10
F_CENTRE,F_USC,F_SL,F_SR,F_AUD = 11,12,13,14,15


def look(front, back, fp, fl=85, bl=90, sl=70, cans=0, hz=40):
    """A stage look: front colour, back colour, mover focus, levels.

    `cans` is the audience-facing par cans (group 2) - deliberately separate and
    normally 0. They point at people; only raise them on purpose.
    """
    c = [f"Group {FRONT} At {fl}",      f"Group {FRONT} Color_Palette {front}",
         f"Group {MID} At {max(fl-15,0)}", f"Group {MID} Color_Palette {front}",
         f"Group {BACK} At {bl}",       f"Group {BACK} Color_Palette {back}",
         f"Group {SLIM} At {sl}",       f"Group {SLIM} Color_Palette {back}",
         f"Group {STRIP} At {sl}",      f"Group {STRIP} Color_Palette {front}",
         f"Group {OH} At 100",          f"Group {OH} Focus_Palette {fp}",
         f"Group {BM} At 100",          f"Group {BM} Focus_Palette {fp}",
         # STROBE MODE 25 = no strobe on these movers. Without it they fall
         # back to the profile's home value and every cue strobes - the cues
         # were never wrong, the parameter was simply never set. Note this
         # does NOT show up in the encoder read-back, so it cannot be verified
         # over OSC; confirm by eye.
         # different per fixture type - 25 closes the Riukoe shutter
         f"Group {OH} Strobe_Mode 63",  f"Group {BM} Strobe_Mode 25"]
    if cans:
        c += [f"Group {CANS} At {cans}", f"Group {CANS} Color_Palette {front}"]
    c.append(f"{HAZE} At {hz}")
    return c


def dark(hz=35):
    """Blackout that keeps the haze, so the room still reads as alive."""
    return ["Group 10 At 0", f"{HAZE} At {hz}"]


# (cue, label, time, link, commands, note)
SHOW = [
 (  1, "PRESHOW",        3,  10, look(AZURE, DEEPBLUE, F_STRAIGHT, 25, 30, 20, 0, 40),
     "Preshow video playing. Low and cool, nothing moving"),
 ( 10, "WELCOME Marisa", 3, 100, look(WARMWHITE, AMBER, F_CENTRE, 80, 45, 45, 0, 30),
     "Marisa on stage. Warm and clean, faces first, nothing distracting"),

 # ---------------- GLITTER RIOT ----------------
 (100, "GR VIDEO",       2, 110, dark(35),
     "Intro video Get Ready for PopStars. Stage dark, screen owns the room"),
 (110, "GR1 BLACKOUT",   0, 111, dark(35),
     "Heads Will Roll - hold blackout, GO the next cue the moment V1 starts"),
 (111, "GR1 Heads Roll", 1, 120, look(RED, MAGENTA, F_CROSS, 90, 95, 80, 0, 50),
     "Snap up on V1. Hard red and magenta, crossed beams. Biggest opener energy"),
 (120, "GR2 Circus",     2, 130, look(YELLOW, MAGENTA, F_FAN, 90, 90, 80, 0, 45),
     "Circus - Lily on yellow mic. Bold and playful, wide fan"),
 (130, "GR3 Dance Night",2, 140, look(HOTPINK, PURPLE, F_ZIGZAG, 90, 95, 80, 0, 50),
     "Dance The Night - Leilani on green mic. Glam pink, sawtooth beams"),
 (140, "GR4 Wanna Dance",2, 190, look(WARMWHITE, AMBER, F_FANAUD, 95, 90, 85, 0, 45),
     "I Wanna Dance With Somebody - Ari. Warm party, beams out over the house"),
 (190, "GR OUT",         1, 200, dark(35),
     "Quick blackout after the last song"),

 # ---------------- THE AUBVIS ----------------
 (200, "AUB VIDEO",      2, 210, dark(35),
     "PopStars Highlight Video 1:30"),
 (210, "AUB1 DOWN",      0, 211, dark(30),
     "From The Start - track takes a few extra seconds. Hold here until V1"),
 (211, "AUB1 From Start",2, 220, look(PEACH, AMBER, F_CENTRE, 70, 60, 55, 0, 40),
     "Aubrey. Laufey - soft, warm, intimate. Keep it small and close"),
 (220, "AUB2 Mr Predict",3, 290, look(LAVENDER, AZURE, F_CENTRE, 65, 65, 50, 0, 45),
     "Violet on yellow mic. Soft piano ballad, cooler than the first"),
 (290, "AUB OUT",        1, 300, dark(35), "Quick blackout"),

 # ---------------- POP TH3ORY ----------------
 (300, "P3 VIDEO",       2, 310, dark(35), "Video Bumper 3, 0:30"),
 (310, "P3-1 STOOLS",    0, 311, dark(30),
     "Lights down while they set stools. GO when the song starts"),
 (311, "P3-1 Midnight",  2, 315, look(DEEPBLUE, INDIGO, F_CENTRE, 75, 85, 60, 0, 50),
     "Midnight Sun. Deep blue, seated, moody and still"),
 (315, "P3 TRANS 1",     3, 321, look(INDIGO, VIOLET, F_CENTRE, 25, 35, 20, 0, 45),
     "Transition music. Lights dim through it - this IS the dim before You Stole The Show"),
 (321, "P3-2 Stole Show",2, 325, look(PURPLE, VIOLET, F_CROSS, 80, 90, 65, 0, 50),
     "Jewel purple, crossed. Builds up out of the transition"),
 (325, "P3 TRANS 2",     3, 330, look(VIOLET, PURPLE, F_CENTRE, 25, 35, 20, 0, 45),
     "Second transition music piece. Same low hold, ready for Gabriela"),
 (330, "P3-3 Gabriela",  2, 390, look(MAGENTA, HOTPINK, F_FAN, 95, 95, 80, 0, 45),
     "Gabriela - KATSEYE. Hot magenta, wide, the big one of the set"),
 (390, "P3 OUT",         1, 400, dark(35), "Quick blackout"),

 # ---------------- TRIFECTA ----------------
 (400, "TRI VIDEO",      2, 410, dark(35), "Bumper 4 Rockstars Rising. Purple group walks on"),
 (410, "TRI1 Everybody", 2, 420, look(DEEPBLUE, WHITE, F_CROSS, 90, 95, 80, 0, 55),
     "Everybody - Backstreet Boys. STROBE ON THE MWAHHH - fader 1, bump it"),
 (420, "TRI2 Burning Up",2, 430, look(RED, RED, F_FAN, 95, 100, 85, 40, 55),
     "Burning Up - LOTS OF RED. Cans in at 40 for heat. Hottest look in the show"),
 (430, "TRI3 Bye Bye",   2, 490, look(WHITE, AZURE, F_ZIGZAG, 100, 95, 85, 0, 50),
     "Bye Bye Bye - crisp white and blue, punchy and sharp"),
 (490, "TRI OUT",        1, 500, dark(35), "Quick blackout"),

 # ---------------- KAAT KREW ----------------
 (500, "KK VIDEO",       2, 510, dark(35), "Bumper 5 KAAT Krew Intro 0:30"),
 (510, "KK1 Me My Girls",2, 520, look(HOTPINK, ROSE, F_FAN, 95, 95, 85, 0, 45),
     "Me and My Girls - A LOT OF PINK. Full pink wash, wide and bright"),
 (520, "KK2 Beautiful",  2, 530, look(WARMWHITE, YELLOW, F_FANAUD, 95, 90, 80, 0, 40),
     "What Makes You Beautiful. Bright, warm, open - beams out to the crowd"),
 (530, "KK3 Baby",       2, 590, look(CYAN, AZURE, F_ZIGZAG, 95, 90, 80, 0, 45),
     "Baby. Cool pop blue, lots of movement"),
 (590, "KK OUT",         1, 600, dark(35), "Quick blackout"),

 # ---------------- PINK SPARK ----------------
 (600, "PS VIDEO",       2, 610, dark(35), "Pink Spark Intro 0:30. They walk on and take places"),
 (610, "PS TALKING",     2, 620, look(WARMWHITE, BLUSH, F_CENTRE, 70, 50, 45, 0, 30),
     "Talking moment - recording is on one file. Soft and warm, let them speak"),
 (620, "PS1 Que Hiciste",2, 629, look(RED, RED, F_CROSS, 95, 100, 85, 50, 55),
     "Que Hiciste - LOTS OF RED. Cans in. Drive it hard"),
 (629, "PS1 BLACKOUT",   1, 630, dark(40),
     "HOLD BLACKOUT until the next song starts. This is the red-into-blue moment"),
 (630, "PS2 I Love You", 3, 631, look(DEEPBLUE, BLUE, F_CENTRE, 60, 70, 50, 0, 50),
     "I Love You - LOTS OF BLUE. Start soft and small"),
 (631, "PS2 BUILD",      6, 640, look(BLUE, AZURE, F_FAN, 95, 100, 85, 0, 60),
     "Grows at the end - take this on the final chorus. Six second build"),
 (640, "PS3 No Mountain",2, 690, look(WARMWHITE, MAGENTA, F_FANAUD, 100, 100, 90, 30, 55),
     "Aint No Mountain - LAST SONG, all the kids on stage. Everything, have fun"),
 (690, "PS OUT",         2, 700, dark(35), "Out of the last song"),

 # ---------------- CLOSING ----------------
 (700, "BOWS",           2, 710, look(WARMWHITE, AMBER, F_FANAUD, 100, 95, 85, 0, 40),
     "All kids on stage. Marisa speaks, bows and pictures. Bright and even, faces read"),
 (710, "HOUSE LIGHTS",   3,   0, look(WARMWHITE, WARMWHITE, F_CENTRE, 100, 100, 90, 60, 0),
     "Closing remarks and dismissal. House up for exit music, haze off"),
]

BLOCKED = {100, 200, 300, 400, 500, 600}     # act videos: reorderable
FX_STOP = "Chan 1 Thru 101 Effect"


class B:
    def __init__(s, conn, dry): s.c, s.dry, s.n, s.errors = conn, dry, 0, []
    def _echo(s, wait=4.0, idle=0.35):
        end, last, e = time.time()+wait, time.time(), ""
        while time.time() < end:
            m = s.c.recv()
            if m:
                last = time.time()
                for a, g in m:
                    if a == "/eos/out/cmd" and g: e = str(g[0])
            elif time.time()-last > idle: break
        return e
    def send(s, cmd, confirm=False, tolerate=()):
        s.n += 1
        if s.dry:
            print(f"      {cmd}"); return
        s.c.send("/eos/newcmd", cmd + "#")
        e = s._echo()
        if "Please Confirm" in e:
            s.c.send("/eos/key/enter",1); s.c.send("/eos/key/enter",0); e = s._echo()
        if "Error" in e and not any(t in e for t in tolerate):
            s.errors.append((cmd, e)); print(f"  !! {cmd}\n     {e}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cues", type=int, nargs="*")
    a = ap.parse_args()

    rows = [r for r in SHOW if not a.cues or r[0] in a.cues]
    conn = None if a.dry_run else E.Conn(a.host, a.port, timeout=8.0)
    b = B(conn, a.dry_run)

    # Record captures the STAGE. Clear it, or the show bleeds into itself.
    b.send("Go_To_Cue Out")
    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")

    # Remove show cues the run sheet no longer has - the old structure gave
    # every act three songs, and this one does not. Utility cues live at 1000+
    # and are deliberately untouched.
    if not a.cues:
        planned = {r[0] for r in SHOW}
        import eosdump as _E
        stale = []
        if conn:
            conn.send("/eos/get/cue/1/count")
            end = time.time() + 4
            n = None
            while time.time() < end:
                for ad, g in conn.recv():
                    if ad == "/eos/out/get/cue/1/count" and g: n = int(g[0])
            print(f"  cue list 1 currently holds {n if n is not None else '?'} cues")
        for old_cue in (230, 320):             # orphans from earlier shapes
            if old_cue < 1000 and old_cue not in planned:
                stale.append(old_cue)
        for cue in stale:
            print(f"  removing stale cue 1/{cue} (not in the run sheet)")
            # already gone on a re-run - that is success, not failure
            b.send(f"Delete Cue 1 / {cue}", confirm=True,
                   tolerate=("Does Not Exist",))

    for cue, label, t, link, cmds, note in rows:
        print(f"  cue 1/{cue:<5} {label:<16} time {t}s  -> {link or 'end'}")
        b.send(FX_STOP)
        b.send("Group 10 Sneak Time 0")
        b.send("Group 10 At 0")
        for c in cmds:
            b.send(c)
        # "Record Cue 1/110" fails; the spaces are required (trap 22)
        b.send(f"Record Cue 1 / {cue} Label {label}", confirm=True)
        b.send(f"Cue 1 / {cue} Time {t}")
        if link:
            b.send(f"Cue 1 / {cue} Link {link}")
        if cue in BLOCKED:
            b.send(f"Cue 1 / {cue} Block")
        if note:
            b.send(f"Cue 1 / {cue} Notes {note}")

    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")
    if conn:
        conn.send("/eos/key/save_show", 1); conn.send("/eos/key/save_show", 0)
        end, saved = time.time()+25, None
        while time.time() < end and not saved:
            for addr, args in conn.recv():
                if addr == "/eos/out/event/show/saved": saved = args[0]
        print(f"\n  saved -> {saved or 'NOT CONFIRMED'}")
        conn.close()
    print(f"{b.n} commands, {len(b.errors)} errors")
    for c, e in b.errors: print(f"  FAILED: {c}\n          {e}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
