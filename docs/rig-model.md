# The rig, and the Augment3d model (in progress)

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
- **assumes a 12 m wide stage** — one number that rescales everything
- +Y is upstage, Z is height above the deck

Assumed heights:

| Fixtures | Z | Basis |
|---|---|---|
| 80–83 | 5.5 m | overhead movers on the truss |
| 85–88, 98 | 0.30 m | the group was named "floor movers" |
| 90–97 | 0.15 m | the group was named "FOOT LIGHTS" |
| 50–53 | 0.30 m | on the deck with the drums |
| 100–101 | 0.40 m | hazers |
| **1–48** | **UNKNOWN** | see below |

## Open questions

1. **Stage width** — everything scales off this. 12 m is a placeholder.
2. **Are the 48 pars on the deck or hung overhead?** They cover the whole
   stage footprint in plan, which is consistent with either. This is the one
   answer that changes the model most.
3. **Truss height** — 5.5 m assumed.
4. **Orientation** — all fixtures default to 0/0/0 (straight down). Correct for
   overhead units; the floor movers and any uplighting pars would want a
   rotation about X.

## How positions get written

`[Chan] [1] [Select] [5] [/] [5] [/] [5] [Enter]` sets channel 1 to 5,5,5.

This is **display-dependent** — it fails from Live with `Syntax Error`. It needs
Patch → the Augment3d tab, with the Position & Orientation section in focus.
Reachable the same way as the macro editor: System Events for navigation, OSC
for the rest.

Verification is available: the patch OSC reply carries `augment3d_position`
(x, y, z, then rotation) and `augment3d_beam`, so every write can be read back.
All 71 currently read `[0,0,0, 0,0,0]` — unplaced, at world origin.

The alternative is a file route — CSV export, edit, import. Untested; needs one
patch CSV export to see whether Augment3d columns survive the round trip.
