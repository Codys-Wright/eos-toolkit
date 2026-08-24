#!/usr/bin/env python3
"""
Which effects actually DO something?

An effect can have a perfect label and an empty step table. Eos reports the
label, the type, entry/exit and scale over OSC, but NOT the step/value table -
so a hollow effect is indistinguishable from a working one by reading alone.
This repo's stock effects were relocated with Copy_To, which preserved every
readable field and dropped the contents.

The only test is to run one and watch the rig. Apply the effect, sample the
selected channel's encoder wheels several times, and see whether any value
moves. Works for colour, intensity and focus effects alike, because every
parameter shows up as a wheel.

  python3 test_effects.py                 # every effect the fader banks use
  python3 test_effects.py 912 917 919     # just these
"""
import argparse, sys, time
import eosdump as E

PARS  = "1 Thru 10"        # a small slice: enough to see, quick to drive
MVRS  = "80 Thru 83"
FX_STOP = "Chan 1 Thru 101 Effect"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("effects", nargs="*", type=int)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--samples", type=int, default=4)
    a = ap.parse_args()

    if a.effects:
        targets = [(n, f"fx {n}", PARS) for n in a.effects]
    else:
        import build_busking_faders as BF
        seen, targets = set(), []
        for rows in BF.PAGES.values():
            for sub, label, chans, fx in rows:
                if fx is None or fx in seen:
                    continue
                seen.add(fx)
                # focus effects need something that can pan and tilt
                targets.append((fx, label, MVRS if "8" in chans[:2] else PARS))
        targets.sort()

    c = E.Conn(a.host, a.port)

    def cmd(t, w=0.55):
        c.send("/eos/newcmd", t + "#")
        end = time.time() + w
        while time.time() < end: c.recv()

    def wheels(ch, w=1.0):
        """All encoder values for one channel. Bounce the selection first:
        these publish on selection CHANGE, so re-reading the same channel
        returns nothing and leaves the previous channel's values in place."""
        c.send("/eos/newcmd", "Chan 84#")
        t = time.time() + 0.3
        while time.time() < t: c.recv()
        c.send("/eos/newcmd", f"Chan {ch}#")
        end, got = time.time() + w, {}
        while time.time() < end:
            for addr, g in c.recv():
                if addr.startswith("/eos/out/active/wheel/") and g:
                    got[addr] = round(float(g[-1]), 2)
        return tuple(sorted(got.items()))

    dead, live = [], []
    print(f"testing {len(targets)} effects\n")
    for fx, label, chans in targets:
        cmd(FX_STOP); cmd("Group 10 Sneak Time 0", 0.35)
        cmd(f"Chan {chans} At Full", 0.3)
        cmd(f"Chan {chans} Effect {fx}", 0.7)
        probe = int(chans.split()[0])
        snaps = {wheels(probe) for _ in range(a.samples)}
        moved = len(snaps) > 1
        (live if moved else dead).append((fx, label))
        print(f"  fx {fx:>4}  {label:<14} {'MOVES' if moved else 'STATIC  <-- dead'}")

    cmd(FX_STOP); cmd("Group 10 Sneak Time 0")
    c.close()
    print(f"\n{len(live)} live, {len(dead)} dead")
    if dead:
        print("dead effects (label is fine, step table is empty):")
        for fx, label in dead:
            print(f"   {fx}  {label}")
    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
