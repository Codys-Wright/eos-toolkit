# Eos command line: traps that cost us hours

Every one of these was found the hard way, by writing something, reading the
state back, and finding it was not what we sent. **Eos accepts a great deal of
input that does not mean what it looks like, and almost never errors.**

The single most important habit: **after every write, read the state back.**
A clean command-line echo means *"I parsed that"*, never *"I did that."*

---

## 1. `Save_Show` is a KEY, not a command

```
/eos/newcmd "Save_Show#"     -> silently swallowed. No error. No file written.
/eos/key/save_show           -> actually saves
```

Verify with the console's own receipt:

```
/eos/out/event/show/saved = "/path/to/Show.esf2"
```

If that message does not arrive within ~15s, **the show was not saved.**
We reported "saved" four times over an hour while nothing reached disk.

The key table in the Show Control guide lists `save_show -> SAVE_SHOW`.
Anything in that table is a key; typing its name does nothing.

## 2. Cue numbers need spaces around the slash

```
Record Cue 2/1      -> "Record Cue 1 2/1 - Error: Syntax Error"
Record Cue 2 / 1    -> works
```

Applies everywhere a list/cue pair appears: `Cue 2 / 110 Label ...`,
`Cue 2 / 190 Link 2 / 200`.

## 3. `Cuelist N Label` is silently reparsed as `Chan N Label`

```
Cuelist 10 Label Zone Sweep   -> becomes "Chan 10 Label", errors,
                                 and Eos auto-names the list after its FIRST CUE
Cue 10 / Label Zone Sweep     -> correct
```

Symptom: cue lists mysteriously named after their opening cue.

## 4. `Effect` will not chain after `At`

```
Group 4 At 100 Effect 927   -> "Error: Syntax Error"
Group 4 At 100              -> ok
Group 4 Effect 927          -> ok
```

Two commands. Same for several other verbs — when a chain fails, split it.

## 5. `Group N At 0` does NOT stop running effects

Zeroing intensity leaves effects running on those channels. The next
`Record` captures them. We built 14 submasters this way and 11 came out with
2-4 effects each instead of one.

```
Sneak Time 0    -> releases all manual control INCLUDING effects
```

Use `Sneak Time 0` as the reset before every record.

## 6. `Record` over an existing target silently does nothing

```
Record Sub 31     (sub 31 already exists)  -> no error, no change
```

Delete first:

```
Delete Sub 31 Thru 44   -> "Please Confirm"
/eos/key/enter          -> confirms
```

Confirmed for submasters. Cues and palettes *do* overwrite, so test per type.

## 7. Destructive commands echo "Please Confirm"

The prompt appears on `/eos/out/cmd`, so it is readable over OSC and can be
answered deliberately rather than blind:

```
Delete Sub 50                -> "... Delete Sub 50  Please Confirm"
/eos/key/enter               -> "... Delete Sub 50 #"
```

Never auto-confirm a prompt you have not read. GUI *dialogs* (file operations)
are a different thing and are NOT visible over OSC.

## 8. `/eos/newcmd` clears; `/eos/cmd` appends

```
/eos/newcmd "Effect 210"   -> line: "Effect 210"
/eos/key/scale             -> line: "Effect 210 Scale "
/eos/newcmd "250"          -> line: "Chan 250"        <-- WIPED IT
/eos/cmd    "250"          -> line: "Effect 210 Scale 250 "
```

Use `newcmd` to start a command, `cmd` to continue one.

## 9. Links must be applied AFTER every target exists

```
Cue 2 / 190 Link 2 / 200    (cue 200 not yet recorded)  -> silently dropped
```

No error; the link reads back as 0. Build all cues, then link in a second pass.

## 10. `-1` is the "unset" sentinel, not a value

Cue times, follow, hang, loop and link all use `-1` for *not independently set*.
Dividing by 1000 for display yields `-0.001s`. Render it as em-dash.

