# XYZ focus — aiming movers at coordinates, not angles

A pan/tilt focus palette stores a different pair of numbers for every fixture,
all of them meaning "point at the drum kit". An XYZ palette stores the drum kit
*once*, as a point in the room, and each mover solves its own angles. Re-hang a
mover and the palette still lands. Add a mover and it inherits the whole
library for free.

Built and verified against Eos **3.3.9.25** with all eight movers.

## The syntax

Documented in the Operations Manual OSC appendix, p.588:

```
/eos/chan/<n>/xyz   <x> <y> <z>    set XYZ for a specific channel
/eos/xyz            <x> <y> <z>    set XYZ for the current selection
/eos/out/xyz                       read the selected channel's position back
Chan <n> XYZ_Format Enable         store this channel's focus as XYZ
```

`XYZ_Format` is a per-channel property of how focus data is **stored**. Without
it, a `Record Focus_Palette` writes pan/tilt and the entire point is lost. You
send it with an underscore; Eos echoes it back with a space.

### There is no command-line form

This is the trap. The obvious guess parses without error:

```
Chan 80 X 0 Y 0 Z 1.5      -> accepted. Does nothing.
Chan 80 Qzz                -> "Error: Syntax Error"
```

`X` is a recognised token, so no syntax error is raised, and nothing moves.
Classic [trap 18](command-line-traps.md#18-submaster-and-fader-properties-what-is-reachable)
— accepted is not applied. Only the `/eos/chan/<n>/xyz` OSC address works, which
also means `/eos/newcmd` cannot do this and neither can the MCP server's
command tool. It needs a raw OSC send.

## Coordinates are always metres

> "OSC XYZ coordinates are measured in decimal meters, regardless of the unit
> selected in Setup > System Settings > Augment3d." — Manual p.588

This matters here specifically, because two documents in this repo use
different units:

- **[norco-location.md](norco-location.md)** — the current, true-metric model.
  Stage centre origin, walls at x = ±5.94 m. **Use this one.**
- **[rig-model.md](rig-model.md)** — the superseded magic-sheet-import era,
  where positions were in *sheet units* at ~1.65 per metre.

Write an XYZ target in sheet units and it lands 65% too far out with no error.

## Eos silently clamps what the rig cannot reach

Asking the overhead movers (hung at z 3.2) to aim at z 3.4 — above their own
trim:

```
wanted (0.0, -1.0, 3.4)
chan 80 got [-7.308,  2.426, 1.804]
chan 81 got [-4.331,  2.908, 2.800]
```

No error. `/eos/out/xyz` reports where the fixture actually ended up, not what
was asked for. The floor beams passed the identical palette, because pointing
at the ceiling is trivial from the deck.

**Reachability is per fixture**, so verify per fixture, and compare against
what was *requested*. A check that treats the read-back as ground truth passes
every time and proves nothing.

```python
if any(abs(got[i] - wanted[i]) > 0.02 for i in range(3)): ...
```

## Convergence is not the only useful shape

A single coordinate for all eight movers gives "everyone look at this spot".
Half the good looks are *relationships between beams* instead — straight out,
crossed, fanned, parallel — and those cannot be expressed as one point.

`build_xyz_focus.py` therefore takes a target as **either** a single `(x,y,z)`
**or** a `{channel: (x,y,z)}` dict, and computes the per-fixture form from where
each mover actually hangs:

```python
def crossed():        # each mover aims at the mirror of its own x
    return {ch: (-x, -1.00, 1.50) if ch in OH else (-x, -1.25, 2.50)
            for ch, (x, y, _z) in HANG.items()}
```

Because the patterns derive from `HANG`, re-hanging a mover and updating one
row re-derives every spread palette. That is the whole argument for XYZ,
applied to the palette library itself.

## The precondition nobody mentions

**Hang to Focus Offset is the XYZ offset from the centre of the fixture base to
the point it actually pans and tilts about** (Manual p.165). Eos uses it to
convert an XYZ beam target into pan/tilt.

Left at zero — which is the default, and the current state of the Riukoe and
Betopper profiles here — every XYZ aim lands slightly off. The error scales with
how far the pivot really is from the base, so it is worst on the floor beams.

It is set per **fixture type** at Patch → {Fixtures} → {Physical Data}. There is
no command-line path to it ([trap 19](command-line-traps.md)), so it cannot be
scripted and does not appear in any read-back.

## Recording the palettes

Order matters:

```
Chan <n> XYZ_Format Enable          per channel, before anything else
Delete Focus_Palette 1 Thru 10      Record Only merges - see trap 26
/eos/chan/<n>/xyz x y z             per channel
  ... verify every channel against its own requested target ...
Chan <sel> Record Focus_Palette <n>
Focus_Palette <n> Label <text>
```

## What XYZ does not fix

- **Colour wheels.** The movers still have no colour mixing; XYZ is focus only.
- **Unpatched channels.** 19 and 98 are at address 0 and must stay out of the
  selection — they render in Augment3d and emit nothing.
- **The visualiser's opinion.** A palette can verify clean and still look wrong
  on stage if the fixture *orientation* in Augment3d is wrong. Orientation is
  the hang, not the aim — see [norco-location.md](norco-location.md).
