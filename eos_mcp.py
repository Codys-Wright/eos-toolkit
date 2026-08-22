#!/usr/bin/env python3
"""
eos-mcp - an MCP server that lets Claude read and drive an ETC Eos console.

Transport: MCP over stdio (newline-delimited JSON-RPC 2.0). No dependencies.
Talks to Eos with the same OSC codec as eosdump.py.

SAFETY TIERS
  default            read-only: status, show data, ping. Cannot change anything.
  --allow-control    adds eos_cmd / eos_key / eos_at. Can move lights and run cues.
  --allow-destructive  additionally permits Record / Update / Delete / Power_Off
                     and friends, which can overwrite or destroy show data.

Each tier must be opted into explicitly on the command line. There is no way to
escalate at runtime.
"""

import argparse
import json
import os
import re
import sys
import threading
import time

import eosdump as E

# --------------------------------------------------------------- Eos link

class EosLink:
    """Persistent connection to Eos: pumps implicit output, runs get-queries."""

    def __init__(self, host, port, slip=False):
        self.host, self.port, self.slip = host, port, slip
        self.lock = threading.Lock()
        self.state = {}          # /eos/out/... implicit output, latest wins
        self.coll = E.Collector()
        self.count = 0           # messages seen; used as a quiet-detector
        self.version = None
        self.conn = None
        self.error = None
        self._connect()
        threading.Thread(target=self._pump, daemon=True).start()

    def _connect(self):
        try:
            self.conn = E.Conn(self.host, self.port, mode="tcp", slip=self.slip)
            self.error = None
        except OSError as e:
            self.conn, self.error = None, str(e)

    def _pump(self):
        while True:
            if self.conn is None:
                time.sleep(2.0)
                self._connect()
                continue
            try:
                msgs = self.conn.recv()
            except OSError as e:
                self.conn, self.error = None, str(e)
                continue
            if not msgs:
                continue
            with self.lock:
                for addr, args in msgs:
                    self.count += 1
                    if addr.startswith("/eos/out/get/"):
                        self.coll.feed(addr, args)
                    else:
                        self.state[addr] = args

    def send(self, addr, *args):
        if self.conn is None:
            raise RuntimeError(f"not connected to Eos ({self.error or 'no link'})")
        self.conn.send(addr, *args)

    def quiet(self, idle=0.4, hard=15.0):
        """Block until the console stops sending for `idle` seconds."""
        start = time.time()
        last_n, last_t = self.count, time.time()
        while time.time() - start < hard:
            time.sleep(0.05)
            with self.lock:
                n = self.count
            if n != last_n:
                last_n, last_t = n, time.time()
            elif time.time() - last_t > idle:
                return
        return

    def ping(self):
        self.send("/eos/ping", "eos-mcp")
        self.quiet(idle=0.25, hard=4)
        return "/eos/out/ping" in self.state

    def get_version(self):
        if self.version:
            return self.version
        self.send("/eos/get/version")
        self.quiet(idle=0.3, hard=5)
        v = self.coll.plain.get("/eos/out/get/version")
        self.version = v[0] if v else None
        return self.version

    def dump(self):
        """Full show dump, reusing eosdump's query plan against the live link."""
        with self.lock:
            self.coll = E.Collector()
        self.send("/eos/get/version")
        self.quiet(idle=0.3, hard=5)

        counts = {}
        for t in E.SIMPLE_TARGETS:
            self.send(f"/eos/get/{t}/count")
            self.quiet(idle=0.3, hard=6)
            a = self.coll.plain.get(f"/eos/out/get/{t}/count")
            counts[t] = int(a[0]) if a else 0

        for t in E.SIMPLE_TARGETS:
            for lo in range(0, counts[t], 40):
                for i in range(lo, min(lo + 40, counts[t])):
                    self.send(f"/eos/get/{t}/index/{i}")
                self.quiet()

        lists = sorted({b.split("/")[5] for b, _ in self.coll.messages()
                        if b.startswith("/eos/out/get/cuelist/")})
        for cl in lists:
            self.send(f"/eos/get/cue/{cl}/count")
            self.quiet(idle=0.3, hard=6)
            a = self.coll.plain.get(f"/eos/out/get/cue/{cl}/count")
            n = int(a[0]) if a else 0
            for lo in range(0, n, 40):
                for i in range(lo, min(lo + 40, n)):
                    self.send(f"/eos/get/cue/{cl}/index/{i}")
                self.quiet()

        ver = self.coll.plain.get("/eos/out/get/version")
        return E.to_json(ver[0] if ver else "unknown", E.build(self.coll),
                         counts, f"{self.host}:{self.port}")

