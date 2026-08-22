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
