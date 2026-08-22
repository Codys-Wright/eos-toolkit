#!/usr/bin/env python3
"""
Move a block of effects to new numbers via Copy_To + Delete.

Copy_To preserves every field readable over OSC (type, entry, exit, duration,
scale) across Absolute, Focus, Linear and StepBased effects - verified. Step
and value tables are NOT readable, so a visual spot-check is still wise.

Runs from LIVE (Copy_To is a Live command).
"""
import argparse, sys, time
import eosdump as E


class Mover:
    def __init__(self, conn, dry):
        self.conn, self.dry, self.errors, self.n = conn, dry, [], 0

    def _rd(self, wait=1.2, idle=0.22):
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

    def cmd(self, s):
        self.n += 1
        if self.dry:
            print(f"    {s}"); return ""
        self.conn.send("/eos/newcmd", s + "#")
        return self._rd()

    def key(self, k):
        if self.dry:
            return ""
        self.conn.send(f"/eos/key/{k}", 1)
        self.conn.send(f"/eos/key/{k}", 0)
        return self._rd()

    def fx(self, n):
        if self.dry:
            return {"type": "?"}
        coll = E.Collector()
        self.conn.send(f"/eos/get/fx/{n}")
        t = l = time.time()
        while time.time() - t < 5:
            m = self.conn.recv()
            if m:
                for a, g in m:
                    coll.feed(a, g)
                l = time.time()
            elif time.time() - l > 0.35:
                break
        r = E.build(coll).get("fx", {}).get(str(n))
        return r if r and r.get("type") else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--map", required=True,
                    help="SRCLO-SRCHI:DSTLO  e.g. 100-159:800")
    a = ap.parse_args()

    src, dst_lo = a.map.split(":")
    lo, hi = (int(x) for x in src.split("-"))
    dst_lo = int(dst_lo)

    conn = None if a.dry_run else E.Conn(a.host, a.port)
    m = Mover(conn, a.dry_run)
    if conn:
        m.key("live")
        m.cmd("Sneak Time 0")

    moved, skipped = 0, 0
    for i, n in enumerate(range(lo, hi + 1)):
        d = dst_lo + i
        before = m.fx(n)
        if not before:
            skipped += 1
            continue
        m.cmd(f"Effect {n} Copy_To Effect {d}")
        after = m.fx(d)
        if not after:
            m.errors.append((n, "clone did not appear"))
            print(f"  !! {n} -> {d}  CLONE FAILED, original kept", file=sys.stderr)
            continue
        fields = ("type", "entry", "exit", "duration", "scale")
        if any(before.get(f) != after.get(f) for f in fields):
            m.errors.append((n, "metadata differs"))
            print(f"  !! {n} -> {d}  metadata differs, original kept", file=sys.stderr)
            continue
        m.cmd(f"Effect {d} Label {before.get('label','')}")
        m.cmd(f"Delete Effect {n}")
        m.key("enter")
        moved += 1
        if moved % 10 == 0:
            print(f"  moved {moved} ...")

    if conn:
        conn.send("/eos/key/save_show", 1); conn.send("/eos/key/save_show", 0)
        end, saved = time.time() + 15, None
        while time.time() < end and not saved:
            for addr, args in conn.recv():
                if addr == "/eos/out/event/show/saved":
                    saved = args[0]
        print(f"\nsaved -> {saved or 'NOT SAVED'}")
        conn.close()
    print(f"moved {moved}, skipped {skipped} (did not exist), "
          f"{len(m.errors)} errors, {m.n} commands")
    for n, why in m.errors:
        print(f"  FAILED {n}: {why}")
    return 1 if m.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
