# The portable FX library

The design that travels between rigs, and the rules for implementing it on a
new one.

This exists because of a specific failure. Ten of the 34 effects this show's
faders referenced turned out to be **hollow** — a correct label, a correct
type, and an empty step table. Eos publishes everything about an effect except
the one field that decides whether it does anything, so they read as healthy
for months. Four of them were in our own authored block.

The conclusion: **never build on an effect because its name matches your
intent.** Author the effects you rely on, run them, and keep that verified set
as the thing you carry.

## Three layers

Only one of these is venue-specific. Keeping them apart is what makes the rest
portable.

| Layer | Holds | Travels? |
|---|---|---|
| **Design** | the effect definitions, the fader layout, "Fan Out is neutral", colour-free presets, the stage points | yes — this document |
| **Profile** | channels, zones, hang positions, which fixtures mix colour vs carry a wheel, wheel charts, room geometry | no — one per rig |
| **Verify** | `test_effects.py`, `verify_song_looks.py`, read-back-and-compare | yes, and it ships *with* the design |

The seam that makes looks portable was already found in `build_effects.py`:
**the effect holds the shape, the group holds the order.** "Left to right" is
the same effect on every rig; only the group's channel order changes. Same
principle as XYZ focus — "point at the drum kit" is a coordinate any rig can
satisfy, not eight fixture-specific angle pairs.

## The fader model

**Fader numbers are absolute and continuous.** A page is only a window of N
onto one long list. The manual is explicit: *"Fader banks share fader mapping
with Eos, but since an OSC Fader Bank can have any number of faders per page,
the paging will be different."*

That means the same fader has several addresses depending on the window:

```
console at 10/page   fader 11  =  page 2, fader 1
console at 20/page   fader 11  =  page 1, fader 11
OSC bank config/8    fader 11  =  page 2, fader 3
```

All three are the same fader. This is why `Fader 1 / 11 Sub 41` "silently
relocated" and overwrote a page — it did not relocate, it addressed fader 11
exactly as asked. See trap 20.

### Lay out in blocks of eight

The control surface is a **Behringer X-Touch**: 8 channel faders plus a master.
So the design is organised in eights, and every bank is a coherent group.

```
 1-8    ESSENTIALS   the eight you always want under your hands
 9-16   ZONES        intensity by area of stage
17-24   COLOUR FX
25-32   MOVEMENT FX
master  EFFECT RATE
```

At 20-per-page the console shows banks 1 and 2 together plus the head of 3. On
the X-Touch the same content pages cleanly in eights. Nothing has to move
between the two views because the numbers are absolute.

### Driving it over OSC

```
/eos/fader/1/config/8        create an 8-per-page OSC fader bank
/eos/fader/1/config/3/8      jump that bank to page 3
/eos/fader/1/page/1          page down one    /page/-1  pages up
/eos/fader/1/2   0.75        set bank 1 fader 2 to 75%
/eos/fader/1/2/fire          bump it
/eos/fader/0/...             THE MASTER FADER - index 0
```

The master carries **effect rate**, so one hand changes the energy of
everything running. A fader's *slider* is set to `Effect Rate` in Tab 36; it
needs no content and there is no command-line path to it.

## The canonical effect set

Five families. Every entry is authored by us, never adopted from stock, and
every entry must pass `test_effects.py` before it is allowed on a fader.

### Intensity texture
Strobe fast · strobe slow · strobe random · twinkle · sparkle · breathe ·
blinder hit

### Chase
Forward · reverse · bounce · build · random

One shape, five attributes. The channel order comes from the paired ordered
group, so a chase is re-aimed by editing the group, not the effect.

### Colour — mixing fixtures
Rainbow wide · rainbow tight · colour fade · colour bump · two-colour alternate

### Colour — wheel fixtures
**Movers have a colour wheel, not colour mixing.** No rainbow will ever run on
them; there is no cyan and no magenta slot to reach. They get their own
equivalents so the same button does the same *job* on every fixture:

Wheel spin slow · wheel spin fast · wheel bump · wheel two-slot alternate

These are absolute effects stepping the `Color Select` parameter between slot
centres. Slot centres come from the rig profile, never guessed — see
`rig-model.md` for this rig's charts.

### Position
Circle · figure-8 · ballyhoo · sweep · cross · spiral

### Spatial
Wave left-right · ripple centre-out · depth build · odd/even

## Non-effect essentials

Three things a busking rig needs that are not effects, all confirmed by
practice as well as by our own gaps:

1. **A global effect rate fader.** One handle over everything running.
2. **A home state that never goes dark.** A base look parked on a sub and left
   up, so clearing everything else cannot black the stage.
3. **Two wash intensity playbacks, not one**, so colour can crossfade without
   dipping through zero.

## Recording rules

These are not style preferences. Each one is a bug this repo has already paid
for.

- **`Record Only`, always, for anything that should not carry colour.** A plain
  `Record` stores every parameter that is not at its default, and an RGB par's
  home colour *is* full white — so a strobe fader recorded with `Record` turns
  the stage white the moment you push it. Trap 26.
- **Delete before recording.** `Record Only` merges into an existing target.
- **Clear the stage first**, in this order:
  ```
  Go_To_Cue Out
  Chan 1 Thru 101 Effect      stop effects - the Chan form; Group does nothing
  Group 10 Sneak Time 0       "Sneak Time 0" alone is a no-op
  ```
- **Effects survive a sneak.** They are stage state and must be stopped
  explicitly, or every recorded target inherits the ones before it. Trap 29.

## Implementing on a new rig

1. Write the **profile**: channels, zones, fixture capabilities, wheel charts,
   hang positions.
2. Build **groups**, including the ordered chase groups — this is where rig
   shape enters the design.
3. Build **XYZ focus points** if the movers are positioned in Augment3d.
4. **Author the effect set**, then run `test_effects.py`. Anything static is
   not finished, whatever its label says.
5. Build **colour-free presets** with `Record Only`.
6. Map the **faders in blocks of eight**, master on effect rate.
7. Verify everything by reading it back *and comparing it to intent*. Reading
   without comparing is what let 38 corrupt macros report success.
