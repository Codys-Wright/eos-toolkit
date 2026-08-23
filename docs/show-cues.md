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

## Status: the colours are NOT verified

The looks are recorded and the notes are in, but **it was never confirmed that
each cue holds its intended colour**. Two things polluted every measurement:

- **Fader 6 CHASE was up at 60%**, so a colour-shifting effect ran over every
  cue that was tested.
- The render measurement averaged the *whole* stage. Each look deliberately puts
  different colours on different zones, so the average tends to neutral and
  proves nothing.

To verify properly: pull every fader to zero, `Go To Cue Out`, then step through
the cues and check **one zone at a time** — sample only the region a single zone
lights, or select one channel and read its colour.

The first build of these cues *did* fail this way and was rebuilt (see trap 21).
The rebuild is believed good but is unconfirmed.
