#!/usr/bin/env python3
"""
WHITE BANK - five faders that make the talent visible over any cue.

The problem: a saturated colour wash looks great and hides faces. Deep blue,
red, magenta - the audience can see the stage and not the people on it.

The fix is a cold-white front wash on its own faders, per stage zone, that can
be pushed up on top of whatever the cue is doing:

    FACE L      group 26   chans 11-14      FOH truss, stage right of centre
    FACE C      group 27   chans 1-2        FOH truss, centre
    FACE R      group 28   chans 15-18      FOH truss, stage left of centre

These are the FOH trusses over the audience - front light is what reads a face.
Back and side wash does not, however bright it is.

DELIBERATELY THE OPPOSITE OF THE FX SUBS. Those use Record Only so they carry
no colour and never fight the cue. These use plain Record so they DO carry
cold white, because overriding the cue's colour is the entire point. Colour is
LTP, so the moment the fader moves off zero the front wash goes white.

Faders 38, 39, 40 - the tail of bank 3, which is empty.

  python3 build_face_light.py --host 10.0.0.5 --dry-run
"""
import argparse, sys, time
import eosdump as E

COLD_WHITE = 10        # colour palette 10, verified by hue read-back
FX_STOP = "Chan 1 Thru 101 Effect"

# WHITE BANK - who gets seen.
#
# The cues carry colour and mood at low level; these carry white light and
# decide who the audience can actually see. Each one covers FRONT *and* MID,
# because the FOH trusses alone (8 fixtures) were not enough light - that was
# the first version's mistake.
#
#  sub, label,       channels,                                    fader
FACES = [
    (61, "WHITE L",   "11 Thru 14 + 3 Thru 4 + 7 Thru 8 + 20 Thru 23", 33),
    (62, "WHITE C",   "1 Thru 2 + 24 Thru 27",                          34),
    (63, "WHITE R",   "15 Thru 18 + 5 Thru 6 + 9 Thru 10 + 28 Thru 31", 35),
    (64, "WHITE ALL", "1 Thru 18 + 20 Thru 31",                         36),
    (65, "WHITE BACK","32 Thru 39 + 42 Thru 46",                        37),
]

PAGE_SIZE = 10


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
            print(f"    {cmd}"); return
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
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--level", type=int, default=100)
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port, timeout=8.0)
    b = B(conn, a.dry_run)

    b.send("Go_To_Cue Out")
    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")

    for sub, label, chans, fader in FACES:
        # A fader has more than one valid-looking address and only one works.
        # Fader 38 is page 4 slot 8 OR page 3 slot 18; the console rejects the
        # first (past page 4's capacity) and accepts the second. Overflow slots
        # on an EARLIER page are the reliable form for faders 31-40.
        if fader > 30:
            pg, slot = 3, fader - 20
        else:
            pg, slot = (fader-1)//PAGE_SIZE + 1, (fader-1) % PAGE_SIZE + 1
        print(f"  sub {sub}  {label:<11} -> fader {fader} (page {pg} slot {slot})")
        b.send(FX_STOP)
        b.send("Group 10 Sneak Time 0")
        b.send("Group 10 At 0")
        b.send(f"Delete Sub {sub}", confirm=True, tolerate=("Does Not Exist",))
        # level and palette must be SEPARATE commands - trap 21
        b.send(f"Chan {chans} At {a.level}")
        b.send(f"Chan {chans} Color_Palette {COLD_WHITE}")
        # scope the record to these channels, nothing else captured
        b.send(f"Chan {chans} Record Sub {sub}", confirm=True)
        b.send(f"Sub {sub} Label {label}")
        # 0 up / manual dwell / 0 down: it flashes while the bump is held,
        # and rides normally on the fader
        b.send(f"Sub {sub} Time 0 Time Manual Time 0")
        b.send(f"Fader {pg} / {slot} Sub {sub}")

    b.send(FX_STOP)
    b.send("Group 10 Sneak Time 0")
    if conn:
        conn.send("/eos/key/save_show", 1); conn.send("/eos/key/save_show", 0)
        end, saved = time.time()+25, None
        while time.time() < end and not saved:
            for ad, args in conn.recv():
                if ad == "/eos/out/event/show/saved": saved = args[0]
        print(f"\n  saved -> {saved or 'NOT CONFIRMED'}")
        conn.close()
    print(f"{b.n} commands, {len(b.errors)} errors")
    for c, e in b.errors: print(f"  FAILED: {c}\n          {e}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
