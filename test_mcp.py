#!/usr/bin/env python3
"""Drive eos_mcp.py over stdio against a fake Eos; verify protocol + safety gates."""
import json, socket, struct, subprocess, sys, threading, time
import eosdump as E
import eos_mcp as M

# ---- safety classifier (pure, no console needed)
cases = {
    "Chan 1 Thru 48 At Full": None,
    "Go_To_Cue 12": None,
    "Record Cue 5": "record",
    "record cue 5": "record",
    "Chan 1 At Full Record": "record",
    "Delete Cue 1 Thru 328": "delete",
    "Update Cue 10": "update",
    "Power_Off": "power_off",
    "Sneak": None,
    "Recorder": None,            # must NOT trip on a substring
    "Undelete": None,
}
for cmd, want in cases.items():
    got = M.classify(cmd)
    assert got == want, f"classify({cmd!r}) = {got!r}, want {want!r}"
print(f"safety classifier: {len(cases)} cases OK (incl. substring non-matches)")

# ---- fake Eos so the server has something to connect to
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0)); srv.listen(1); port = srv.getsockname()[1]
received = []
def fake():
    while True:
        c, _ = srv.accept()
        threading.Thread(target=session, args=(c,), daemon=True).start()

def session(c):
    buf = b""
    def send(addr, args=()):
        p = E.enc_msg(addr, args); c.sendall(struct.pack(">I", len(p)) + p)
    send("/eos/out/show/name", ["REV REMIX"])
    send("/eos/out/active/cue/text", ["1/12 \"you say you want\""])
    send("/eos/out/event/state", [1])
    while True:
        try: chunk = c.recv(65536)
        except OSError: return
        if not chunk: return
        buf += chunk
        while len(buf) >= 4:
            (n,) = struct.unpack_from(">I", buf, 0)
            if len(buf) < 4+n: break
            pkt, buf = buf[4:4+n], buf[4+n:]
            out = []; E.dec_packet(pkt, out)
            for addr, args in out:
                received.append((addr, args))
                if addr == "/eos/get/version": send("/eos/out/get/version", ["3.3.9.25"])
                elif addr == "/eos/ping": send("/eos/out/ping", args)
                elif addr in ("/eos/cmd", "/eos/newcmd"): send("/eos/out/cmd", args)
threading.Thread(target=fake, daemon=True).start()

def run(extra_args, calls):
    p = subprocess.Popen([sys.executable, "eos_mcp.py", "--port", str(port),
                          "--cache", "/tmp/eosmcp-cache.json"] + extra_args,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    def send(o): p.stdin.write(json.dumps(o) + "\n"); p.stdin.flush()
    send({"jsonrpc":"2.0","id":1,"method":"initialize",
          "params":{"protocolVersion":"2024-11-05","capabilities":{}}})
    init = json.loads(p.stdout.readline())
    send({"jsonrpc":"2.0","method":"notifications/initialized"})
    send({"jsonrpc":"2.0","id":2,"method":"tools/list"})
    tools = json.loads(p.stdout.readline())
    results = []
    for i, (name, args) in enumerate(calls, start=3):
        send({"jsonrpc":"2.0","id":i,"method":"tools/call",
              "params":{"name":name,"arguments":args}})
        results.append(json.loads(p.stdout.readline()))
    p.stdin.close(); p.terminate()
    return init, tools, results

# ---- read-only mode
init, tools, res = run([], [("eos_status", {}), ("eos_cmd", {"command":"Chan 1 At Full"})])
assert init["result"]["serverInfo"]["name"] == "eos-mcp", init
names = [t["name"] for t in tools["result"]["tools"]]
assert names == ["eos_status","eos_show_data","eos_ping"], names
print("read-only mode exposes:", names)
status = json.loads(res[0]["result"]["content"][0]["text"])
print("  status ->", {k:status[k] for k in ("eos_version","show_name","active_cue","mode","control_enabled")})
assert status["show_name"] == "REV REMIX" and status["mode"] == "Live"
assert res[1]["result"]["isError"] is True
assert "control is disabled" in res[1]["result"]["content"][0]["text"]
print("  eos_cmd correctly refused in read-only mode")

# ---- control mode, destructive still blocked
init, tools, res = run(["--allow-control"],
    [("eos_cmd", {"command":"Chan 1 Thru 48 At Full"}),
     ("eos_cmd", {"command":"Record Cue 999"}),
     ("eos_at",  {"channels":"1-48","level":75}),
     ("eos_at",  {"channels":"1; rm -rf /","level":50})])
names = [t["name"] for t in tools["result"]["tools"]]
assert "eos_cmd" in names and "eos_at" in names, names
print("control mode exposes:", names)
ok = json.loads(res[0]["result"]["content"][0]["text"])
assert ok.get("sent") == "Chan 1 Thru 48 At Full#", ok
print("  allowed:", ok["sent"])
blocked = json.loads(res[1]["result"]["content"][0]["text"])
assert res[1]["result"]["isError"] and "record" in blocked["error"], blocked
print("  blocked:", blocked["error"][:78] + "...")
at = json.loads(res[2]["result"]["content"][0]["text"])
assert at.get("sent") == "Chan 1-48 At 75#", at
print("  allowed:", at["sent"])
inj = json.loads(res[3]["result"]["content"][0]["text"])
assert res[3]["result"]["isError"] and "must be digits" in inj["error"], inj
print("  rejected injection attempt in channel list")

# ---- destructive explicitly enabled
_, _, res = run(["--allow-control","--allow-destructive"],
                [("eos_cmd", {"command":"Record Cue 999"})])
r = json.loads(res[0]["result"]["content"][0]["text"])
assert r.get("sent") == "Record Cue 999#", r
print("  with --allow-destructive:", r["sent"])
print("\nALL MCP TESTS PASSED")
