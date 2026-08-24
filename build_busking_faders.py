#!/usr/bin/env python3
"""
Five pages of busking faders for the Norco rig.

  PAGE 1  (subs  1-10)  FX          - ten effects. No intensity masters here.
  PAGE 2  (subs 41-50)  ZONES       - six stage zones + four fixture families
  PAGE 3  (subs 31,39,40)           - only three usable faders on this console
  PAGE 4  (subs 11-20)  COLOUR FX
  PAGE 5  (subs 21-30)  MOVEMENT

SUB NUMBER IS NOT FADER NUMBER. They coincided by accident on page 1 and the
old version of this script relied on that, which is why pages 2-5 were mapped
by hand and drifted from what this file claimed. Mapping is explicit now:
FADERS below assigns every sub to a (page, slot), and the mapping is asserted
on every run.

Keep slot in 1-10. `Fader 1 / 11 Sub 41` does not error - it silently lands on
page 2 fader 1 and overwrites whatever was there. See trap 20.

  python3 build_busking_faders.py --dry-run
  python3 build_busking_faders.py --pages 1 2
"""
import argparse, sys, time
import eosdump as E

ALL    = "1 Thru 18 + 20 Thru 97"   # skips 19 and 98: patched at address 0, so
                                    # they emit nothing but still render in A3D
PARS   = "1 Thru 48"
COLOUR = "1 Thru 48 + 50 Thru 53 + 90 Thru 97"   # everything with RGB
OH     = "80 Thru 83"                            # gobo movers  = "spots"
BM     = "85 Thru 88"                            # beam movers
MVR    = "80 Thru 83 + 85 Thru 88"
BARS   = "90 Thru 97"
SLIM   = "50 Thru 53"
HAZE   = "100 Thru 101"

# Stopping effects needs a CHANNEL RANGE. "Group 10 Effect" echoes clean, errors
# nothing, and stops nothing - verified by recording probe subs and reading the
# fx list back. Only the Chan form works. See trap 29.
FX_STOP = "Chan 1 Thru 101 Effect"
FRONT  = "1 Thru 2 + 11 Thru 18"
MID    = "3 Thru 10 + 20 Thru 31"
BACK   = "32 Thru 48"          # was 40-48, which disagreed with the BACK zone
                               # in build_song_looks.py. 32-48 is the seam and
                               # everything upstage of it - the two now match.

# Width zones, taken from groups 9/12/10 (Left All / Centre All / Right All).
# PARS ONLY: strips 90-97 and slimpars 50-53 are operator-placed and have no
# recorded x, so there is no honest way to split them left from right yet.
# Measure them and they belong in here.
LEFT   = "3 Thru 4 + 7 Thru 8 + 11 Thru 14 + 20 Thru 23 + 32 Thru 35 + 40 Thru 42"
RIGHT  = "5 Thru 6 + 9 Thru 10 + 15 Thru 18 + 28 Thru 31 + 36 Thru 39 + 46 Thru 48"
CENTR  = "1 Thru 2 + 24 Thru 27 + 43 Thru 45"

# Fader times. Masters get a Manual dwell so the bump flashes while held;
# effects get a soft in/out so colours and positions do not hard-cut.
#   up / dwell / down
# NOT SET HERE: fader mode. The old page 1 FX subs are mode Effect /
# fader_mode I-Master, which is the right behaviour for an effect fader - the
# fader scales the effect rather than acting as a plain HTP master. Every other
# FX sub in the show is Additive / Proportional. No command-line syntax for it
# has been found, so it stays a Tab 36 job by hand. Read `fader_mode` back in
# the dump to see which subs still need it.
TIMES = {
    "master":  (0, "Manual", 0),
    "colour":  (1, "Hold",   1),
    "focus":   (2, "Hold",   2),
    "intens":  (1, "Hold",   1),
}
KIND = {1:"master"}                    # strobe: bump-to-flash, Manual dwell
KIND.update({n:"colour" for n in (2,3,7)})     # RNBOW SMOOT CBUMP
KIND.update({n:"focus"  for n in (4,5,9)})     # OHMOV BMMOV MVBAL
KIND.update({n:"intens" for n in (6,8,10)})    # CHASE SPRKL IFADE
KIND.update({n:"colour" for n in range(11,21)})
KIND.update({n:"focus"  for n in range(21,29)})
KIND.update({n:"intens" for n in (29,30)})
KIND.update({n:"intens" for n in range(31,41)})
KIND.update({n:"master" for n in range(41,51)})