# ------------------------------------------------------------ safety gate

# Commands that alter stored show data or the console itself. Blocked unless
# --allow-destructive. Matched case-insensitively against the command string.
DESTRUCTIVE = re.compile(
    r"(?:^|[\s\[])(record|update|delete|erase|replace|copy_to|move_to|"
    r"power_off|reset|new_show|open_show|save_show)(?:$|[\s\]])", re.I)


def classify(cmd):
    m = DESTRUCTIVE.search(cmd)
    return m.group(1).lower() if m else None

# ---------------------------------------------------------------- tooling

def tool_defs(allow_control, allow_destructive):
    tools = [
        {
            "name": "eos_status",
            "description": ("Current live state of the Eos console: active and "
                            "pending cue, command line contents, Live/Blind mode, "
                            "show name, and connection health. Read-only."),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "eos_show_data",
            "description": ("Read show data from the console: patch, cues, groups, "
                            "submasters, palettes, effects, macros, and more. Uses a "
                            "cached snapshot unless refresh=true. Read-only."),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "description": ("Which section to return. Omit for a summary "
                                        "of every section with counts."),
                        "enum": ["patch", "cuelists", "cues", "groups", "subs",
                                 "presets", "intensity_palettes", "focus_palettes",
                                 "color_palettes", "beam_palettes", "curves",
                                 "effects", "snapshots", "magic_sheets",
                                 "pixel_maps", "macros"],
                    },
                    "match": {
                        "type": "string",
                        "description": ("Optional case-insensitive substring filter "
                                        "applied to each record's text."),
                    },
                    "refresh": {
                        "type": "boolean",
                        "description": ("Re-query the console instead of using the "
                                        "cached snapshot. Takes 10-60s on a large show."),
                    },
                },
            },
        },
        {
            "name": "eos_ping",
            "description": "Check that the console is reachable and responding. Read-only.",
            "inputSchema": {"type": "object", "properties": {}},
        },
    ]
    if allow_control:
        extra = ("" if allow_destructive else
                 " Commands that modify stored show data (Record, Update, Delete, "
                 "Power_Off, ...) are BLOCKED on this server.")
        tools += [
            {
                "name": "eos_cmd",
                "description": (
                    "Send a command line to Eos, exactly as typed on the console, "
                    "e.g. 'Chan 1 Thru 48 At Full' or 'Go_To_Cue 12'. Terminate "
                    "with '#' or set enter=true to execute." + extra),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string",
                                    "description": "Eos command line text."},
                        "enter": {"type": "boolean",
                                  "description": "Append '#' to execute. Default true."},
                        "clear_first": {"type": "boolean",
                                        "description": ("Clear the command line before "
                                                        "sending. Default true.")},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "eos_key",
                "description": ("Press a console key by name, e.g. 'go_0', 'stop', "
                                "'live', 'blind', 'clear_cmd', 'out', 'full'." + extra),
                "inputSchema": {
                    "type": "object",
                    "properties": {"key": {"type": "string"}},
                    "required": ["key"],
                },
            },
            {
                "name": "eos_save",
                "description": ("Save the show file. Verified against the "
                                "console's own save-confirmation event, and "
                                "returns the path actually written. Requires "
                                "--allow-destructive."),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "eos_at",
                "description": ("Set one or more channels to an intensity level. "
                                "Safer and more direct than eos_cmd for simple level "
                                "changes. Level is 0-100."),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "channels": {"type": "string",
                                     "description": "e.g. '1', '1-48', '1,5,9'"},
                        "level": {"type": "number",
                                  "description": "0-100 intensity percentage."},
                    },
                    "required": ["channels", "level"],
                },
            },
        ]
    return tools

# ------------------------------------------------------------ tool bodies

