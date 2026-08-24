#!/usr/bin/env python3
"""
Build an evergreen colour palette library on a live Eos console, laid out as
5x5 DIRECT SELECT PAGES. Wipes every existing colour palette first.

  PAGE 1  (1-25)    DISTINCT  - 20 hues evenly around the wheel + 5 neutrals
  PAGE 2  (26-50)   WARM      - Red / Orange / Amber / Yellow / Lime, 5 shades each
  PAGE 3  (51-75)   COOL      - Green / Teal / Cyan / Sky / Blue
  PAGE 4  (76-100)  DEEP      - Indigo / Violet / Purple / Magenta / Pink
  PAGE 5  (101-125) SPECIALS  - whites, pastels, saturates, tints, looks

Each shade row runs deep -> pale, so a column always means the same thing:
    col 1 Deep (dark, saturated)   col 2 Rich   col 3 pure hue
    col 4 Light (desaturated)      col 5 Pale (washed out)

NOTE: cues store a REFERENCE to a palette, not its values, so rebuilding these
changes how existing cues look. That is intentional here.
"""
import argparse, colorsys, math, sys, time
import eosdump as E

def hsv(h, s, v):
    return colorsys.hsv_to_rgb(h / 360.0, s, v)

# ---- page 1: 20 evenly spread hues + 5 neutrals ---------------------------
DISTINCT = [
    ("Red", 0), ("Orange", 25), ("Amber", 40), ("Yellow", 58), ("Lime", 85),
    ("Green", 120), ("Emerald", 150), ("Teal", 172), ("Cyan", 185), ("Sky", 202),
    ("Azure", 215), ("Blue", 228), ("Deep Blue", 242), ("Indigo", 258),
    ("Violet", 275), ("Purple", 292), ("Magenta", 310), ("Hot Pink", 325),
    ("Rose", 342), ("Blush", 355),
]
NEUTRALS = [
    ("White",      (1.00, 1.00, 1.00)),
    ("Warm White", (1.00, 0.85, 0.62)),
    ("Cool White", (0.78, 0.89, 1.00)),
    ("Lavender",   (0.78, 0.68, 1.00)),
    ("Peach",      (1.00, 0.72, 0.58)),
]

# ---- pages 2-4: shade families, five steps deep -> pale --------------------
FAMILIES = [
    ("Red", 0), ("Orange", 25), ("Amber", 40), ("Yellow", 58), ("Lime", 85),
    ("Green", 120), ("Teal", 168), ("Cyan", 185), ("Sky", 205), ("Blue", 228),
    ("Indigo", 255), ("Violet", 275), ("Purple", 292), ("Magenta", 310),
    ("Pink", 335),
]
STEPS = [("Deep", 1.00, 0.45), ("Rich", 1.00, 0.72), ("", 1.00, 1.00),
         ("Light", 0.52, 1.00), ("Pale", 0.22, 1.00)]

# ---- page 5: hand-picked specials -----------------------------------------
SPECIALS = [
    ("White",       (1.00, 1.00, 1.00)), ("Warm White", (1.00, 0.85, 0.62)),
    ("Cool White",  (0.78, 0.89, 1.00)), ("Straw",      (1.00, 0.93, 0.72)),
    ("Ice Blue",    (0.85, 0.95, 1.00)),
    ("Peach",       (1.00, 0.72, 0.58)), ("Cream",      (1.00, 0.95, 0.84)),
    ("Mint",        (0.72, 1.00, 0.85)), ("Powder",     (0.75, 0.86, 1.00)),
    ("Lilac",       (0.85, 0.75, 1.00)),
    ("Blood Red",   (0.42, 0.00, 0.02)), ("Congo Blue", (0.10, 0.00, 0.55)),
    ("UV Purple",   (0.30, 0.00, 0.70)), ("Deep Teal",  (0.00, 0.30, 0.30)),
    ("Deep Magenta",(0.45, 0.00, 0.35)),
    ("Rose Tint",   (1.00, 0.82, 0.86)), ("Amber Tint", (1.00, 0.90, 0.75)),
    ("Green Tint",  (0.84, 1.00, 0.84)), ("Blue Tint",  (0.84, 0.90, 1.00)),
    ("Violet Tint", (0.92, 0.84, 1.00)),
    ("Fire",        (1.00, 0.28, 0.00)), ("Sunset",     (1.00, 0.42, 0.20)),
    ("Ocean",       (0.00, 0.55, 0.80)), ("Forest",     (0.05, 0.40, 0.12)),
    ("Neon",        (0.55, 1.00, 0.10)),
]