## 11. Effect writes silently fail unless the Effect editor is open

```
Effect 200  [Enter]     (editor closed)  -> "Error: Effect Does Not Exist"
Effect 200  [Enter]     (editor open)    -> "Effect 200 Create Type" + softkeys
```

OSC key presses do not navigate displays, so a script cannot open the editor for
itself. A human presses `[Effect] [Effect]` once; the script does the rest.
Detect focus by watching softkeys:

```
closed -> Address | Query | Snapshot | Highlight | Assert | ...
open   -> Edit | Properties | Icon | Offset
```

See [Authoring effects](authoring-effects.md).

## 12. Stray side effects from invalid commands

`Record Fx 222` reported OK and created **cue 22/222** — a cue in a cue list,
from a command about effects. Always re-count after an experimental command.

## 13. `Select` is a KEY, not a command-line word

The Augment3d write path was recorded as
`[Chan] [1] [Select] [x] [/] [y] [/] [z]`. The brackets mean **keys**, but it
got transcribed into an OSC command-line string, where `Select` arrives as
literal text and Eos rejects it:

```
Chan 44 Select 1 / 2 / 3   -> "Chan 44 Select - Error: Syntax Error"
Chan 44 Select 1           -> "Chan 44 Select - Error: Syntax Error"
Chan 44 Select             -> "Chan 44 Select - Error: Syntax Error"
Chan 44                    -> OK
```

The error text lands immediately after `Select`, which reads like a *coordinate*
problem and sends you off tuning number formats. It is not. On macOS:

```
Select  =  Control + Enter      (System Events)
Patch   =  ;                    (single keystroke, no modifier)
```

`/eos/key/patch` does **not** work — there is no OSC key by that name, so it
falls through to the command line as the word "Patch" and errors. Display
navigation stays keystroke-only.

Confirmed against ETC's `EosFamily_KeyboardShortcuts.pdf`, which was already
cited in [sources.md](sources.md) — the answer was on disk the whole time.

## 14. `.` is Cell and `/` is a list separator — decimals are unrepresentable

Even with the channel correctly selected via the real Select key, coordinates
cannot be typed on the command line. Sending `0.46 / 0.42 / 5.5` parses as:

```
Chan 44 + 0 Cell 46 : Chan 0 Cell 42 : Chan 5 Cell 5
```

`.` is the multicell **Cell** separator and `/` separates list items. The whole
string is read as a *channel selection*, never as coordinates. This is
structural, not a formatting problem — integers fail the same way.

Harmless, as it happens: a selection is not an assignment, and with no `@` no
address was written. Verified — channel 44 stayed at address 646 with position
`[0,0,0, 0,0,0]`. But note how close this sits to `Unpatch`, and re-read the
patch after any experiment in this display.

## 15. The Augment3d verb is `Position` — `Select` is the *hardware* gesture

Traps 13 and 14 described the failure correctly but drew the wrong conclusion.
Coordinates **are** enterable from the command line. The missing token was a
verb:

```
Chan 44 Select   0.15 / 1.35 / 9.08   -> Syntax Error  (Select = a key, not text)
Chan 44          0.15 / 1.35 / 9.08   -> parsed as a channel selection
Chan 44 Position 0.15 / 1.35 / 9.08   -> WORKS
```

The manual writes the gesture as `[Chan] [1] [Select] [5] [/] [5] [/] [5]`
because it documents a **console with a keypad**, where `[Select]` opens the
coordinate-entry mode. Over OSC you want the keyword `Position` instead. Both
reach the same parser; only one is reachable from a script.

`/` was never the problem. It arrives fine over OSC every time — it only ever
errored for lack of a verb in front of it. Note the reverse though:

**Synthesised `/` keystrokes are silently dropped.** Typing `//9.08` via System
Events against `Chan 44` produced `Chan 449 Cell 08` — the slashes vanished and
the digits appended to the channel number. Neither the main-row slash nor the
numeric keypad slash (`key code 75`) delivers the token. Send coordinates over
OSC, not as keystrokes.

