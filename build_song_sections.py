#!/usr/bin/env python3
"""
Section cues inside a song - verse / chorus / breakdown / build / final.

The show structure (build_show.py) gives every song ONE base look. This adds
the sections underneath it, in the nine free numbers after each song cue, so
adding detail never renumbers anything.

    111  GR1 Heads Roll     the song's base look, from the run sheet
    112-119                 sections, linked in order, last one rejoins 120

LINKS ARE A SECOND PASS. Setting a link to a cue that does not exist yet is
accepted and silently keeps the old value - that bit us on the P3 transitions.
So: record everything, then link everything.

TEMPO DRIVES THE TIMES. At 132 BPM a beat is 0.455s and a bar is 1.818s, so a
four-bar build is 7.3s, not "about seven". Section fade times are written as
bars and converted, which means a tempo change is one number.

  python3 build_song_sections.py --host 10.0.0.5 --song heads --dry-run
"""
import argparse, sys, time
import eosdump as E
from build_show import (look, dark, WASH, CANS, STRIP, SLIM, OH, BM,
                        FRONT, MID, BACK, HAZE, FX_STOP,
                        RED, ORANGE, AMBER, YELLOW, GREEN, CYAN, AZURE, BLUE,
                        DEEPBLUE, INDIGO, VIOLET, PURPLE, MAGENTA, HOTPINK,
                        WHITE, WARMWHITE, COOLWHITE,
                        F_STRAIGHT, F_PARA, F_FAN, F_CROSS, F_WALLS,
                        F_FANAUD, F_SPLIT, F_ZIGZAG, F_DS, F_DRUMS,
                        F_CENTRE, F_SL, F_SR, F_AUD)


def bars(n, bpm):
    """n bars at bpm, in seconds, rounded to a tenth."""
    return round(n * 4 * 60.0 / bpm, 1)


# --- the rig's house style -------------------------------------------------
# Levels are LOW by design. The cue is colour and mood; the white bank on
# faders 11-15 decides who the audience can actually see. Only the genuinely
# huge moments are written bright.

# STROBE MODE IS DIFFERENT PER FIXTURE TYPE. Get this wrong and the fixture
# goes dark rather than erroring:
#   Riukoe overheads (group 7)  -> 63
#   Betopper beams   (group 8)  -> 25
# Both are also PARKED at these values on the console, so they hold regardless
# of cues, subs or presets. Parking is the real fix; setting them in cues is
# belt and braces.
OH_STROBE, BM_STROBE = 63, 25

def oh(fp, gobo=1, lvl=100):
    """Overhead gobo movers: position, gobo, shutter held open."""
    return [f"Group 7 At {lvl}", f"Group 7 Focus_Palette {fp}",
            f"Group 7 Strobe_Mode {OH_STROBE}", f"Group 7 Gobo_Select {gobo}"]

def bm(fp, lvl=100, spin=True, gobo=None):
    """Beam movers. DEFAULT IS THE SLOW SPINNING GOBO - Beam Fx Select 2 with
    Index/Speed at full. That is the house look for these fixtures; pass
    spin=False only when a clean hard beam is specifically wanted."""
    c = [f"Group 8 At {lvl}", f"Group 8 Focus_Palette {fp}",
         f"Group 8 Strobe_Mode {BM_STROBE}"]
    if gobo is not None:
        c.append(f"Group 8 Gobo_Select {gobo}")
    if spin:
        c += ["Group 8 Beam_Fx_Index/Speed Full", "Group 8 Beam_Fx_Select 2"]
    else:
        c.append("Group 8 Beam_Fx_Select 1")
    return c

def wash(front_cp, back_cp, fl, bl, sl, cans=0, hz=45):
    """The coloured bed. Front/mid take one colour, back/slims another."""
    c = [f"Group 16 At {fl}",            f"Group 16 Color_Palette {front_cp}",
         f"Group 17 At {max(fl-10,0)}",  f"Group 17 Color_Palette {front_cp}",
         f"Group 19 At {bl}",            f"Group 19 Color_Palette {back_cp}",
         f"Group 5 At {sl}",             f"Group 5 Color_Palette {back_cp}",
         f"Group 4 At {sl}",             f"Group 4 Color_Palette {front_cp}"]
    if cans:
        c += [f"Group 2 At {cans}", f"Group 2 Color_Palette {front_cp}"]
    c.append(f"Chan 100 Thru 101 At {hz}")
    return c

