#!/usr/bin/env python3
"""
Prove the mover presets actually move the movers.

Every mover line in build_presets.py used to be written as
    Group 7 At 100 Focus_Palette 3
which is trap 21: the LEVEL applies and the palette is silently dropped. Every
preset recorded a mover intensity and no mover position, the echo reported
success, and nothing moved. Read-back of the preset itself would not have
caught it either - the preset exists and is well formed.

The only test is to recall each one from a known state and read pan/tilt back.

  python3 verify_presets.py                # the mover-position bank, 26-50
  python3 verify_presets.py 31 44 51
"""
import argparse, sys, time
import eosdump as E

MVR_PRESETS = list(range(26, 51))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("presets", nargs="*", type=int, default=MVR_PRESETS)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    a = ap.parse_args()
    c = E.Conn(a.host, a.port)

    def cmd(t, w=0.7):
        c.send("/eos/newcmd", t + "#")
        end = time.time() + w
        while time.time() < end: c.recv()

    def pantilt(ch, w=1.0):
        # publishes on selection CHANGE, so bounce off an empty channel first
        c.send("/eos/newcmd", "Chan 84#")
        t = time.time() + 0.25
        while time.time() < t: c.recv()
        c.send("/eos/newcmd", f"Chan {ch}#")
        end, got = time.time() + w, None
        while time.time() < end:
            for addr, g in c.recv():
                if addr == "/eos/out/pantilt" and g and len(g) >= 6:
                    got = (round(float(g[4]), 1), round(float(g[5]), 1))
        return got

    cmd("Go_To_Cue Out"); cmd("Chan 1 Thru 101 Effect")
    cmd("Sub 1 Thru 137 At 0"); cmd("Group 10 Sneak Time 0", 1.0)

    # What SHOULD each preset do? Read it out of the builder rather than
    # guessing. "Did it differ from home?" is a bad oracle: Straight is pan 0 /
    # tilt 0 for a mover hung straight down, so a correct preset looks
    # identical to home, and a preset that only addresses one group leaves the
    # other at home legitimately. Both read as failures.
    import re, build_presets as BP
    want = {}
    for num, label, cmds in BP.MOVER_POS:
        fps = {}
        for line in cmds:          # not `c` - that is the connection
            m = re.match(r"Group (\d+) At \d+ Focus_Palette (\d+)", line)
            if m:
                fps[int(m.group(1))] = int(m.group(2))
        want[num] = (label, fps)          # {7: fp_for_OH, 8: fp_for_BM}

    # Learn where each focus palette actually puts each group, by recalling the
    # palette itself. Split At from the palette - trap 21.
    ref = {}
    for fp in sorted({f for _l, d in want.values() for f in d.values()}):
        cmd("Group 10 Sneak Time 0", 0.5)
        cmd("Chan 80 Thru 83 + 85 Thru 88 At 100", 0.3)
        cmd(f"Chan 80 Thru 83 + 85 Thru 88 Focus_Palette {fp}", 1.1)
        ref[fp] = (pantilt(80), pantilt(85))
    print(f"  learned reference positions for {len(ref)} focus palettes\n")

    bad = []
    for n in a.presets:
        if n not in want:
            continue
        label, fps = want[n]
        cmd("Group 10 Sneak Time 0", 0.5)
        cmd(f"Group 10 Preset {n}", 1.2)
        got = {7: pantilt(80), 8: pantilt(85)}
        probs = []
        for grp, fp in fps.items():
            expect = ref[fp][0 if grp == 7 else 1]
            actual = got[grp]
            if expect is None or actual is None or actual != expect:
                probs.append(f"grp{grp} wanted FP{fp} {expect} got {actual}")
        mark = "ok" if not probs else "MISMATCH"
        print(f"  preset {n:>3} {label:<17} OH {str(got[7]):<16} "
              f"BM {str(got[8]):<16} {mark}")
        for pr in probs:
            print(f"        {pr}")
            bad.append((n, label, pr))

    cmd("Group 10 Sneak Time 0")
    c.close()
    print(f"\n{len([n for n in a.presets if n in want])} presets checked, "
          f"{len(bad)} mismatches")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
