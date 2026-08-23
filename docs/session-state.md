# Where things stand

Snapshot of the show file and the open threads, so a fresh session can pick up
without re-deriving anything.

## The show file

`Popstars Playground.esf2` — saved in `~/Downloads/`, and re-saved after every
build. The original reference show is untouched at
`REV REMIX ver10 FINAL 7-26 2026-07-26 20-46-53.esf3d`.

| | Count | Where |
|---|---|---|
| Cue list 1 **PopStars** | 53 cues | 31 show cues (1–690) + 22 legacy utility cues (1000–4999) |
| Cue list 900 | 328 cues | the original reference show, preserved |
| Cue lists 10–22 | 13 chases | looping cue lists — Zone Sweep, Colour Cycle 8, Build and Blow… |
| Effects | 148 | **ours at 1–37**; stock colour fades moved to 800–860, shapes at 900+ |
| Groups | 112 | 1–100 in four paged banks + ordered chase groups 201–212 |
| Colour palettes | 150 | 6 pages incl. blackbody colour temperature 2700–6500K |
| Focus palettes | 62 | 12 original + two 5×5 coordinate grids inside the measured envelope |
| Intensity palettes | 25 | balance page — levels are guesses, never tuned by eye |
| Presets | 75 | signature looks · colour washes · mover looks |
| Submasters | 137 | 1–100 stock-effect bank, 101–137 paired to effects 1–37 |
| Macros | 42 | **101–137 one-press FX**, 140 stop-all, plus the show's original 1/2/5 |
| Magic sheets | 9 | 5 original + probe sheets; six generated sheets sit unimported in `~/Downloads/` |

### The show structure

Acts are numbered by **identity**, sequenced by **links**, and each act's video
cue is **blocked** so acts are reorderable without renumbering:

```
1/1    Speech            -> 1/100
1/100  GR Video (block) · 110/120/130 songs · 190 Out -> 1/200
1/200  AUB ...           -> 1/300
1/300  P3  ...           -> 1/400
1/400  TRI ...           -> 1/500
1/500  KK  ...           -> 1/600
1/600  PS  ...
```

Scene markers on 1, 100, 200, 300, 400, 500, 600 — jump by name with
`[Go To Cue]` → `{Scenes}`.

## The live workflow

1. **Cue list 1** with `[Go]` — structure, and the colour for each song
2. **Colour palettes** — retint if a song wants something different
3. **FX macros 101–137** — one press, each stops the previous, `140` clears
4. **FX submasters** — additive, on faders, for deliberate layering

Macros are radio buttons; submasters are layers. That distinction is the whole
operating model.

## Open threads

Everything below is the state as of the end of the Norco build session. See
[norco-location.md](norco-location.md), [busking-faders.md](busking-faders.md)
and [show-cues.md](show-cues.md) for the detail.

### Done and verified

- **The room** is modelled to the real venue and loaded on the console. Built by
  `a3d_room.py` from two numbers (stage width x depth in feet).
- **The rig**: 57 fixtures placed and aimed by `build_rig_positions.py`, every
  one confirmed by read-back. 12 more (movers 85-88, bars 90-97) are
  operator-placed and **the builder must not write them**.
- **Direct selects**: four banks of ten — groups, colour, focus, beam.
- **Colour palettes 1-10** rebuilt with explicit RGB and verified by reading hue
  back. Yellow is 26 deg off Orange, Purple 30 deg off Magenta; both were
  near-identical before.
- **Busking faders**: five pages built, mapped, timed and filtered by
  `build_busking_faders.py`; the button actions set by hand in Tab 36 and read
  back clean.

### Done but NOT verified

- **The 18 song cues.** `build_song_looks.py` recorded a look and a vibe note
  for every song. The notes are confirmed on screen. **The colours are not.**
  The first build recorded 18 identical cues because of
  [trap 21](command-line-traps.md); the rebuild is believed correct but every
  measurement of it was polluted — fader 6 was up at 60% running a colour
  effect, and averaging the whole render cannot distinguish a multi-colour look.
  **Verify one zone at a time, with all faders at zero and the cue list out.**

### Not started

- **A global effect rate fader.** Set any fader's *slider* to `Effect Rate` in
  Tab 36 — it needs no content and controls every running effect. Page 2 fader
  10 (`RIG`) is the most redundant slot. No command-line path exists.
- **A hardware shutter strobe.** `Chan N Shutter <n>` is accepted, so the pars
  have the parameter; the ranges are unknown.
- **Chases 32-36, 38, 40 have no fader** — page 3 only has three usable slots
  until its reserved faders are freed in Setup.

### Known-approximate

- **Ceiling height is an operator estimate** (12 ft), not a measurement.
  Everything vertical scales off it.
- **Tilt is capped at 65 deg**, so both audience trusses aim parallel instead of
  the far one raking flatter.
- **Channels 19 and 98 are unpatched** (address 0) and deliberately unplaced.
- **Fader pages 4-5 button config** was read back clean *before* the last two
  fixes, not after.

**Colour FX macro bank** — agreed but not built. Macros 141–165 pointing at the
absolute colour effects (800–860) and rainbows (910–919), same stop-then-start
shape. Note a colour effect **overrides the cue's colour** while it runs, unlike
the intensity ones.

**Never verified by eye** — everything below was confirmed structurally but
never watched running:
- chase *direction* on effects 1–37 and cue lists 10–22 (group order is
  unreadable over OSC)
- cycle times (not in the `get/fx` reply)
- the 61 colour fades moved to 800–860 (`Copy_To` preserves every readable
  field, but step/value tables are not readable)
- scene markers (no scene field in the cue reply)
- intensity palette balance levels — pure guesses
- the 31 cue looks — built from palette names, never seen on stage

**Six magic sheets** generated in `~/Downloads/` (`MS - GROUPS.xml` etc.),
never imported.

## Working agreements

- Everything is regenerated from scripts, never hand-edited on the console — so
  a change means editing data at the top of a script and re-running.
- Read state back after every write. Eos does not error on input it does not
  understand.
- Scripts that use System Events synthesise **real keystrokes**; the operator
  must not touch the computer while they run.