# EVERY EFFECT HERE MUST BE VERIFIED LIVE. An effect can carry a perfect label
# and an empty step table - Eos publishes the label, type and scale over OSC
# but never the step/value table, so a hollow effect reads as a healthy one.
# Run test_effects.py after any change here.
#
# Known dead on this show (label fine, does nothing):
#   2 Chase Rev  3 Chase Bounce  6 Sparkle  9 Fire  413 Step R-Y-B
#   800 Red-Blue  814 Green-Mag  848 Cyan-Orange  856 Mag-Yellow
#   912 Rainbow RGB
# Page 1 previously used 912 for RNBOW and 6 for SPRKL. Now 919 and 7.
# Page 4 slots 15-18 and 20 are still pointed at dead effects - they need
# effects we author ourselves, not more scavenged stock ones.
#
# (sub, label, channels, effect or None -> plain intensity master)
#
# BANKS OF EIGHT. The control surface is a Behringer X-Touch: 8 channel faders
# plus a master. Fader numbers are absolute and continuous (trap 20), so an
# OSC fader bank of 8 pages cleanly through these while the console, set to 20
# per page, shows banks 1-2 and the head of 3 all at once.
BANKS = {
# --- BANK 1, faders 1-8: the eight you always want under your hands --------
1: [( 1,"STROBE",      ALL,   941),   ( 2,"RAINBOW",      COLOUR,919),
    ( 3,"COL SMOOTH",      COLOUR,910),   ( 4,"OH MOVE",      OH,    903),
    ( 5,"BM MOVE",      BM,    909),   ( 6,"PAR CHASE",      PARS,   28),
    ( 7,"SPARKLE",      PARS,     7),  ( 8,"INT FADE",      PARS,   936)],

# --- BANK 2, faders 9-16: THE STAGE, LAID OUT LEFT TO RIGHT ----------------
# Fader 1 of the bank is stage left, fader 8 is stage right, so your hand
# position matches the part of the stage it controls. Depth sits in the
# middle, downstage to upstage, with the two whole-rig masters before RIGHT.
41: None,   # placeholder so the dict literal below stays readable
2: [(41,"LEFT",   LEFT, None),  (42,"FRONT",  FRONT,None),
    (43,"MID",    MID,  None),  (44,"BACK",   BACK, None),
    (45,"CENTRE",  CENTR,None),  (46,"MOVERS",  MVR,  None),
    (47,"HAZE",   HAZE, None),  (48,"RIGHT",  RIGHT,None)],

# --- BANK 3, faders 17-24: colour FX ---------------------------------------
3: [(11,"RAINBOW WD",COLOUR,919),  (12,"RAINBOW LG", COLOUR,917),
    (13,"COL FADE",COLOUR,911),  (14,"COL BUMP", COLOUR,913),
    (15,"STEP RGB", COLOUR,500),
    # The mover colour-wheel equivalents. Movers have a wheel, not colour
    # mixing, so no rainbow will ever run on them - these step Color Select
    # between slot centres instead. TODO means the effect is not authored yet;
    # the builder SKIPS these rather than recording them as silent intensity
    # masters, which is what a None here would do.
    (16,"WHEEL SPIN", MVR, "TODO"), (17,"WHEEL BUMP", MVR, "TODO"),
    (18,"WHEEL ALT", MVR, "TODO")],

# --- BANK 4, faders 25-32: movement ----------------------------------------
4: [(21,"OH CIRCLE",OH,  901),  (22,"OH SQUARE",OH,  902),
    (23,"OH SPIRAL",OH,  906),  (24,"OH TRIANGL",OH,  905),
    (25,"BM SEARCH",BM,  934),  (26,"BM CAN CAN",BM,  904),
    (27,"BM SWEEP",BM,  926),  (28,"MVR BALLY",MVR, 909)],

# --- BANK 5, faders 33-40: overflow masters --------------------------------
5: [(51,"WASH", PARS, None), (52,"BARS", BARS,None),
    (53,"SLIMPARS",SLIM, None), (54,"OH INTENS",OH,  None),
    (55,"BM INTENS",BM,   None)],
}
del BANKS[41]
PAGES = BANKS          # the builder still calls them pages

