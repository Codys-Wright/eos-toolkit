# Authoring effects over OSC

> **TL;DR** — Effect authoring requires the Effect editor to have focus, and
> OSC cannot navigate displays. Either a human presses `[Effect]` `[Effect]`,
> **or** on macOS a script sends that gesture via System Events (see
> [Closing the loop](#closing-the-loop-macos) below) and needs no human at all.
> Without focus, every write fails with `Error: Effect Does Not Exist`.

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


## Closing the loop (macOS)

OSC cannot navigate displays, but macOS System Events can — and it ships with
the OS, so nothing needs installing.

**Requires** System Settings > Privacy & Security > **Accessibility** > enable
whichever app runs the script. Without it, osascript fails with
`not allowed to send keystrokes. (1002)`.

### The Mac hotkey is NOT the published one

The widely circulated Eos hotkey tables are Windows-oriented and list
**Ctrl+E** for the Effect key. On macOS that arrives as a plain `e`, which is
**Recall From** — a completely different command that will happily start
building a wrong command line.

```
macOS:  Effect  =  Option + E
```

Confirmed against ETC's own `EosFamily_KeyboardShortcuts.pdf`, which lists
`Effect  Alt E` — Alt being Option on a Mac keyboard. Also useful from that
table: `[Expand] & [Effect]` opens the Effect Status Display (Tab 8).

### The gesture is timing sensitive

`[Effect] [Effect]` must be two presses in quick succession. Sent 1.2s apart
they register as two separate Effect keypresses and the editor does not open.
Sent ~80ms apart, in a single osascript, it works:

```applescript
tell application "System Events"
  keystroke "e" using {option down}
  delay 0.08
  keystroke "e" using {option down}
end tell
```

### Confirming focus over OSC

The editor publishes a distinctive softkey set, so a script can verify rather
than assume:

```
Live         -> Address | Query | Snapshot | Highlight | Assert | ...
Effect key   -> Size | Replace With | Offset | Axis | Edit | BPM | Rate | ...
EDITOR OPEN  -> Step | In Time | On State | InsrtBefore | Properties | ...
```

The command-line prompt also changes from `LIVE: Cue 22 / 6 :` to
`BLIND: Effect 203 :`.

`eos_focus.py` wraps all of this. `build_effects.py` calls it automatically when
it detects an unfocused editor, so the effects phase now needs no human step.

### Verified end to end

Created, typed, stepped, channel-assigned, cycle-timed, labelled, read back and
deleted — with no human input at any point:

```
stepbased  -> Effect 230 Create Type StepBased #
fx 230     -> {type: StepBased, entry: Cascade, scale: 100}
step 1 Thru 4, Group 212, CycleTime 1.5, Label "Auto Built"
RESULT     -> {label: "Auto Built", type: StepBased, entry: Cascade, scale: 100}
```

### What is still out of reach

Accessibility grants **keystrokes only**. Screen Recording is a separate
permission; without it `screencapture` fails with
`could not create image from rect`, so a script still cannot *see* the screen.
Eos is a Qt app that paints its own UI, so the accessibility tree exposes only a
handful of popup buttons and no display tabs — reading UI state means
screenshots, not the tree.

Still unreadable either way: magic sheet contents, scene markers, palette
values, effect step contents.