class Server:
    def __init__(self, link, args):
        self.link = link
        self.allow_control = args.allow_control
        self.allow_destructive = args.allow_destructive
        self.cache_path = args.cache
        self._cache = None

    # -- read

    def status(self):
        s = self.link.state
        g = lambda k, d="": (s.get(k) or [d])[0]
        out = {
            "connected": self.link.conn is not None,
            "eos_version": self.link.get_version(),
            "host": f"{self.link.host}:{self.link.port}",
            "show_name": g("/eos/out/show/name"),
            "active_cue": g("/eos/out/active/cue/text"),
            "pending_cue": g("/eos/out/pending/cue/text"),
            "command_line": g("/eos/out/cmd"),
            "mode": {0: "Blind", 1: "Live"}.get(g("/eos/out/event/state", None),
                                                "unknown"),
            "previous_cue": g("/eos/out/previous/cue/text"),
            "active_channels": g("/eos/out/active/chan"),
            # Eos publishes no "which tab is focused" message. Softkey labels are
            # the closest available proxy for what context the console is in.
            "softkeys": [x for x in ((s.get(f"/eos/out/softkey/{i}") or [""])[0]
                                     for i in range(1, 13)) if x],
            "user_id": g("/eos/out/user", None),
            "locked": bool(g("/eos/out/event/locked", 0)),
            "wheel_mode": {0.0: "Coarse", 1.0: "Fine"}.get(g("/eos/out/wheel", None)),
            "selection_color_hs": s.get("/eos/out/color/hs") or [],
            "selection_pantilt": s.get("/eos/out/pantilt") or [],
            "control_enabled": self.allow_control,
            "destructive_enabled": self.allow_destructive,
        }
        if self.link.error:
            out["error"] = self.link.error
        return out

    def show_data(self, section=None, match=None, refresh=False):
        doc = self._load(refresh)
        if section is None:
            return {"meta": doc.get("meta", {}),
                    "sections": {k: (len(v) if isinstance(v, list)
                                     else {kk: len(vv) for kk, vv in v.items()})
                                 for k, v in doc.items() if k != "meta"}}
        data = doc.get(section)
        if data is None:
            return {"error": f"no section {section!r}",
                    "available": [k for k in doc if k != "meta"]}
        if match:
            m = match.lower()
            keep = lambda r: m in json.dumps(r).lower()
            if isinstance(data, dict):
                data = {k: [r for r in v if keep(r)] for k, v in data.items()}
            else:
                data = [r for r in data if keep(r)]
        return {section: data}

    def _load(self, refresh):
        if refresh or self._cache is None:
            if refresh or not os.path.exists(self.cache_path):
                doc = self.link.dump()
                with open(self.cache_path, "w") as f:
                    json.dump(doc, f, indent=2)
                self._cache = doc
            else:
                with open(self.cache_path) as f:
                    self._cache = json.load(f)
        return self._cache

    # -- control

    def cmd(self, command, enter=True, clear_first=True):
        if not self.allow_control:
            return {"error": "control is disabled; start with --allow-control"}
        if re.search(r"\bsave_show\b", command, re.I):
            return {"error": "'Save_Show' does nothing as a command-line entry "
                             "on Eos - it is a KEY. Use the eos_save tool."}
        bad = classify(command)
        if bad and not self.allow_destructive:
            return {"error": f"blocked: {command!r} contains '{bad}', which can "
                             f"modify or destroy show data. This server was started "
                             f"without --allow-destructive."}
        text = command if not enter or command.rstrip().endswith("#") else command + "#"
        self.link.send("/eos/newcmd" if clear_first else "/eos/cmd", text)
        self.link.quiet(idle=0.3, hard=5)
        return {"sent": text,
                "command_line": (self.link.state.get("/eos/out/cmd") or [""])[0],
                "active_cue": (self.link.state.get("/eos/out/active/cue/text") or [""])[0]}

    def key(self, name):
        if not self.allow_control:
            return {"error": "control is disabled; start with --allow-control"}
        bad = classify(name)
        if bad and not self.allow_destructive:
            return {"error": f"blocked: key {name!r} is destructive"}
        self.link.send(f"/eos/key/{name}", 1)
        self.link.send(f"/eos/key/{name}", 0)
        self.link.quiet(idle=0.3, hard=5)
        return {"pressed": name,
                "command_line": (self.link.state.get("/eos/out/cmd") or [""])[0]}

    def save(self):
        if not self.allow_control:
            return {"error": "control is disabled; start with --allow-control"}
        if not self.allow_destructive:
            return {"error": "saving overwrites the show file; start with "
                             "--allow-destructive"}
        with self.lock_state():
            self.link.state.pop("/eos/out/event/show/saved", None)
        self.link.send("/eos/key/save_show", 1)
        self.link.send("/eos/key/save_show", 0)
        deadline = time.time() + 15.0
        while time.time() < deadline:
            ev = self.link.state.get("/eos/out/event/show/saved")
            if ev:
                return {"saved": True, "path": ev[0]}
            time.sleep(0.2)
        return {"error": "no /eos/out/event/show/saved received within 15s - "
                         "the show was probably NOT written to disk"}

    def lock_state(self):
        return self.link.lock

    def at(self, channels, level):
        if not self.allow_control:
            return {"error": "control is disabled; start with --allow-control"}
        try:
            lvl = max(0, min(100, float(level)))
        except (TypeError, ValueError):
            return {"error": f"level {level!r} is not a number"}
        if not re.fullmatch(r"[0-9,\-\s]+", str(channels)):
            return {"error": f"channels {channels!r} must be digits, commas, dashes"}
        text = f"Chan {channels} At {lvl:g}#"
        self.link.send("/eos/newcmd", text)
        self.link.quiet(idle=0.3, hard=5)
        return {"sent": text,
                "active_channels": (self.link.state.get("/eos/out/active/chan") or [""])[0]}

    def call(self, name, a):
        if name == "eos_status":
            return self.status()
        if name == "eos_ping":
            return {"reachable": self.link.ping(),
                    "eos_version": self.link.get_version()}
        if name == "eos_show_data":
            return self.show_data(a.get("section"), a.get("match"),
                                  bool(a.get("refresh")))
        if name == "eos_cmd":
            return self.cmd(a["command"], a.get("enter", True),
                            a.get("clear_first", True))
        if name == "eos_key":
            return self.key(a["key"])
        if name == "eos_at":
            return self.at(a["channels"], a["level"])
        if name == "eos_save":
            return self.save()
        return {"error": f"unknown tool {name!r}"}