def sides(cp, lvl):
    """Stage left and right - where the effects go."""
    return [f"Group 11 At {lvl}", f"Group 11 Color_Palette {cp}",
            f"Group 13 At {lvl}", f"Group 13 Color_Palette {cp}"]

def centre(cp, lvl):
    """Centre stage - kept CLEAN. No effects here, ever, in this scheme:
    it is the part of the stage where the audience has to read a face."""
    return [f"Group 12 At {lvl}", f"Group 12 Color_Palette {cp}"]

def rear(cp, lvl, strips=None, cans=0, hz=45):
    c = [f"Group 19 At {lvl}", f"Group 19 Color_Palette {cp}",
         f"Group 5 At {strips if strips is not None else lvl}",
         f"Group 5 Color_Palette {cp}",
         f"Group 4 At {strips if strips is not None else lvl}",
         f"Group 4 Color_Palette {cp}"]
    if cans:
        c += [f"Group 2 At {cans}", f"Group 2 Color_Palette {cp}"]
    c.append(f"Chan 100 Thru 101 At {hz}")
    return c


def fx(group, effect, rate=None, scale=None):
    """An effect baked into the cue, optionally slowed or shrunk.

    RATE AND SCALE ONLY APPLY TO A RUNNING EFFECT. "Effect 903 Rate 40" with
    the effect stopped returns "Effect Not Running" - so the order is start it,
    adjust it, then Record, and the cue captures the override. Editing the
    effect's stored definition instead would change it everywhere.

    The stock mover shapes are authored at scale 25, which on this rig throws
    the overheads around far too hard and too fast. 40/12 is a drift.
    """
    c = [f"Group {group} Effect {effect}"]
    if rate is not None:
        c.append(f"Effect {effect} Rate {rate}")
    if scale is not None:
        c.append(f"Effect {effect} Scale {scale}")
    return c


# How hard the overhead movers should work. Their stock scale of 25 is a
# whip; this is a drift you can leave running under a song.
OH_SLOW = dict(rate=35, scale=10)
OH_MED  = dict(rate=55, scale=18)

