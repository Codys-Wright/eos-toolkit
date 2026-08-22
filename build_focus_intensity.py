#!/usr/bin/env python3
"""
Build focus-palette grids and an intensity-palette page on a live Eos console.

FOCUS GRIDS are laid out inside the rig's MEASURED working envelope, learned by
recalling each existing focus palette and reading /eos/out/pantilt back:

    Movers OH   (80-83)      pan 63..101   tilt 77..80
    Movers Beam (85-88,98)   pan -56..51   tilt 90 (ceiling) .. 114 (floor)

so every grid point lands somewhere the rig already points, not at the back wall.

  FP 26-50   OH grid    rows = tilt (Lo..Hi), cols = pan (Out..Ctr)
  FP 51-75   Beam grid  rows = tilt (Ceil..Floor), cols = pan (L2..R2)
  IP  1-25   intensity balance page

Focus palettes 1-23 are LEFT ALONE - presets 51-75 reference them by number.
"""
import argparse, sys, time
import eosdump as E

# --- focus grids: (fp_lo, group, pans, tilts, col_names, row_names, prefix) --
OH_PANS  = [62, 73, 84, 95, 105]
OH_TILTS = [70, 74, 78, 82, 86]
OH_COLS  = ["Out", "OutM", "Mid", "MidC", "Ctr"]
OH_ROWS  = ["Lo", "LoM", "Md", "MdH", "Hi"]

BM_PANS  = [-58, -30, -2, 26, 54]
BM_TILTS = [90, 96, 102, 108, 114]
BM_COLS  = ["L2", "L1", "C", "R1", "R2"]
BM_ROWS  = ["Ceil", "Hi", "Md", "Lo", "Flr"]

GRIDS = [
    (26, 7, OH_PANS, OH_TILTS, OH_COLS, OH_ROWS, "OH"),
    (51, 8, BM_PANS, BM_TILTS, BM_COLS, BM_ROWS, "BM"),
]

HAZE = "Chan 100 Thru 101"

# --- intensity palettes: (num, label, [setup commands]) ---------------------
# Levels are a STARTING POINT. Balance is a visual judgement - walk the page
# with the rig up and nudge what looks wrong.
IPS = [
    # row 1 - flat levels
    ( 1, "Full",         ["Group 1 At 100"]),
    ( 2, "Three Qtr",    ["Group 1 At 75"]),
    ( 3, "Half",         ["Group 1 At 50"]),
    ( 4, "Quarter",      ["Group 1 At 25"]),
    ( 5, "Low",          ["Group 1 At 10"]),
    # row 2 - depth distribution
    ( 6, "Front Heavy",  ["Group 16 At 100", "Group 17 At 60", "Group 19 At 25"]),
    ( 7, "Mid Heavy",    ["Group 16 At 45", "Group 17 At 100", "Group 19 At 45"]),
    ( 8, "Back Heavy",   ["Group 16 At 25", "Group 17 At 60", "Group 19 At 100"]),
    ( 9, "Even Wash",    ["Group 3 At 85", "Group 6 At 85", "Group 5 At 70",
                          "Group 51 At 100"]),
    (10, "Front Only",   ["Group 16 At 90"]),
    # row 3 - width distribution
    (11, "Left Heavy",   ["Group 11 At 100", "Group 12 At 55", "Group 13 At 25"]),
    (12, "Centre Heavy", ["Group 11 At 40", "Group 12 At 100", "Group 13 At 40"]),
    (13, "Right Heavy",  ["Group 11 At 25", "Group 12 At 55", "Group 13 At 100"]),
    (14, "Outside In",   ["Group 11 At 100", "Group 13 At 100", "Group 12 At 30"]),
    (15, "Inside Out",   ["Group 12 At 100", "Group 11 At 35", "Group 13 At 35"]),
    # row 4 - by fixture type
    (16, "Pars Only",    ["Group 3 At 90"]),
    (17, "Movers Only",  ["Group 51 At 100", f"{HAZE} At 50"]),
    (18, "Strips Only",  ["Group 5 At 90"]),
    (19, "Wash + Movers",["Group 3 At 85", "Group 6 At 85", "Group 51 At 100"]),
    (20, "No Movers",    ["Group 3 At 90", "Group 6 At 90", "Group 5 At 75"]),
    # row 5 - show states
    (21, "Blackout",     []),
    (22, "Preshow",      ["Group 5 At 20", f"{HAZE} At 40"]),
    (23, "Work Light",   ["Group 3 At 70", "Group 5 At 50"]),
    (24, "Video Safe",   ["Group 5 At 15", f"{HAZE} At 45"]),
    (25, "Full Rig",     ["Group 1 At 100", f"{HAZE} At 55"]),
]


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

    def save(self):
        if self.dry:
            print("  <key save_show>"); return
        self.conn.send("/eos/key/save_show", 1)
        self.conn.send("/eos/key/save_show", 0)
        end = time.time() + 15
        while time.time() < end:
            for addr, args in self.conn.recv():
                if addr == "/eos/out/event/show/saved":
                    print(f"  saved -> {args[0]}"); return
        self.errors.append(("save_show", "no confirmation event"))
        print("  !! SAVE NOT CONFIRMED", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=["focus", "intensity"])
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    if a.only in (None, "focus"):
        print("clearing focus palettes 26-75 (1-23 kept: presets reference them)")
        b.send("Delete Focus_Palette 26 Thru 75", confirm=True,
               tolerate=("Does Not Exist",))
        for base, grp, pans, tilts, cols, rows, tag in GRIDS:
            for r, (tilt, rname) in enumerate(zip(tilts, rows)):
                for cidx, (pan, cname) in enumerate(zip(pans, cols)):
                    num = base + r * 5 + cidx
                    label = f"{tag} {rname} {cname}"
                    print(f"fp {num:>3}  {label:<14} pan={pan} tilt={tilt}")
                    b.send("Sneak Time 0")
                    b.send(f"Group {grp} At 100")
                    b.send(f"Group {grp} Pan {pan}")
                    b.send(f"Group {grp} Tilt {tilt}")
                    b.send(f"Group {grp} Record Focus_Palette {num}")
                    b.send(f"Focus_Palette {num} Label {label}")

    if a.only in (None, "intensity"):
        print("\nclearing intensity palettes 1-25")
        b.send("Delete Intensity_Palette 1 Thru 25", confirm=True,
               tolerate=("Does Not Exist",))
        for num, label, cmds in IPS:
            print(f"ip {num:>3}  {label}")
            b.send("Sneak Time 0")
            b.send("Group 1 At 0")
            for c in cmds:
                b.send(c)
            b.send(f"Group 1 Record Intensity_Palette {num}")
            b.send(f"Intensity_Palette {num} Label {label}")

    b.send("Sneak Time 0")
    b.save()
    if conn:
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors:
        print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
