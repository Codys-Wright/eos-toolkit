#!/usr/bin/env python3
"""
Compare a remote console against this machine's, section by section.

A full eosdump over a network link can time out on the biggest sections, and a
timed-out section is NOT an empty one - see ask_count in eosdump.py. This asks
for counts only, with retries and generous waits, so it works over WiFi.

  python3 check_remote.py 10.0.0.5
"""
import sys, time
import eosdump as E

SECTIONS = ["patch", "group", "fp", "cp", "bp", "ip", "preset",
            "sub", "macro", "fx", "cuelist", "curve", "snap", "ms"]


def counts(host, tries=4, wait=2.5):
    c = E.Conn(host, 3032, timeout=8.0)
    out = {}
    for sec in SECTIONS:
        for _ in range(tries):
            c.send(f"/eos/get/{sec}/count")
            end = time.time() + wait
            got = None
            while time.time() < end:
                for a, g in c.recv():
                    if a == f"/eos/out/get/{sec}/count" and g:
                        got = int(g[0])
            if got is not None:
                out[sec] = got
                break
        else:
            out[sec] = None          # no reply - explicitly NOT zero
    c.close()
    return out


def main():
    remote = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.5"
    local = counts("127.0.0.1")
    rem = counts(remote)
    print(f"  section    local  {remote}")
    diffs, unknown = [], []
    for sec in SECTIONS:
        a, b = local.get(sec), rem.get(sec)
        if b is None or a is None:
            mark, _ = "   <-- NO REPLY (unknown, not zero)", unknown.append(sec)
        elif a != b:
            mark = "   <-- DIFFERS"; diffs.append(sec)
        else:
            mark = ""
        print(f"  {sec:<9} {str(a):>6} {str(b):>9}{mark}")
    print()
    print("  differing:", diffs or "none")
    if unknown:
        print("  no reply for:", unknown, "- re-run, do not assume empty")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
