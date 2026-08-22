#!/usr/bin/env python3
"""
Rename every effect on the console to a consistent, readable scheme.

Renaming is FREE and SAFE: a cue references an effect by NUMBER, so labels can
change without touching a single cue. Numbers are never altered here.

Scheme:
  Fade <A>-<B>    absolute two-colour crossfades (100-159, 520-526)
  Step <A>-<B>    absolute stepped colour changes (400-413, 500-501)
  <Shape>         focus shapes (901-933); " Sm" marks the small-scale variants
  <Name>          linear movers/colour sweeps (904-940)
  Int <Name>      intensity effects (936-941)
Duplicate behaviours get a trailing "2" so they stay distinguishable.
"""
import argparse, re, sys, time
import eosdump as E

CANON = {
    "RED": "Red", "GREEN": "Green", "BLUE": "Blue", "BLIE": "Blue",
    "LIME GREEN": "Lime", "LIME": "Lime", "CYAN": "Cyan",
    "MAGENTA": "Magenta", "MAG": "Magenta", "MAG'": "Magenta",
    "PINK": "Pink", "PURPLE": "Purple", "YELLOW": "Yellow",
    "ORANGE": "Orange", "WHITE": "White",
}

# Explicit names for anything that is not a clean "<A> <B> FADE/step" pattern.
OVERRIDE = {
    401: "Step Grn-Org-Cyan", 405: "Step Red-Blu-Wht",
    407: "Step Red-Yel-Purp", 410: "Step Green-Purple",
    411: "Step Green-Purple 2",
    412: "Step Sisters", 413: "Step Red-Yel-Blue", 500: "Step RGB",
    501: "Pop Magenta", 525: "Fade Red-Pink-Yel", 526: "Fade Blue-Yellow",
    901: "Circle", 902: "Square", 903: "Fig 8", 905: "Triangle",
    906: "Spiral", 907: "Square Rev", 908: "Circle Rev",
    927: "Fig 8 Sm", 928: "Circle Sm", 929: "Square Sm", 930: "Fig 8 Sm 2",
    932: "Triangle Sm", 933: "Spiral Sm",
    904: "Can Can", 909: "Ballyhoo", 910: "Colour Smooth",
    911: "Colour Fade", 912: "Rainbow RGB", 913: "Colour Bump",
    914: "Hue-Sat Fade", 915: "Ramp", 916: "Ramp Inverted",
    917: "Rainbow RGB Lg", 918: "Rainbow CMY", 919: "Rainbow RGB Wide",
    926: "Sweep Slow", 931: "Can Can Sm", 934: "Search Light",
    940: "Pan Sweep",
    936: "Int Fade", 937: "Int Step", 938: "Int Fade 2",
    939: "Int Strobe", 941: "Int Strobe Fast",
}


def canon_pair(label, tail):
    """'RED LIME GREEN FADE' -> ('Red','Lime'); returns None if it doesn't fit."""
    body = label.upper().replace(tail.upper(), "").strip()
    body = re.sub(r"\s+", " ", body)
    for a in sorted(CANON, key=len, reverse=True):
        if body.startswith(a + " ") or body == a:
            rest = body[len(a):].strip()
            for b in sorted(CANON, key=len, reverse=True):
                if rest == b:
                    return CANON[a], CANON[b]
    return None


def new_name(num, label):
    if num in OVERRIDE:
        return OVERRIDE[num]
    for tail, prefix in (("FADE", "Fade"), ("STEP", "Step")):
        if label.upper().rstrip("-").strip().endswith(tail):
            pair = canon_pair(label.rstrip("- ").strip(), tail)
            if pair:
                return f"{prefix} {pair[0]}-{pair[1]}"
    return label.strip() or f"Effect {num}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    c = E.Conn(a.host, a.port)
    coll = E.Collector()

    def drain(idle=0.5, hard=40):
        s = l = time.time()
        while time.time() - s < hard:
            m = c.recv()
            if m:
                for ad, g in m:
                    coll.feed(ad, g)
                l = time.time()
            elif time.time() - l > idle:
                break

    c.send("/eos/get/fx/count"); drain()
    n = int((coll.plain.get("/eos/out/get/fx/count") or [0])[0])
    for lo in range(0, n, 40):
        for i in range(lo, min(lo + 40, n)):
            c.send(f"/eos/get/fx/index/{i}")
        drain()
    fx = E.build(coll).get("fx", {})

    # Build names, then de-duplicate by appending a counter.
    plan, seen = [], {}
    for k in sorted(fx, key=int):
        num, old = int(k), fx[k].get("label", "")
        name = new_name(num, old)
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            name = f"{name} {seen[name]}"
        plan.append((num, old, name))

    changed = [p for p in plan if p[1] != p[2]]
    print(f"{n} effects; {len(changed)} labels will change\n")
    for num, old, name in plan:
        mark = "  " if old == name else "->"
        print(f"  {num:>4} {mark} {old[:30]:<30} {name}")

    if a.dry_run:
        c.close(); return 0

    errs = 0
    for num, old, name in changed:
        c.send("/eos/newcmd", f"Effect {num} Label {name}#")
        t, echo = time.time(), ""
        while time.time() - t < 0.6:
            for ad, g in c.recv():
                if ad == "/eos/out/cmd" and g:
                    echo = str(g[0])
        if "Error" in echo:
            errs += 1
            print(f"  !! {num}: {echo}", file=sys.stderr)

    c.send("/eos/key/save_show", 1); c.send("/eos/key/save_show", 0)
    end, saved = time.time() + 15, None
    while time.time() < end and not saved:
        for ad, g in c.recv():
            if ad == "/eos/out/event/show/saved":
                saved = g[0]
    print(f"\nrenamed {len(changed)}, {errs} errors; saved -> {saved or 'NOT SAVED'}")
    c.close()
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
