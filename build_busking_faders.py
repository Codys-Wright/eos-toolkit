#!/usr/bin/env python3
"""
Five pages of busking faders for the Norco rig. Sub N lives on fader N, so
subs 1-10 are page 1, 11-20 page 2, and so on.

  PAGE 1  (1-10)   ESSENTIALS  - the six effects you reach for, plus four
                                 intensity masters. Nothing else needed to
                                 put light on stage.
  PAGE 2  (11-20)  COLOUR FX   - rainbows, fades and steps across the rig
  PAGE 3  (21-30)  MOVEMENT    - mover shapes, plus intensity effects
  PAGE 4  (31-40)  CHASES      - step-based, designed to stack with page 2/3
  PAGE 5  (41-50)  CATEGORIES  - one intensity master per fixture family

  python3 build_busking_faders.py --dry-run
  python3 build_busking_faders.py --pages 1 5
"""
import argparse, sys, time
import eosdump as E

ALL    = "1 Thru 98"
PARS   = "1 Thru 48"
COLOUR = "1 Thru 48 + 50 Thru 53 + 90 Thru 97"   # everything with RGB
OH     = "80 Thru 83"                            # gobo movers  = "spots"
BM     = "85 Thru 88"                            # beam movers
MVR    = "80 Thru 83 + 85 Thru 88"
BARS   = "90 Thru 97"
SLIM   = "50 Thru 53"
HAZE   = "100 Thru 101"
FRONT  = "1 Thru 2 + 11 Thru 18"
MID    = "3 Thru 10 + 20 Thru 31"
BACK   = "40 Thru 48"

# Fader times. Masters get a Manual dwell so the bump flashes while held;
# effects get a soft in/out so colours and positions do not hard-cut.
#   up / dwell / down
TIMES = {
    "master":  (0, "Manual", 0),
    "colour":  (1, "Hold",   1),
    "focus":   (2, "Hold",   2),
    "intens":  (1, "Hold",   1),
}
KIND = {1:"master"}                    # strobe: bump-to-flash
KIND.update({n:"colour" for n in (2,3)})
KIND.update({n:"focus"  for n in (4,5)})
KIND.update({6:"intens"})
KIND.update({n:"master" for n in range(7,11)})
KIND.update({n:"colour" for n in range(11,21)})
KIND.update({n:"focus"  for n in range(21,29)})
KIND.update({n:"intens" for n in (29,30)})
KIND.update({n:"intens" for n in range(31,41)})
KIND.update({n:"master" for n in range(41,51)})

# (sub, label, channels, effect or None -> plain intensity master)
PAGES = {
1: [( 1,"STROBE",     ALL,    11),   ( 2,"RAINBOW",    COLOUR,912),
    ( 3,"COL SMOOTH", COLOUR,910),   ( 4,"OH MOVE",    OH,    903),
    ( 5,"BM MOVE",    BM,    909),   ( 6,"PAR CHASE",  PARS,   28),
    ( 7,"SPOT",       MVR,   None),  ( 8,"FRONT",      FRONT, None),
    ( 9,"WASH",       PARS,  None),  (10,"HAZE",       HAZE,  None)],
2: [(11,"Rainbow Wide",COLOUR,919),  (12,"Rainbow Lg", COLOUR,917),
    (13,"Colour Fade", COLOUR,911),  (14,"Colour Bump",COLOUR,913),
    (15,"Red-Blue",    COLOUR,800),  (16,"Green-Mag",  COLOUR,814),
    (17,"Cyan-Orange", COLOUR,848),  (18,"Mag-Yellow", COLOUR,856),
    (19,"Step RGB",    COLOUR,500),  (20,"Step R-Y-B", COLOUR,413)],
3: [(21,"OH Circle",  OH,   901),    (22,"OH Square",  OH,   902),
    (23,"OH Spiral",  OH,   906),    (24,"OH Triangle",OH,   905),
    (25,"BM Search",  BM,   934),    (26,"BM Can Can", BM,   904),
    (27,"BM Sweep",   BM,   926),    (28,"All Mvr Bally",MVR,909),
    (29,"Int Strobe", PARS, 939),    (30,"Int Fade",   PARS, 936)],
4: [(31,"Chase Fwd",  PARS,   1),    (32,"Chase Rev",  PARS,   2),
    (33,"Chase Bounce",PARS,  3),    (34,"Chase Build",PARS,   4),
    (35,"Chase L-R",  PARS,  28),    (36,"Chase Ctr Out",PARS,30),
    (37,"Sparkle",    PARS,   6),    (38,"Twinkle",    PARS,   7),
    (39,"Fire",       PARS,   9),    (40,"Lightning",  PARS,   8)],
5: [(41,"WASH",   PARS, None),  (42,"SLIMS",  SLIM, None),
    (43,"SPOTS",  OH,   None),  (44,"BEAMS",  BM,   None),
    (45,"BARS",   BARS, None),  (46,"HAZE",   HAZE, None),
    (47,"FRONT",  FRONT,None),  (48,"MID",    MID,  None),
    (49,"BACK",   BACK, None),  (50,"RIG ALL",ALL,  None)],
}

class B:
    def __init__(s, conn, dry): s.c, s.dry, s.n, s.errors = conn, dry, 0, []
    def send(s, cmd, confirm=False, tolerate=()):
        s.n += 1
        if s.dry:
            print(f"    {cmd}"); return
        s.c.send("/eos/newcmd", cmd + "#"); time.sleep(0.16)
        echo = ""
        for a, g in s.c.recv():
            if a == "/eos/out/cmd" and g: echo = g[0]
        if "Please Confirm" in echo:
            if not confirm:
                s.errors.append((cmd, "unexpected confirm")); return
            s.c.send("/eos/key/enter", 1); s.c.send("/eos/key/enter", 0); time.sleep(0.2)
            echo = ""
            for a, g in s.c.recv():
                if a == "/eos/out/cmd" and g: echo = g[0]
        if "Error" in echo and not any(t in echo for t in tolerate):
            s.errors.append((cmd, echo)); print(f"  !! {cmd}\n     {echo}", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pages", type=int, nargs="*", default=sorted(PAGES))
    a = ap.parse_args()
    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = B(conn, a.dry_run)
    for pg in a.pages:
        rows = PAGES[pg]
        lo, hi = rows[0][0], rows[-1][0]
        print(f"\nPAGE {pg}  (subs {lo}-{hi})")
        b.send(f"Delete Sub {lo} Thru {hi}", confirm=True, tolerate=("Does Not Exist",))
        for sub, label, chans, fx in rows:
            kind = "master" if fx is None else f"fx {fx}"
            print(f"  sub {sub:>3}  {label:<14} {kind:<8} {chans}")
            b.send("Sneak Time 0")
            b.send(f"Chan {chans} At Full")
            if fx is not None: b.send(f"Chan {chans} Effect {fx}")
            b.send(f"Record Sub {sub}", confirm=True)
            b.send(f"Sub {sub} Label {label}")
            up, dwell, dn = TIMES[KIND.get(sub, "master")]
            b.send(f"Sub {sub} Time {up} Time {dwell} Time {dn}")
    b.send("Sneak Time 0")
    if conn:
        conn.send("/eos/key/save_show", 1); conn.send("/eos/key/save_show", 0); time.sleep(1.0)
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors: print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0

if __name__ == "__main__":
    sys.exit(main())
