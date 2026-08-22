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

**Augment3d model** — **DONE**. The room is modelled to the real venue and all
70 fixtures are placed, aimed and verified. See
[norco-location.md](norco-location.md) for every dimension, the coordinate
convention, the scene-file mechanics and the rig layout.

Two scripts reproduce it:

```bash
python3 a3d_room.py <extracted-show-dir> 30 22   # room, from stage W x D in feet
python3 build_rig_positions.py --send            # all 70 fixtures, positions + aim
```

Still approximate, in priority order:

- **Ceiling height is an operator estimate (12 ft), not a measurement.**
  Everything vertical scales off it — the 3.25 m par trim, every tilt angle,
  the booth partition height.
- **Tilt is capped at 65°**, so both audience rows aim parallel instead of the
  far row raking flatter. Geometry wants ~70° and ~74°.
- **Channels 1 and 2** point straight upstage; a lone side par usually toes in.
- **Pairs are not fanned** — only groups of four are.

**Busking layout** — direct selects built and verified, four banks of ten:

```
groups   Rig All, Pars All, Movers All, Strips, SlimPars,
         Front/Mid/Back Wash, Left All, Right All
colour   Red Orange Yellow Green Cyan Blue Purple Magenta WarmWhite ColdWhite
focus    OH Up/Centre Ceiling/Centre Up/Side Walls, Beam Ceiling/Ctr/Drum/
         Side Walls/Cross Corners/Floor Ctr
beam     Open, Spots Big, Spots Small, Stars, Star, Flower, Flower Fat,
         Spiral, X, Zebra
```

Palettes were duplicated by **recall-then-record**, not `Copy To` (which is a
key, not command-line text). Beam originals were stashed at 101–108 first
because sources and targets overlapped.

Known gaps in that bank: `Open` (BP 1) only covers channels 80–83 — no
open-gobo palette exists anywhere for the floor beams 85–88. Focus palettes
5–10 cover 85–88 but not 98. Beam palettes 2, 3, 4, 7, 9, 10 carry junk
channels (pars and strips inside a gobo palette) inherited from a rig-wide
original.

**Faders** — only partly scriptable; see [trap 18](command-line-traps.md).
Timing and mode work from the command line; intensity master, effect mode,
solo, exclude-solo, freeze and rate ranges are Tab 36 and mouse-only.

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
