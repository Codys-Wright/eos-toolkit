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

## 20. Fader numbers are absolute; a "page" is only a window

```
Fader 1 / 11 Sub 41   ->  "Fader 1 / 11 Mapped To Sub 41"
```

At 10 faders per page that landed on what the console was *showing* as page 2
fader 1, and it overwrote a page of content that had just been mapped. The echo
confirmed success both times.

**It did not wrap or relocate.** Fader numbering is one continuous list and a
page is a window of N onto it. The manual: *"Fader banks share fader mapping
with Eos, but since an OSC Fader Bank can have any number of faders per page,
the paging will be different."* So one fader has several addresses:

```
console at 10/page   fader 11  =  page 2, fader 1
console at 20/page   fader 11  =  page 1, fader 11
OSC bank config/8    fader 11  =  page 2, fader 3
```

All three are fader 11. Change the console's faders-per-page and every
`Fader <page> / <slot>` command in your scripts resolves somewhere new, while
the absolute fader it should have hit stays where it was.

**Re-check every `page / slot` pair after changing the page size**, and prefer
reasoning in absolute fader numbers. Going past the page size is still not an
error — it just resolves further down the one list.

## 21. `At <level>` and ANY palette in one command: the palette is dropped

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


### It is not just colour

This applies to **every** palette type, and the focus case is the one that hurt.
Every mover line in `build_presets.py` was written as:

```
Group 7 At 100 Focus_Palette 3        <- level applies, focus is DROPPED
Group 7 At 100                        <- split, and both land
Group 7 Focus_Palette 3
```

Proved by read-back: combined gave chan 80 pan/tilt `(0.0, 0.0)`, split gave
`(-29.7, -69.6)`. Every one of 100 presets recorded a mover intensity and no
mover position. Nothing errored, and the presets themselves read back as valid
and well formed - the missing data is invisible unless you recall the preset
and read pan/tilt off the fixture.

The durable fix is to split at the point of sending rather than at each call
site, so a later edit cannot reintroduce it:

```python
_AT_PAL = re.compile(r"^(?P<sel>.+?) At (?P<lvl>\S+) "
                     r"(?P<pal>(?:Color|Focus|Beam|Intensity)_Palette .*)$")
```

## 31. A preset does not follow the palette it was recorded from

Change a focus palette, and presets recorded against it keep the OLD position
until they are re-recorded. They store the resolved values, not a live
reference - so a palette edit silently splits the library in two: the palette
says one thing, every preset built on it says another.

Observed directly: FP 2 was clamping the overhead movers, so presets 29 and 30
recorded the clamped position. Fixing FP 2 and re-reading those presets still
gave the clamped values.

**Any palette change means re-running the preset builder behind it.** The
order is always:

```
build_xyz_focus.py     palettes first
build_presets.py       then everything recorded against them
verify_presets.py      then prove it
```

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

## 25. `Sneak Time 0` clears nothing

It reads like "clear the stage instantly". It is not a clear at all — `Sneak`
here takes `Time` as its argument, so the whole command just sets a *time*. It
parses, it echoes clean, and the stage is exactly as it was.

```
Sneak Time 0            -> sets a time. Clears nothing.
Group 10 Sneak Time 0   -> actually sneaks group 10 back to background
```

The no-op version was the reset line in **seven** builders in this repo. Every
palette, preset, sub and cue they recorded inherited whatever happened to be on
stage at the time.

## 26. `Record` captures the stage, including the running cue

From the manual (p.239): `Record` stores the relevant parameter data "for all
channels that are **not currently at their default value**". A live cue puts
channels at non-default values, so a cue is an *input* to every record.

The symptom is silent and delayed: presets recorded during a pink song cue
recall pink, no matter what colour their own commands set, for every parameter
the script did not explicitly write.

Two defences, and the second is not optional:

```
Go_To_Cue Out                # release the list - Record Only sees background
Group 10 Sneak Time 0        # clear manual data (NOT "Sneak Time 0", trap 25)
```

**Read-back does not catch this.** The record succeeds and the target reads
back as a valid, well-formed preset. It just contains the wrong values.
Verification proves a write landed; it cannot prove the input was clean.

### `Record Only` for colour-free targets

`Record Only` stores **only manual parameter data** (p.240). Set intensity and
focus, never touch colour, and colour is simply absent from the target — which
is what makes a preset droppable onto any song cue without fighting its colour.