# ------------------------------------------------------------- MCP stdio

def serve(server, allow_control, allow_destructive):
    out = sys.stdout

    def reply(rid, result=None, error=None):
        msg = {"jsonrpc": "2.0", "id": rid}
        if error is not None:
            msg["error"] = error
        else:
            msg["result"] = result
        out.write(json.dumps(msg) + "\n")
        out.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, rid, params = req.get("method"), req.get("id"), req.get("params") or {}

        if method == "initialize":
            reply(rid, {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "eos-mcp", "version": "0.1.0"},
            })
        elif method in ("notifications/initialized", "initialized"):
            pass  # notification: no reply
        elif method == "tools/list":
            reply(rid, {"tools": tool_defs(allow_control, allow_destructive)})
        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments") or {}
            try:
                res = server.call(name, args)
                is_err = isinstance(res, dict) and "error" in res
                reply(rid, {"content": [{"type": "text",
                                         "text": json.dumps(res, indent=2)}],
                            "isError": is_err})
            except Exception as e:
                reply(rid, {"content": [{"type": "text",
                                         "text": f"{type(e).__name__}: {e}"}],
                            "isError": True})
        elif method == "ping":
            reply(rid, {})
        elif rid is not None:
            reply(rid, error={"code": -32601, "message": f"unknown method {method}"})


def main():
    ap = argparse.ArgumentParser(description="MCP server for ETC Eos.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3032)
    ap.add_argument("--slip", action="store_true")
    ap.add_argument("--cache", default=os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "show.json"))
    ap.add_argument("--allow-control", action="store_true",
                    help="permit commands that move lights and run cues")
    ap.add_argument("--allow-destructive", action="store_true",
                    help="additionally permit Record/Update/Delete/Power_Off")
    a = ap.parse_args()
    if a.allow_destructive and not a.allow_control:
        ap.error("--allow-destructive requires --allow-control")

    link = EosLink(a.host, a.port, a.slip)
    serve(Server(link, a), a.allow_control, a.allow_destructive)


if __name__ == "__main__":
    main()
