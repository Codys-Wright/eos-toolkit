#!/usr/bin/env python3
"""
Build DESIGNED effects as looping cue lists on a live Eos console.

Effect definitions cannot be authored over OSC - the Effect editor is GUI-only.
A looping cue list does the same job from the operator's seat and IS fully
authorable, so these are custom FX built around this specific rig: its zone
groups, its colour library, its mover focus grid.

Each chase is one cue list. Every cue is a step; Follow sets the step time; the
last cue links back to the first, so it self-runs forever once started.

  Fire with:  Go_To_Cue <list> / 1
  Stop with:  Off  (or park the list on a fader and pull it down)

  python3 build_chases.py --dry-run
  python3 build_chases.py --lists 10 11
"""
import argparse, sys, time
import eosdump as E

RIG = "Group 1"

# (list, name, follow_seconds, additive, [ (label, [commands]) , ... ])
#   additive=False -> each step starts from black, so only that step shows
#   additive=True  -> steps accumulate, for builds
CHASES = [
    (10, "Zone Sweep", 0.35, False, [
        ("Left",   ["Group 11 At 100 Color_Palette 21"]),
        ("Centre", ["Group 12 At 100 Color_Palette 21"]),
        ("Right",  ["Group 13 At 100 Color_Palette 21"]),
    ]),
    (11, "Zone Bounce", 0.35, False, [
        ("Left",    ["Group 11 At 100 Color_Palette 21"]),
        ("Centre",  ["Group 12 At 100 Color_Palette 21"]),
        ("Right",   ["Group 13 At 100 Color_Palette 21"]),
        ("Centre2", ["Group 12 At 100 Color_Palette 21"]),
    ]),
    (12, "Depth Build", 0.45, True, [
        ("Front", ["Group 16 At 100 Color_Palette 22"]),
        ("Mid",   ["Group 17 At 100 Color_Palette 22"]),
        ("Wide",  ["Group 18 At 100 Color_Palette 22"]),
        ("Back",  ["Group 19 At 100 Color_Palette 22"]),
        ("Hold",  []),
        ("Clear", ["Group 1 At 0"]),
    ]),
    (13, "Depth Sweep", 0.35, False, [
        ("Front", ["Group 16 At 100 Color_Palette 12"]),
        ("Mid",   ["Group 17 At 100 Color_Palette 12"]),
        ("Wide",  ["Group 18 At 100 Color_Palette 12"]),
        ("Back",  ["Group 19 At 100 Color_Palette 12"]),
    ]),
    (14, "Quarter Chase", 0.30, False, [
        ("Qtr 1", ["Group 87 At 100 Color_Palette 17"]),
        ("Qtr 2", ["Group 88 At 100 Color_Palette 17"]),
        ("Qtr 3", ["Group 89 At 100 Color_Palette 17"]),
        ("Qtr 4", ["Group 90 At 100 Color_Palette 17"]),
    ]),
    (15, "Odd Even Flash", 0.20, False, [
        ("Odd",  ["Group 21 At 100 Color_Palette 21"]),
        ("Even", ["Group 22 At 100 Color_Palette 21"]),
    ]),
    (16, "Colour Cycle 8", 0.60, False, [
        (f"C{i+1}", [f"Group 3 At 85 Color_Palette {cp}",
                     f"Group 6 At 85 Color_Palette {cp}",
                     f"Group 5 At 70 Color_Palette {cp}"])
        for i, cp in enumerate([1, 3, 4, 6, 9, 12, 17, 18])
    ]),
    (17, "Warm Cool Pulse", 0.80, False, [
        ("Warm", ["Group 3 At 90 Color_Palette 22", "Group 5 At 70 Color_Palette 22"]),
        ("Cool", ["Group 3 At 90 Color_Palette 23", "Group 5 At 70 Color_Palette 23"]),
    ]),
    (18, "Rainbow March", 0.50, False, [
        ("A", ["Group 11 At 90 Color_Palette 1", "Group 12 At 90 Color_Palette 6",
               "Group 13 At 90 Color_Palette 12"]),
        ("B", ["Group 11 At 90 Color_Palette 6", "Group 12 At 90 Color_Palette 12",
               "Group 13 At 90 Color_Palette 1"]),
        ("C", ["Group 11 At 90 Color_Palette 12", "Group 12 At 90 Color_Palette 1",
               "Group 13 At 90 Color_Palette 6"]),
    ]),
    (19, "Mover Grid Walk", 0.50, False, [
        (f"P{i+1}", [f"Group 7 At 100 Focus_Palette {fp}",
                     "Chan 100 Thru 101 At 50"])
        for i, fp in enumerate([36, 37, 38, 39, 40])
    ]),
    (20, "Strip Chase", 0.25, False, [
        (f"S{ch}", [f"Chan {ch} At 100 Color_Palette 21"])
        for ch in range(90, 98)
    ]),
    (21, "Centre Burst", 0.30, False, [
        ("Core",  ["Group 12 At 100 Color_Palette 21"]),
        ("Sides", ["Group 11 At 100 Color_Palette 21",
                   "Group 13 At 100 Color_Palette 21"]),
        ("Wide",  ["Group 18 At 100 Color_Palette 21"]),
        ("Out",   ["Group 1 At 0"]),
    ]),
    (22, "Build and Blow", 0.35, True, [
        ("1 Front", ["Group 16 At 80 Color_Palette 1"]),
        ("2 Mid",   ["Group 17 At 85 Color_Palette 2"]),
        ("3 Wide",  ["Group 18 At 90 Color_Palette 3"]),
        ("4 Back",  ["Group 19 At 95 Color_Palette 4"]),
        ("5 BLOW",  ["Group 1 At 100 Color_Palette 21"]),
        ("6 Out",   ["Group 1 At 0"]),
    ]),
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lists", type=int, nargs="*")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    for lst, name, follow, additive, steps in CHASES:
        if a.lists and lst not in a.lists:
            continue
        print(f"cue list {lst}  {name}  ({len(steps)} steps @ {follow}s)")
        b.send(f"Delete Cue {lst} / 1 Thru {lst} / 999", confirm=True,
               tolerate=("Does Not Exist",))
        b.send("Sneak Time 0")
        for i, (label, cmds) in enumerate(steps, start=1):
            if not additive:
                b.send("Group 1 At 0")
            for cm in cmds:
                b.send(cm)
            b.send(f"Record Cue {lst} / {i}")
            b.send(f"Cue {lst} / {i} Label {label}")
            b.send(f"Cue {lst} / {i} Time 0")
            b.send(f"Cue {lst} / {i} Follow {follow}")
        b.send(f"Cue {lst} / {len(steps)} Link {lst} / 1")
        b.send(f"Cue {lst} / Label {name}")
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