```
Group 10 Record_Only Preset 5     # underscore in; echoes as "Record Only"
```

**`Record Only` merges into an existing target.** The manual is explicit: "the
data will be added to that palette. The original palette will not be completely
overwritten." So a re-runnable builder *must* `Delete` first, or every run
accumulates onto the last one.

## 27. `Go_To_Cue Out Time 0` is a syntax error — and Eos adds a word

```
Go_To_Cue Out           -> fine
Go_To_Cue Out Time 0    -> "Go To Cue Out Time 0:00 Preset - Error: Syntax Error"
```

Note the `Preset` that Eos appended on its own. Same family as trap 4: a
rejected command is not always rejected *cleanly*, and the echo can contain
tokens nobody typed.

## 28. Group numbers live in two forms, and a rename catches only one

Renumbering the group library means editing two different things:

```python
"Group 3 At 85 Color_Palette 21"      # a number inside a command STRING
(15, "Drums Feature", 1, [...])       # a bare int - the record SCOPE
```

A regex over `Group (\d+)` finds the first and silently misses the second.
Twenty-six presets kept `scope = 1` through a renumber; group 1 had gone from
"Rig All" to "Washers", so every one of them recorded the washers only and
dropped all mover data. Nothing errored.

If you renumber groups, grep for bare scope ints too, and re-read anything that
takes a group as a *parameter* rather than as text.

## 29. The effect stop works on channels and silently fails on groups

`<selection> Effect [Enter]` with no effect number is Eos's stop-all-effects.
It only works if the selection is a **channel range**:

```
Chan 1 Thru 101 Effect     -> stops every running effect
Group 10 Effect            -> accepted, echoes clean, stops NOTHING
```

Both echo identically. Neither errors. Proven by recording a probe sub with no
effect of its own after each, and reading the `fx` list back:

```
after "Group 10 Effect"        sub 200  fx=[913, 936]     still running
after "Chan 1 Thru 101 Effect" sub 202  fx=[]             clean
```

### Why this one matters more than most

**Effects are stage state, and a sneak does not touch them.** `Group 10 Sneak
Time 0` returns channels to background and leaves every effect running, so any
`Record` that follows captures them. Recording ten FX submasters in a row with
a group-form stop between each gives you subs that accumulate: sub 1 gets its
own effect, sub 2 gets its own plus sub 1's, and the plain intensity masters
recorded afterwards carry all of them.

It also silently broke the FX macro bank. Macros 101-137 are built to stop the
running effect before starting their own, which is what makes them behave as
radio buttons instead of stacking. They were built with the group form:

```python
STOP = ["group", "1", "effect", "enter"]      # never stopped anything
STOP = ["chan", "1", "thru", "1", "0", "1", "effect", "enter"]   # works
```

Note the keystroke form — a macro stores digits as separate key presses, so
this is a third place a group or channel number hides from a text search. See
trap 28.

## 30. `Macro <n>` on the command line does not fire the macro

```
/eos/newcmd "Macro 140#"          -> echoes "Macro 140 #". Nothing runs.
/eos/key/macro + 1 + 4 + 0 + enter -> the macro executes
```

The command line accepts the text and does nothing with it — no error, no
execution. Firing needs the **[Macro] key**, the same way `Save_Show` only
works as a key (trap 1).

This cost a wrong diagnosis: macro 140 was fired the command-line way, the
effects it should have stopped were still running, and the macro bank was
declared broken. It was fine. **When a target does not seem to work, check that
you actually triggered it before concluding anything about its content.**

### A bare leading digit auto-completes to `Chan` on playback

A macro whose stored body starts with a number executes as a channel selection:

```
stored body:  1 Thru 1 0 1 Effect  \r
executes as:  Chan 1 Thru 101 Effect
```

So macro bodies need no `Chan` keystroke — which is just as well, because
`chan` is not an Eos hotkey. Typing it as letters inside the Macro Editor
produces `Copy_To Rem_Dim @ Sneak`, since C, H, A and N are each their own
hotkey there. Every macro in a 38-macro build came out that way, and the build
reported 0 errors because it printed the bodies without comparing them.

## 32. Strobe Mode differs per fixture type, and is invisible over OSC

