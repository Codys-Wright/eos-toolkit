#!/usr/bin/env python3
"""
Verify that every song cue actually holds the colour it was designed with.

This has been the show's outstanding verification debt. Two things defeated
earlier attempts (see docs/show-cues.md):
  - a fader was up running a colour effect over every cue under test
  - the measurement averaged the WHOLE stage, and each look deliberately puts
    different colours on different zones, so the average tends to neutral

So: clear everything, stop effects, pull the subs out, then sample ONE ZONE AT
A TIME by selecting a single representative channel and reading its hue back.

Reference hues are learned from the colour palettes themselves rather than
assumed, so this tests "did the cue store the palette I asked for", not "does
Eos agree with my idea of blue".

  python3 verify_song_looks.py
  python3 verify_song_looks.py --cues 110 120
"""
import argparse, sys, time
import eosdump as E
import build_song_looks as D

# one representative channel per zone, and the DESIGN column it comes from
# DESIGN row is (cue, label, front, mid, back, movers, bars, foh, fbm, haze)
# so the column indices are          2      3    4      5       6
# BARS is 6, NOT 5 - 5 is the mover colour. Getting this wrong reports the
# right stage as wrong, which is the most expensive kind of test failure.
ZONES = [("FRONT", 1,  2), ("MID", 3, 3), ("BACK", 32, 4),
         ("SLIM",  50, 4), ("BARS", 90, 6)]

HUE_TOL = 4.0      # degrees


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--cues", type=int, nargs="*")
    a = ap.parse_args()

    c = E.Conn(a.host, a.port)

    def cmd(t, w=0.7):
        c.send("/eos/newcmd", t + "#")
        end = time.time() + w
        while time.time() < end: c.recv()

    def hue(chan, w=1.6):
        """Select one channel and read its hue/sat back.

        /eos/out/color/hs is published on SELECTION CHANGE, not on demand. Ask
        for the same channel twice in a row and the second read returns
        nothing - and whatever variable you stored it in still holds the
        PREVIOUS channel's colour, which reads as a plausible answer. So bounce
        the selection off another channel first to guarantee a fresh publish,
        and drain the socket before asking.
        """
        c.send("/eos/newcmd", "Chan 84#")      # a gap in the patch: no data
        t = time.time() + 0.5
        while time.time() < t: c.recv()
        c.send("/eos/newcmd", f"Chan {chan}#")
        end, got = time.time() + w, None
        while time.time() < end:
            for addr, g in c.recv():
                if addr == "/eos/out/color/hs" and g and len(g) >= 2:
                    got = (round(float(g[0]), 2), round(float(g[1]), 2))
        return got

    print("clearing: cue out, effects stopped, subs out")
    cmd("Go_To_Cue Out")
    cmd(D.FX_STOP)
    cmd("Sub 1 Thru 137 At 0")
    cmd("Group 10 Sneak Time 0")

    print("\nlearning reference hues from the colour palettes themselves")
    REF = {}
    for cp in range(1, 11):
        cmd("Group 10 Sneak Time 0", 0.4)
        cmd("Chan 1 At Full", 0.3)
        cmd(f"Chan 1 Color_Palette {cp}", 0.4)
        REF[cp] = hue(1)
        print(f"   CP {cp:>2} -> {REF[cp]}")
    cmd("Group 10 Sneak Time 0")

    rows = [r for r in D.DESIGN if not a.cues or r[0] in a.cues]
    bad, checked = [], 0
    print("\nchecking each cue, one zone at a time")
    for row in rows:
        cue, label = row[0], row[1]
        # The song cues fade over 3s. Sampling the first zone 1.2s in caught
        # it mid-crossfade and reported a hue sitting between two palettes.
        cmd(f"Go_To_Cue 1 / {cue}", 5.0)
        line = []
        for zname, chan, col in ZONES:
            want_cp = row[col]
            got, want = hue(chan), REF.get(want_cp)
            checked += 1
            if got is None or want is None:
                ok = False; why = f"no read-back ({got})"
            else:
                dh = abs(got[0] - want[0])
                dh = min(dh, 360 - dh)          # hue is circular
                ok = dh <= HUE_TOL
                why = f"hue {got[0]} want {want[0]} (CP {want_cp})"
            line.append(f"{zname}:{'ok' if ok else 'BAD'}")
            if not ok: bad.append((cue, label, zname, why))
        print(f"   1/{cue:<4} {label:<12} " + "  ".join(line))

    cmd("Go_To_Cue Out")
    cmd("Group 10 Sneak Time 0")
    c.close()

    print(f"\n{checked} zone checks, {len(bad)} failures")
    for cue, label, z, why in bad:
        print(f"   1/{cue} {label} {z}: {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