# Console faders-per-page. A "page" is only a WINDOW onto one continuous list
# of fader numbers (trap 20), so this is the single place that knowledge lives.
# Change it here when you change it in Setup, and every mapping re-derives.
# THE CONSOLE'S FADER PAGE SIZE IS 10. Showing 20 faders on screen is a
# display setting and does not change this. Slot numbers continue past the page
# size rather than erroring, so Fader 2 / 16 is fader 26, not "page 2 slot 16".
#     absolute fader = (page - 1) * 10 + slot
PAGE_SIZE = 10

# This console's fader grid is NOT uniform. Probed by parse-checking a mapping
# at every slot: 1-16 and 21 and 31-40 accept one, 17-20 and 22-30 do not.
# 27 usable faders, in three runs.
USABLE = set(range(1, 17)) | {21} | set(range(31, 41))

# Where each 8-wide bank starts, in absolute fader numbers. Banks 1 and 2 sit
# in the first run; bank 3 goes to 33-40, which is both contiguous-usable and
# exactly page 5 of an 8-wide OSC fader bank on the X-Touch.
BANK_BASE = {1: 1, 2: 9, 3: 33}

# How far to sweep when clearing mappings the plan no longer claims.
TIDY_UPTO = 40

def fader_of(bank, slot):
    """Absolute fader number for a slot in an 8-wide bank."""
    return BANK_BASE[bank] + slot - 1

def page_slot(fader):
    """Absolute fader number -> the (page, slot) the command line wants."""
    return (fader - 1) // PAGE_SIZE + 1, (fader - 1) % PAGE_SIZE + 1

# sub -> absolute fader number
FADERS = {}
for _bank, _rows in BANKS.items():
    if _bank not in BANK_BASE:
        continue          # no usable run of faders assigned to this bank yet
    for _i, (_sub, _lab, _ch, _fx) in enumerate(_rows):
        _f = fader_of(_bank, _i + 1)
        assert _f in USABLE, f"fader {_f} is reserved on this console"
        if _fx == "TODO":
            # Not authored yet, so the plan does NOT claim this fader - which
            # lets the tidy pass clear whatever the old layout left there.
            # Claiming it while skipping the build is how stale mappings
            # survived a re-layout twice.
            continue
        FADERS[_sub] = _f

class B:
    """A flat 0.16s sleep was not enough. Two things went wrong with it:
    the echo read caught whatever was mid-flight after a big state change
    (spurious "Error" on a command that was fine), and commands were fired
    before the console had finished acting on the previous one - so an effect
    stop had not taken hold by the time the next Record ran, and effects
    accumulated into every sub. Wait for the reply stream to go idle instead,
    which is what every other builder in this repo does."""

    def __init__(s, conn, dry): s.c, s.dry, s.n, s.errors = conn, dry, 0, []

    def _echo(s, wait=3.0, idle=0.25):
        end, last, echo = time.time() + wait, time.time(), ""
        while time.time() < end:
            msgs = s.c.recv()
            if msgs:
                last = time.time()
                for a, g in msgs:
                    if a == "/eos/out/cmd" and g: echo = str(g[0])
            elif time.time() - last > idle:
                break
        return echo

    def send(s, cmd, confirm=False, tolerate=(), settle=0.0):
        s.n += 1
        if s.dry:
            print(f"    {cmd}"); return
        s.c.send("/eos/newcmd", cmd + "#")
        echo = s._echo()
        if "Please Confirm" in echo:
            if not confirm:
                s.errors.append((cmd, "unexpected confirm")); return
            s.c.send("/eos/key/enter", 1); s.c.send("/eos/key/enter", 0)
            echo = s._echo()
        if "Error" in echo and not any(t in echo for t in tolerate):
            s.errors.append((cmd, echo)); print(f"  !! {cmd}\n     {echo}", file=sys.stderr)
        if settle: time.sleep(settle)

