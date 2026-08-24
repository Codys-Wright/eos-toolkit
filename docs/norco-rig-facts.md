# The Norco rig, as it actually is

Everything below was established against the real console (Eos **3.3.5.69** on
the venue Mac) rather than the Nomad, and verified by read-back or by eye.

## Fixture control values

The two mover types look interchangeable on the desk and are not.

| | Riukoe overhead 80-83 | Betopper beam 85-88 |
|---|---|---|
| Strobe Mode (open) | **63** | **25** |
| Parameters | Position Blink, Dimmer Curve | Beam Fx Select, Beam Fx Index/Speed, PWM Frequency |
| Gobo wheel | 8 slots in DMX 0-63 | different, chart unknown |
| Colour wheel | 8 slots, 16 DMX each | different, chart unknown |

**Strobe Mode 25 closes the Riukoe's shutter.** Both are now PARKED at their
correct value so it cannot come back. See trap 32.

### The house look for the beam movers

```
Group 8 Strobe_Mode 25
Group 8 Beam_Fx_Index/Speed Full
Group 8 Beam_Fx_Select 2
```

A slow spinning gobo. This is the default unless a clean hard beam is wanted
(`Beam_Fx_Select 1`). Stored as **preset 101 BM SPIN**; 102 is the clean
version and 103 opens the overheads.

The `/` in `Beam_Fx_Index/Speed` needs no escaping - verified by read-back.
Note `Full` on that parameter resolves to 10, not its maximum.

## Addressing

Read off the console. **Both universes are in use** and addresses repeat
across them - 260, 302 and 303 all exist twice.

| Chan | Addr | Univ/Addr | Mode | What |
|---|---|---|---|---|
| 90 | 260 | 1/260 | 7ch | far left bar |
| 91 | 240 | 1/240 | 7ch | centre bar |
| 92 | 732 | 2/220 | 7ch | far right bar |
| 93 | 276 | 1/276 | 7ch | centre-left bar |
| 94 | 795 | 2/283 | 7ch | centre-right bar |
| 95 | 772 | 2/260 | 3ch | TV uplight L |
| 96 | 779 | 2/267 | 3ch | TV uplight R |
| 97 | 782 | 2/270 | 7ch | front centre bar |
| 85 | 870 | 2/358 | 12ch | floor mover, far left |
| 88 | 882 | 2/370 | 12ch | floor mover, far right |
| 86 | 894 | 2/382 | 12ch | floor mover, centre-left |
| 87 | 906 | 2/394 | 12ch | floor mover, centre-right |
| 98 | 0 | — | — | **unpatched phantom** |
| 100 | 303 | 1/303 | ? | hazer L |
| 101 | 814 | 2/302 | ? | hazer R |

Note the floor movers are **not in channel order by address** - 88 sits
between 85 and 86.

## Groups 1-10

```
 1 Washers      1-39, 42-46, 50-53      everything that washes the stage
 2 Pars         40-41, 47-48            AUDIENCE-FACING CANS - blinders
 3 Movers       80-83, 85-88
 4 Strips       90-97
 5 SlimPars     50-53
 6 Hazers       100-101
 7 OH Movers    80-83     LOAD-BEARING
 8 Beam Movers  85-88     LOAD-BEARING
 9 Movers + Strips
10 All          1-18, 20-97             LOAD-BEARING (the reset target)
```

**Group 2 is not "the pars".** 40, 41, 47 and 48 are hard cans on the back
wall pointing at the audience. They are deliberately excluded from Back Wash,
Upstage, Left All and Right All so a wash can never blind the room by accident.

## Faders

```
 1-9    FX          STROBE RAINBOW COL-SMOOTH OH-MOVE BM-MOVE
                    PAR-CHASE SPARKLE INT-FADE MVR-BALLY
 10     MASTER FX   Tab 36 job - set the slider to Effect Rate
 11-15  WHITE       L / C / R / ALL / BACK - who the audience can see
 16-20  FRONT MID BACK MOVERS CANS
 21-30  the 13 chase cue lists
 33-37  LEFT CENTRE RIGHT HAZE BLACKOUT
```

**Fader 37 is an inhibitive BLACKOUT.** Live it at FULL; pull DOWN to kill
everything including the white faders. It defaults to zero, which is blackout
- see trap 34, it took the whole rig down minutes before a show.

Usable faders are **1-17, 21-30 and 33-37 only**. Everything else rejects a
mapping. Mapping is readable through the OSC fader bank
(`/eos/out/fader/1/<n>/name`), which `verify_faders.py` uses.

## Show design

The house style, arrived at over one build:

- **Cues carry colour and mood at LOW level** - verse 35/45/30, chorus
  50/60/45, big moments 85-100. The stage reads as atmosphere.
- **The white bank decides who is seen.** Faders 11-15, cold white, front
  and mid together.
- **Effects live on the sides.** Groups 11 and 13 get chases; group 12
  (centre) never does, so there is always somewhere a face reads.
- **Mover shapes rotate per song** so no two look alike. All twelve stock
  shapes (901-909, 926, 934, 940) are verified live.
- **Fade times come from tempo.** A bar at 132 BPM is 1.818s, so a four-bar
  build is 7.3s. `bars(n, bpm)` in `build_song_sections.py`.
