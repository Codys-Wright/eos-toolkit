#!/usr/bin/env python3
"""Fake Eos console speaking the documented OSC protocol, to test eosdump."""
import socket, struct, threading, subprocess, sys, os, json, time
import eosdump as E

# Show data lifted from the Show Control User Guide examples, plus a small rig.
PATCH = [
    (1, 1, "House Left Lustr", "ETC_Fixtures", "S4_LED_S2_Lustr_Direct", 1, 1, 0, "R80"),
    (2, 1, "House Right Lustr", "ETC_Fixtures", "S4_LED_S2_Lustr_Direct", 12, 12, 0, "R80"),
    (3, 1, "Haze", "Chauvet", "Hurricane_Haze_1DX", 100, 100, 0, ""),
]
CUES = [
    ("1", "0", "Preset", 3000, 0, 3000, 0, "", "", 0, 0),
    ("2", "0", "Act 1 Top", 5000, 0, 5000, 0, "M", "B", 2000, 0),
    ("2.5", "0", "Build", 8000, 0, 8000, 0, "", "", 0, 0),
    ("3", "0", "Blackout", 0, 0, 4000, 0, "", "", 0, 0),
]

def msg(addr, args):
    return E.enc_msg(addr, args)

def handle(c):
    buf = b""
    def send(addr, args=()):
        p = msg(addr, args)
        c.sendall(struct.pack(">I", len(p)) + p)
    while True:
        try:
            chunk = c.recv(65536)
        except OSError:
            return
        if not chunk:
            return
        buf += chunk
        while len(buf) >= 4:
            (n,) = struct.unpack_from(">I", buf, 0)
            if len(buf) < 4 + n: break
            pkt, buf = buf[4:4+n], buf[4+n:]
            out = []
            E.dec_packet(pkt, out)
            for addr, _ in out:
                reply(send, addr)

def reply(send, addr):
    p = addr.split("/")
    if addr == "/eos/get/version":
        send("/eos/out/get/version", ["3.3.5.69"]); return
    if addr.endswith("/count"):
        t = "/".join(p[3:-1])
        n = {"patch": len(PATCH), "cuelist": 1, "cue/1": len(CUES),
             "group": 2, "sub": 1, "fx": 1, "macro": 1}.get(t, 0)
        send(f"/eos/out/get/{t}/count", [n]); return
    if "/index/" in addr:
        t = "/".join(p[3:p.index("index")])
        i = int(p[-1])
        if t == "patch":
            ch, part, lbl, mfg, mdl, ad, ia, lv, gel = PATCH[i]
            args = [i, f"uid-patch-{i}", lbl, mfg, mdl, ad, ia, lv, gel] + [""]*10 + [1]
            # Deliberately split across two packets to exercise list reassembly.
            send(f"/eos/out/get/patch/{ch}/{part}/list/0/20", args[:9])
            send(f"/eos/out/get/patch/{ch}/{part}/list/9/20", args[9:])
            send(f"/eos/out/get/patch/{ch}/{part}/notes", [i, f"uid-patch-{i}", f"note for ch{ch}"])
        elif t == "cuelist":
            send("/eos/out/get/cuelist/1/list/0/13",
                 [i, "uid-cl-1", "Main", "Master", "Proportional", True, False, True,
                  False, False, False, 1, False])
        elif t == "cue/1":
            num, part, lbl, up, upd, dn, dnd, mark, blk, fol, hang = CUES[i]
            send(f"/eos/out/get/cue/1/{num}/{part}/list/0/27",
                 [i, f"uid-cue-{i}", lbl, up, upd, dn, dnd, 0,0,0,0,0,0,
                  False, 0, 100, mark, blk, "", 0, fol, hang, False, 0, False, "", 0])
        elif t == "group":
            send(f"/eos/out/get/group/{i+1}/list/0/3", [i, f"uid-g{i}", f"Group {i+1}"])
            send(f"/eos/out/get/group/{i+1}/channels/list/0/4",
                 [i, f"uid-g{i}", "1-2", 3])
        elif t == "sub":
            send("/eos/out/get/sub/1/list/0/13",
                 [i, "uid-s1", "Haze", "Additive", "Proportional", True, False,
                  True, False, "", "0", "Man", "0"])
        elif t == "fx":
            send("/eos/out/get/fx/901/list/0/8",
                 [i, "uid-fx", "Circle", "Focus", "Immediate", "Immediate", "Infinite", 25])
        elif t == "macro":
            send("/eos/out/get/macro/1/list/0/4", [i, "uid-m1", "Blackout", ""])
            send("/eos/out/get/macro/1/text/list/0/3", [i, "uid-m1", "Go_To_Cue Out Time 0"])

srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 0)); srv.listen(1)
port = srv.getsockname()[1]
threading.Thread(target=lambda: handle(srv.accept()[0]), daemon=True).start()

r = subprocess.run([sys.executable, "eosdump.py", "--host", "127.0.0.1",
                    "--port", str(port), "-o", "/tmp/eostest"],
                   capture_output=True, text=True, timeout=180)
print(r.stdout, r.stderr)
assert r.returncode == 0, "eosdump failed"
doc = json.load(open("/tmp/eostest.json"))
print(json.dumps(doc, indent=2)[:2200])
print("\n===== DIGEST =====\n")
print(open("/tmp/eostest.md").read())
