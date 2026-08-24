#!/usr/bin/env python3
"""
Build the first ten focus palettes as AUGMENT3D XYZ POSITIONS, not pan/tilt.

Why XYZ. A pan/tilt focus palette stores a different pair of numbers for every
fixture, all meaning "point at the drum kit". An XYZ palette stores the drum kit
*once*, as a coordinate, and every mover solves its own angles. Re-hang a mover
and the palette still lands; add a mover and it inherits the whole library.

    FP 1-8    SPREAD PATTERNS - relationships between beams
    FP 9-10   the two convergence points worth front-page space
    FP 11-20  the rest of the convergence points

Coordinates are in DECIMAL METRES in the room's own frame, straight out of
docs/norco-location.md:

    origin  stage centre, at the downstage deck surface
    +X      stage left        +Y      upstage        +Z      up
    walls   x = +/-5.94       lip     y = -3.76      ceiling z = +3.454

Manual references (see docs/sources.md):
    p.588  /eos/chan/<n>/xyz sets a channel's XYZ; /eos/out/xyz reads it back.
           "OSC XYZ coordinates are measured in decimal meters, regardless of
           the unit selected in Setup > System Settings > Augment3d."
    p.238  Focus palettes store pan/tilt OR XYZ, per {Enable/Disable XYZ Format}
    p.165  Hang to Focus Offset is used to convert an XYZ beam end to pan/tilt

PRECONDITION, and it is not enforceable from here: Hang to Focus Offset is still
zero on the Riukoe and Betopper profiles. Eos uses it to convert an XYZ target
into pan/tilt, so until it is set at Patch > {Fixtures} > {Physical Data} every
aim below lands slightly off - worst on the floor beams, which sit lowest.
There is no command-line path to it. See trap 19.

WARNING: this rewrites FP 1-10, which presets 16-19, 51-58 and 68-75 reference
(they use FP 1-4). Re-run build_presets.py afterwards to re-record them.

  python3 build_xyz_focus.py --dry-run
  python3 build_xyz_focus.py --verify-only
"""
import argparse, sys, time
import eosdump as E

OH  = [80, 81, 82, 83]          # overhead gobo movers, on the truss
BM  = [85, 86, 87, 88]          # floor beam movers, mid-stage
MVR = OH + BM                   # 98 is UNPATCHED - never include it (trap: rig-model)

SEL = "80 Thru 83 + 85 Thru 88"

# Where the movers actually hang, read back from the console's Augment3d data.
# Per-fixture targets are computed off these, so re-hang a mover, update the
# row, re-run, and the spread patterns re-derive themselves.
HANG = {
    80: (-3.0, 2.20, 3.2), 81: (-1.0, 2.20, 3.2),    # OH, on the truss
    82: ( 1.0, 2.20, 3.2), 83: ( 3.0, 2.20, 3.2),
    85: (-4.0, -1.25, 0.17), 86: (-1.5, -1.25, 0.02),  # BM, on the deck
    87: ( 1.5, -1.25, 0.02), 88: ( 4.0, -1.25, 0.00),
}

WALL_X = 5.94          # the side walls, from docs/norco-location.md

# --- AUDIENCE SAFETY --------------------------------------------------------
# Anything downstage of the stage lip is over people. A beam aimed at 1.5-2.4 m
# out in the house is pointed at a standing person's face, and the beam keeps
# descending past its target. An audit of the first draft found SEVEN palettes
# doing this, including "Audience" aimed at z 1.5 seven metres out.
#
# Rule: any target in the house is lifted to at least HOUSE_MIN_Z. Heads are
# ~1.8 m standing and the ceiling is 3.454, so 2.9 clears people while staying
# in the room. Applied centrally, so a new pattern cannot forget it.
STAGE_LIP_Y  = -3.76
HOUSE_MIN_Z  = 2.90

