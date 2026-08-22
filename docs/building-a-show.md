# Building show content at scale

Recipes and traps for generating cues, groups, palettes, presets and
submasters from a script. Every one of these was learned by writing something,
reading it back, and finding it was not what we sent.

## The rule

**After every write, read the state back.** Eos rarely errors on input it does
not understand. A clean command-line echo means *"I parsed that"*, never
*"I did that."*

Every bug in this project was caught by reading back, and none would have been
caught any other way.

## What each container can hold

| Container | Channels | Levels | Colour | Effect | Notes |
|---|---|---|---|---|---|
| Group | yes | — | — | — | order matters for step effects |
| Palette | yes | one category only | | | IP / FP / CP / BP |
| Preset | yes | all categories | yes | **no** | the `fx` field stays empty however you record |
| Submaster | yes | yes | yes | **yes** | additive; brings its own level |
| Macro | — | — | — | runs a command | touches only what you tell it |
| Cue | yes | yes | yes | yes | the show |

That table decides the tool. Wanting "one button that applies an effect without
disturbing colour" rules out presets (cannot hold effects) and submasters
(bring a level), leaving macros.

## Cues

- **Spaces around the slash**: `Record Cue 2 / 110`. `Cue 2/110` fails.
- **Links are applied last.** A link to a cue that does not exist yet is
  silently dropped — no error, reads back as 0. Build every cue, then link.
- **Links store an absolute list number.** Copying a list to a new number
  leaves its links pointing at the old one. Rebuild rather than copy.
- **`-1` is the "unset" sentinel** for times, follow, hang, loop and link.
  Dividing by 1000 for display gives `-0.001s`.
- **Whole cue lists copy**: `Cue 15 / Copy_To Cue 950 /`.
- **Cue list labels**: `Cue 10 / Label Zone Sweep`. `Cuelist 10 Label` is
  reparsed as `Chan 10 Label` and Eos then auto-names the list after its first
  cue.
- **Delete ranges must exceed the highest cue number.**
  `Delete Cue 1 / 1 Thru 1 / 999` silently misses everything above 999.

### Blocks make acts reorderable

In a tracking console a cue inherits whatever the previous cue left. If acts
can play in any order, each act's first cue must be **blocked**, or the look
depends on what preceded it.

Reorderable structure needs three things together: numbers encode *identity*,
links encode *order*, blocks make each act *self-contained*.

## Groups, palettes, presets

- **Scope the record**: `Group 1 Record Color_Palette 152` records only group 1.
  An unscoped `Record Color_Palette 152` grabs every channel with colour data.
- **`Chan 1 Thru 6 Record Group 152`** likewise scopes a group.
- **Colour numerically**: `/eos/color/rgb` with floats 0.0–1.0.
- **Pan/tilt numerically**: `Group 7 Pan 45`, `Group 7 Tilt 30`.
- **Cues reference palettes.** Renumbering or overwriting a palette changes
  every cue that used it. Groups are safe — a cue stores channel values, not a
  group reference.

## Submasters

- **`Record Sub` over an existing sub silently does nothing.** Delete first.
- **`Group N At 0` does not stop running effects**, so the next record captures
  them. We built 14 subs this way and 11 came out with 2–4 effects each.
  Use **`Sneak Time 0`** as the reset — it releases all manual control
  including effects.

## Reading values back

`get` returns metadata, never parameter values. But you can **recall and
observe**:

```
Group 7 Focus_Palette 1      then read /eos/out/pantilt
  -> [panMin, panMax, tiltMin, tiltMax, panNow, tiltNow]
```

That turns "I cannot know where your lights point" into a measurement — we used
it to learn a rig's real working envelope before generating a focus grid.

`/eos/out/color/hs` fires on **manual** colour changes but **not** on palette
recall, so the same trick does not work for colour.

## Moving things safely

`Copy_To` preserves every OSC-readable field across Absolute, Focus, Linear and
StepBased effects. Step and value tables are not readable, so verify what you
can and spot-check the rest:

```
clone -> re-read -> compare type/entry/exit/duration/scale
      -> only delete the original if they match
```

Sixty effects moved that way with zero errors, and any single failure would have
stopped at that effect with the original still in place.

## Saving

`Save_Show` typed on the command line is **silently swallowed**. It is a KEY:

```
/eos/key/save_show
```

Wait for `/eos/out/event/show/saved` — it carries the file path and is the only
proof a save happened. If it does not arrive within ~15s, nothing was written.