SONGS = {
 # =====================================================================
 "heads": dict(
    name="Heads Will Roll", bpm=132, base=111, rejoin=120,
    sections=[
      (111, "HWR Verse 1", 1,
       wash(1, 17, 35, 45, 30, 0, 45) + oh(4, gobo=6) + bm(4) + fx(7, 903, **OH_SLOW),
       "Off with your head. Low and urgent - red over magenta. OH drift on a "
       "slow fig 8, beams on the spinning gobo. Ride WHITE C for the singer"),

      (112, "HWR Chorus 1", 0.25,
       wash(1, 17, 55, 65, 50) + oh(3, gobo=6) + bm(3) + fx(1, 28) + fx(7, 901, **OH_MED),
       "Dance dance dance til youre dead. Snap in, wash chase underneath, "
       "movers fan out. Still not the biggest - save that"),

      (113, "HWR Verse 2", 1,
       wash(1, 16, 35, 45, 30) + oh(8, gobo=9) + bm(8) + fx(7, 906, **OH_SLOW),
       "Second verse. Same low bed, movers sawtooth so it feels different "
       "without getting brighter"),

      (114, "HWR Chorus 2", 0.25,
       wash(1, 17, 60, 70, 55) + oh(3, gobo=6) + bm(3) + fx(1, 28) + fx(8, 909, rate=50, scale=15),
       "Chorus two. A step up on the first - beams ballyhoo underneath the "
       "chase. Getting there, not there yet"),

      (115, "HWR Breakdown", 2,
       wash(1, 13, 20, 30, 20, 0, 60) + oh(11, gobo=1) + bm(1, spin=False)
       + fx(4, 936),
       "Strip it right back. Red over deep blue, movers pull to centre, clean "
       "beams standing straight up in the haze. Strips breathe"),

      (116, "HWR Build", 4,
       wash(1, 17, 60, 75, 60, 20, 60) + oh(3, gobo=6) + bm(3) + fx(1, 28) + fx(7, 901, **OH_MED),
       "Four bar build. Take it EARLY and let it grow into the final chorus"),

      (117, "HWR Final", 0.25,
       wash(21, 1, 95, 100, 90, 60, 60) + oh(6, gobo=6) + bm(6)
       + fx(1, 28) + fx(8, 909, rate=80, scale=30),
       "THE moment. White over red, cans in at 60, beams out over the house. "
       "Everything. Bump STROBE on fader 1 if it needs one more gear"),

      (118, "HWR Out", 1,
       ["Group 10 At 0", "Chan 100 Thru 101 At 40"],
       "Button. Out to haze, ready for Circus"),
    ]),

 # =====================================================================
 "circus": dict(
    name="Circus (Britney Spears)", bpm=115, base=120, rejoin=130,
    sections=[
      (120, "CIR Verse 1", 1,
       wash(4, 17, 35, 45, 30, 0, 45) + oh(11, gobo=4) + bm(11)
       + fx(7, 901, **OH_SLOW),
       "Theres only two types of people. Yellow over magenta, low and cheeky. "
       "OH drifting a slow circle. Ride WHITE C on Lily"),

      (121, "CIR Pre 1", 2,
       wash(4, 18, 45, 55, 40) + oh(3, gobo=4) + bm(3) + fx(7, 940, **OH_MED),
       "Im like the ringleader. Pan sweep starts, lifting into the chorus"),

      (122, "CIR Chorus 1", 0.25,
       wash(4, 17, 55, 65, 50) + oh(3, gobo=7) + bm(3)
       + fx(1, 28) + fx(8, 904, rate=60, scale=20),
       "All eyes on me in the center of the ring. CAN CAN on the beams - the "
       "circus kick. Wash chase underneath"),

      (123, "CIR Verse 2", 1.5,
       wash(2, 16, 35, 45, 30) + oh(8, gobo=9) + bm(8) + fx(7, 903, **OH_SLOW),
       "Second verse, shift to orange over purple so it is not a repeat. "
       "Movers on a slow fig 8, zigzag spread"),

      (124, "CIR Pre 2", 2,
       wash(4, 18, 45, 55, 40) + oh(3, gobo=4) + bm(3) + fx(8, 926, rate=50),
       "Second lift. Beams on the slow sweep this time, not the pan"),

      (125, "CIR Chorus 2", 0.25,
       wash(4, 17, 60, 70, 55, 20) + oh(3, gobo=7) + bm(3)
       + fx(1, 28) + fx(8, 904, rate=70, scale=25) + fx(7, 909, **OH_MED),
       "Chorus two - can can plus overhead ballyhoo, cans just touched in at 20"),

      (126, "CIR Bridge", 2,
       wash(16, 15, 25, 35, 25, 0, 55) + oh(11, gobo=1) + bm(1, spin=False)
       + fx(7, 908, **OH_SLOW),
       "Bridge. Purple and violet, right down. Reverse circle overhead, clean "
       "beams standing in the haze"),

      (127, "CIR Final", 0.25,
       wash(21, 17, 90, 100, 85, 55, 60) + oh(6, gobo=7) + bm(6)
       + fx(1, 28) + fx(7, 909, rate=85, scale=30) + fx(8, 934, rate=75),
       "Last chorus. White over magenta, cans in, ballyhoo overhead and search "
       "light on the beams. This is the big one"),

      (128, "CIR Out", 1,
       ["Group 10 At 0", "Chan 100 Thru 101 At 40"],
       "Button, out to haze. Next is Dance The Night"),
    ]),

 # =====================================================================
 # SIDES GO CRAZY, CENTRE STAYS CLEAN. Every effect is scoped to groups 11
 # and 13 (stage left / right). Group 12 (centre) never gets one, so there is
 # always somewhere the audience can read a face no matter how busy it gets.
 "dance": dict(
    name="Dance The Night (Dua Lipa)", bpm=110, base=130, rejoin=140,
    sections=[
      (130, "DTN Verse 1", 1,
       sides(17, 40) + centre(22, 35) + rear(16, 45, 30, 0, 45)
       + oh(11, gobo=4) + bm(11) + fx(7, 902, **OH_SLOW),
       "Barbie disco. Magenta sides, warm centre so Leilani reads. Slow square "
       "overhead. Centre stays clean all song"),

      (131, "DTN Pre 1", 2,
       sides(18, 50) + centre(22, 40) + rear(16, 55, 35)
       + oh(3, gobo=4) + bm(3) + fx(11, 28) + fx(13, 28),
       "Lift. Chase starts on the SIDES only - centre untouched"),

      (132, "DTN Chorus 1", 0.25,
       sides(18, 60) + centre(22, 45) + rear(9, 65, 45)
       + oh(3, gobo=7) + bm(3) + fx(11, 28) + fx(13, 28)
       + fx(8, 904, rate=65, scale=22),
       "Hot pink sides over cyan back, can can on the beams. Sides busy, "
       "centre calm - push WHITE C if she needs more"),

      (133, "DTN Verse 2", 1.5,
       sides(9, 40) + centre(22, 35) + rear(16, 45, 30)
       + oh(8, gobo=9) + bm(8) + fx(7, 905, **OH_SLOW),
       "Flip the sides to cyan for the second verse. Triangle overhead"),

      (134, "DTN Chorus 2", 0.25,
       sides(18, 65) + centre(22, 50) + rear(9, 70, 50, 20)
       + oh(3, gobo=7) + bm(3) + fx(11, 28) + fx(13, 7)
       + fx(8, 904, rate=75, scale=25) + fx(7, 907, **OH_MED),
       "Chorus two - chase one side, sparkle the other. Reverse square "
       "overhead. Deliberately asymmetric"),

      (135, "DTN Bridge", 2,
       sides(16, 25) + centre(24, 40) + rear(15, 30, 20, 0, 55)
       + oh(11, gobo=1) + bm(1, spin=False) + fx(7, 906, **OH_SLOW),
       "Drop out. Sides right down, CENTRE COMES UP - the one moment the "
       "middle is the brightest thing on stage. Clean beams in haze"),

      (136, "DTN Final", 0.25,
       sides(18, 95) + centre(21, 70) + rear(9, 100, 85, 55, 60)
       + oh(6, gobo=7) + bm(6) + fx(11, 28) + fx(13, 28)
       + fx(7, 909, rate=85, scale=30) + fx(8, 934, rate=80),
       "Everything. Hot pink sides, white centre, cans in, ballyhoo and search "
       "light. Still readable in the middle"),

      (137, "DTN Out", 1,
       ["Group 10 At 0", "Chan 100 Thru 101 At 40"],
       "Button. Next is I Wanna Dance With Somebody"),
    ]),

 # =====================================================================
 # Closes Glitter Riot, so the final chorus has to be the biggest thing in the
 # act. The KEY CHANGE is the moment - everything before it is held back on
 # purpose so there is somewhere left to go.
 "somebody": dict(
    name="I Wanna Dance With Somebody", bpm=119, base=140, rejoin=190,
    sections=[
      (140, "IWD Verse 1", 1,
       sides(3, 40) + centre(22, 40) + rear(2, 45, 30, 0, 40)
       + oh(11, gobo=4) + bm(11) + fx(7, 903, **OH_SLOW),
       "Clock strikes upon the hour. Warm amber, 80s party but held low. "
       "Slow fig 8 overhead. Ari on WHITE C"),

      (141, "IWD Pre 1", 2,
       sides(4, 50) + centre(22, 45) + rear(2, 55, 35)
       + oh(3, gobo=4) + bm(3) + fx(7, 940, **OH_MED),
       "Somebody who, somebody who. Yellow lifts, pan sweep starts"),

      (142, "IWD Chorus 1", 0.25,
       sides(18, 60) + centre(22, 50) + rear(3, 65, 50)
       + oh(3, gobo=7) + bm(3) + fx(11, 28) + fx(13, 28)
       + fx(7, 901, **OH_MED),
       "Oh I wanna dance with somebody. Pink sides over amber, chase on the "
       "sides, circle overhead. Centre stays warm and clean"),

      (143, "IWD Verse 2", 1.5,
       sides(25, 40) + centre(22, 40) + rear(2, 45, 30)
       + oh(8, gobo=9) + bm(8) + fx(7, 905, **OH_SLOW),
       "Second verse - peach sides so it is not a repeat. Triangle overhead"),

      (144, "IWD Chorus 2", 0.25,
       sides(18, 65) + centre(22, 55) + rear(3, 70, 55, 20)
       + oh(3, gobo=7) + bm(3) + fx(11, 28) + fx(13, 7)
       + fx(8, 904, rate=70, scale=22),
       "Chorus two. Chase one side, sparkle the other, can can on the beams. "
       "Cans just in at 20 - still holding back"),

      (145, "IWD Bridge", 2,
       sides(17, 30) + centre(24, 45) + rear(15, 35, 25, 0, 55)
       + oh(11, gobo=1) + bm(1, spin=False) + fx(8, 926, rate=45),
       "Instrumental. Pull way down, centre up, clean beams sweeping slowly "
       "in the haze. Let the room breathe before the lift"),

      (146, "IWD KEY CHANGE", 2,
       sides(4, 75) + centre(21, 65) + rear(3, 85, 70, 35, 60)
       + oh(3, gobo=7) + bm(3) + fx(11, 28) + fx(13, 28)
       + fx(7, 909, **OH_MED),
       "THE KEY CHANGE. Two second lift into it - yellow and white, cans in at "
       "35, everything opens out. Take it right on the modulation"),

      (147, "IWD Final", 0.25,
       sides(18, 100) + centre(21, 80) + rear(3, 100, 90, 70, 65)
       + oh(6, gobo=7) + bm(6) + fx(11, 28) + fx(13, 28)
       + fx(7, 909, rate=90, scale=35) + fx(8, 934, rate=85),
       "Biggest look in Glitter Riot. Cans at 70, beams over the house, "
       "ballyhoo and search light. Bump STROBE on the last hit"),

      (148, "IWD Out", 1,
       ["Group 10 At 0", "Chan 100 Thru 101 At 35"],
       "Quick blackout - end of the Glitter Riot set"),
    ]),
}

