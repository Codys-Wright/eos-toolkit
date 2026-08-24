# Where things stand

Snapshot of the show file and the open threads, so a fresh session can pick up
without re-deriving anything. Updated 2026-08-23.

## The show file

`Popstars Playground 3D FULL ROOM With Edits.esf3d` in `~/Downloads/`, re-saved
after every build.

| | Count | Notes |
|---|---|---|
| Groups | 112 | 1-10 renamed as plain plurals, **All at 10** |
| Focus palettes | 73 | **1-20 are Augment3d XYZ coordinates** |
| Colour palettes | 150 | 1-10 verified by hue read-back |
| Beam palettes | 27 | **not curated** - still needs eyes on the rig |
| Presets | 100 | 1-25 position+intensity, 26-50 movers, 51-100 full looks |
| Submasters | 135 | banks of eight on faders 1-8, 9-16, 33-40 |
| Macros | 42 | 101-137 FX, 140 stop-all |
| Cue list 1 | 53 cues | 18 song looks, colours verified |

## What is verified, and how

Everything below was proved by reading the rig back, not by trusting an echo.

- **Song cue colours** - 90 zone checks, 0 failures (`verify_song_looks.py`).
  This was the show's oldest open item.
- **Mover presets 26-50** - 25 checked against their focus palettes, 0
  mismatches (`verify_presets.py`).
- **Fader mapping** - 40 faders, 0 unaccounted for (`verify_faders.py`).
- **XYZ focus palettes 1-20** - every one of 160 per-channel read-backs within
  2 cm of the requested coordinate.
- **Effects** - `test_effects.py` runs each one and reports which are hollow.
  10 of 34 were: 2, 3, 6, 9, 413, 800, 814, 848, 856, 912.
- **Complete looks 51-100** - 250 checks, 0 failures (`verify_looks.py`):
  colour on four zones plus mover position, for all fifty.
- **Colour-free presets** - proved on stage to leave a cue's colour untouched.

## The operating model

1. **Song cue** owns the colour scheme.
2. **Presets 1-50** own position and intensity, and carry no colour at all, so
   any of them drops onto any cue without fighting it.
3. **Presets 51-100** are complete looks for when you want the whole thing.
4. **Bank 2 faders (9-16)** are the stage laid out left to right.
5. **Bank 1 faders (1-8)** are effect layers.
6. **FX macros 101-140** are radio buttons; each stops the previous.

## Open threads

### Needs someone at the console

- **Beam palettes 1-10.** Neither fixture profile publishes gobo names over
  OSC, and Augment3d does not render the patterns. The DMX charts and slot
  centres are in `rig-model.md`; `gobo_walk.py` puts four slots on the four OH
  movers at once. Ten minutes with the rig up.
- **I-Master on the FX subs.** Without it a sub's recorded level masks its own
  effect (HTP). `Sub N Effect_Master` parses and does nothing - trap 18. Tab 36,
  by hand. `build_busking_faders.py` prints the list that needs it.
- **The effect rate fader.** Set a fader's slider to Effect Rate in Tab 36. No
  command-line path.

### Known gaps

- **The Betopper wheel chart is unknown** - 12 gobos and 12 colours on a
  different chart from the Riukoe. The beam movers are parked on Open in the
  song cues until someone reads it off the fixture.
- **Hang to Focus Offset is zero** on both mover profiles. Eos uses it to
  convert an XYZ target to pan/tilt, so every aim is slightly off until it is
  set at Patch > {Fixtures} > {Physical Data}.
- **Fader banks 4 and 5 are unmapped.** The grid is irregular - usable faders
  are 1-16, 21 and 31-40 only.
- **Mover colour-wheel effects** (WHEEL SPIN / BUMP / ALT) are not authored.
  The builder skips them rather than recording silent intensity masters.

## Build order matters

Three dependencies that fail silently if you get them wrong:

```
build_groups.py        groups 7, 8 and 10 are load-bearing
build_xyz_focus.py     palettes BEFORE anything recorded against them
build_presets.py       presets store RESOLVED values, not live references
verify_presets.py
```

```
build_popstars.py      structure
build_song_looks.py    the look inside each song cue - SAME cue numbers
verify_song_looks.py
```

Re-running `build_popstars.py` alone silently discards all 18 song looks.
Changing a focus palette without re-running the presets leaves the palette and
every preset built on it disagreeing (trap 31).

## Working agreements

- Everything is regenerated from scripts, never hand-edited on the console.
- **Read state back, and compare it to intent.** Reading without comparing is
  how 38 corrupt macros reported success.
- **Clear the stage before recording**: `Go_To_Cue Out`,
  `Chan 1 Thru 101 Effect`, `Group 10 Sneak Time 0`. Record captures the stage.
- Scripts using System Events synthesise real keystrokes; do not touch the
  computer while they run.
