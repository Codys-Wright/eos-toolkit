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
| Macros | yes** | yes** | yes | yes (confirm) |
| Magic sheets | yes (empty) | via XML import | yes | yes (confirm) |
| Effects | yes** | yes** | yes | yes (confirm) |

\*\* requires the Effect editor open on the console — see [Authoring effects](authoring-effects.md)

\* the cue reply has 27 fields and scene is not one of them; confirm visually.

Colour can be set numerically via `/eos/color/rgb` (floats 0.0-1.0).
Pan/tilt via `Group N Pan <deg>` / `Tilt <deg>`, readable back on
`/eos/out/pantilt`.

## NOT automatable

### Effect definitions — possible, with one precondition

**Effects can be authored over OSC** once a human opens the Effect editor
(`[Effect] [Effect]`). OSC keys cannot navigate displays, so a script cannot
open it for itself — but with it open, creation, typing, steps, channels and
properties are all scriptable.

See **[Authoring effects](authoring-effects.md)** for the full procedure.

With the editor CLOSED, every attempt fails with `Error: Effect Does Not Exist`,
which is what made this look like a hard boundary for a long time.

### Macros — possible, via a hybrid

Learn mode does NOT work (OSC commands execute live instead of recording), but
the Macro Editor does: OSC to navigate, **synthesised keystrokes** to type the
body. See **[Authoring macros](authoring-macros.md)**.

### Magic sheets — container yes, canvas no

`Record Magic_Sheet`, `Label` and `Delete` all work over OSC. Placing objects
does not, and contents are unreadable. But sheets **import and export as XML**,
so they can be generated offline. See **[Magic sheets](magic-sheets.md)**.

### Still GUI-only
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