# ---- page 6: correlated colour temperature, 2700K -> 6500K -----------------
# Denser sampling through the warm/theatrical end where the eye is fussiest.
CCT = [2700, 2800, 2900, 3000, 3100,
       3200, 3300, 3400, 3500, 3600,
       3800, 4000, 4200, 4400, 4600,
       4800, 5000, 5200, 5400, 5600,
       5800, 6000, 6200, 6400, 6500]


def kelvin(k):
    """Blackbody CCT -> RGB (Tanner Helland approximation), normalised so the
    brightest channel sits at full so the fixture runs at max output."""
    t = k / 100.0
    if t <= 66:
        r = 255.0
        g = 99.4708025861 * math.log(t) - 161.1195681661
        b = 0.0 if t <= 19 else 138.5177312231 * math.log(t - 10) - 305.0447927307
    else:
        r = 329.698727446 * math.pow(t - 60, -0.1332047592)
        g = 288.1221695283 * math.pow(t - 60, -0.0755148492)
        b = 255.0
    rgb = [min(255.0, max(0.0, c)) for c in (r, g, b)]
    peak = max(rgb) or 1.0
    return tuple(c / peak for c in rgb)


def library():
    """Yield (number, label, (r,g,b)) for all 125 palettes."""
    out = []
    for i, (name, h) in enumerate(DISTINCT):
        out.append((1 + i, name, hsv(h, 1.0, 1.0)))
    for i, (name, rgb) in enumerate(NEUTRALS):
        out.append((21 + i, name, rgb))
    n = 26
    for fam, h in FAMILIES:
        for step, s, v in STEPS:
            label = f"{step} {fam}".strip()
            out.append((n, label, hsv(h, s, v)))
            n += 1
    for i, (name, rgb) in enumerate(SPECIALS):
        out.append((101 + i, name, rgb))
    for i, k in enumerate(CCT):
        out.append((126 + i, f"{k}K", kelvin(k)))
    return out


class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _echo(self, wait=3.0, idle=0.25):
        end, last, echo = time.time() + wait, time.time(), ""
        while time.time() < end:
            msgs = self.conn.recv()
            if msgs:
                last = time.time()
                for addr, args in msgs:
                    if addr == "/eos/out/cmd" and args:
                        echo = str(args[0])
            elif time.time() - last > idle:
                break
        return echo

    def send(self, cmd, confirm=False, tolerate=()):
        self.n += 1
        if self.dry:
            print(f"  {cmd}")
            return
        self.conn.send("/eos/newcmd", cmd + "#")
        echo = self._echo()
        if "Please Confirm" in echo:
            if not confirm:
                self.errors.append((cmd, "unexpected confirm prompt"))
                self.conn.send("/eos/key/clear_cmd", 1)
                self.conn.send("/eos/key/clear_cmd", 0)
                return
            self.conn.send("/eos/key/enter", 1)
            self.conn.send("/eos/key/enter", 0)
            echo = self._echo()
        if "Error" in echo and not any(t in echo for t in tolerate):
            self.errors.append((cmd, echo))
            print(f"  !! {cmd}\n     -> {echo}", file=sys.stderr)

    def rgb(self, r, g, b):
        self.n += 1
        if self.dry:
            print(f"  /eos/color/rgb {r:.3f} {g:.3f} {b:.3f}")
            return
        self.conn.send("/eos/color/rgb", float(r), float(g), float(b))
        time.sleep(0.30)


# STAGE STATE IS AN INPUT TO EVERY Record. "Sneak Time 0" sets a TIME - it
# clears nothing. Use "Group 10 Sneak Time 0", which actually sneaks the whole
# rig back to background, and release the cue list before building. Otherwise
# whatever is on stage when this runs gets recorded into the target.
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-wipe", action="store_true")
    ap.add_argument("--range", type=int, nargs=2, metavar=("LO", "HI"))
    a = ap.parse_args()

    lib = library()
    if a.range:
        lib = [x for x in lib if a.range[0] <= x[0] <= a.range[1]]

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    # Release the cue list first - Record captures the stage.
    b.send("Go_To_Cue Out")
    b.send("Group 10 Sneak Time 0")
    if not a.no_wipe:
        print("wiping every existing colour palette")
        b.send("Delete Color_Palette 1 Thru 600", confirm=True,
               tolerate=("Does Not Exist",))

    b.send("Group 10 Sneak Time 0")
    for num, label, (r, g, bl) in lib:
        print(f"cp {num:>3}  {label}")
        b.send("Group 10 At 100")          # Group 10 = All (whole rig, no phantoms)
        b.rgb(r, g, bl)
        b.send(f"Group 10 Record Color_Palette {num}")
        b.send(f"Color_Palette {num} Label {label}")
    b.send("Group 10 Sneak Time 0")

    if conn:
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors:
        print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