```
Riukoe overheads  (80-83)   Strobe Mode 63     open
Betopper beams    (85-88)   Strobe Mode 25     open
```

Send 25 to the Riukoe and it **closes the shutter** - the fixture goes dark.
Same command, same parameter name, opposite result, no error either way.

Worse: **`Strobe Mode` is not published over OSC at all.** The console exposes
12-13 parameters per fixture through `/eos/out/active/wheel/<n>` and this is
not one of them, though it parses as a command. So it cannot be read back and
cannot be verified by any tool here - confirm by eye, then trust.

Every cue in the show strobed for hours because the parameter was simply never
set, and the profile's home value happens to be a strobe. **An unset parameter
is not neutral - it is whatever the profile says.**

The real fix is not to set it in every cue but to **Park** it (trap 33).

## 33. `Park` goes at the END of the command

```
Park Chan 85 Thru 88 Strobe_Mode 25    -> Error: Syntax Error
Chan 85 Thru 88 Strobe_Mode 25 Park    -> parses
```

A parked parameter holds regardless of cues, subs, presets or manual data,
which makes it the right tool for a value that must never vary. Parking the
mover shutters fixed globally what setting them per-cue only patched.

## 34. An inhibitive sub defaults to ZERO, and zero means blackout

An inhibitive submaster caps the level of its channels no matter where the
light comes from - the only thing that can override an additive fader. It is
therefore the right tool for a blackout master.

It is also **inverted, and it defaults to the wrong end**:

```
sub at FULL   no inhibition, everything normal
sub at ZERO   everything it contains is dead
```

Record one and it sits at zero, silently killing the entire rig while the
cues, faders and command line all report perfect health. This happened
minutes before a show. **Park it at full the moment you create it.**

## 35. Effect Rate and Scale only apply to a RUNNING effect

```
Effect 903 Rate 40      (stopped)  -> Error: Effect Not Running
Group 7 Effect 903                            start it first
Effect 903 Rate 40                            now it takes
```

There is no per-cue form - `Group 7 Effect 903 Rate 40` is a syntax error.
So the order when building a cue is **start the effect, adjust it, then
Record**, and the cue captures the override. Get the order wrong and every
cue gets the effect at its stored speed.

This is what makes one effect usable in several places: the same Fig 8 at
rate 35 is a drift in a verse and at rate 85 is a whip in the final chorus.

## 36. `Update` over a range is how you fix the whole show at once

```
Update Cue 1 / 1 Thru 4999          every cue in list 1
Update Preset 1 Thru 100            needs a channel SELECTION first
```

`Update` writes only the parameters that are **manually set right now** into
every target in the range. Putting one value on stage and updating the range
changed one thing across 42 cues and left everything else untouched - far
better than rebuilding.

The danger is the precondition: **whatever is manual when you press Update
gets baked into every cue in the range.** Clear the stage twice before using
it. And `Update Preset` failed repeatedly with "Channel List is Empty" even
with channels selected - the cue form works, the preset form was never solved.

## 37. Parse-checking without executing tells you nothing about targets

Sending a command with no `#` terminator checks that it is *well formed*. It
does **not** check that the target exists or that the slot is real.

The fader grid in this repo was mapped that way and was wrong three times over.
`Fader 3 / 18 Sub 41` parsed happily and failed on execution. The real usable
set on this console is:

```
faders 1-17, 21-30 (cue lists), 33-37       usable
faders 18-20, 31-32, 38-40                  not
```

Parse-checking is still useful for *syntax* discovery - it is how the XYZ,
Park and Strobe Mode forms were found without moving a light. Just never
conclude a target exists from it.

## 38. Cues track - only send what changes

A cue builder that zeroes the rig and restates every parameter produces ~30
commands per cue and cues that are impossible to edit. Eos cues **track**:
anything not changed carries forward.

Sending only the difference from the previous cue roughly halves the build
time and, more importantly, makes each cue contain **the move it makes**
rather than a snapshot of the whole rig.

Effects are the exception - they do not track. Stop them explicitly
(`Chan 1 Thru 101 Effect`) whenever either cue involves one.

## 39. `Macro <n>` on the command line does not fire the macro

Covered at trap 30, repeated here because it cost a wrong diagnosis: firing
needs the **[Macro] key**, and a macro fired the command-line way does
nothing at all while looking like it worked.