def safe(pt):
    """Lift a target clear of the audience if it is out in the house."""
    x, y, z = pt
    return (x, y, max(z, HOUSE_MIN_Z)) if y < STAGE_LIP_Y else (x, y, z)

# --- the ten points, in metres --------------------------------------------
# A palette target is EITHER a single (x,y,z) that every mover converges on,
# OR a dict of {channel: (x,y,z)} so each mover gets its own aim. The dict form
# is what makes "straight out", "crossed" and "fanned" possible at all - those
# are not points in space, they are relationships between beams, and pan/tilt
# palettes can only express them as eight unrelated angle pairs.
#
# z 1.5 is roughly a standing performer's head; z 1.0 picks out a seated kit.
# These are geometric stage landmarks, not measurements of where anyone
# stands. Walk them with the rig up and nudge.

def _t(oh_fn, bm_fn):
    """Build a per-fixture target dict from two rules."""
    return {ch: (oh_fn(x, y) if ch in OH else bm_fn(x, y))
            for ch, (x, y, _z) in HANG.items()}

# --- SPREAD PATTERNS: relationships between beams, not points in space ------
# Only 8 of 70 fixtures move, so the movers earn their keep by doing what
# nothing else on the rig can - shape, motion and beams out over the audience.
# Convergence points are useful but they all look the same from the house;
# these are the ones worth having under a finger.

def straight():
    """Each mover along its own axis: OH down, floor beams up. Eight vertical
    shafts standing in their own positions - the haze look."""
    return _t(lambda x, y: (x, y, 0.0), lambda x, y: (x, y, 3.40))

def parallel_out():
    """Parallel paths thrown downstage. The FLOOR movers carry it out over the
    house; the overheads stay on stage - at z 3.2 they can only reach the
    audience by aiming down into people's faces, and the safety lift then puts
    the target out of their tilt range entirely. Verified: OH clamped to home
    on every attempt."""
    return _t(lambda x, y: (x, -3.00, 1.40), lambda x, y: (x, -9.00, 3.10))

def fanned(k=1.8):
    """Splayed outward past their own x - the widest the rig opens up."""
    return _t(lambda x, y: (x * k, -2.00, 1.00),
              lambda x, y: (x * 1.5, -1.25, 3.00))

def crossed():
    """Each mover aims at the mirror of its own x, so the beams cross at
    centre. OH cross low over the stage, beams cross high above head height."""
    return _t(lambda x, y: (-x, -1.00, 1.50), lambda x, y: (-x, -1.25, 2.50))

def house(oh_y=-2.50, oh_z=1.40, bm_y=-9.00, bm_z=3.10, spread=1.0):
    """Throw into the house with the FLOOR movers only; keep the OH on stage.

    The overheads hang at z 3.2 and can tilt down to horizontal but never above
    it, so the only way they reach the audience is by aiming DOWN - which at
    seven metres puts the beam at face height. There is no target that is both
    reachable for them and safe. Verified: every OH audience target clamped.

    The floor beams are at deck level pointing up, so their beams rise away
    from people. They get the house; the overheads stay downstage on the band.
    """
    return _t(lambda x, y: (x * spread, oh_y, oh_z),
              lambda x, y: (x * spread, bm_y, bm_z))

def walls():
    """Stage-right half onto the SR wall, stage-left half onto SL."""
    return _t(lambda x, y: (-WALL_X if x < 0 else WALL_X, 0.00, 2.00),
              lambda x, y: (-WALL_X if x < 0 else WALL_X, -1.00, 2.40))

def fan_audience(k=2.2):
    """Fanned wide but thrown out over the house - the big reveal position."""
    return _t(lambda x, y: (x * k, -6.00, 2.20),
              lambda x, y: (x * 1.8, -8.00, 2.00))

def split_lr():
    """Two opposing clusters: the SR half all to far stage right, the SL half
    all to far stage left. Reads as two solid blades rather than eight beams."""
    return _t(lambda x, y: (-5.20 if x < 0 else 5.20, -1.50, 1.40),
              lambda x, y: (-5.50 if x < 0 else 5.50, -5.00, 3.00))

