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

**Augment3d model** — **DONE**, 2026-08-22. 67 of 69 fixtures placed and
verified.

Positions came from Eos's own **Set Channel Locations From Magic Sheet**
(Patch → right-click the Augment3d tab), run against magic sheet 2 (LIGHTING
POSITIONS) — not from `a3d_positions.json`, which is now superseded for X/Y and
kept only as the record of intended heights.

The import writes the sheet's second axis into **both Y and Z**, so every
fixture landed at `z == y`. Corrected with six range commands using the verb
`Position` (not `Select`, which is a hardware key):

```
Chan 1 Thru 18 + 20 Thru 48 Position / / 9.08
```

Empty coordinates mean "no change", so X/Y were preserved — verified: no X/Y
moved, no address changed. See [rig-model.md](rig-model.md) and traps 13–15.

Coordinates are **sheet units, ~1.65 per metre**, not metres. Deliberate — a
uniformly scaled model renders identically, and it is one global multiply to
convert if the stage is ever measured.

Still open on this thread:
- **Channel 98** — patched floor mover, absent from the magic sheet, no X/Y
  from any source. Needs operator input.
- **Channel 19** — unpatched, left at origin on purpose.
- **Orientation** — every fixture is still `0/0/0` (straight down). Correct for
  the overhead units, wrong for floor movers 85–88 and 98, which point
  somewhere else. Never measured.
- **Never seen by eye.** The whole model is verified *structurally* over OSC.
  Nobody has confirmed the rendered 3D view looks like the actual room.

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
