#!/usr/bin/env python3
"""
Build the PopStars cue list (list 2) on a live Eos console over OSC.

The show is DATA, not keystrokes. Change ORDER or an act's palette below and
re-run; the console is rebuilt to match. Cue numbers encode act IDENTITY, and
links encode RUNNING ORDER, so reordering never renumbers anything.

  python3 build_popstars.py --dry-run      # print commands, send nothing
  python3 build_popstars.py --acts 100     # build one act
  python3 build_popstars.py                # build everything
"""
import argparse, sys, time
import eosdump as E

# --------------------------------------------------------------- the show

# Act identity -> permanent 100-block. NEVER changes, whatever the running order.
ACTS = {
    # primary / secondary = the act's colour identity on the wash.
    # mover / floor = contrasting accents. All numbers refer to the rebuilt
    # 1-125 colour library (page 1 = 25 distinct hues).
    100: dict(name="Glitter Riot", tag="GR",
              primary=3,  secondary=2,  mover=21,  floor=4),    # amber / orange
    200: dict(name="The Aubvis",   tag="AUB",
              primary=12, secondary=9,  mover=105, floor=11),   # blue / cyan
    300: dict(name="Pop Th3ory",   tag="P3",
              primary=17, secondary=18, mover=15,  floor=16),   # magenta / pink
    400: dict(name="Trifecta",     tag="TRI",
              primary=5,  secondary=6,  mover=7,   floor=8),    # lime / green
    500: dict(name="Kaat Krew",    tag="KK",
              primary=1,  secondary=2,  mover=121, floor=111),  # red / fire
    600: dict(name="PinkSpark",    tag="PS",
              primary=18, secondary=21, mover=19,  floor=20),   # pink / white
}

# RUNNING ORDER. Reorder this list, re-run, and only the links change.
ORDER = [100, 200, 300, 400, 500, 600]

HAZE = "Chan 100 Thru 101"
RESET = "Group 1 At 0"          # Group 1 = Rig All; colour/focus persist

# Groups, from the rebuilt 1-100 library:
#   1 Rig All  3 Pars All  5 Strips  6 SlimPars
#   7 Movers OH  8 Movers Beam  16 Front Wash  25 Pars Split


def video(a):
    """Stage low so the video reads. Blocked: acts must not inherit state."""
    return [f"Group 5 At 15 Color_Palette 112",      # strips, Congo Blue
            f"{HAZE} At 45"]


def song1(a):
    """Full wash, act primary colour, movers centre."""
    return [f"Group 3 At 80 Color_Palette {a['primary']}",
            f"Group 6 At 80 Color_Palette {a['primary']}",
            f"Group 7 At 100 Focus_Palette 2 Beam_Palette 15 Color_Palette {a['mover']}",
            f"Group 8 At 100 Focus_Palette 16 Color_Palette {a['floor']}",
            f"Group 5 At 60 Color_Palette {a['primary']}",
            f"{HAZE} At 40"]


def song2(a):
    """Moodier: split pars only, secondary colour, movers to the walls."""
    return [f"Group 25 At 55 Color_Palette {a['secondary']}",
            f"Group 6 At 60 Color_Palette {a['secondary']}",
            f"Group 7 At 90 Focus_Palette 4 Beam_Palette 17 Color_Palette {a['mover']}",
            f"Group 8 At 90 Focus_Palette 20 Color_Palette {a['floor']}",
            f"Group 5 At 35 Color_Palette {a['secondary']}",
            f"{HAZE} At 45"]


def song3(a):
    """Anthem: everything up, white accents, movers open and wide."""
    return [f"Group 3 At 100 Color_Palette {a['secondary']}",
            f"Group 6 At 100 Color_Palette 21",
            f"Group 7 At 100 Focus_Palette 1 Beam_Palette 13 Color_Palette 21",
            f"Group 8 At 100 Focus_Palette 23 Color_Palette 21",
            f"Group 5 At 80 Color_Palette 21",
            f"{HAZE} At 50"]


def act_out(a):
    """Clean handoff to the next act's video."""
    return [f"{HAZE} At 40"]


SONGS = [(10, "Song 1", song1), (20, "Song 2", song2), (30, "Song 3", song3)]

# ------------------------------------------------------------- the driver

class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def send(self, cmd, confirm=False):
        self.n += 1
        if self.dry:
            print(f"  {cmd}")
            return
        self.conn.send("/eos/newcmd", cmd + "#")
        if confirm:
            deadline = time.time() + 2.0
            echo = ""
            while time.time() < deadline:
                for addr, args in self.conn.recv():
                    if addr == "/eos/out/cmd" and args:
                        echo = str(args[0])
            if "Please Confirm" in echo:
                self.conn.send("/eos/key/enter", 1)
                self.conn.send("/eos/key/enter", 0)
                time.sleep(0.5)
            return
        # Drain, watching the console's own echo for a parse error.
        deadline = time.time() + 3.0
        last = time.time()
        echo = ""
        while time.time() < deadline:
            msgs = self.conn.recv()
            if msgs:
                last = time.time()
                for addr, args in msgs:
                    if addr == "/eos/out/cmd" and args:
                        echo = str(args[0])
            elif time.time() - last > 0.30:
                break
        if "Error" in echo:
            self.errors.append((cmd, echo))
            print(f"  !! {cmd}\n     -> {echo}", file=sys.stderr)

    def link(self, frm, to):
        """Links must be applied AFTER every cue exists - Eos silently drops a
        link to a cue that isn't there yet."""
        print(f"link 2/{frm} -> 2/{to}")
        self.send(f"Cue 2 / {frm} Link 2 / {to}")

    def cue(self, num, label, body, block=False, link=None, up=3):
        print(f"cue 2/{num}  {label}")
        self.send(RESET)
        for c in body:
            self.send(c)
        self.send(f"Record Cue 2 / {num}")
        self.send(f"Cue 2 / {num} Label {label}")
        self.send(f"Cue 2 / {num} Time {up}")
        if block:
            self.send(f"Cue 2 / {num} Block")



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--acts", type=int, nargs="*",
                    help="only build these act blocks, e.g. --acts 100 200")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)
    todo = a.acts if a.acts else ORDER
    if not a.acts:
        print("clearing cue list 2")
        b.send("Delete Cue 2 / 1 Thru 2 / 999", confirm=True)

    for i, block in enumerate(ORDER):
        if block not in todo:
            continue
        act = ACTS[block]
        tag = act["tag"]
        nxt = ORDER[i + 1] if i + 1 < len(ORDER) else None

        b.cue(block, f"{tag} Video", video(act), block=True, up=2)
        for off, name, fn in SONGS:
            b.cue(block + off, f"{tag} {name}", fn(act), up=3)
        b.cue(block + 90, f"{tag} Out", act_out(act), up=3)

    # Second pass: every cue now exists, so links will hold.
    for i, blk in enumerate(ORDER):
        if blk not in todo:
            continue
        if i + 1 < len(ORDER):
            b.link(blk + 90, ORDER[i + 1])

    if conn:
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors:
        print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
