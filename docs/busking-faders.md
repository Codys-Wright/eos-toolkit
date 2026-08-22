# The busking fader system

Five pages of faders for the Norco rig, built by `build_busking_faders.py`.
The design follows the ETC busking tutorial, adapted to a rig with no colour
mixing on the movers and a console with a restricted fader configuration.

## Layout

```
PAGE 1  ESSENTIALS   STROB RNBOW SMOOT OHMOV BMMOV CHASE SPOT FRONT WASH HAZE
PAGE 2  CATEGORIES   WASH SLIMS SPOTS BEAMS BARS HAZE FRONT MID BACK RIG
PAGE 3  (3 slots)    CFWD  ..  SPRKL FIRE
PAGE 4  COLOUR FX    RNBWW RNBWL CFADE CBUMP R-BLU G-MAG C-ORG M-YEL SRGB SRYB
PAGE 5  MOVEMENT     OHCIR OHSQR OHSPI OHTRI BMSCH BMCAN BMSWP MVBAL ISTRB IFADE
```

Page 1 is a working show on its own: four intensity masters to build a base
state, six effects to modulate it. Pages 4 and 5 stack on top — they are
recorded against overlapping channel sets deliberately, so a colour fade under
a chase layers rather than fights.

**Labels are capped at 5 characters** — that is all the fader display shows.

## Sub numbers are fader numbers

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

### This console's fader grid

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