### Partial updates and ranges

Empty coordinates mean "no change" and auto-complete to `*`:

```
Chan 43 Position / / 9.08   -> echoed as "Position * / * / 9.08"
```

So Z can be rewritten without disturbing X and Y. Ranges work, and a single
value applies uniformly (two values would interpolate across the range):

```
Chan 1 Thru 18 + 20 Thru 48 Position / / 9.08
```

Verified on 67 fixtures at once: no X/Y moved, no address changed.

### Which display

`Position` works from **Patch** (prompt `Patch Channel:`). It does *not* work
from the Augment3d display (`BLIND: A3D Edit`) — there, `Control+Enter` does
nothing at all and digits fall back to channel selection. The two are easy to
confuse: A3D Edit is the rendered 3D view, the Augment3d **tab in Patch** is a
channel list with XYZ columns.

## 16. Three ways a write silently does nothing

Over one session of placing 70 fixtures, three *distinct* silent failures
turned up. Only read-back caught all three.

**Wrong display.** `Position` is valid in Patch and nowhere else. Ninety
commands sent from `BLIND: Magic Sheet 2` all errored; the script wasn't
reading echoes, so it reported success. Check `/eos/out/cmd` for `Error` after
every command:

```python
conn.send("/eos/newcmd", cmd + "#"); time.sleep(0.13)
echo = next((a[0] for addr,a in conn.recv() if addr=="/eos/out/cmd" and a), "")
if "Error" in echo: ...
```

**Dropped keystrokes.** Synthesised `/` never arrives. Typing `//9.08` against
`Chan 44` produced `Chan 449 Cell 08` — slashes vanished, digits appended to the
channel. Neither the main-row slash nor the numeric keypad (`key code 75`)
works. Coordinates go over OSC, never as keystrokes.

**Accepted but not applied.** Two of 140 commands echoed cleanly and did not
take effect. Echo-checking is necessary but *not sufficient*. Re-read the value:

```
/eos/get/patch/index/<i>  ->  /eos/out/get/patch/<ch>/<part>/augment3d/position
```

Note `index` is the **position in the patch list**, not the channel number —
channel 80 is index 52, not 79. Build the map from a patch dump once; indices
are stable when positions change.

## 17. Softkey indices are neither 1-based nor contiguous

Patch reports `{4: Query, 5: Fixtures, 6: Properties}`; the Fixture Editor
reports `{3: Lamp Controls, 4: Physical Data, 5: Patch, 6: Fixture Info}`. The
status helper compacts empties, so its list order is not the index.

Read `/eos/out/softkey/N` raw and match on the label before pressing. Guessing
an index in Patch could hit `Unpatch`.

## 18. Submaster and fader properties: what is reachable

Probed against 3.3.9.25. Verified by reading `/eos/get/sub/<n>` back.

**Works, and confirmed by read-back:**

```
Sub N Time <up> Time <Hold|Manual|secs> Time <down>     up / dwell / down
Sub N Additive  |  Sub N Inhibitive                     mode
```

`Time Manual` is the "flash while the bump is held" setting.
`Sub N Time` alone resets up/down but **leaves dwell unchanged** — set it
explicitly.

**Parses, but not verifiable over OSC** (fader config is not exposed —
`/eos/get/fader/...` returns nothing):

```
Fader N Filter Intensity      Sub N Priority <n>      Sub N Independent
```

**No text path at all** — these are Tab 36, mouse only:

- Intensity Master (`Master Intensity` parses but the echo drops `Intensity`)
- Effect mode, Solo, Exclude Solo, Freeze, effect rate ranges, HTP/LTP

The echo is the diagnostic. `Fader 1 Filter Intensity` echoes back *with*
`Intensity`; `Fader 1 Master Intensity` echoes as `Master` alone — same
"accepted" status, but one kept its argument and the other ate it.