# =========================================================================
# THE REST OF THE SHOW, from a template.
#
# Five cues per song - verse / chorus / verse 2 / BIG / out - because that is
# what fits the time. Each song gets its own colour identity and its own pair
# of mover shapes, so no two look the same. Refine any of them later by
# editing the row; the template regenerates.
#
# key, name, bpm, base, rejoin, side, centre, back, alt-side, big, gobo,
#   (verse shape, chorus shape, verse2 shape), note
TEMPLATE = [
 ("start",  "From The Start",         82, 211, 220, 25, 22,  3, 20, 22, 4, (903, 901, 908),
  "Laufey - soft and jazzy. Keep it small and warm all the way through"),
 ("predict","Mr Predictable",         76, 220, 290, 24, 22, 11, 15, 21, 1, (901, 926, 908),
  "Soft piano ballad. NOTE - no Laufey track called Mr Predictable exists; timed as a 76bpm ballad. Check the actual track"),
 ("midnight","Midnight Sun",         151, 311, 315, 13, 22, 14, 16, 21, 6, (903, 902, 906),
  "Deep blue, seated on stools. Moody and still"),
 ("stole",  "You Stole The Show",     88, 321, 325, 16, 22, 15, 13, 21, 9, (908, 905, 903),
  "Jewel purple. Builds out of the transition"),
 ("gabriela","Gabriela",             146, 330, 390, 17, 22, 18, 16, 21, 7, (901, 904, 907),
  "KATSEYE - hot magenta, the big one of the Pop Th3ory set"),
 ("everybody","Everybody",           108, 410, 420, 13, 23, 21, 16, 21, 6, (902, 904, 907),
  "Backstreet Boys. The MWAHHH lands in the A-CAPPELLA BREAKDOWN after the bridge, right before the last chorus slams in - that breakdown into chorus is the biggest cue in the song. Bump STROBE on fader 1"),
 ("burning","Burning Up",            114, 420, 430,  1, 22,  1,  2,  1, 7, (904, 909, 901),
  "LOTS OF RED - hottest look in the show. Cans in on the chorus"),
 ("byebye", "Bye Bye Bye",           172, 430, 490, 21, 23, 11, 12, 21, 9, (907, 902, 940),
  "Crisp white and blue, punchy and sharp. Fast tempo - short fades"),
 ("girls",  "Me And My Girls",       135, 510, 520, 18, 22, 19, 17, 18, 7, (901, 904, 905),
  "A LOT OF PINK. Full pink wash, wide and bright"),
 ("beautiful","What Makes You Beautiful",125, 520, 530, 4, 22, 3, 25, 21, 4, (903, 940, 901),
  "Bright warm and open - beams out to the crowd"),
 ("baby",   "Baby",                  130, 530, 590,  9, 22, 11, 10, 21, 6, (905, 901, 908),
  "Cool pop blue, lots of movement"),
 ("que",    "Que Hiciste",           116, 620, 629,  1, 22,  1,  2,  1, 7, (904, 909, 902),
  "LOTS OF RED. Drive it hard - blackout held after this one"),
 ("iloveyou","I Love You (Eilish)",   68, 630, 640, 12, 22, 13, 11, 12, 1, (926, 901, 903),
  "LOTS OF BLUE. Starts soft and small, gets much bigger at the end"),
 ("mountain","Aint No Mountain (Ross)", 99, 640, 690, 22, 21, 17,  4, 21, 7, (901, 904, 909),
  "LAST SONG, Diana Ross version - spoken build into a gospel climax with a HARD button, not a fade. Hold back until the choir lands"),
]

