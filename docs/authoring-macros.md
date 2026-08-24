# Authoring macros over OSC

Macros **can** be written from a script, but not the obvious way. Learn mode
does not work, and neither do OSC key presses. What works is a hybrid: OSC to
navigate, real synthesised keystrokes to type the body.

## Why macros

Applying an effect normally takes two steps - select channels, then choose the
effect. A macro collapses that to one button, and unlike a submaster it carries
**no intensity of its own**, so it layers onto whatever the cue already has.
Set the colour in the cue, fire an FX macro on top.

The alternatives do not work:

| Container | Holds an effect? | Notes |
|---|---|---|
| Preset | **no** | the `fx` field stays empty whether you Record or Record Only |
| Submaster | yes | but brings its own level, which fights the cue |
| **Macro** | n/a - runs a command | correct tool; touches only what you tell it |

## What does NOT work

- **Learn mode.** `/eos/key/learn` toggles, but commands sent over OSC while
  learning **execute live instead of being recorded**. The macro stays empty.
- **`/eos/key/edit`.** Does not enter macro edit mode.
- **OSC key presses as the body.** In edit mode they do not insert.
- **Command strings as the body.** In the macro editor a bare number is read as
  a *macro number*, so `/eos/newcmd "Group 203 Effect 1"` became `Macro 203`.
- **`{Done}`.** Exits edit mode without committing typed keystrokes.
- **Softkeys while in edit mode.** They are an insert palette - pressing
  softkey 6 inserted a literal `Clear_CmdLine` into the macro body.

## The recipe that works

```
1. [Macro] [Macro]                open the Macro Editor (Tab 18)
                                  Display navigation, so System Events:
                                  Mac hotkey M, twice, ~80ms apart
2. /eos/newcmd "<num>#"           a bare number IS a macro number in this
                                  display; an unused one creates an empty macro
3. /eos/softkey/6                 {Edit}. Verify it took - the softkeys change
                                  to Loop Begin | Loop End | Wait | Delete |
                                  Wait for Entr | Done | Wait For Inpt
4. body via SYSTEM EVENTS         real console keystrokes, one AppleScript
5. Ctrl+Enter                     [Select] = save
6. /eos/newcmd "Macro <n> Label <text>#"
```

Delete a macro before rebuilding it - edit mode **appends** to existing content.

### Mac hotkeys for macro bodies

```
Group  G          Effect  Alt+E        Enter   Return
At     @          Full    F            Thru    T
Select Ctrl+Enter     Escape  Escape   Macro   M
```

Verified against ETC's `EosFamily_KeyboardShortcuts.pdf`.

### Result

```
Macro 101 "FX Chase Fwd"  ->  Group 2 0 3 Effect 1 \r
```

Digits arrive separately because they are individual keypresses; Eos assembles
them. That is the correct stored form.

## Making FX buttons mutually exclusive

An effect started by a macro keeps running when you fire the next one - they
stack, because nothing stopped the first. `Group <n> Effect [Enter]` with no
effect number is Eos's **stop flag**: it kills running effects on those channels
without touching levels or colour.

So each FX macro is stop-then-start:

```
Group 1 Effect ⏎          stop every running effect (group 1 = chans 1-98)
Group 203 Effect 1 ⏎      start this one
```

Now the buttons behave like radio buttons. For layering two effects at once,
use submasters instead - those are additive by design, and their faders let you
ride the depth.

## The focus hazard

System Events types into **whatever app is frontmost**. If focus moves mid-run,
the keystrokes land in someone's text editor - we sent half a macro into a chat
window this way.

Re-focus Eos before *every* keystroke batch, not once at the start, so drift
costs one batch instead of the run:

```python
osa('tell application "System Events" to tell process "Eos Family" '
    'to set frontmost to true')
time.sleep(0.35)
```

And tell the operator not to touch the computer while it runs.


## Firing a macro

`Macro <n>` typed on the command line does **not** run it — it echoes and does
nothing. Use the key:

```python
for k in ("macro", "1", "4", "0", "enter"):
    conn.send(f"/eos/key/{k}", 1); conn.send(f"/eos/key/{k}", 0)
```

See [trap 30](command-line-traps.md).

## Verifying a macro

Reading the body back is not enough — compare it to what you meant to type. A
38-macro build once returned `Copy_To Rem_Dim @ Sneak 1 Thru 1 0 1 Effect` for
every single macro, printed all 38 of them, and exited 0.

The cause: `chan` is not in `HOTKEY`, so it was typed as four letters, and in
the Macro Editor C/H/A/N are the hotkeys Copy_To / Rem_Dim / @ / Sneak. Any
unmapped multi-character token does this. `build_macros.py` now raises rather
than typing one, and flags a body containing those tokens as an error.

No `Chan` keystroke is needed anyway: a macro body starting with a bare digit
auto-completes to a channel selection when it plays back.