Also: `Sub N Filter Intensity` parses and changes **nothing** in the read-back.
That is the *record* filter, not the Tab 36 fader filter. Accepted is not
applied.

## 19. Augment3d fixture models

`Fixture Model` decides what a fixture looks like in Augment3d. There is **no
command-line syntax** — `Chan N Model`, `Symbol`, `Augment3d Model` all error.

Reach it at **Patch → {Fixtures} → {Physical Data}**. It is set **per fixture
type**, not per channel, so one change covers every channel patched to that
type.

`Chan N Beam Angle <n>` *does* work from the command line.

Same page: **Hang to Focus Offset X/Y/Z**, the offset from the base to the
pan/tilt pivot, used when converting an XYZ beam target to pan/tilt. Left at
zero, aimed positions on movers are slightly off.

## 20. `Fader <n>` wraps instead of erroring

Fader pages hold **10** faders. Addressing a fader beyond that does not error —
it silently relocates:

```
Fader 1 / 11 Sub 41   ->  "Fader 1 / 11 Mapped To Sub 41"   ... lands on page 2 fader 1
Fader 20 Sub 20       ->  "Fader 1 / 20 Mapped To Sub 20"   ... lands on page 2 fader 10
```

That overwrote an entire page of content that had just been mapped, and the
echo confirmed success both times. Always address faders as
`Fader <page> / <fader>` and keep `<fader>` in 1–10.

Capacity is also not uniform, so probe before designing a layout — on this
console page 3 has only faders 1, 9 and 10, and pages 6+ do not exist. See
[The busking fader system](busking-faders.md).

## 21. `At <level>` and `Color_Palette` in one command: the palette is dropped

The single worst silent failure found so far.

```
Chan 1 Thru 48 At Full          then  Chan 1 Thru 48 Color_Palette 6   -> BLUE
Chan 1 Thru 48 At Full Color_Palette 6                                 -> no colour
```

Measured off the Augment3d render: split gives `R49 G57 B165`, combined gives
`R131 G125 B93`. The level applies, the palette is discarded, and the echo
reports the whole string back as though it worked:

```
LIVE: Cue 110 : Chan 12 @ 80 Color Palette 6 #
```

This built 18 song cues that all recorded the same colour before anyone noticed.
**Always send level and palette as separate commands.** The same split applies to
`Focus_Palette`.

## 22. `Record Cue 1/110` fails; `Record Cue 1 / 110` works

The list/cue separator needs spaces, exactly like the fader syntax.

```
Record Cue 1/110 Label X    ->  "Record Cue 100 1/110 - Error: Syntax Error"
Record Cue 1 / 110 Label X  ->  Please Confirm            (correct)
Record Cue 110 Label X      ->  Please Confirm            (implicit list 1)
```

The error is stranger than a plain rejection — the *active* cue number gets
spliced into the echo, so it reads as if a cue "100" were part of the command.

## 23. Cue notes

`Notes`, not `Note`:

```
Cue 1 / 110 Note  Cool open   ->  Syntax Error
Cue 1 / 110 Notes Cool open   ->  works
```

Notes display in a bar at the bottom of the PSD and, with *Display Pending Cue
Notes* enabled, for the pending cue too — so they are readable during a show,
not just in the editor.

## 24. Screenshots capture the frontmost app; accessibility clicks do not care

`tell process "Eos Family" to click button N of window 1` reaches Eos **even
when another application is in front**. `screencapture` does not — it captures
whatever is actually on top.

That combination produces very confusing debugging: the click lands correctly,
the screenshot shows a different application, and the automation appears to have
failed when it worked. Bring Eos frontmost *before screenshotting*, and check:

```applescript
tell application "System Events" to get name of first process whose frontmost is true
```

Related: a coordinate click (`click at {x, y}`) is aimed at the screen, so it
*does* need Eos frontmost, and an early one landed on the workspace selector and
switched the console to an empty workspace.
