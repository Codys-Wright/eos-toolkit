# What can and cannot be automated over OSC

Measured on Eos **3.3.9.25**. "Automatable" means: drivable end-to-end from a
script, with the result verifiable by reading state back.

## Fully automatable

| Target | Create | Edit | Label | Delete |
|---|---|---|---|---|
| Cues | yes | yes | yes | yes (confirm) |
| Cue lists | yes | yes | yes (`Cue N / Label`) | yes |
| Groups | yes | yes | yes | yes (confirm) |
| Colour palettes | yes | yes | yes | yes (confirm) |
| Focus palettes | yes | yes | yes | yes (confirm) |
| Intensity palettes | yes | yes | yes | yes (confirm) |
| Presets | yes | yes | yes | yes (confirm) |
| Submasters | yes | delete+rerecord | yes | yes (confirm) |
| Scenes | yes (`Cue N Scene <label>`) | — | — | unverifiable* |

\* the cue reply has 27 fields and scene is not one of them; confirm visually.

Colour can be set numerically via `/eos/color/rgb` (floats 0.0-1.0).
Pan/tilt via `Group N Pan <deg>` / `Tilt <deg>`, readable back on
`/eos/out/pantilt`.

## NOT automatable

### Effect definitions — hard boundary

Everything tried, all failed:

| Attempt | Result |
|---|---|
| `Effect N Enter` | "Effect Does Not Exist" — selects, never creates |
| `/eos/key/stepbased`, `absolute`, `linear`, `focus_effect`, `color_effect` | no change to type |
| `Record Effect N` | "Effect Not Running" — even while running |
| `Record Effect N` after Scale/Rate/Cycletime overrides | still refused |
| `/eos/key/blind` then `Effect N Enter` | "Effect Does Not Exist" |
| `Effect N Step 1 Thru 8` | "Effect Not Running" |
| `display_effects`, `open_pattern_effects`, `effect_edit`, `create_type`, `displays` | editor will not open |
| `Effect A Copy_To Effect B` | **works** — but a clone behaves identically |

**Why:** Rate, Scale, Entry, Exit and Duration exist at two levels — the value
stored in the *definition*, and a per-instance *override* applied when a channel
runs the effect. The command line only ever reaches the override. Verified: set
`Effect 210 Scale 250` while running, definition stays `scale=10`.

That override is still useful — it bakes into a submaster or cue, which is how
you get genuine variety from a fixed effect library.

**Workaround for designed FX: build them as looping cue lists.** One cue per
step, `Follow` for step time, last cue `Link`s back to the first. Fully
authorable, arbitrarily complex, and it can use *your* groups and palettes.
See `build_chases.py`.

### Also GUI-only

- Magic sheet creation and editing (contents are not even readable)
- File operations: New Show, Save As, Partial Show Read, CSV/ASCII export
  (`save_show` is the exception — it is a key and does work)
- Anything behind a modal dialog. Command-line "Please Confirm" prompts ARE
  visible on `/eos/out/cmd`; window dialogs are not.

## Probing a rig's capabilities

Fixture families differ in what parameters they have. Discover it empirically
rather than assuming — apply an effect and read the error:

```
Group <n> At 100
Group <n> Effect <fx>     -> "Error: No Channels Were Modified" if unsupported
```

Example result from a real rig (48 RGB pars, 4+5 movers, 8 strips):

| Effect type | Pars / Strips / SlimPars | Movers |
|---|---|---|
| RGB colour (910, 912, 913, 917) | yes | **no — colour WHEELS, not mixing** |
| Absolute colour (100-159) | yes | yes |
| Focus / movement (901-933) | no — no pan/tilt | yes |
| Intensity (936-941) | yes | yes |
| CMY (918), Hue-Sat (914) | no | no |

Tell-tale in the show file: palette names like `OH White Red`,
`OH Orange Cyan` are wheel positions parked between two slots — only a wheel
does that.
