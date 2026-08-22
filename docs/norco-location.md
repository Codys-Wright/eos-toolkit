# The Norco location

Rockstars of Tomorrow, 1900 Lampton Lane, Norco CA. This is the venue the show
file models: the room, the Augment3d scene, and where all 70 fixtures live.

Every dimension here is **measured or operator-confirmed**. Where a number is
still inferred it says so.

## The room

```
                        upstage wall  y = +2.95
        +--------------------------------------+
        |            UPSTAGE LIFT              |   30 ft wide, 13 ft deep, z +0.152
        |         (the original stage)         |
        +--------------------------------------+   <- 13 ft seam, y = -1.01
         \                                    /     flare, 45 deg, 4.5 ft per side
          +----------------------------------+      y = -2.39
          |         DOWNSTAGE DECK           |      39 ft wide, z 0.000
          +----------------------------------+   <- stage lip, y = -3.76
          |                                  |
          |            AUDIENCE              |      39 ft wide, 33 ft deep, z -0.203
          |                                  |
          +-------------------+--------------+   <- y = -13.81
                              | BOOTH | CLST |      7 ft deep alcove
                              +-------+------+      y = -15.95
```

| Dimension | Value | Source |
|---|---|---|
| Theater width | **39 ft** (11.89 m) | plan, confirmed by the operator |
| Stage width at its widest | **39 ft** | operator |
| Stage width upstage of the flare | **30 ft** | operator |
| Stage depth | **22 ft** | operator (as-built was 11–13 ft, since extended) |
| Seam / flare start | **13 ft** from the upstage wall | operator |
| Audience depth | **33 ft** past the stage lip | operator |
| Floor-to-ceiling | **12 ft** | operator estimate |
| Stage deck above the audience floor | **8 in** | operator |
| Upstage lift above the deck | **6 in** | operator |
| Sound booth | 7 ft deep x 13 ft wide | plan + operator |
| Storage closet | 7 ft, stage-left of the booth | operator |

**Do not trust the plan's "1413 Sq. Ft." as the room area.** That is the
*seating area only* — the stage is listed separately at 150 sq ft. Solving for
a 1413 sq ft total forces the depth down to ~36 ft and squeezes the audience,
which is what produced two wrong builds before the operator gave the 33 ft
figure directly.