for _k, _name, _bpm, _base, _rejoin, _side, _ctr, _back, _alt, _big, _gobo, _shapes, _note in TEMPLATE:
    _a, _b, _c = _shapes
    SONGS[_k] = dict(name=_name, bpm=_bpm, base=_base, rejoin=_rejoin, sections=[
      (_base, f"{_k[:3].upper()} Verse 1", 1,
       sides(_side, 40) + centre(_ctr, 38) + rear(_back, 45, 30, 0, 45)
       + oh(11, gobo=_gobo) + bm(11) + fx(7, _a, **OH_SLOW), _note),
      (_base+1, f"{_k[:3].upper()} Chorus 1", 0.25,
       sides(_side, 60) + centre(_ctr, 48) + rear(_back, 65, 48)
       + oh(3, gobo=_gobo) + bm(3) + fx(11, 28) + fx(13, 28)
       + fx(8, _b, rate=65, scale=22),
       "Chorus. Chase on the sides, centre clean so faces read"),
      (_base+2, f"{_k[:3].upper()} Verse 2", 1.5,
       sides(_alt, 40) + centre(_ctr, 38) + rear(_back, 45, 30)
       + oh(8, gobo=_gobo) + bm(8) + fx(7, _c, **OH_SLOW),
       "Second verse - colour shifts so it is not a repeat"),
      (_base+3, f"{_k[:3].upper()} BIG", 0.25,
       sides(_big, 95) + centre(21, 70) + rear(_back, 100, 85, 55, 60)
       + oh(6, gobo=_gobo) + bm(6) + fx(11, 28) + fx(13, 28)
       + fx(7, 909, rate=85, scale=30) + fx(8, 934, rate=80),
       "The big moment. Cans in, beams over the house, ballyhoo and search"),
      (_base+4, f"{_k[:3].upper()} Out", 1,
       ["Group 10 At 0", "Chan 100 Thru 101 At 38"], "Out"),
    ])
    # Midnight Sun and You Stole The Show rejoin at base+4, which is already
    # the Pop Th3ory transition cue. Drop the generated Out so it is not
    # overwritten - the transition already does that job.
    if _rejoin == _base + 4:
        SONGS[_k]["sections"] = SONGS[_k]["sections"][:-1]


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
    ap.add_argument("--host", default="10.0.0.5")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--song", default="heads")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fast", action="store_true",
                    help="only the three cues that matter: base look, the big "
                         "moment, and the out. Section detail comes later.")
    a = ap.parse_args()
    S = SONGS[a.song]
    bpm = S["bpm"]
    # Songs marked full=True keep every cue even in fast mode - their shape
    # IS the point (the Everybody strobe hit, the I Love You swell).
    if a.fast and not S.get("full"):
        # Base look, BIG moment, out. Enough to run the song tonight; the
        # verse/chorus detail can be filled into the gaps afterwards without
        # renumbering, because sections play in order and only the last cue
        # links on.
        rows = S["sections"]
        keep = [rows[0]] + [r for r in rows if r[1].endswith("BIG")] + [rows[-1]]
        seen, uniq = set(), []
        for r in keep:
            if r[0] not in seen:
                seen.add(r[0])
                uniq.append(r)
        S["sections"] = uniq

    print(f"  {S['name']} - {bpm} BPM, 1 bar = {bars(1,bpm)}s")
    conn = None if a.dry_run else E.Conn(a.host, a.port, timeout=8.0)
    b = B(conn, a.dry_run)

    b.send("Go_To_Cue Out")
    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")

    # ---- pass 1: record every section cue
    # CUES TRACK. Only the first cue of a song needs a full state; after that
    # anything unchanged carries forward, so send only the DIFFERENCE. This
    # roughly halves the commands per song, and it also makes each cue contain
    # the MOVE it makes rather than a restatement of the whole rig - which is
    # what you actually want when editing one later.
    prev = None
    for cue, label, nbars, cmds, note in S["sections"]:
        t = bars(nbars, bpm)
        if prev is None:
            send_list = list(cmds)
            b.send(FX_STOP)
            b.send("Group 10 Sneak Time 0")
            b.send("Group 10 At 0")
        else:
            pset = set(prev)
            send_list = [c for c in cmds if c not in pset]
            # effects do NOT track - stop the running ones whenever either cue
            # involves an effect, then start only what this cue asks for
            if any("Effect" in c for c in cmds + prev):
                b.send(FX_STOP)
                send_list = [c for c in cmds if c not in pset or "Effect" in c]
        n_tracked = len(cmds) - len(send_list)
        extra = "" if prev is None else f"   ({len(send_list)} sent, {n_tracked} tracked)"
        print(f"\n  cue 1/{cue}  {label:<16} {nbars} bar = {t}s{extra}")
        for c in send_list:
            b.send(c)
        prev = list(cmds)
        b.send(f"Record Cue 1 / {cue} Label {label}", confirm=True)
        b.send(f"Cue 1 / {cue} Time {t}")
        if note:
            b.send(f"Cue 1 / {cue} Notes {note}")

    # ---- pass 2: ONE link, at the song boundary
    # Cues play in numeric order by default, so the sections need no links -
    # which means a cue can be inserted (or renumbered to a decimal) without
    # re-pointing anything. Only the last section links on to the next song.
    last = S["sections"][-1][0]
    print(f"\n  linking {last} -> {S['rejoin']} (song boundary only)")
    b.send(f"Cue 1 / {last} Link {S['rejoin']}")

    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")
    if conn:
        conn.send("/eos/key/save_show",1); conn.send("/eos/key/save_show",0)
        end, saved = time.time()+25, None
        while time.time()<end and not saved:
            for ad,args in conn.recv():
                if ad=="/eos/out/event/show/saved": saved=args[0]
        print(f"\n  saved -> {saved or 'NOT CONFIRMED'}")
        conn.close()
    print(f"{b.n} commands, {len(b.errors)} errors")
    for c,e in b.errors: print(f"  FAILED: {c}\n          {e}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())


# =========================================================================
# HAND-WRITTEN OVERRIDES - these two songs have a specific shape the template
# cannot express, so they replace the generated version entirely.

# EVERYBODY. The run sheet says STROBE DURING MWAHHH. The kiss lands in the
# a-cappella breakdown after the bridge, and the full band slams back in
# immediately after - so it needs three cues in a row: tension, hit, slam.
SONGS["everybody"] = dict(
  name="Everybody (Backstreet Boys)", bpm=108, base=410, rejoin=420,
  full=True, sections=[
    (410, "EVE Verse 1", 1,
     sides(13, 40) + centre(23, 38) + rear(21, 45, 30, 0, 45)
     + oh(11, gobo=6) + bm(11) + fx(7, 902, **OH_SLOW),
     "Everybody rock your body. Deep blue sides, cool white centre, held low"),
    (411, "EVE Chorus 1", 0.25,
     sides(13, 60) + centre(23, 48) + rear(21, 65, 48)
     + oh(3, gobo=6) + bm(3) + fx(11, 28) + fx(13, 28)
     + fx(8, 904, rate=65, scale=22),
     "Backstreets back alright. Chase the sides, can can the beams"),
    (412, "EVE BREAKDOWN", 2,
     sides(16, 18) + centre(23, 30) + rear(13, 22, 15, 0, 60)
     + oh(11, gobo=1) + bm(1, spin=False),
     "A-CAPPELLA BREAKDOWN. Am I original, am I the only one. Strip it to "
     "almost nothing - clean beams in haze, centre only. Build the tension"),
    (413, "EVE MWAHHH", 0.1,
     sides(21, 100) + centre(21, 100) + rear(21, 100, 95, 90, 60)
     + oh(6, gobo=1) + bm(6) + fx(1, 941),
     "*MWAH* - THE HIT. Everything white, cans at 90, STROBE. Snap in on the "
     "kiss and hold it for a beat. This is the moment in the song"),
    (414, "EVE Final", 0.25,
     sides(13, 95) + centre(21, 75) + rear(21, 100, 85, 60, 60)
     + oh(6, gobo=6) + bm(6) + fx(11, 28) + fx(13, 28)
     + fx(7, 909, rate=85, scale=30) + fx(8, 934, rate=80),
     "Band slams back in. Out of the strobe straight into the last chorus"),
    (415, "EVE Out", 1,
     ["Group 10 At 0", "Chan 100 Thru 101 At 38"], "Out"),
  ])

# I LOVE YOU (Billie Eilish). Slow ballad, ~68 feel. LOTS OF BLUE, starts tiny
# and swells at the end. Effects here must be almost invisible - slow colour
# drift and a long intensity breathe, nothing that reads as "an effect".
SONGS["iloveyou"] = dict(
  name="I Love You (Eilish)", bpm=68, base=630, rejoin=640,
  full=True, sections=[
    (630, "ILY Intro", 4,
     sides(13, 18) + centre(11, 25) + rear(14, 22, 12, 0, 55)
     + oh(11, gobo=1) + bm(1, spin=False) + fx(4, 936),
     "Almost nothing. Deep blue, tiny, one voice. Strips breathing very "
     "slowly. Four bar fade in - let it arrive rather than appear"),
    (631, "ILY Verse", 3,
     sides(12, 30) + centre(11, 35) + rear(13, 35, 20, 0, 55)
     + oh(11, gobo=1) + bm(11, spin=False) + fx(7, 926, rate=25, scale=8),
     "Verse. Barely wider. Movers drifting so slowly you should not notice "
     "them moving, only that the room is alive"),
    (632, "ILY Chorus", 2,
     sides(12, 45) + centre(21, 45) + rear(11, 50, 35, 0, 55)
     + oh(3, gobo=1) + bm(3, spin=False) + fx(1, 910),
     "Chorus opens out. Colour drifting slowly across the wash. Still soft - "
     "there is a long way left to go"),
    (633, "ILY Bridge", 3,
     sides(14, 22) + centre(24, 40) + rear(13, 25, 15, 0, 60)
     + oh(11, gobo=1) + bm(1, spin=False) + fx(4, 936),
     "Strip back down for the bridge. Centre is the brightest thing in the "
     "room. Haze up so the beams read"),
    (634, "ILY SWELL", 8,
     sides(11, 85) + centre(21, 70) + rear(12, 95, 75, 30, 60)
     + oh(6, gobo=1) + bm(6, spin=False) + fx(1, 910) + fx(7, 901, rate=25, scale=12),
     "THE SWELL. Eight bar build - take it at the top of the last chorus and "
     "let it grow the whole way. Wide blue, beams out, still beautiful "
     "rather than loud. The biggest this song ever gets"),
    (635, "ILY Out", 3,
     ["Group 10 At 0", "Chan 100 Thru 101 At 45"],
     "Long slow fade. Do not snap this one"),
  ])
