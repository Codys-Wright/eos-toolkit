#!/usr/bin/env python3
"""
eosdump - pull show data out of a running ETC Eos / Eos Nomad over OSC.

No third-party dependencies. Speaks OSC 1.0 (packet-length framed) or
OSC 1.1 (SLIP) over TCP, or plain UDP.

Protocol reference: Eos Family Show Control User Guide,
"Appendix: Advanced OSC" -> "Integrating Your App with Eos".
"""

import argparse
import json
import re
import socket
import struct
import sys
import time
from datetime import datetime

# ---------------------------------------------------------------- OSC codec

def _pad(b):
    """OSC pads every chunk out to a multiple of 4 bytes."""
    return b + b"\0" * (-len(b) % 4)


def enc_str(s):
    return _pad(s.encode("utf-8") + b"\0")


def enc_msg(addr, args=()):
    tags = ","
    body = b""
    for a in args:
        if isinstance(a, bool):
            tags += "T" if a else "F"
        elif isinstance(a, int):
            tags += "i"
            body += struct.pack(">i", a)
        elif isinstance(a, float):
            tags += "f"
            body += struct.pack(">f", a)
        else:
            tags += "s"
            body += enc_str(str(a))
    return enc_str(addr) + enc_str(tags) + body


def _read_str(data, i):
    end = data.index(b"\0", i)
    s = data[i:end].decode("utf-8", "replace")
    return s, i + (-(-(end - i + 1) // 4)) * 4


def dec_packet(data, out):
    """Decode one OSC packet (message or bundle) into out as (addr, args)."""
    if data[:8] == b"#bundle\0":
        i = 16  # skip '#bundle\0' + 8-byte timetag
        while i + 4 <= len(data):
            (n,) = struct.unpack_from(">i", data, i)
            i += 4
            if n <= 0 or i + n > len(data):
                break
            dec_packet(data[i:i + n], out)
            i += n
        return out
    try:
        addr, i = _read_str(data, 0)
        tags, i = _read_str(data, i)
    except (ValueError, IndexError):
        return out
    args = []
    for t in tags[1:]:
        try:
            if t == "i":
                args.append(struct.unpack_from(">i", data, i)[0]); i += 4
            elif t == "f":
                args.append(round(struct.unpack_from(">f", data, i)[0], 6)); i += 4
            elif t == "h":
                args.append(struct.unpack_from(">q", data, i)[0]); i += 8
            elif t == "d":
                args.append(struct.unpack_from(">d", data, i)[0]); i += 8
            elif t == "s" or t == "S":
                s, i = _read_str(data, i); args.append(s)
            elif t == "b":
                (n,) = struct.unpack_from(">i", data, i); i += 4 + (-(-n // 4)) * 4
                args.append(None)
            elif t == "T":
                args.append(True)
            elif t == "F":
                args.append(False)
            elif t in "NI":
                args.append(None)
        except (struct.error, ValueError, IndexError):
            break
    out.append((addr, args))
    return out

# ------------------------------------------------------------- transports

SLIP_END, SLIP_ESC, SLIP_ESC_END, SLIP_ESC_ESC = 0xC0, 0xDB, 0xDC, 0xDD


class Conn:
    """TCP (length-prefixed or SLIP) / UDP transport for OSC packets."""

    def __init__(self, host, port, mode="tcp", slip=False, rx_port=8001, timeout=5.0):
        self.mode, self.slip, self.buf = mode, slip, b""
        if mode == "tcp":
            self.sock = socket.create_connection((host, port), timeout=timeout)
        else:
            self.dest = (host, port)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("", rx_port))
        self.sock.settimeout(0.15)

    def send(self, addr, *args):
        pkt = enc_msg(addr, args)
        if self.mode == "udp":
            self.sock.sendto(pkt, self.dest)
        elif self.slip:
            f = bytearray([SLIP_END])
            for b in pkt:
                if b == SLIP_END:
                    f += bytes([SLIP_ESC, SLIP_ESC_END])
                elif b == SLIP_ESC:
                    f += bytes([SLIP_ESC, SLIP_ESC_ESC])
                else:
                    f.append(b)
            f.append(SLIP_END)
            self.sock.sendall(bytes(f))
        else:
            self.sock.sendall(struct.pack(">I", len(pkt)) + pkt)

    def recv(self):
        """Return a list of (addr, args) available right now."""
        try:
            chunk = self.sock.recv(65536) if self.mode == "tcp" else self.sock.recv(65536)
        except socket.timeout:
            return []
        except OSError:
            return []
        if not chunk:
            return []
        out = []
        if self.mode == "udp":
            dec_packet(chunk, out)
            return out
        self.buf += chunk
        if self.slip:
            while SLIP_END in self.buf:
                i = self.buf.index(bytes([SLIP_END]))
                frame, self.buf = self.buf[:i], self.buf[i + 1:]
                if not frame:
                    continue
                d, esc = bytearray(), False
                for b in frame:
                    if esc:
                        d.append(SLIP_END if b == SLIP_ESC_END else SLIP_ESC)
                        esc = False
                    elif b == SLIP_ESC:
                        esc = True
                    else:
                        d.append(b)
                dec_packet(bytes(d), out)
        else:
            while len(self.buf) >= 4:
                (n,) = struct.unpack_from(">I", self.buf, 0)
                if len(self.buf) < 4 + n:
                    break
                dec_packet(self.buf[4:4 + n], out)
                self.buf = self.buf[4 + n:]
        return out

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

# ------------------------------------------------------------- collector

NUMERIC = re.compile(r"^[0-9]+(\.[0-9]+)?$")


class Collector:
    """Reassembles OSC List Convention replies into complete arg lists."""

    def __init__(self):
        self.parts = {}   # base address -> {offset: arg}
        self.plain = {}   # address -> args (replies with no /list/ segment)

    def feed(self, addr, args):
        if "/list/" in addr:
            base, tail = addr.rsplit("/list/", 1)
            bits = tail.split("/")
            try:
                off = int(bits[0])
            except ValueError:
                off = 0
            slot = self.parts.setdefault(base, {})
            for k, a in enumerate(args):
                slot[off + k] = a
        else:
            self.plain[addr] = args

    def messages(self):
        """Yield (base_address, ordered_args) for every reply, list-split or not.

        Replies like /eos/out/get/patch/1/1/notes arrive whole, with no /list/
        segment, so they must be yielded alongside the reassembled ones.
        """
        for base, slot in self.parts.items():
            yield base, [slot[k] for k in sorted(slot)]
        for addr, args in self.plain.items():
            yield addr, args

# ------------------------------------------------------- record schemas

PATCH = ["index", "uid", "label", "manufacturer", "model", "address",
         "intensity_address", "current_level", "gel"] + \
        [f"text{i}" for i in range(1, 11)] + ["part_count"]

CUELIST = ["index", "uid", "label", "playback_mode", "fader_mode", "independent",
           "htp", "assert", "block", "background", "solo_mode", "timecode_list",
           "oos_sync"]

CUE = ["index", "uid", "label", "up_time", "up_delay", "down_time", "down_delay",
       "focus_time", "focus_delay", "color_time", "color_delay", "beam_time",
       "beam_delay", "preheat", "curve", "rate", "mark", "block", "assert",
       "link", "follow", "hang", "all_fade", "loop", "solo", "timecode",
       "part_count"]

SUB = ["index", "uid", "label", "mode", "fader_mode", "htp", "exclusive",
       "background", "restore", "priority", "up_time", "dwell_time", "down_time"]

PRESETISH = ["index", "uid", "label", "absolute", "locked"]
FX = ["index", "uid", "label", "type", "entry", "exit", "duration", "scale"]
MACRO = ["index", "uid", "label", "mode"]
LABELED = ["index", "uid", "label"]
PIXMAP = ["index", "uid", "label", "server_channel", "interface", "width",
          "height", "pixel_count", "fixture_count"]

SCHEMA = {
    "patch": PATCH, "cuelist": CUELIST, "cue": CUE, "sub": SUB,
    "preset": PRESETISH, "ip": PRESETISH, "fp": PRESETISH,
    "cp": PRESETISH, "bp": PRESETISH,
    "fx": FX, "macro": MACRO, "group": LABELED, "curve": LABELED,
    "snap": LABELED, "ms": LABELED, "pixmap": PIXMAP,
}

# Target types that support /count and /index queries.
SIMPLE_TARGETS = ["patch", "cuelist", "group", "macro", "sub", "preset",
                  "ip", "fp", "cp", "bp", "curve", "fx", "snap", "pixmap", "ms"]

PLURAL = {"patch": "patch", "cuelist": "cuelists", "cue": "cues",
          "group": "groups", "macro": "macros", "sub": "subs",
          "preset": "presets", "ip": "intensity_palettes",
          "fp": "focus_palettes", "cp": "color_palettes",
          "bp": "beam_palettes", "curve": "curves", "fx": "effects",
          "snap": "snapshots", "pixmap": "pixel_maps", "ms": "magic_sheets"}

# ------------------------------------------------------------- the dump

IDLE_SCALE = 1.0      # raised by --slow for networked consoles


def drain(conn, coll, idle=0.45, hard=120.0):
    """Read replies until the console goes quiet for `idle` seconds."""
    start = last = time.time()
    n = 0
    while time.time() - start < hard:
        msgs = conn.recv()
        if msgs:
            for addr, args in msgs:
                coll.feed(addr, args)
                n += 1
            last = time.time()
        elif time.time() - last > idle:
            break
    return n


def ask_count(conn, coll, path, tries=3):
    """How many of `path` exist?

    NEVER return 0 for "no reply". Over a network the console can be slower
    than the drain window, and a silent 0 is indistinguishable from an empty
    section - this reported a full 100-preset library as empty and very nearly
    got the transfer declared broken. Retry, then say so loudly.
    """
    key = f"/eos/out/get/{path}/count"
    for attempt in range(tries):
        conn.send(f"/eos/get/{path}/count")
        drain(conn, coll, idle=0.35 * IDLE_SCALE, hard=8 * IDLE_SCALE)
        args = coll.plain.get(key)
        if args:
            return int(args[0])
        if attempt + 1 < tries:
            print(f"  (no count for {path}, retry {attempt + 1})", file=sys.stderr)
    raise SystemExit(
        f"No count reply for '{path}' after {tries} tries.\n"
        f"  This is NOT the same as zero. Likely a slow link - try --slow.")


def dump(conn, verbose=True):
    coll = Collector()

    conn.send("/eos/get/version")
    drain(conn, coll, idle=0.4 * IDLE_SCALE, hard=8 * IDLE_SCALE)
    ver = coll.plain.get("/eos/out/get/version")
    if not ver:
        raise SystemExit(
            "No reply from Eos.\n"
            "  * Is the show open in Eos/Nomad?\n"
            "  * Setup > System > Show Control: enable {String RX} and {String TX}\n"
            "  * ECU > Settings > Network > Interface Protocols: enable {UDP Strings & OSC}\n"
            "  * If OSC TCP mode is set to OSC 1.1, re-run with --slip\n"
        )
    version = ver[0]
    if verbose:
        print(f"connected to Eos {version}")

    counts = {}
    for t in SIMPLE_TARGETS:
        counts[t] = ask_count(conn, coll, t)
        if verbose and counts[t]:
            print(f"  {t:<8} {counts[t]}")

    for t in SIMPLE_TARGETS:
        for lo in range(0, counts[t], 40):
            for i in range(lo, min(lo + 40, counts[t])):
                conn.send(f"/eos/get/{t}/index/{i}")
            drain(conn, coll)

    # Cue lists are enumerated first, then cues are queried per list.
    lists = sorted({b.split("/")[5] for b, _ in coll.messages()
                    if b.startswith("/eos/out/get/cuelist/")})
    cue_counts = {}
    for cl in lists:
        cue_counts[cl] = ask_count(conn, coll, f"cue/{cl}")
        if verbose and cue_counts[cl]:
            print(f"  cue list {cl}: {cue_counts[cl]} cues")
        for lo in range(0, cue_counts[cl], 40):
            for i in range(lo, min(lo + 40, cue_counts[cl])):
                conn.send(f"/eos/get/cue/{cl}/index/{i}")
            drain(conn, coll)

    return version, coll, counts


def build(coll):
    """Turn reassembled OSC replies into nested records keyed by target number."""
    store = {}

    def slot(ttype, nums):
        return store.setdefault(ttype, {}).setdefault("/".join(nums), {"target": "/".join(nums)})

    for base, args in coll.messages():
        if not base.startswith("/eos/out/get/"):
            continue
        parts = base[len("/eos/out/get/"):].split("/")
        ttype, rest = parts[0], parts[1:]
        # Peel off EVERY trailing non-numeric token, not just one. Eos 3.x adds
        # nested sub-keys the 2.x spec never documented, e.g.
        # /eos/out/get/patch/1/1/augment3d/position -> target 1/1, key
        # "augment3d_position". Peeling only one token would make "augment3d"
        # look like part of the target number and invent a phantom channel.
        tail = []
        while rest and not NUMERIC.match(rest[-1]):
            tail.insert(0, rest.pop())
        subkey = "_".join(tail) if tail else None
        if not rest or subkey == "count":
            # e.g. /eos/out/get/cue/1/count is a tally, not a cue record.
            continue
        rec = slot(ttype, rest)
        if subkey is None:
            fields = SCHEMA.get(ttype)
            if fields:
                for k, name in enumerate(fields):
                    if k < len(args):
                        rec[name] = args[k]
            else:
                rec["args"] = args
        else:
            # sub-messages are [index, uid, *values]
            rec[subkey] = args[2:] if len(args) > 2 else []
    return store


def to_json(version, store, counts, host):
    out = {"meta": {"eos_version": version, "host": host,
                    "dumped_at": datetime.now().isoformat(timespec="seconds"),
                    "counts": counts}}
    for ttype, recs in store.items():
        key = PLURAL.get(ttype, ttype)
        if ttype == "cue":
            grouped = {}
            for t, r in recs.items():
                grouped.setdefault(t.split("/")[0], []).append(r)
            for k in grouped:
                grouped[k].sort(key=lambda r: r.get("index", 0))
            out[key] = grouped
        else:
            out[key] = sorted(recs.values(), key=lambda r: r.get("index", 0))
    return out

# --------------------------------------------------------------- digest

def ms(v):
    """Format an Eos duration. Eos uses -1 to mean 'not set / inherit'."""
    if not isinstance(v, (int, float)):
        return ""
    if v < 0:
        return "\u2014"          # em dash: unset, not zero
    if v == 0:
        return "0"
    return f"{v / 1000:g}"


def esc(v):
    return str(v if v is not None else "").replace("|", "\\|").strip()


def opt(v):
    """Render Eos's -1 'unset' sentinel as an em dash rather than a number."""
    if isinstance(v, (int, float)) and v < 0:
        return "\u2014"
    return esc(v)


def digest(doc):
    L = []
    m = doc["meta"]
    L.append(f"# Eos show dump\n")
    L.append(f"- Console: Eos **{m['eos_version']}** at `{m['host']}`")
    L.append(f"- Captured: {m['dumped_at']}\n")

    patch = doc.get("patch", [])
    if patch:
        L.append(f"## Patch ({len(patch)} entries)\n")
        L.append("| Chan | Part | Label | Manufacturer | Model | Addr | Gel | Notes |")
        L.append("|---|---|---|---|---|---|---|---|")
        for p in patch:
            t = p["target"].split("/")
            note = p.get("notes") or []
            L.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                t[0], t[1] if len(t) > 1 else "", esc(p.get("label")),
                esc(p.get("manufacturer")), esc(p.get("model")),
                p.get("address", ""), esc(p.get("gel")),
                esc(note[0]) if note else ""))
        L.append("")

    cls = doc.get("cuelists", [])
    cues = doc.get("cues", {})
    for cl in cls:
        n = cl["target"]
        rows = cues.get(n, [])
        L.append(f"## Cue list {n} — {esc(cl.get('label')) or '(no label)'} "
                 f"({len(rows)} cues)\n")
        L.append("| Cue | Label | Up | Down | Follow | Hang | Mark | Block | Link | Loop | Timecode |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for c in rows:
            t = c["target"].split("/")
            num = t[1] if len(t) > 1 else "?"
            part = t[2] if len(t) > 2 else "0"
            label = esc(c.get("label"))
            if part not in ("0", ""):
                num = f"{num} p{part}"
            L.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                num, label, ms(c.get("up_time")), ms(c.get("down_time")),
                ms(c.get("follow")), ms(c.get("hang")), esc(c.get("mark")),
                esc(c.get("block")), opt(c.get("link")), opt(c.get("loop")),
                esc(c.get("timecode"))))
        L.append("")

    def simple(key, title, cols, getters):
        rows = doc.get(key, [])
        if not rows:
            return
        L.append(f"## {title} ({len(rows)})\n")
        L.append("| " + " | ".join(cols) + " |")
        L.append("|" + "---|" * len(cols))
        for r in rows:
            L.append("| " + " | ".join(str(g(r)) for g in getters) + " |")
        L.append("")

    chans = lambda r: esc(", ".join(str(x) for x in r.get("channels", [])))
    simple("groups", "Groups", ["Num", "Label", "Channels"],
           [lambda r: r["target"], lambda r: esc(r.get("label")), chans])
    simple("subs", "Submasters", ["Num", "Label", "Mode", "Fader", "HTP", "Up", "Dwell", "Down"],
           [lambda r: r["target"], lambda r: esc(r.get("label")),
            lambda r: esc(r.get("mode")), lambda r: esc(r.get("fader_mode")),
            lambda r: r.get("htp", ""), lambda r: esc(r.get("up_time")),
            lambda r: esc(r.get("dwell_time")), lambda r: esc(r.get("down_time"))])
    simple("effects", "Effects", ["Num", "Label", "Type", "Entry", "Exit", "Duration", "Scale"],
           [lambda r: r["target"], lambda r: esc(r.get("label")),
            lambda r: esc(r.get("type")), lambda r: esc(r.get("entry")),
            lambda r: esc(r.get("exit")), lambda r: esc(r.get("duration")),
            lambda r: r.get("scale", "")])
    simple("macros", "Macros", ["Num", "Label", "Mode", "Text"],
           [lambda r: r["target"], lambda r: esc(r.get("label")),
            lambda r: esc(r.get("mode")),
            lambda r: esc(" ".join(str(x) for x in r.get("text", [])))])
    for k, title in [("presets", "Presets"), ("intensity_palettes", "Intensity palettes"),
                     ("focus_palettes", "Focus palettes"), ("color_palettes", "Color palettes"),
                     ("beam_palettes", "Beam palettes")]:
        simple(k, title, ["Num", "Label", "Channels"],
               [lambda r: r["target"], lambda r: esc(r.get("label")), chans])
    simple("magic_sheets", "Magic sheets", ["Num", "Label"],
           [lambda r: r["target"], lambda r: esc(r.get("label"))])
    simple("snapshots", "Snapshots", ["Num", "Label"],
           [lambda r: r["target"], lambda r: esc(r.get("label"))])
    simple("curves", "Curves", ["Num", "Label"],
           [lambda r: r["target"], lambda r: esc(r.get("label"))])
    return "\n".join(L) + "\n"

# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description="Dump ETC Eos show data over OSC.")
    ap.add_argument("--slow", action="store_true",
                    help="stretch every wait ~4x: use for a console over the "
                         "network, where replies are far slower than localhost")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Eos/Nomad IP (default 127.0.0.1 for Nomad on this machine)")
    ap.add_argument("--port", type=int, default=None,
                    help="TCP 3032 by default; with --udp, the Eos OSC RX port (8000)")
    ap.add_argument("--udp", action="store_true", help="use UDP instead of TCP")
    ap.add_argument("--rx-port", type=int, default=8001,
                    help="UDP only: local port to listen on = Eos {OSC TX Port} (8001)")
    ap.add_argument("--slip", action="store_true",
                    help="TCP only: console is set to OSC 1.1 (SLIP) mode")
    ap.add_argument("-o", "--out", default="show", help="output basename (default: show)")
    ap.add_argument("--raw", action="store_true",
                    help="also write <out>.raw.txt listing every reply address seen")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args()
    if a.slow:
        global IDLE_SCALE
        IDLE_SCALE = 4.0

    port = a.port if a.port else (8000 if a.udp else 3032)
    mode = "udp" if a.udp else "tcp"

    try:
        conn = Conn(a.host, port, mode=mode, slip=a.slip, rx_port=a.rx_port)
    except OSError as e:
        raise SystemExit(f"Could not reach {a.host}:{port} ({mode.upper()}): {e}")

    try:
        version, coll, counts = dump(conn, verbose=not a.quiet)
    finally:
        conn.close()

    if a.raw:
        with open(f"{a.out}.raw.txt", "w") as f:
            for base, args in sorted(coll.messages()):
                f.write(f"{base}\t{len(args)} args\n")

    doc = to_json(version, build(coll), counts, f"{a.host}:{port}")
    with open(f"{a.out}.json", "w") as f:
        json.dump(doc, f, indent=2)
    with open(f"{a.out}.md", "w") as f:
        f.write(digest(doc))
    if not a.quiet:
        print(f"\nwrote {a.out}.json and {a.out}.md")


if __name__ == "__main__":
    main()
