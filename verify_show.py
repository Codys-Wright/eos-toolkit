#!/usr/bin/env python3
"""
Prove cue list 1 matches the run sheet: every cue present, with the right
label, link and block flag.

The whole structure depends on LINKS - each cue points at the next, and the act
videos are blocked so acts can be reordered. A wrong or missing link does not
error, it just quietly plays the wrong thing next, which you would discover
during the show.

Reads with generous timeouts because the console is over the network. A missing
reply is reported as UNKNOWN, never as absent - see ask_count in eosdump.py for
why that distinction matters.

  python3 verify_show.py --host 10.0.0.5
"""
import argparse, sys, time
import eosdump as E
import build_show as S

CUE = E.CUE          # field order of a cue reply


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="10.0.0.5")
    ap.add_argument("--port", type=int, default=3032)
    a = ap.parse_args()
    c = E.Conn(a.host, a.port, timeout=8.0)

    def fetch(cue, tries=3, wait=2.2):
        """Read one cue's record. None means no reply - NOT "absent".

        The address needs a PART index: /eos/get/cue/1/110/0. Without it the
        console sends only live playback chatter and no record at all, which
        looks exactly like a missing cue. That reported all 42 as missing when
        every one of them was fine.
        """
        for _ in range(tries):
            c.send(f"/eos/get/cue/1/{cue}/0")
            coll = E.Collector()
            end = time.time() + wait
            while time.time() < end:
                for ad, g in c.recv():
                    coll.feed(ad, g)
            for base, args in coll.messages():
                if base.endswith(f"/cue/1/{cue}/0") and len(args) > 20:
                    rec = dict(zip(CUE, args))
                    # notes follow the schema'd fields
                    rec["notes"] = args[len(CUE)] if len(args) > len(CUE) else ""
                    return rec
        return None

    print(f"  checking {len(S.SHOW)} cues against the run sheet\n")
    missing, wrong = [], []
    for cue, label, t, link, cmds, note in S.SHOW:
        rec = fetch(cue)
        if rec is None:
            print(f"   1/{cue:<5} {label:<16} UNKNOWN - no reply")
            missing.append(cue); continue
        got_label = str(rec.get("label", ""))
        got_link = str(rec.get("link", "")).strip()
        got_block = str(rec.get("block", "")).strip()
        probs = []
        if got_label != label:
            probs.append(f"label {got_label!r} != {label!r}")
        if link and got_link not in (str(link), f"{link}.0"):
            probs.append(f"link {got_link!r} != {link}")
        if cue in S.BLOCKED and not got_block:
            probs.append("not blocked")
        mark = "ok" if not probs else "; ".join(probs)
        print(f"   1/{cue:<5} {got_label:<16} link {got_link:<6} "
              f"{'B' if got_block else ' '}  {mark}")
        if probs:
            wrong.append((cue, probs))

    c.close()
    print(f"\n{len(S.SHOW)} cues, {len(wrong)} wrong, {len(missing)} no reply")
    for cue, probs in wrong:
        print(f"   1/{cue}: {'; '.join(probs)}")
    if missing:
        print("   no reply for:", missing, "- re-run, do not assume missing")
    return 1 if (wrong or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
