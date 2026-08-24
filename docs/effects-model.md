# How Eos effects actually work

The mental model that makes the effects engine predictable, and the parts that
are not obvious from the UI.

## The five types

| Type | Drives | Notes |
|---|---|---|
| **StepBased** | whatever the On/Off states hold — **intensity by default** | channels live *in the steps*; order comes from the group |
| **Absolute** | literal parameter values from a table | the only colour effects that reach **colour wheels** |
| **Focus** | offsets around the current position | movers only; shapes — circle, figure 8, spiral |
| **Linear** | a value ramp | sweeps, rainbows, ballyhoo |
| **Color** | hue/sat | **unusable on RGB-only rigs** |

## Step effects modulate INTENSITY, not colour

A step effect drives each step's channels between an **On State** and an **Off
State**. Left at defaults those are `100` and `0` — intensity values. So a
chase, a strobe, a sparkle or a fire flicker changes *brightness* and leaves
colour alone.

That is the property that makes them layerable: set colour in the cue, run a
step effect on top, and they do not fight. Point Fire Flicker at an amber wash
and you get fire; point it at deep blue and you get storm light.

Colour effects (Absolute, or Linear rainbows) **override** the colour while they
run, because they write the same parameter. A colour effect is a bigger
commitment than an intensity one.

## Channel order comes from the group

For a StepBased effect, channels enter the steps **in group storage order**.
That is the most expressive lever available to a script: shape is authored in
the GUI, order is scriptable.

```
Chan 34 + 31 + 12 + 5 Record Group 200      stores exactly that sequence
```

One hand-made 8-step effect plus N ordered groups = N distinct chases. Build
the order, not the effect.

**Caveat:** group order is **not verifiable over OSC**. The reply uses the OSC
Number Range format, which compresses to sorted ranges — a scatter group reads
back as `['1-48']`. It is a set representation, not a sequence. Confirm by eye.

## Attributes turn one effect into six

Set from the `{Attributes}` softkey, or the keys `bounce`, `build`, `negative`,
`positive`, `random_groups`, `random_rate`, `reverse_steps`.

| Attribute | Effect |
|---|---|
| Forward | default, steps 1→5 |
| **Reverse** | 5→1. The key is `reverse_steps`; the bare `reverse` key errors |
| **Bounce** | 1,2,3,4,5,4,3,2,1 alternating |
| **Build** | each step ADDS to the last; all on at the end, then resets |
| **Negative** | inverted — channels sit ON and the active step goes OUT |
| **Random Group** | step order continuously randomised |
| **Random Rate** | per-step time randomised in a range, e.g. `50 Thru 200` |

Negative is the one most people never build, and on a full wash it gives a dark
gap travelling across the stage — something no amount of forward chasing does.

## Rate and Scale exist at TWO levels

This is the subtlety that makes the command line confusing:

- the value stored in the **definition** (editable in the Effect editor)
- a per-instance **override** applied when channels run the effect

The command line reaches whichever the current context implies:

```
from LIVE, effect running     Effect 1 Rate 250   -> sets the OVERRIDE
from LIVE, nothing running    Effect 1 Rate 250   -> "Error: Effect Not Running"
from inside the EDITOR        Effect 1 Rate 250   -> edits the DEFINITION
```

Same words, different target, no error either way. `Error: Effect Not Running`
means "no instance to override", **not** "this command does not exist" — that
misreading cost hours.

The override is useful: it bakes into a submaster or cue, which is how you get
real variety from a fixed effect library.

## Stopping effects

`Group <n> Effect [Enter]` with **no effect number** is the stop flag. It kills
running effects on those channels without touching levels or colour.

```
Group 1 Effect ⏎        stop everything (group 1 = chans 1-98)
```

Effects do NOT stop on their own when you start another, so anything meant to
behave like a radio button must stop first.

Note `Group 1` is channels 1–98 on this rig; effects on channels outside that
(haze at 100–101) would survive.

## Probing what a rig can actually run

Fixture families differ. Discover empirically rather than assume:

```
Group <n> At 100
Group <n> Effect <fx>     -> "Error: No Channels Were Modified" if unsupported
```

Measured on a rig of 48 RGB pars, 9 movers, 8 strips:

| Effect type | Pars / Strips / SlimPars | Movers |
|---|---|---|
| RGB colour (910, 912, 913, 917) | yes | **no — colour WHEELS, not mixing** |
| Absolute colour (800-860, 4xx) | yes | yes |
| Focus / movement (901-933) | no — no pan/tilt | yes |
| Intensity (936-941) | yes | yes |
| CMY (918), Hue-Sat (914) | no | no |

Tell-tale in the show file: palette names like `OH White Red`, `OH Orange Cyan`
are wheel positions parked *between* two gel slots. Only a wheel does that.

## Hollow effects: a perfect label and an empty step table

**An effect that reads back correctly can do nothing at all.** Eos publishes an
effect's label, type, entry/exit, scale and rate over OSC. It does **not**
publish the step or value table. So the one thing that determines whether an
effect produces motion is the one thing you cannot read.

On this show, 10 of the 34 effects the fader banks referenced were hollow:

```
  2 Chase Rev    3 Chase Bounce    6 Sparkle    9 Fire
413 Step R-Y-B  800 Red-Blue     814 Green-Mag
848 Cyan-Orange 856 Mag-Yellow   912 Rainbow RGB
```

Two causes, and both matter:

- **`Copy_To` damage.** The stock colour fades were relocated to 800-860 with
  `Copy_To`, which preserves every *readable* field and drops the step table.
  The copies kept their names and lost their contents.
- **Authoring that never landed.** Effects 2, 3, 6 and 9 are in our own 1-37
  block. They were never successfully written, and nothing caught it, because
  the label looked right ever after.

`912 Rainbow RGB` is the cautionary one: the name is perfect, the type is
Linear, the scale is 25, and it has never produced a single hue change. A
submaster was built on it purely because the label matched the intent.

### Testing

The only test is to run one and watch a parameter move.

```bash
python3 test_effects.py              # every effect the fader banks use
python3 test_effects.py 912 919      # specific ones
```

It applies each effect, then samples the selected channel's encoder wheels
several times and reports whether any value changed. Works for colour,
intensity and focus effects alike, since every parameter surfaces as a wheel.

Two gotchas it has to work around, both worth knowing on their own:

- Wheel and colour values publish on **selection change**, not on demand, so
  the sampler bounces the selection off an empty channel before every read.
  Without that you get the *previous* channel's values and never know.
- Effects survive a sneak. Stop them with `Chan 1 Thru 101 Effect` between
  tests - the `Group` form does nothing (trap 29).

### The lesson for the library

Do not build a fader, macro or cue on a stock effect because its name matches
what you want. Author the effects you rely on, verify them by running them, and
keep that verified set as the thing you carry between rigs.
