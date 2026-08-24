# The show cue list

Cue list 1 "PopStars" is the show. `build_song_looks.py` builds a full stage
look for each of the 18 song cues.

## Structure

Six performance groups, each with a video, three songs and an out:

```
1/1      Speech
1/100    GR Video    1/110-130  GR Song 1-3    1/190  GR Out
1/200    AUB Video   1/210-230                 1/290
1/300    P3 Video    1/310-330                 1/390
1/400    TRI Video   1/410-430                 1/490
1/500    KK Video    1/510-530                 1/590
1/600    PS Video    1/610-630                 1/690
1/1000+  utility looks - STAGE RIGHT, FULL STAGE, EMERGENCY LIGHT, and so on
```

The list uses **scene markers** (`Opening Speech`, `Glitter Riot`, `The Aubvis`,
`Pop Th3ory`) which group the cues visually in the PSD.

## The design

Each group gets a colour identity; its three songs move through that identity so
the stage changes without the group losing its look.

| Group | Identity | Song 1 -> 2 -> 3 |
|---|---|---|
| GR | cool | blue -> cyan -> cold white, building |
| AUB | warm | orange -> red -> warm white |
| P3 | jewel | purple -> magenta -> blue, deepening |
| TRI | fresh | green -> cyan -> yellow |
| KK | golden | warm white -> yellow -> orange |
| PS | pop | magenta/cyan contrast, biggest look last |

Zones, levels and haze are in the `DESIGN` and `LVL` tables at the top of the
script. Edit and re-run — that is the whole point of the file.

```
FRONT  1-2 + 11-18      FOH trusses over the audience     80%
MID    3-10 + 20-31     stage lip and mid stage           65%
BACK   32-48            the 13 ft seam and upstage        90%
SLIM   50-53            column slimpars                   75%
BARS   90-97            TV uplights and footlights       100%
OH     80-83            gobo movers, + a focus palette   100%
BM     85-88            beam movers, + a focus palette   100%
HAZE   100-101          35-55% rising through the show
```

## Cue notes

Every song cue carries a note describing what the look is *for*. These display
in a bar at the bottom of the PSD **including for the pending cue**, so the
operator reads the next vibe before taking it.

```
Cue 1 / 110 Notes Cool open. Deep blue wash on cyan depth. Calm and wide
```

Keep them plain — no quotes, slashes or brackets.

## Build order matters

`build_popstars.py` and `build_song_looks.py` **write the same cue numbers**.
Popstars builds the structure — acts as blocks, links, scene markers — and
records 110/120/130, 210/220/230 and so on as part of that. Song looks then
records the *look* into those same cues.

```
1.  python3 build_popstars.py       structure: blocks, links, scenes
2.  python3 build_song_looks.py     the look inside each song cue
3.  python3 verify_song_looks.py    prove the colours landed
```

**Re-running popstars on its own silently discards every song look**, and
nothing errors — the cues still exist and still play. If you touch the
structure, re-run steps 2 and 3 behind it.

## Status: verified

**90 zone checks, 0 failures** (2026-08-23). Every one of the 18 song cues holds
the colour it was designed with, on all five RGB zones — front, mid, back,
slimpars and bars.

Run it with `python3 verify_song_looks.py`. It clears the stage, learns the
reference hue of each colour palette from the console rather than assuming one,
then walks the cues sampling a single channel per zone.

### What defeated the earlier attempts

- **A fader was up** running a colour effect over every cue under test.
- **The measurement averaged the whole stage.** Each look deliberately puts
  different colours on different zones, so the average tends to neutral and
  proves nothing.

The verifier handles both: `Sub 1 Thru 137 At 0`, `Chan 1 Thru 101 Effect`,
`Go_To_Cue Out`, then one channel at a time.

### Three things that made the verifier itself lie before it told the truth

Worth knowing, because each produced a confident wrong answer:

1. **`/eos/out/color/hs` publishes on SELECTION CHANGE, not on demand.** Asking
   for the same channel twice returns nothing the second time — and the stored
   value still holds the *previous* channel's colour. A stale read looks
   exactly like a real one. The fix is to bounce the selection off an empty
   channel before every sample.
2. **The cues fade over 3 seconds.** Sampling 1.2s after `Go_To_Cue` caught the
   first zone mid-crossfade, returning hues that sat between two palettes.
   Later zones passed only because the earlier samples had eaten the time.
3. **An off-by-one in the zone table.** BARS was compared against DESIGN column
   5, which is the *mover* colour, not column 6. It reported a correct stage as
   broken — the most expensive kind of test failure.

### Not covered

The movers are **not** checked. They have colour wheels, so there is no hue to
read back, and their slot values come from an OEM chart rather than a Riukoe
document (see [rig-model.md](rig-model.md)). The beam movers are parked on Open
because their 12-slot wheel chart is still unknown. Confirm those by eye.