# STAGE STATE IS AN INPUT TO EVERY Record. "Sneak Time 0" sets a TIME - it
# clears nothing. Use "Group 10 Sneak Time 0", which actually sneaks the whole
# rig back to background, and release the cue list before building. Otherwise
# whatever is on stage when this runs gets recorded into the target.
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pages", type=int, nargs="*", default=sorted(PAGES))
    ap.add_argument("--no-tidy", dest="tidy", action="store_false",
                    help="leave fader mappings the plan does not claim")
    a = ap.parse_args()
    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = B(conn, a.dry_run)
    # Release the cue list first - Record captures the stage.
    b.send("Go_To_Cue Out")
    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")
    # UNMAP WHAT THE PLAN NO LONGER CLAIMS. The builder maps faders but never
    # used to clear them, so a re-layout left the previous assignment sitting
    # on every fader the new plan does not reach - four stale faders survived
    # the move to banks of eight, and only verify_faders.py caught them.
    # "Fader P / F Unmap" and "... Delete" are both syntax errors; the verb is
    # Delete Fader P / F.
    if a.tidy:
        planned = set(FADERS.values())
        for fader in range(1, TIDY_UPTO + 1):
            if fader not in planned:
                pg_, slot = page_slot(fader)
                b.send(f"Delete Fader {pg_} / {slot}", confirm=True,
                       tolerate=("Does Not Exist", "Nothing To Delete"))

    for pg in a.pages:
        rows = PAGES[pg]
        lo, hi = rows[0][0], rows[-1][0]
        fl = [FADERS[s] for s, *_ in rows if s in FADERS]
        span = f"faders {min(fl)}-{max(fl)}" if fl else "unmapped"
        print(f"\nBANK {pg}  (subs {lo}-{hi})  -> {span}")
        b.send(f"Delete Sub {lo} Thru {hi}", confirm=True, tolerate=("Does Not Exist",))
        for sub, label, chans, fx in rows:
            if fx == "TODO":
                print(f"  sub {sub:>3}  {label:<14} SKIPPED - effect not authored yet")
                continue
            kind = "master" if fx is None else f"fx {fx}"
            print(f"  sub {sub:>3}  {label:<14} {kind:<8} {chans}")
            # A sneak clears CHANNEL data. It does not stop EFFECTS -
            # they keep running and Record captures every one still
            # active, so without this each sub inherits the effects of
            # all the subs recorded before it. "Group 10 Effect" with no
            # effect number is Eos's stop.
            b.send(FX_STOP, settle=0.4)
            b.send("Group 10 Sneak Time 0", settle=0.2)
            # FX subs need a base level AND fader_mode = I-Master.
            #
            # Base level only:  subs are HTP, so the recorded 100 competes with
            #   the effect's own output and wins - PAR CHASE looked like "turn
            #   everything on" while the chase ran invisibly underneath.
            # No base level:    Absolute effects like STROBE still work, but
            #   StepBased chases and INT FADE have no intensity reference and
            #   output nothing at all.
            #
            # I-Master resolves it: the fader scales the EFFECT instead of
            # asserting a level. It is NOT scriptable - "Sub N Effect_Master"
            # parses, echoes clean and leaves fader_mode at Proportional
            # (trap 18). Set it by hand in Tab 36 for every sub listed by
            #     python3 -c "import json;d=json.load(open('show.json'));
            #     print([s['target'] for s in d['subs']
            #            if s.get('fx') and s.get('fader_mode')!='I-Master'])"
            b.send(f"Chan {chans} At Full")
            if fx is not None:
                b.send(f"Chan {chans} Effect {fx}")
            b.send(f"Record_Only Sub {sub}", confirm=True)
            b.send(f"Sub {sub} Label {label}")
            up, dwell, dn = TIMES[KIND.get(sub, "master")]
            b.send(f"Sub {sub} Time {up} Time {dwell} Time {dn}")
            # Map it. Without this the sub exists but sits on whatever fader
            # the console last had it on - which is how the documented layout
            # and the real one drifted apart.
            if sub in FADERS:
                fader = FADERS[sub]
                pg_, slot = page_slot(fader)
                assert 1 <= slot <= PAGE_SIZE, f"slot {slot} outside the page"
                b.send(f"Fader {pg_} / {slot} Sub {sub}")
            else:
                print(f"      (unmapped - no fader slot for sub {sub})")
    b.send("Group 10 Sneak Time 0")
    if conn:
        conn.send("/eos/key/save_show", 1); conn.send("/eos/key/save_show", 0); time.sleep(1.0)
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors: print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0

if __name__ == "__main__":
    sys.exit(main())
