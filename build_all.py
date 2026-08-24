#!/usr/bin/env python3
"""
Build every song's section cues, one after another, pausable and resumable.

Progress is written to .build_all_state after each song completes, so if this
is stopped - Ctrl-C, a crash, or the console going away - re-running with
--resume picks up at the next unbuilt song rather than redoing the lot.

Stopping mid-song is safe: that song is simply not marked done, so it gets
rebuilt from the start next time. Cue records are idempotent.

  python3 build_all.py --host 10.0.0.5
  python3 build_all.py --host 10.0.0.5 --resume
  python3 build_all.py --list
"""
import argparse, json, pathlib, subprocess, sys, time

STATE = pathlib.Path(__file__).with_name(".build_all_state")

# show order
# Trifecta first, then the last two groups, then back for the earlier ones.
ORDER = ["everybody", "burning", "byebye",        # Trifecta
         "girls", "beautiful", "baby",            # Kaat Krew
         "que", "iloveyou", "mountain",           # Pink Spark
         "start", "predict",                      # The Aubvis
         "midnight", "stole", "gabriela"]         # Pop Th3ory


def load():
    if STATE.exists():
        try: return json.loads(STATE.read_text())
        except Exception: pass
    return {"done": []}


def save(st):
    STATE.write_text(json.dumps(st, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="10.0.0.5")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--fast", action="store_true",
                    help="3 cues per song instead of 5")
    ap.add_argument("--reset", action="store_true", help="forget all progress")
    a = ap.parse_args()

    if a.reset:
        STATE.unlink(missing_ok=True); print("progress cleared"); return 0

    st = load() if a.resume else {"done": []}
    todo = a.only or [s for s in ORDER if s not in st["done"]]

    if a.list:
        for s in ORDER:
            print(f"  {'done' if s in st['done'] else '    '}  {s}")
        return 0

    print(f"  {len(todo)} songs to build: {', '.join(todo)}")
    if st["done"]:
        print(f"  already done: {', '.join(st['done'])}")

    for i, song in enumerate(todo, 1):
        print(f"\n{'='*58}\n  [{i}/{len(todo)}] {song}\n{'='*58}", flush=True)
        t0 = time.time()
        r = subprocess.run(
            [sys.executable, "build_song_sections.py",
             "--host", a.host, "--song", song]
            + (["--fast"] if a.fast else []),
            cwd=str(pathlib.Path(__file__).parent))
        if r.returncode != 0:
            print(f"\n  !! {song} failed (exit {r.returncode}) - STOPPING.")
            print(f"     fix it, then: python3 build_all.py --resume")
            save(st)
            return 1
        st.setdefault("done", []).append(song)
        save(st)
        print(f"  {song} done in {time.time()-t0:.0f}s "
              f"({len(st['done'])}/{len(ORDER)} of the show)", flush=True)

    print(f"\n  ALL DONE - {len(st['done'])} songs built")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n  stopped. resume with:  python3 build_all.py --resume")
        sys.exit(130)
