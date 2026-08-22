#!/usr/bin/env python3
"""
Build a step-based effect library on a live Eos console.

REQUIRES THE EFFECT EDITOR TO BE OPEN. A human presses [Effect] [Effect] once;
this script does the rest. With the editor closed every write fails silently
with "Error: Effect Does Not Exist" - the script checks for that and aborts.

Design: an effect's SHAPE is authored here, but its chase ORDER comes from the
group, because channels enter the steps in group storage order. So each effect
is paired with a purpose-built ordered group. Change the order, change the look,
without touching the effect.

  Groups  201-212   ordered channel sequences
  Effects 201-212   step-based chases, one per group

  python3 build_effects.py --dry-run
  python3 build_effects.py --only 201 202
"""
import argparse, sys, time
import eosdump as E
try:
    import eos_focus
except ImportError:
    eos_focus = None

def seq(*blocks):
    out = []
    for b in blocks:
        out.extend(b)
    return out

# --- spatial blocks, read off the rig plot -------------------------------
FRONT_L, FRONT_C, FRONT_R = [11,12,13,14], [1,2], [15,16,17,18]
MID_L,   MID_R            = [3,4,7,8], [5,6,9,10]
MIDC_L,  MID_C,  MIDC_R   = [20,21,22,23], [24,25,26,27], [28,29,30,31]
WIDE_L,  WIDE_R           = [32,33,34,35], [36,37,38,39]
BACK_L,  BACK_C, BACK_R   = [40,41,42], [43,44,45], [46,47,48]

L_TO_R = seq(WIDE_L, MIDC_L, FRONT_L, MID_L, BACK_L,
             FRONT_C, MID_C, BACK_C,
             MIDC_R, FRONT_R, MID_R, WIDE_R, BACK_R)
CTR_OUT = seq(FRONT_C, MID_C, BACK_C, MIDC_L, MIDC_R,
              FRONT_L, FRONT_R, MID_L, MID_R, WIDE_L, WIDE_R, BACK_L, BACK_R)
FRONT_BACK = seq(FRONT_C, FRONT_L, FRONT_R, MID_L, MIDC_L, MID_C, MIDC_R,
                 MID_R, WIDE_L, WIDE_R, BACK_L, BACK_C, BACK_R)
# fixed scatter - deterministic, not random, so re-runs are identical
SCATTER = [17,3,42,28,9,35,1,46,22,12,39,5,31,48,14,26,7,44,19,33,
           2,40,25,11,37,6,29,16,45,21,8,34,13,47,24,4,38,30,10,43,
           18,27,36,15,41,23,32,20]

CHASES = [
    (201, "Chase Odd 6",    6, list(range(1, 49, 2)),           0.6),
    (202, "Chase Even 6",   6, list(range(2, 49, 2)),           0.6),
    (203, "Chase L to R",   8, L_TO_R,                          0.8),
    (204, "Chase R to L",   8, L_TO_R[::-1],                    0.8),
    (205, "Chase Ctr Out",  6, CTR_OUT,                         0.7),
    (206, "Chase Out In",   6, CTR_OUT[::-1],                   0.7),
    (207, "Chase Front Bk", 4, FRONT_BACK,                      0.6),
    (208, "Chase Back Frnt",4, FRONT_BACK[::-1],                0.6),
    (209, "Chase Scatter",  8, SCATTER,                         0.5),
    (210, "Chase Quarters", 4, list(range(1, 49)),              0.8),
    (211, "Chase Strips",   8, list(range(90, 98)),             0.4),
    (212, "Chase Movers",   8, [80,81,82,83,85,86,87,88],       0.9),
]


