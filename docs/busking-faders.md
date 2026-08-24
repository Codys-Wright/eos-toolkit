# The busking fader system

Five pages of faders for the Norco rig, built by `build_busking_faders.py`.
The design follows the ETC busking tutorial, adapted to a rig with no colour
mixing on the movers and a console with a restricted fader configuration.

## Layout

Organised in **banks of eight**, because the control surface is a Behringer
X-Touch: 8 channel faders plus a master. Fader numbers are absolute and
continuous (trap 20), so an OSC fader bank of 8 pages cleanly through these
while the console at 20-per-page shows banks 1-2 together.

```
BANK 1  faders  1-8   STROBE  RAINBOW  COL SMOOTH  OH MOVE
                      BM MOVE  PAR CHASE  SPARKLE  INT FADE
BANK 2  faders  9-16  THE STAGE, LEFT TO RIGHT
                      LEFT  FRONT  MID  BACK  CENTRE  MOVERS  HAZE  RIGHT
BANK 3  faders 17-24  colour FX + mover wheel equivalents
BANK 4  faders 25-32  movement
BANK 5  faders 33-40  overflow masters
MASTER                effect rate
```

**Bank 2 is a map of the stage.** Fader 1 of the bank is stage left and fader 8
is stage right, so hand position matches the part of the stage it controls,
with depth running downstage-to-upstage through the middle.

### Fader mapping IS readable

This document used to say it was not, and that belief is why the documented
layout and the real one drifted apart for months - nobody could check.

It is published through the **OSC fader bank** channel rather than the `get/`
query protocol everything else here uses:

```
/eos/fader/1/config/20            create a 20-wide OSC bank
/eos/out/fader/1/1/name           -> ['S 1 STROBE']
/eos/out/fader/1/9/name           -> ['S 41 LEFT']
```

`verify_faders.py` reads that and compares it to the builder's table. It
immediately found four stale mappings left over from the previous layout: the
builder mapped faders but never *un*mapped them, so anything the new plan did
not reach kept its old assignment. The verb is `Delete Fader <page> / <n>` -
both `Unmap` and `Fader P / F Delete` are syntax errors.

**Labels are capped at 5 characters** — that is all the fader display shows.

## Sub numbers are NOT fader numbers

`Fader <page> / <fader> Sub <n>` maps content to a fader, and it is scriptable:

```
Fader 1 / 1 Sub 1        ->  "Fader 1 / 1 Mapped To Sub 1"
Fader 2 / 1 Sub 21       ->  page 2, fader 1
Fader 2.1 Sub 21         ->  same thing, dot notation also works
```

Do **not** use the bare `Fader <n>` form. `Fader 1 / 11` is accepted and
silently **wraps into page 2 fader 1** — pages hold 10 faders, so an
out-of-range fader number relocates rather than erroring. That overwrote a
whole page of content before it was noticed.

### This console's fader grid — probed 2026-08-23

**The fader page size is 10.** Showing 20 faders on screen is a display
setting and does not change it. Slot numbers continue past the page size
instead of erroring, so `Fader 2 / 16` is fader 26, not "page 2, slot 16":

```
absolute fader = (page - 1) * 10 + slot
```

Parse-checking a mapping at every slot gives the real shape:

```
usable   1-16,  21,  31-40      27 faders
reserved 17-20, 22-30
```

That is why `Fader 1 / 16` worked while `Fader 2 / 16` failed — faders 16 and
26, one usable and one reserved, from commands that look almost identical.

Banks 1 and 2 sit at faders 1-8 and 9-16. Bank 3 goes to **33-40**, which is
both a contiguous usable run and exactly page 5 of an 8-wide OSC fader bank on
the X-Touch.

### The old probe

Probe before designing a layout — capacity is not uniform:

```
page 1  ..........   all 10 usable
page 2  ..........
page 3  .XXXXXXX..   only faders 1, 9, 10 - the rest are reserved
page 4  ..........
page 5  ..........
page 6+ XXXXXXXXXX   do not exist
```

Five pages, and page 3 has three usable slots. Chases 32–36, 38 and 40 have no
fader as a result; they still work from the command line and direct selects.

Scanning the whole grid takes 20 seconds:

```python
ok = "Error" not in send(f"Fader {pg} / {f} Sub 21")
```

## What is scriptable

Verified against 3.3.9.25 by reading state back.

```
Fader P / F Sub N                                   map content to a fader
Fader P / F Filter Intensity                        intensity-only filter
Sub N Time <up> Time <Hold|Manual|secs> Time <down> up / dwell / down
Sub N Additive | Sub N Inhibitive                   mode
Sub N Label <text>                                  <= 5 chars to be readable
```

Recording a sub, from `build_fx.py`'s proven recipe:

```
Sneak Time 0            release manual AND running effects
Chan <list> At Full
Chan <list> Effect <fx>     (omit for a plain intensity master)
Record Sub <n>              prompts Please Confirm if the sub exists
Sub <n> Label <text>
```

**`Sneak Time 0` does not release instantly.** A sub recorded immediately after
another that shares channels can capture the previous effect still bleeding
off. It bit sub 9 (pars 1–48) right after sub 6 ran an effect on the same pars;
sub 41, identical content recorded 30 commands later, came out clean. Assert
that anything meant to be a plain master has an empty `/fx/list/`.

## What is not scriptable

**Nothing configures fader buttons or modes.** Checked in the v3.1 manual, the
v3.3 online help and the ETC community:

- **OSC** — `/eos/fader/...` covers levels, paging, load, unload, fire, stop,
  home, min, max, `%`. No configuration methods at all.
- **Macros** — learn mode records *button presses*. The config is a mouse popup,
  so there is nothing to capture. (Tab 36 can assign *a macro to a button*,
  which is the opposite direction.)
- **Softkeys** — Tab 15 offers only `Hold | Execute | Manual | Edit | Offset`.
- **Command line** — `Master Intensity` parses but the echo drops `Intensity`;
  `Solo`, `Freeze`, `Mode Effect`, `Exclude Solo`, `Rate` all error.

So Intensity Master, Effect mode, Solo, Exclude Solo, Freeze and effect rate
ranges are **Tab 36 with a mouse** — or UI automation.

## Driving Tab 36 through accessibility

Eos is Qt and exposes almost nothing, **but the fader tiles and their popup
menus are named buttons**. This works:

```applescript
-- the tile's configurable button
tell application "System Events" to tell process "Eos Family"
  click button 31 of window "Eos : 1"        -- a "Group/Assert" button
end tell
-- then the popup, which is a DIFFERENT window
tell application "System Events" to tell process "Eos Family"
  click button "Freeze" of window 1
end tell
```

Each tile enumerates as:

```
S 2  RNBOW | 1x | (2 unnamed) | Load | Master | Group/Assert | Bump
```

`Load` is locked because every fader is mapped 1x, so the tutorial's "upper
button" is unavailable — the two configurable buttons are **Group/Assert** and
**Bump**.

Traps in that loop:

- **Offsets are not fixed.** A fader showing `Effect Rate(60,800)` enumerates as
  *two* names (`Effect Rate(60` and `800)`), shifting everything after it.
  Search forward from the header for the label you want.
- **`window 1` goes stale.** After the first popup it stops reliably pointing at
  the next one, so later clicks open menus without selecting in them. Re-resolve
  each iteration.
- **Include `Bump` when segmenting a tile.** Omitting it makes the scan run past
  the tile boundary and report the *next* fader's button as a duplicate.
- **Check the last fader on each page first** — three misses in one pass were
  all fader 10, where the tile sits at the edge of the scroll area.
- **Verify before advancing.** Enumerate the popup and abort if the wanted entry
  is absent, rather than clicking a coordinate and hoping. That guard caught a
  mis-click that had opened the fader *config window* instead of a button menu.

Screen coordinates are `screencapture` pixels ÷ 2 on a Retina display. Clicking
by name is far safer than by coordinate — an early coordinate click landed on
the workspace selector and switched the console to an empty workspace.

## Fader times

```
masters   0 / Manual / 0     bump flashes while held
colour    1 / Hold   / 1     stops colours hard-cutting
focus     2 / Hold   / 2     movement rakes slower
intensity 1 / Hold   / 1
```

## Button assignments

```
sub 1        Solo           the strobe suppresses everything else
subs 2-6     Freeze         hold the current colour or position
subs 7-10    Group/Assert   intensity masters, unchanged
subs 41-50   Group/Assert   category masters, unchanged
subs 11-40   Freeze         all effects
```

Sub 8 FRONT carries **Exclude Solo**, so the front wash stays up when the
strobe solos everything else.

## Effects: pick the right type for the job

**A strobe must be an `Absolute` effect, not `StepBased`.**

`Strobe All` (fx 11) is StepBased with **Cascade entry**. Two problems: Cascade
staggers fixtures *into* the effect so the hit never lands together, and step
effects interpolate between their On and Off states, so there is always a fade
however short. It reads as a soft flutter rather than a strobe.

`Int Strobe Fast` (fx 941) is **Absolute** — it writes literal values from a
table, so it snaps between out and full. Sub 1 STROB now runs that.

See [effects-model.md](effects-model.md) for the five types.

## A fader has three configurable layers

Only the first is reachable from the command line, and this trips people up
repeatedly:

| Layer | What it is | Scriptable? |
|---|---|---|
| **Target / ID** | what content the fader holds | **yes** — `Fader P / F Sub N` |
| **Slider mode** | Master, Effect Rate, Effect Size, Rate Master, Master Only, Effect Master, Levels Only | no |
| **Button actions** | Solo, Freeze, Assert, Off/On, Release, Mark NPs, Macro... | no |

### A global effect rate fader

Set any fader's **slider** to **Effect Rate**. Per the manual it "controls the
rate of *any running effects*", so it is a global rate control and the fader
needs no content mapped to it at all. It centres to home — push up or pull down
to ride the whole rig faster or slower.

There is **no command-line path**: `Fader P / F Effect`, `Global Effect`, `Rate`,
`Rate Master` all error. `Mapped To Effect` is recognised but incomplete. Tab 36,
by hand.

Fader 6 CHASE already shows `Effect Rate(60,800)` — the same slider mode scoped
to its own sub rather than global.

## The fixtures have a real shutter

`Chan 1 Shutter 50` is accepted — the pars carry a shutter/strobe parameter. A
hardware shutter strobe is crisper than any intensity effect, because the fixture
does the chopping instead of the console re-sending levels.

Not implemented: it needs the Uking par's shutter ranges (typically something
like 0–7 closed, 8–215 strobe speed, 216+ open), which are not readable from the
profile over OSC. Either read the DMX chart or step the value and watch.