The plan's `27'` is the width of the **opening between the storage rooms**, not
the stage. The stage itself is 30 ft.

## Coordinates

Augment3d is **metric**, and this model is dimensionally true — the 39 ft
theater width lands on walls at x = ±5.94 m.

```
+X = stage left      +Y = upstage      +Z = up
origin: stage centre, at the downstage deck surface
```

Deck heights: audience `-0.203`, downstage deck `0.000`, upstage lift `+0.152`,
ceiling `+3.454`.

## Building the room

`a3d_room.py` builds the entire scene from **two numbers**:

```bash
python3 a3d_room.py <extracted-show-dir> <stage_width_ft> <stage_depth_ft>
python3 a3d_room.py /tmp/show 30 22          # current
```

Everything downstream — flares, stage side walls, upstage wall, riser face,
both decks, back wall, alcove, booth, closet, ceiling — derives from those.
Change the width and the flare recomputes; change the depth and the audience,
back wall and alcove all move with it.

### Working on the scene file

The scene is `working.a3d` inside the `.esf3d`, itself a ZIP:

```bash
unzip -q show.esf3d -d out && cd out
mkdir a3d && cd a3d && unzip -q ../working.a3d
chmod -R u+rw .            # entries extract with no permission bits
# edit Scene/Primitive.json and Scene/Scene.json
zip -q -r -X ../working.a3d version.json resource_database.json Resources Scene
cd .. && zip -q -X out.esf3d version.json showdat.dat showlog.log working.a3d
```

Adding a primitive means writing **both** files: an item in
`Scene/Primitive.json` *and* a `{"type":2,"uid":...}` entry in `Scene.json`'s
tree. A primitive missing from the tree does not render.

### Size is derived, scale is authoritative

Each object carries `size` (metres) and `local.scale` (a multiplier on
`local_bounds.size`, the unscaled mesh). **`size` is output, not input** — Eos
rewrites it as the world axis-aligned bounding box. A 1.94 m plane rotated 45°
comes back as `size (1.37, 1.37, ...)`, because 1.94/√2 = 1.37.

So author in real units and back-solve:

```python
scale.x = (target_metres) / local_bounds.size.x
```

Writing `size` alone is silently ignored. The Augment3d Inspector exposes
Position / Scale / Rotation — not Size — so the file route is the *only* way to
set a true dimension.

### Rotation needs the quaternion

Objects store `eulers` **and** `quat`, and the renderer reads the quaternion.
Setting eulers alone leaves the object unrotated while the inspector claims
otherwise. For a Z rotation:

```python
quat = {"w": cos(a/2), "x": 0, "y": 0, "z": sin(a/2)}
```

For a tilt composed with a pan (the TVs), apply X then Z — the same order the
fixtures use: `q = qz ⊗ qx`.

### Walls are single-sided

Wall meshes are one-sided planes. `Wall - Upstage` sits at y = +2.95 with euler
0 and is visible from the room, so **euler 0 faces −y**. Anything at the back of
the room needs 180.

There is no bulk rule. `Wall - Alcove Step` (x = −0.15) needs 180 while
`Wall - Closet Divider` (x = +3.81) needs 0 — same mesh, mirrored positions,
opposite answers, because the normal must point at whichever side people stand
on.

**Do not hedge with back-to-back pairs.** Placing each wall twice at 0 and 180
guarantees visibility and also makes it opaque from behind — which blocked the
camera in the sound booth. Derive the normal instead.

Also: the two side-wall meshes are *different* (`Wall - Stage Left` vs
`Wall - Stage Right`, different `model_uid`). Cloning the Left mesh for a
right-hand wall produces an invisible wall.

### Pivots

Walls and TVs pivot at their **base**; grounds and the ceiling pivot at their
**centre**. Confirm before moving anything:

```python
pivot_is_base = abs(obj["center"]["z"] - (pos.z + size.z/2)) < 0.01
```

### Props store offsets, not absolute heights

A prop's `z` is its offset **above the deck it stands on** — the snare at
`0.101` means 10 cm above the riser. When a deck moves, re-seat props with
`new_z = deck_height + existing_offset`. Snapping them to the deck flattens the
drum kit into the floor.

Fixture heights on the console are **absolute** and need the opposite
treatment.

## The rig

70 fixtures. `build_rig_positions.py` places and aims all of them; every
position derives from named constants (`SEAM`, `FRONT`, `AUD_1_3`, `AUD_FAR`,
`PIPE`, `FAN_OUT/FAN_IN`), so moving a row repositions *and* re-aims it.

```
y  1.80   40,41,47,48          upstage
y  1.20   42,46                drum-kit corners, aimed at the kit
y -1.01   32-39, 43-45         13 ft seam; 32-39 panned inward, 43-45 straight
y -2.70   24-27                mid stage, fanned
y -3.76   7-10, 20-23, 28-31   stage lip, in line with the speaker array
y -7.42   3-6, 11-18           12 ft out  (6 ceiling tiles)
y -9.86   1, 2                 20 ft out, singles at x +-5.00
```

Pars hang at `z 3.25`, 8 in under the ceiling. Overhead movers 80–83 on truss
at `z 3.20`, y 2.20. Floor beams 85–88 + 98 at y −1.30 on the deck, aimed up.
Slimpars 50–53 on the upstage wall, aimed downstage.

### The eight bar lights

The channel count validates the mapping — six 7-channel and two 3-channel,
matching exactly six + two described positions:

| Channels | Type | Position |
|---|---|---|
| 90, 91, 92 | 7ch | uplighting the three upstage TVs (x −3.50 / 0 / +3.50) |
| 93, 97, 94 | 7ch | footlights at the foot of the stage end (x −3.00 / 0 / +3.00) |
| 95, 96 | **3ch** | uplighting the two side (flare) TVs, x ±4.90 |

### Fan

Groups of four splay outward: `-12, -4, +4, +12` degrees. Applied to 20–23,
28–31, 11–14, 15–18 and 24–27. Channels 32–39 keep a hard inward cross instead
— they are the one angled group per side. Pairs are not fanned.

### Known-approximate

- **Tilt is capped at 65°.** Both audience rows hit the cap, so they aim
  parallel rather than the far row raking flatter. Geometry wants ~70° and ~74°.
- **Channels 1 and 2 point straight upstage**; a lone side par would normally
  toe in.
- **Ceiling height is an estimate**, not a measurement. Everything vertical
  scales off it.

## Ceiling tiles as a measuring tool

The suspended grid is **2 ft** on the axis running toward the stage — confirmed
by two independent operator statements that cross-check: the 6-tile row sits at
12 ft, and the furthest fixtures are only ~halfway into a 33 ft audience. At
4 ft per tile the 6-tile row would land at 24 ft, beyond the furthest row, which
is impossible.

Counting tiles is the cheapest way to get a real distance out of this room.
