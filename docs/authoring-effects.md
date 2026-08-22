# Authoring effects over OSC

> **TL;DR** — A human presses `[Effect]` `[Effect]` once to open the Effect
> editor. From then on a script can create and edit effects over OSC. The human
> does not do the editing; they only provide display focus, which OSC cannot.
> Close the editor and every write silently fails with
> `Error: Effect Does Not Exist`.

**Effects CAN be created and edited over OSC** — but only while the **Effect
editor display is open on the console**. This one precondition is the difference
between "impossible" and "fully scriptable", and nothing in the OSC
documentation mentions it.

## The precondition

A human must press **`[Effect]` `[Effect]`** on the console (or open the Effects
tab). OSC key presses do **not** navigate displays — `/eos/key/effect` reaches
the command line but never moves the UI, so a script cannot open it for itself.

With the editor closed, every creation attempt fails with
`Error: Effect Does Not Exist`. With it open, everything below works.

You can tell the editor is focused by watching softkeys:

```
closed  ->  Address | Query | Snapshot | Highlight | Assert | ...
open    ->  Edit | Properties | Icon | Offset
```

## Creating an effect

```
/eos/newcmd "Effect 200"        # no terminator
/eos/key/enter                  # -> "Effect 200 Create Type"
                                #    softkeys: StepBased | Absolute | Focus
                                #              | Linear | Color
/eos/key/stepbased              # -> effect 200 now exists
```

Verify:

```
/eos/get/fx/200
 -> {type: "StepBased", entry: "Cascade", exit: "Immediate",
     duration: "Infinite", scale: 100}
```

Type keys: `stepbased`, `absolute`, `focus_effect`, `linear`, `color_effect`.

## Building a step-based effect

```
/eos/key/step                   # line: "Effect 200 Step "
/eos/cmd    "1 Thru 5"          # APPEND - newcmd would wipe the line
/eos/key/enter                  # -> "Please Confirm"
/eos/key/enter                  # confirmed, 5 steps created

/eos/newcmd "Group 21"          # channels for the steps
/eos/key/enter
```

**Channels enter the steps in the order they are stored in the group.** That is
the most powerful lever available to a script: effect *shape* is authored in the
GUI, but chase *order* comes from group order, and groups are fully scriptable.

```
Chan 34 + 31 + 12 + 5 Record Group 200   # stores exactly that sequence
```

One hand-made 5-step effect plus N ordered groups = N distinct chases.

## Editor softkeys once a StepBased effect is open

```
Step | In Time | On State | InsrtBefore | Properties |
Focus Palette | Color Palette | Beam Palette | BPM | Icon | Offset
```

## Setting properties

```
/eos/newcmd "Effect 200"
/eos/key/cycletime
/eos/cmd    "2"
/eos/key/enter                  # -> "Effect 200 CycleTime 0:02 #"
```

Property keys: `cycletime`, `entry`, `exit`, `duration`, `scale`, `rate`,
`steptime`, `intime`, `decaytime`, `dwell`, `trail`, `grouping`, `spread`,
`hform`, `vform`, `reverse_steps`, `random_rate`, `infinite`.

Labels work from Live or the editor:

```
Effect 200 Label Odd Par Chase
```

## What you still cannot verify over OSC

`/eos/get/fx/<n>` returns only `label, type, entry, exit, duration, scale`.
Step counts, per-step channels, cycle time and attributes are **not** in the
reply. Verify by running the effect and reading `/eos/out/active/chan`:

```
Group 21 At 100
Group 21 Effect 200
 -> /eos/out/active/chan = "1,3,5,7,9,11,13,15,..."
```

## Running vs stored - the two-level trap

`Rate`, `Scale`, `Entry`, `Exit`, `Duration` exist at two levels:

- the value stored in the **definition** (editable in the editor, as above)
- a per-instance **override** applied when a channel runs the effect

Sending `Effect 200 Scale 250` from Live with the effect running is accepted but
only sets the override; the definition is unchanged. From inside the editor it
edits the definition. Same words, different target, no error either way.

The old error `Error: Effect Not Running`, sent from Live with nothing running,
was what made this look impossible for so long. It means "no instance to
override", not "this command does not exist".


## The two-phase constraint

Building step-based chases needs **both** contexts, and only a human can switch
between them:

| Phase | Context | Why |
|---|---|---|
| 1. ordered groups | **Live** | `Chan ... Record Group N` is a Live command; from the editor it returns `Syntax Error` |
| 2. effects | **Effect editor** | creation needs display focus |

`/eos/key/live` switches to Live and works. **Nothing gets you back** —
`/eos/key/effect` twice from OSC just types the words on the command line. A
human must press `[Effect] [Effect]` again.

So scripts should be split by phase and fail loudly if run in the wrong one:

```
python3 build_effects.py --phase groups     # from Live
# human presses [Effect] [Effect]
python3 build_effects.py --phase effects    # from the editor
```

Detect the wrong context by checking for `Does Not Exist` on the first
`Effect <n>` + `enter`, and abort rather than issuing 190 more commands that
will all silently fail.

## Group order is real but unverifiable over OSC

Channels enter steps in **group storage order**, which is the main design lever.
But the group reply uses the OSC Number Range format, which compresses to sorted
ranges:

```
requested  32,33,34,35,20,21,22,23,11,12,...   (left to right across the stage)
reads back ['1-18', '20-48']                    (a SET, not a sequence)
```

A group with no compressible runs reads back as a literal list
(`[1,3,5,7,...]`), so some groups *look* order-preserving and others do not —
that is the encoding changing shape, not the data.

Level polling does not resolve it either: one pass of patch queries takes ~3s
while a chase cycle is under 1s, so samples land at random phases.

**Chase order has to be confirmed by eye.** Everything else about an effect can
be verified from the console.
