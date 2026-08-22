#!/usr/bin/env python3
"""
Build the PopStars FX submaster bank (subs 31-44) on a live Eos console.

These are LAYER effects: push a fader during any song to add movement, colour
churn, or energy on top of whatever look is running. They are independent of
the cue list, so they work in any act, in any order.

Subs 1-22 belong to the reference show and are never touched.

  python3 build_fx_subs.py --dry-run
  python3 build_fx_subs.py
"""
import argparse, sys, time
import eosdump as E

# (sub, group, effect, level, label)  -- effects chosen from the 26 that the
# reference show actually used, so they are known-good on this rig.
BANK = [
    # (sub, group, effect, level, rate, scale, label)
    #
    # 5x5 DIRECT SELECT GRID - row = what it affects, column = variation:
    #   51 OH Fig8      52 OH Fig8 Fast  53 OH Circle    54 OH Circle Big  55 OH Wide
    #   56 BM Pan       57 BM Pan Fast   58 BM Sweep     59 BM Sweep Fast  60 BM Pan Wide
    #   61 Col Smooth   62 Col Smth Fast 63 Col RYB      64 Col Grn Purple 65 Col Red Mag
    #   66 Par Step     67 Par Step Fast 68 Par Fade     69 Par Strobe     70 Par Ramp
    #   71 Rig Step     72 Rig Strobe    73 Rig Colour   74 OddEven Chase  75 Rig RB White
    #
    # Rate/Scale are overrides on the RUNNING effect - Eos will not let you edit
    # a stored effect definition from the command line ("Effect Not Running"),
    # but it will happily record a modified instance into a submaster.
    # Every effect here is one the reference show actually used on this rig.

    # row 1 - overhead movers (80-83)
    (51, 107, 927, 100, 100, 100, "OH Fig8"),
    (52, 107, 927, 100, 250, 100, "OH Fig8 Fast"),
    (53, 107, 928, 100, 100, 100, "OH Circle"),
    (54, 107, 928, 100, 100, 200, "OH Circle Big"),
    (55, 107, 930, 100, 100, 200, "OH Wide"),
    # row 2 - beam movers (85-88, 98)
    (56, 108, 940, 100, 100, 100, "BM Pan"),
    (57, 108, 940, 100, 250, 100, "BM Pan Fast"),
    (58, 108, 926, 100, 100, 100, "BM Sweep"),
    (59, 108, 926, 100, 250, 100, "BM Sweep Fast"),
    (60, 108, 940, 100, 100, 200, "BM Pan Wide"),
    # row 3 - colour churn on the par wash
    (61, 102, 910,  90, 100, 100, "Col Smooth"),
    (62, 102, 910,  90, 250, 100, "Col Smth Fast"),
    (63, 102, 413,  90, 100, 100, "Col RYB"),
    (64, 102, 411,  90, 100, 100, "Col Grn Purple"),
    (65, 102, 520,  90, 100, 100, "Col Red Mag"),
    # row 4 - intensity on the par wash
    (66, 102, 937, 100, 100, 100, "Par Step"),
    (67, 102, 937, 100, 250, 100, "Par Step Fast"),
    (68, 102, 936, 100, 100, 100, "Par Fade"),
    (69, 102, 939, 100, 100, 100, "Par Strobe"),
    (70, 102, 915, 100, 100, 100, "Par Ramp"),
    # row 5 - whole rig / big moments
    (71, 101, 937, 100, 100, 100, "Rig Step"),
    (72, 101, 939, 100, 150, 100, "Rig Strobe"),
    (73, 101, 910,  90, 100, 100, "Rig Colour"),
    (74, 121, 937, 100, 150, 100, "OddEven Chase"),
    (75, 101, 405,  90, 100, 100, "Rig RB White"),
]


class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _echo(self, wait=3.0, idle=0.30):
        deadline, last, echo = time.time() + wait, time.time(), ""
        while time.time() < deadline:
            msgs = self.conn.recv()
            if msgs:
                last = time.time()
                for addr, args in msgs:
                    if addr == "/eos/out/cmd" and args:
                        echo = str(args[0])
            elif time.time() - last > idle:
                break
        return echo

    def send(self, cmd, confirm=False):
        """Send a command. Eos echoes 'Please Confirm' on destructive ones;
        that prompt is readable over OSC, so confirming is not done blind."""
        self.n += 1
        if self.dry:
            print(f"  {cmd}" + ("   [+confirm]" if confirm else ""))
            return
        self.conn.send("/eos/newcmd", cmd + "#")
        echo = self._echo()
        if "Please Confirm" in echo:
            if not confirm:
                self.errors.append((cmd, "unexpected confirmation prompt"))
                print(f"  !! {cmd} asked to confirm; refusing", file=sys.stderr)
                self.conn.send("/eos/key/clear_cmd", 1)
                self.conn.send("/eos/key/clear_cmd", 0)
                return
            print(f"     confirming: {echo}")
            self.conn.send("/eos/key/enter", 1)
            self.conn.send("/eos/key/enter", 0)
            echo = self._echo()
        if "Error" in echo:
            self.errors.append((cmd, echo))
            print(f"  !! {cmd}\n     -> {echo}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    # 'Record Sub' over an EXISTING sub silently does nothing, so any previous
    # version of the bank has to be deleted first.
    print("clearing subs 31-75 (old bank + this grid)")
    b.send("Delete Sub 31 Thru 75", confirm=True)

    for sub, grp, fx, lvl, rate, scale, label in BANK:
        print(f"sub {sub}  {label}")
        # 'Group 5 At 0' zeroes intensity but does NOT stop running effects,
        # so each sub inherited the previous one's. Sneak releases all manual
        # control - including effects - back to background.
        b.send("Sneak Time 0")
        b.send(f"Group {grp} At {lvl}")
        b.send(f"Group {grp} Effect {fx}")   # 'Effect' will not chain after 'At'
        # Rate/Scale only apply to a RUNNING effect, so they must come last.
        if rate != 100:
            b.send(f"Effect {fx} Rate {rate}")
        if scale != 100:
            b.send(f"Effect {fx} Scale {scale}")
        b.send(f"Record Sub {sub}")
        b.send(f"Sub {sub} Label {label}")

    b.send("Sneak Time 0")
    if conn:
        conn.close()
    print(f"\n{b.n} commands, {len(b.errors)} errors")
    for cmd, echo in b.errors:
        print(f"  FAILED: {cmd}\n          {echo}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
