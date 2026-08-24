#!/usr/bin/env python3
"""
Walk the gobo wheel so a human can name the slots.

The Riukoe profile exposes Gobo Select as a bare number - Eos reports
"Gobo Select [4]", never "Gobo Select [Stars]" - so the only way to learn what
each slot looks like is to project it and look.

Four OH movers, four gobos at a time, aimed straight down at the deck so each
pattern lands on the floor as a readable shape rather than a beam in haze.

  python3 gobo_walk.py 0 1 2 3         # slots 0-3 on movers 80-83
  python3 gobo_walk.py 4 5 6 7         # slots 4-7
  python3 gobo_walk.py --off           # done, clear the stage
"""
import argparse, sys, time
import eosdump as E

OH = [80, 81, 82, 83]

# Wheel slots for the Riukoe / Lixada 11ch shell, from the OEM DMX chart.
# ALL EIGHT GOBOS LIVE IN DMX 0-63, i.e. the first 25% of the parameter.
# 64-127 is the SHAKE version of each slot and 128-255 is rotation, so a naive
# 0-100 sweep spends three quarters of its range outside the gobo wheel and
# lands on shakes that look like nothing.
#   slot n -> DMX centre 8n+4 -> Eos percent
GOBO_PCT = {0: 2, 1: 5, 2: 8, 3: 11, 4: 14, 5: 17, 6: 20, 7: 24}

# Colour wheel: 16 DMX values per slot, centre 16n+8.
COLOUR_PCT = {"Open": 3, "Red": 9, "Pale Blue": 16, "Orange": 22,
              "Blue": 28, "Yellow": 35, "Green": 41, "Pink": 47}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("values", nargs="*", type=int,
                    help="up to 4 GOBO SLOT NUMBERS (0-7), one per mover 80-83")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--off", action="store_true", help="clear and go home")
    ap.add_argument("--haze", type=int, default=0,
                    help="haze level; 0 keeps the floor pattern crisp")
    a = ap.parse_args()

    c = E.Conn(a.host, a.port)
    def cmd(t, w=0.45):
        c.send("/eos/newcmd", t + "#"); time.sleep(w)
        e = ""
        for addr, g in c.recv():
            if addr == "/eos/out/cmd" and g: e = str(g[0])
        return e

    cmd("Chan 1 Thru 101 Effect")          # trap 29: the Chan form, not Group
    if a.off:
        cmd("Group 10 Sneak Time 0")
        print("cleared"); c.close(); return 0

    if not a.values:
        print("give up to 4 values, e.g.  python3 gobo_walk.py 0 10 20 30")
        c.close(); return 1

    cmd("Group 10 Sneak Time 0")
    # Everything else out, so the only thing on stage is the four patterns.
    cmd("Chan 80 Thru 83 At Full")
    cmd(f"{'Chan 100 Thru 101 At ' + str(a.haze)}")
    # Straight down: each mover lands its pattern on the deck beneath itself.
    for ch in OH:
        cmd(f"Chan {ch} Focus_Palette 7")

    print("\n  aimed straight down at the deck, full, no colour\n")
    for ch, slot in zip(OH, a.values):
        pct = GOBO_PCT.get(slot)
        if pct is None:
            print(f"    chan {ch}   slot {slot} is not 0-7, skipped"); continue
        cmd(f"Chan {ch} Gobo_Select {pct}")
        name = "Open" if slot == 0 else f"Gobo {slot}"
        print(f"    chan {ch}   slot {slot} ({name})  = {pct}% = DMX {slot*8+4}"
              f"   <- name this one")
    print("\n  stage-right to stage-left order is 80, 81, 82, 83")
    print("  (chan 80 is at x -3.0, chan 83 at x +3.0)")
    print("\n  next:  python3 gobo_walk.py <four more values>")
    print("  done:  python3 gobo_walk.py --off")
    c.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
