#!/usr/bin/env python3
"""
Prove each of the 50 complete looks (presets 51-100) holds what it was designed
with: the right colour on each zone, and the movers in the right position.

Same discipline as verify_song_looks.py, for the same reasons:
  - clear everything first; a fader or a running effect pollutes every reading
  - sample ONE ZONE AT A TIME, because a look deliberately puts different
    colours on different zones and any average tends to neutral
  - learn the reference hues FROM the console rather than assuming them, so
    this tests "did the look store the palette I asked for", not "does Eos
    agree with my idea of blue"
  - bounce the selection off an empty channel before every read, because
    /eos/out/color/hs and /eos/out/pantilt publish on selection CHANGE and a
    repeat read silently returns the PREVIOUS channel's values

  python3 verify_looks.py
  python3 verify_looks.py 51 52 53
"""
import argparse, sys, time
import eosdump as E
import build_presets as BP

# representative channel per zone, and which LOOKS colour column it takes
#   fcp = front colour, bcp = back colour
ZONES = [("FRONT", 1,  "fcp"), ("BACK", 40, "bcp"),
         ("SLIM",  50, "bcp"), ("BARS", 90, "fcp")]
HUE_TOL = 4.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("looks", nargs="*", type=int)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    a = ap.parse_args()
    c = E.Conn(a.host, a.port)

    def cmd(t, w=0.6):
        c.send("/eos/newcmd", t + "#")
        end = time.time() + w
        while time.time() < end: c.recv()

    def read(ch, addr, w=1.2):
        c.send("/eos/newcmd", "Chan 84#")
        t = time.time() + 0.25
        while time.time() < t: c.recv()
        c.send("/eos/newcmd", f"Chan {ch}#")
        end, got = time.time() + w, None
        while time.time() < end:
            for ad, g in c.recv():
                if ad == addr and g:
                    got = g
        return got

    def hue(ch):
        g = read(ch, "/eos/out/color/hs")
        return round(float(g[0]), 1) if g and len(g) >= 2 else None

    def pantilt(ch):
        g = read(ch, "/eos/out/pantilt")
        return (round(float(g[4]), 1), round(float(g[5]), 1)) if g and len(g) >= 6 else None

    print("clearing: cue out, effects stopped, subs out")
    cmd("Go_To_Cue Out"); cmd("Chan 1 Thru 101 Effect")
    cmd("Sub 1 Thru 137 At 0"); cmd("Group 10 Sneak Time 0", 1.0)

    rows = [r for r in BP.LOOKS if not a.looks or r[0] in a.looks]
    cps = sorted({r[2] for r in rows} | {r[3] for r in rows})
    fps = sorted({r[4] for r in rows})

    print(f"learning {len(cps)} reference hues from the colour palettes")
    REF = {}
    for cp in cps:
        cmd("Group 10 Sneak Time 0", 0.35)
        cmd("Chan 1 At Full", 0.25)
        cmd(f"Chan 1 Color_Palette {cp}", 0.4)     # never combined - trap 21
        REF[cp] = hue(1)

    print(f"learning {len(fps)} reference mover positions")
    FREF = {}
    for fp in fps:
        cmd("Group 10 Sneak Time 0", 0.35)
        cmd("Chan 80 Thru 83 At 100", 0.25)
        cmd(f"Chan 80 Thru 83 Focus_Palette {fp}", 0.9)
        FREF[fp] = pantilt(80)
    cmd("Group 10 Sneak Time 0")

    print("\nchecking each look, one zone at a time")
    bad, checked = [], 0
    for row in rows:
        num, label, fcp, bcp, fp = row[:5]
        want = {"fcp": fcp, "bcp": bcp}
        cmd("Group 10 Sneak Time 0", 0.4)
        cmd(f"Group 10 Preset {num}", 1.1)
        marks = []
        for zname, ch, col in ZONES:
            cp = want[col]
            got, exp = hue(ch), REF.get(cp)
            checked += 1
            if got is None or exp is None:
                ok, why = False, f"no read-back ({got})"
            else:
                dh = abs(got - exp); dh = min(dh, 360 - dh)
                ok = dh <= HUE_TOL
                why = f"hue {got} want {exp} (CP {cp})"
            marks.append(f"{zname}:{'ok' if ok else 'BAD'}")
            if not ok: bad.append((num, label, zname, why))
        gotpt, exppt = pantilt(80), FREF.get(fp)
        checked += 1
        pok = gotpt is not None and gotpt == exppt
        marks.append(f"MVR:{'ok' if pok else 'BAD'}")
        if not pok:
            bad.append((num, label, "MVR", f"wanted FP{fp} {exppt} got {gotpt}"))
        print(f"   {num:>3} {label:<16} " + "  ".join(marks))

    cmd("Group 10 Sneak Time 0")
    c.close()
    print(f"\n{checked} checks, {len(bad)} failures")
    for num, label, z, why in bad:
        print(f"   {num} {label} {z}: {why}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