def zigzag():
    """Alternating near and far targets, so beam lengths sawtooth across the
    stage. Much more interesting in haze than any single convergence point."""
    order = sorted(HANG)
    near = {ch: (i % 2 == 0) for i, ch in enumerate(order)}
    return {ch: ((x, -2.00, 1.20) if near[ch] else (x, -8.00, 2.40))
            for ch, (x, y, _z) in HANG.items()}


POINTS = [
    # --- 1-8: SPREAD PATTERNS, the reason to have movers at all ---
    ( 1, "Straight",     straight()),
    ( 2, "Parallel Out", parallel_out()),
    ( 3, "Fan Out",      fanned()),
    ( 4, "Crossed",      crossed()),
    ( 5, "Wall Split",   walls()),
    ( 6, "Fan Audience", house(spread=1.8)),
    ( 7, "Split LR",     split_lr()),
    ( 8, "Zigzag",       zigzag()),
    # --- 9-10: the two convergence points worth front-page space ---
    ( 9, "DS Centre",    ( 0.00, -3.00, 1.50)),
    (10, "Drums",        ( 0.00,  1.50, 1.00)),
    # --- 11-20: convergence points, second page ---
    (11, "Centre",       ( 0.00, -1.00, 1.50)),
    (12, "US Centre",    ( 0.00,  1.80, 1.50)),
    (13, "Stage Left",   ( 3.00, -1.00, 1.50)),
    (14, "Stage Right",  (-3.00, -1.00, 1.50)),
    (15, "Audience",     house()),
    (16, "Lip Left",     ( 3.00, -3.40, 1.50)),
    (17, "Lip Right",    (-3.00, -3.40, 1.50)),
    (18, "Aud Left",     _t(lambda x, y: ( 2.50, -2.50, 1.40),
                             lambda x, y: ( 4.50, -9.00, 3.10))),
    (19, "Aud Right",    _t(lambda x, y: (-2.50, -2.50, 1.40),
                             lambda x, y: (-4.50, -9.00, 3.10))),
    (20, "Upstage Wall", ( 0.00,  2.80, 2.20)),
]

# Dropped: "Ceiling" as a convergence point. The OH movers hang at z 3.2 and
# cannot aim at z 3.4 - Eos accepted the target, clamped it, and reported the
# clamped position back through /eos/out/xyz without raising anything.

TOL = 0.02      # metres; read-back must land within 2 cm of what we asked for


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
            print(f"    {cmd}")
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

    def xyz(self, chan, pt):
        """Set one channel's XYZ. This is an OSC address, NOT a command line.

        There is no command-line equivalent. `Chan 80 X 0 Y 0 Z 1.5` parses
        without a syntax error and does nothing - trap 18, accepted is not
        applied. Only /eos/chan/<n>/xyz actually moves the fixture.
        """
        self.n += 1
        if self.dry:
            print(f"    /eos/chan/{chan}/xyz {pt[0]} {pt[1]} {pt[2]}")
            return
        self.conn.send(f"/eos/chan/{chan}/xyz", *pt)
        time.sleep(0.12)

    def read_xyz(self, chan, wait=1.2):
        """Select one channel and read /eos/out/xyz back."""
        if self.dry:
            return None
        self.conn.send("/eos/newcmd", f"Chan {chan}#")
        got, end = None, time.time() + wait
        while time.time() < end:
            for addr, args in self.conn.recv():
                if addr == "/eos/out/xyz" and args:
                    got = [round(float(v), 3) for v in args]
        return got

    def save(self):
        if self.dry:
            print("  <key save_show>")
            return
        self.conn.send("/eos/key/save_show", 1)
        self.conn.send("/eos/key/save_show", 0)
        end = time.time() + 15
        while time.time() < end:
            for addr, args in self.conn.recv():
                if addr == "/eos/out/event/show/saved":
                    print(f"  saved -> {args[0]}")
                    return
        self.errors.append(("save_show", "no confirmation event"))
        print("  !! SAVE NOT CONFIRMED", file=sys.stderr)


