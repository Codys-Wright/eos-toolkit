#!/usr/bin/env python3
"""
Prove what is actually mapped to each fader.

For a long time this repo believed fader mapping could not be read back, and
said so in docs/busking-faders.md. That belief is why the documented layout and
the real one drifted apart - nobody could check, so nobody did.

It IS readable, just not through the get/ query protocol everything else uses.
Create an OSC fader bank and Eos publishes a name per fader:

    /eos/out/fader/1/1/name   ['S 1 STROB']
    /eos/out/fader/1/11/name  ['S 41 FRONT']

The name carries the sub number, so this compares the console against the
FADERS table in build_busking_faders.py and reports any disagreement.

  python3 verify_faders.py
  python3 verify_faders.py --faders 24     # read a wider window
"""
import argparse, re, sys, time
import eosdump as E
import build_busking_faders as BF


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--faders", type=int, default=20,
                    help="how many faders to read in one bank window")
    ap.add_argument("--bank", type=int, default=1)
    a = ap.parse_args()

    c = E.Conn(a.host, a.port)
    c.send(f"/eos/fader/{a.bank}/config/{a.faders}")

    names, end = {}, time.time() + 4.0
    while time.time() < end:
        for addr, g in c.recv():
            m = re.match(rf"/eos/out/fader/{a.bank}/(\d+)/name$", addr)
            if m and g:
                names[int(m.group(1))] = str(g[0])
    c.close()

    if not names:
        print("no fader names came back - is the bank index right?")
        return 1

    # expected: absolute fader number -> sub. FADERS is {sub: (page, slot)},
    # and fader numbering is CONTINUOUS, so the absolute fader for a given
    # (page, slot) depends on the page size in force. Invert by sub instead.
    # FADERS is {sub: absolute fader number}. Fader numbers are continuous;
    # pages are only windows onto them (trap 20), so compare on the absolute.
    want = {sub: fader for sub, fader in BF.FADERS.items()}

    print(f"reading {len(names)} faders from OSC bank {a.bank}\n")
    bad = []
    for n in sorted(names):
        raw = names[n]
        m = re.match(r"S (\d+)\s*(.*)", raw)
        sub = int(m.group(1)) if m else None
        label = m.group(2).strip() if m else raw
        expect_fader = want.get(sub)
        known = sub in want
        expect = (f"expects fader {expect_fader}"
                  + ("" if expect_fader == n else "   <-- WRONG FADER")
                  ) if known else "not in FADERS"
        flag = "" if known else "   <-- not in the builder's table"
        if not known and raw.strip():
            bad.append((n, raw))
        print(f"  fader {n:>3}  {raw:<16} sub {str(sub):<5} {expect}{flag}")

    print(f"\n{len(names)} faders read, {len(bad)} unaccounted for")
    for n, raw in bad:
        print(f"   fader {n}: {raw!r} is on the console but not in FADERS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
