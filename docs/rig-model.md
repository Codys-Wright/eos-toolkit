# The rig, and the Augment3d model

> **Superseded for the venue and the placed rig.** The room, the coordinate
> convention, the scene-file mechanics and the final fixture layout now live in
> [norco-location.md](norco-location.md). This file is kept for the fixture
> inventory, the magic-sheet import history and the OSC write path.


## The rig, measured

71 patched channels:

| Channels | Fixture | Notes |
|---|---|---|
| 1–48 | Uking Par | 48 of them, spread across the whole stage |
| 50–53 | Chauvet SlimPAR Tri 7 IRC (7ch) | with the drums, upstage |
| 80–83 | Riukoe Mini Gobo Moving Head (11ch) | **overhead**, on the truss |
| 85–88, 98 | Betopper 150W LED Beam Moving Head | **floor**, mid-stage |
| 90–97 | Rockville Rockstrip 252 | foot lights (90–94, 97 are 7ch; 95–96 are 3ch) |
| 100–101 | Chauvet Hurricane Haze 1DX | upstage corners |

**Movers have colour wheels, not colour mixing.** Every RGB-based effect fails
on 80–88 with `No Channels Were Modified`; absolute and focus effects work. The
tell-tale is in the old palette names — `OH White Red`, `OH Orange Cyan` are
wheel positions parked between two gel slots.

Nothing on the rig has **CMY** or **Hue/Sat** parameters.

## Layout, from the LIGHTING POSITIONS magic sheet

The magic sheet is a plan view with real X/Y for 69 targets. Depth bands,
upstage to downstage:

```
  movers 80 81 82 83                       <- overhead truss
  haze 100/101, slimpars 50-53, strips 90-94
  pars 40 41 47 48, strips 93 94
  pars 42 46
  pars 43 44 45
  pars 32-39                                <- wide
  pars 20-23 28-31, strip 96
  strip 95, pars 7-10 24-27
  movers 85 86 87 88                        <- floor / beam
  pars 3-6, strip 97
  pars 11-18
  pars 1 2                                  <- downstage
```

Scenic reference objects on that sheet: two **truss** markers upstage, a
**pipe** far stage-left, two **speakers** mid-stage.

## Proposed Augment3d positions

`a3d_positions.json` holds derived world coordinates. Method:

- X and Y scaled from the magic sheet plot, centred on the stage
- **assumes a 12 m wide stage** — one number that rescales everything;
  confirmed by the operator 2026-08-22 as approximately correct
- +Y is upstage, Z is height above the deck

Assumed heights:

| Fixtures | Z | Basis |
|---|---|---|
| 80–83 | 5.5 m | overhead movers on the truss |
| 85–88, 98 | 0.30 m | the group was named "floor movers" |
| 90–97 | 0.15 m | the group was named "FOOT LIGHTS" |
| 50–53 | 0.30 m | on the deck with the drums |
| 100–101 | 0.40 m | hazers |
| 1–48 | 5.5 m | hung overhead; operator-confirmed 2026-08-22 |

## Open questions — resolved 2026-08-22

Answered by the operator; the model no longer has free parameters.

1. **Stage width** — ~12 m. The placeholder stands, so no X/Y rescale was
   needed.
2. **Are the 48 pars on the deck or hung overhead?** **Overhead, on truss.**
   All 47 patched pars were given Z = 5.5 m, the same trim as movers 80–83.
3. **Truss height** — 5.5 m confirmed.
4. **Orientation** — the pars being overhead means the 0/0/0 straight-down
   default is correct for them as written. Still outstanding for the **floor
   movers 85–88, 98**, which point somewhere other than down and need a
   rotation about X that nobody has measured.

Remaining assumption, not a measurement: the pars are placed at the *mover*
trim because 5.5 m is the only height datum in evidence. If the par truss hangs
at a different height, every par beam renders the wrong length in Augment3d.
Worth one glance at the rig before trusting the render.

## How positions get written — SOLVED 2026-08-22

Verified end to end against Eos **3.3.9.25**, 67 fixtures written in six
commands with no human step beyond one mouse click to reach the tab.

### The syntax

```
Chan 44 Position 0.15 / 1.35 / 9.08      set X, Y and Z
Chan 43 Position / / 9.08                set Z only; X and Y untouched
Chan 1 Thru 18 + 20 Thru 48 Position / / 9.08     ranges, applied uniformly
```

`Position` is the verb. The manual's `[Chan] [1] [Select] [5] [/] [5] [/] [5]`
documents the **hardware keypad gesture**; `[Select]` is a key, not a word, and
is unreachable over OSC. See [traps 13–15](command-line-traps.md).

Empty coordinates auto-complete to `*` ("no change"), which is what makes a
Z-only rewrite safe. Works from **Patch**, not from the `BLIND: A3D Edit`
display.

### Getting to the tab

`;` opens Patch over System Events. The Augment3d **tab within Patch** still
needs one mouse click — Eos publishes no "which tab is focused" message, and
the accessibility tree exposes no display tabs, so this is the one manual step
that remains.

## Where the positions actually came from

Not from this repo's derived numbers. Eos has a native import:

> **Patch → right-click the Augment3d tab → Set Channel Locations From Magic
> Sheet** — specify the sheet number and any X/Y/Z constraints.

Run against magic sheet **2 (LIGHTING POSITIONS)**, it placed 69 of 71 fixtures
using the sheet's own stored coordinates. That is strictly better data than
`a3d_positions.json`, which was hand-derived by reading the same plot by eye.

**The derived file is now superseded** for X and Y. It is kept only as the
record of intended *heights*, which the import cannot supply.

### The import's one flaw: Z is a copy of Y

A magic sheet is a 2D plan, so the importer had two numbers for three axes. It
wrote the sheet's second axis into **both Y and Z** — confirmed, `z == y` on all
71 fixtures immediately after import. Downstage units land ~10 units *below* the
deck.

Fix is the Z-only rewrite above. Heights applied:

| Fixtures | Z | Metres |
|---|---|---|
| 1–48, 80–83 | 9.08 | 5.5 m, truss trim |
| 50–53, 85–88 | 0.50 | 0.30 m, deck |
| 90–97 | 0.25 | 0.15 m, foot lights |
| 100–101 | 0.66 | 0.40 m, hazers |

### Units are sheet units, not metres

Imported X spans exactly ±10. Regressed against our metre-based derivation that
is **~1.65 units per metre**, and the ~12 m stage across a 20-unit span gives
1.67 independently. Two estimates agreeing.

Heights above are therefore metres × 1.65. Kept deliberately in sheet units:
beam angle is angular, so a uniformly scaled model renders identically. If the
stage is ever measured properly it is one global multiply, not a re-derivation.

### Axis convention, confirmed

**Z is height.** From the FPE section: floor points "should be on the same plane
(have the same Z coordinate)", and X/Y are measured out from the origin across
the floor.

### Still unplaced

- **Channel 19** — unpatched (address 0). Left at origin deliberately.
- **Channel 98** — a patched floor mover absent from magic sheet 2, so it has no
  X/Y from any source. Needs coordinates from the operator or a drag in
  Augment3d Edit Mode.

### The file route is a dead end

`working.a3d` unzips fine, but `Scene/Scene.json` holds **4 objects** and
`Library.json` 16 scene-library entries (`Venues`, materials) — no fixtures and
none of the patch UIDs. Fixture positions live in `showdat.dat`. Do not pursue
this; use `Position` over OSC.

### Verification

The patch reply carries `augment3d_position` (x, y, z, rotation, flag). After
the write: no X/Y moved, no address changed, `z == y` only on the two unplaced
channels.
