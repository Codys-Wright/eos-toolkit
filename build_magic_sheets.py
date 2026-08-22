#!/usr/bin/env python3
"""
Generate Eos control-surface magic sheets as importable .xml.

Reads the live console for target labels, then writes one sheet per library.
Buttons use real TARGETs (not CMD) so they show live state - an active preset
or running effect highlights itself, which a command button cannot do.

  TARGETTYPE 3=Group 9=Preset 13=Effect 10=Sub 2=Cue
  TARGETTYPE 6 + TARGETLISTID 1=IP 2=FP 3=CP 4=BP

Import each with: magic sheet editor > Background Settings tab > import icon.

  python3 build_magic_sheets.py --template <an exported sheet>.xml
"""
import argparse, copy, os, time
import eosdump as E
import ms_gen as M

BTN_W, BTN_H = 130, 74
DX, DY = 142, 86


def fetch(conn, kind, count_path=None):
    """Pull {number: label} for a target type off the console."""
    coll = E.Collector()
    cp = count_path or kind
    conn.send(f"/eos/get/{cp}/count")

    def drain(idle=0.5, hard=40):
        s = l = time.time()
        while time.time() - s < hard:
            m = conn.recv()
            if m:
                for a, g in m:
                    coll.feed(a, g)
                l = time.time()
            elif time.time() - l > idle:
                break
    drain()
    n = int((coll.plain.get(f"/eos/out/get/{cp}/count") or [0])[0])
    for lo in range(0, n, 40):
        for i in range(lo, min(lo + 40, n)):
            conn.send(f"/eos/get/{cp}/index/{i}")
        drain()
    out = {}
    for r in (E.build(coll).get(kind) or {}).values():
        t = r["target"].split("/")[0]
        out[t] = r.get("label", "") or ""
    return out


def sheet(tpl_tree, btn_tpl, entries, cols, targettype, targetlistid=None,
          title=None):
    """entries = [(targetid, label), ...] laid out on a grid."""
    out = M.new_sheet(tpl_tree)
    for n, (tid, label) in enumerate(entries):
        it = copy.deepcopy(btn_tpl)
        M.set_item(it,
                   x=(n % cols) * DX,
                   y=(n // cols) * DY,
                   w=BTN_W, h=BTN_H,
                   targettype=targettype, targetid=tid,
                   targetlistid=targetlistid,
                   text=label[:16])
        M.add(out, it)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--template", required=True,
                    help="an exported magic sheet .xml with a Button object")
    ap.add_argument("--outdir", default=os.path.expanduser("~/Downloads"))
    a = ap.parse_args()

    tpl = M.load(a.template)
    try:
        btn = M.find_template(tpl, "Button")
    except KeyError:
        btn = M.find_template(tpl, "ChannelButton")

    conn = E.Conn(a.host, a.port)
    print("reading the console...")
    groups  = fetch(conn, "group")
    presets = fetch(conn, "preset")
    effects = fetch(conn, "fx")
    subs    = fetch(conn, "sub")
    cps     = fetch(conn, "cp")
    fps     = fetch(conn, "fp")
    conn.close()

    def rows(d, lo=None, hi=None):
        ks = sorted(d, key=lambda x: float(x))
        if lo is not None:
            ks = [k for k in ks if lo <= float(k) <= hi]
        return [(k, d[k] or f"#{k}") for k in ks]

    jobs = [
        ("MS - GROUPS.xml",   rows(groups),                10, M.TARGETTYPE["group"],   None),
        ("MS - COLOURS.xml",  rows(cps),                   10, M.TARGETTYPE["palette"], M.PALETTE_LIST["cp"]),
        ("MS - PRESETS.xml",  rows(presets),               10, M.TARGETTYPE["preset"],  None),
        ("MS - FX SUBS.xml",  rows(subs),                  10, M.TARGETTYPE["sub"],     None),
        ("MS - EFFECTS.xml",  rows(effects, 200, 399),      8, M.TARGETTYPE["effect"],  None),
        ("MS - FOCUS.xml",    rows(fps),                    9, M.TARGETTYPE["palette"], M.PALETTE_LIST["fp"]),
    ]
    for name, entries, cols, tt, tlid in jobs:
        if not entries:
            print(f"  skip {name} (nothing to place)")
            continue
        s = sheet(tpl, btn, entries, cols, tt, tlid)
        p = os.path.join(a.outdir, name)
        M.save(s, p)
        print(f"  {name:<22} {len(entries):>4} buttons, {cols} cols")
    print(f"\nwritten to {a.outdir}")
    print("import each: magic sheet editor > Background Settings tab > import icon")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