class Build:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _read(self, wait=1.4, idle=0.28):
        end, last = time.time() + wait, time.time()
        echo, sk = "", {}
        while time.time() < end:
            msgs = self.conn.recv()
            if msgs:
                last = time.time()
                for addr, args in msgs:
                    if addr == "/eos/out/cmd" and args:
                        echo = str(args[0])
                    if "/softkey/" in addr and args:
                        sk[addr] = args[0]
            elif time.time() - last > idle:
                break
        return echo, sk

    def newcmd(self, s, term=False):
        self.n += 1
        if self.dry:
            print(f"    newcmd {s!r}{' + #' if term else ''}")
            return "", {}
        self.conn.send("/eos/newcmd", s + ("#" if term else ""))
        return self._read()

    def app(self, s):
        self.n += 1
        if self.dry:
            print(f"    append {s!r}")
            return "", {}
        self.conn.send("/eos/cmd", s)
        return self._read()

    def key(self, k):
        self.n += 1
        if self.dry:
            print(f"    key    {k}")
            return "", {}
        self.conn.send(f"/eos/key/{k}", 1)
        self.conn.send(f"/eos/key/{k}", 0)
        return self._read()

    def fail(self, what, echo):
        self.errors.append((what, echo))
        print(f"  !! {what}: {echo[-60:]}", file=sys.stderr)

    def fx(self, n):
        if self.dry:
            return {"type": "StepBased"}
        coll = E.Collector()
        self.conn.send(f"/eos/get/fx/{n}")
        t = l = time.time()
        while time.time() - t < 5:
            m = self.conn.recv()
            if m:
                for a, g in m:
                    coll.feed(a, g)
                l = time.time()
            elif time.time() - l > 0.4:
                break
        r = E.build(coll).get("fx", {}).get(str(n))
        return r if r and r.get("type") else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", type=int, nargs="*")
    ap.add_argument("--phase", choices=["groups", "effects"], required=True,
                    help="groups: run from LIVE.  effects: run with the Effect "
                         "editor OPEN. They cannot be combined - switching to "
                         "Live loses editor focus, and OSC cannot get it back.")
    a = ap.parse_args()

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    b = Build(conn, a.dry_run)

    # --- PHASE 1: ordered groups. Must run from LIVE.
    if a.phase == "groups":
        print("=== ordered groups (run this from LIVE)")
        for num, label, steps, chans, cyc in CHASES:
            if a.only and num not in a.only:
                continue
            sel = " + ".join(str(x) for x in chans)
            print(f"group {num}  {label}  ({len(chans)} chans)")
            b.newcmd(f"Delete Group {num}", term=True)
            b.key("enter")                  # answer any confirm
            e, _ = b.newcmd(f"Chan {sel} Record Group {num}", term=True)
            if "Error" in e:
                b.fail(f"group {num}", e)
            b.newcmd(f"Group {num} Label {label}", term=True)

    # --- PHASE 2: effects. Requires the Effect editor to be focused.
    for num, label, steps, chans, cyc in CHASES:
        if a.phase != "effects" or (a.only and num not in a.only):
            continue
        print(f"effect {num}  {label}  ({steps} steps @ {cyc}s)")
        b.newcmd(f"Delete Effect {num}", term=True)
        b.key("enter")

        b.newcmd(f"Effect {num}")
        e, sk = b.key("enter")
        if "Does Not Exist" in e and eos_focus and not a.dry_run:
            # Display focus is the one thing OSC cannot do. Reach for macOS
            # System Events, then retry once.
            print("   editor not focused - opening it via System Events")
            try:
                eos_focus.open_effect_editor()
                b.newcmd(f"Effect {num}")
                e, sk = b.key("enter")
            except Exception as ex:
                b.fail(f"effect {num}", f"could not open editor: {ex}")
                break
        if "Does Not Exist" in e:
            b.fail(f"effect {num}", "EFFECT EDITOR IS NOT OPEN - press [Effect][Effect] "
                                    "(or grant Accessibility so this can do it)")
            print("\nABORTING: open the Effect editor and re-run.", file=sys.stderr)
            break
        b.key("stepbased")
        if not b.fx(num):
            b.fail(f"effect {num}", "not created after stepbased")
            continue

        b.key("step")
        b.app(f"1 Thru {steps}")
        b.key("enter")
        b.key("enter")                      # confirms "Please Confirm"

        b.newcmd(f"Group {num}")
        b.key("enter")

        b.newcmd(f"Effect {num}")
        b.key("cycletime")
        b.app(str(cyc))
        b.key("enter")

        b.newcmd(f"Effect {num} Label {label}", term=True)

    if conn:
        b.newcmd("Sneak Time 0", term=True)
        conn.send("/eos/key/save_show", 1)
        conn.send("/eos/key/save_show", 0)
        end, saved = time.time() + 15, None
        while time.time() < end and not saved:
            for addr, args in conn.recv():
                if addr == "/eos/out/event/show/saved":
                    saved = args[0]
        print(f"\nsaved -> {saved or 'NOT SAVED'}")
        conn.close()

    print(f"{b.n} commands, {len(b.errors)} errors")
    for what, echo in b.errors:
        print(f"  FAILED {what}: {echo[-70:]}")
    return 1 if b.errors else 0


if __name__ == "__main__":
    sys.exit(main())