def targets(spec):
    """Normalise a palette target to {channel: (x,y,z)} for all eight movers.

    Every target passes through safe(), so no pattern - present or future -
    can aim a beam into the audience at head height.
    """
    if isinstance(spec, dict):
        return {ch: safe(pt) for ch, pt in spec.items()}
    return {ch: safe(spec) for ch in MVR}


def verify(b, spec, label):
    """Read every mover's XYZ back and compare to what we asked for.

    Compare per channel against ITS OWN target, and against what was
    REQUESTED - not against whatever the console now reports. Eos clamps an
    out-of-range target silently and echoes the clamped value, so a check that
    trusts the read-back as ground truth would pass every time.
    """
    bad = []
    tgt = targets(spec)
    for ch in MVR:
        pt = tgt[ch]
        got = b.read_xyz(ch)
        if got is None:
            bad.append((ch, "no /eos/out/xyz reply"))
            continue
        if len(got) < 3 or any(abs(got[i] - pt[i]) > TOL for i in range(3)):
            bad.append((ch, f"wanted {pt}, got {got}"))
    for ch, why in bad:
        b.errors.append((f"verify chan {ch} @ {label}", why))
        print(f"  !! chan {ch}: {why}", file=sys.stderr)
    return not bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify-only", action="store_true",
                    help="recall each palette and check the XYZ read-back; write nothing")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    if a.verify_only:
        print("VERIFY ONLY - recalling each palette and reading XYZ back\n")
        for num, label, spec in POINTS:
            b.send("Sneak Time 0")
            # TRAP 21: combining At <level> with a palette applies the level
            # and silently drops the palette. Verifying with the combined form
            # read back the PREVIOUS palette's position and reported it as a
            # mismatch against the current one.
            b.send(f"Chan {SEL} At 100")
            b.send(f"Chan {SEL} Focus_Palette {num}")
            ok = verify(b, spec, label)
            print(f"  fp {num:>2}  {label:<12} {'ok' if ok else 'MISMATCH'}")
        b.send("Sneak Time 0")
        if conn:
            conn.close()
        print(f"\n{len(b.errors)} problems")
        return 1 if b.errors else 0

    # XYZ format is a per-channel property of how focus data is STORED.
    # Without it the Record below writes pan/tilt and the whole point is lost.
    print("enabling XYZ format on all eight movers")
    for ch in MVR:
        b.send(f"Chan {ch} XYZ_Format Enable")

    print("\nclearing focus palettes 1-20")
    print("  (presets 16-19, 51-58, 68-75 reference FP 1-4 - re-run build_presets.py)")
    b.send("Delete Focus_Palette 1 Thru 20", confirm=True,
           tolerate=("Does Not Exist",))

    for num, label, spec in POINTS:
        tgt = targets(spec)
        kind = "per-fixture" if isinstance(spec, dict) else "converge"
        print(f"\nfp {num:>2}  {label:<13} {kind}")
        for ch in MVR:
            x, y, z = tgt[ch]
            print(f"       chan {ch}  x={x:>6.2f}  y={y:>6.2f}  z={z:>5.2f}")
        b.send("Sneak Time 0")
        b.send(f"Chan {SEL} At 100")
        for ch in MVR:
            b.xyz(ch, tgt[ch])
        if not a.dry_run:
            time.sleep(0.3)
            verify(b, spec, label)
        b.send(f"Chan {SEL} Record Focus_Palette {num}")
        b.send(f"Focus_Palette {num} Label {label}")

    b.send("Sneak Time 0")
    b.save()
    if conn:
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors:
        print(f"  FAILED: {cmd}\n          {echo}")
    print("\nNEXT: python3 build_presets.py     # re-record presets that used FP 1-4")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
