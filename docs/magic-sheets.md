# Magic sheets

## What OSC gives you

Almost nothing. `/eos/get/ms/<n>` returns **number, UID and label only**. There
is no way to read what is on a sheet, and no command-line grammar for placing
objects — `Magic_Sheet 20 Chan 1`, `... Object Chan 1`, `... Add Chan 1` all
return `Syntax Error`.

What *does* work over OSC:

```
Record Magic_Sheet 20              create an empty sheet
Magic_Sheet 20 Label Test Sheet    label it
Delete Magic_Sheet 20              delete it (confirm)
Magic_Sheet 1                      display sheet 1
Magic_Sheet 1 / 2                  display sheet 1, view 2
```

So the container is scriptable; the canvas is not.

## The real authoring path: XML

> *"Magic Sheets can be exported and imported in .xml format. The export and
> import icons are located at the bottom of the background settings tab."*
> — Eos Family v3.1.0 Operations Manual, p.425

This is the way in. XML is readable and writable, so a script can generate a
complete magic sheet offline and the operator imports it in one action.

**Workflow**

1. In the magic sheet editor, open the **background settings** tab
2. Click the **export** icon, save the `.xml`
3. Generate or edit XML against that schema
4. Click the **import** icon

Export one existing sheet first — the schema is not published, so it has to be
learned from a real file.

## Building by hand, quickly

If you are placing objects yourself, the editor has three features that make it
much faster than dragging one at a time:

- **Quick Layout** — place many instances of a selected object in a row
- **Create Array** — rectangle (rows, columns, spacing) or circle (count, size)
- **Target: Start + Increment** — auto-numbers targets as you place them

The increment is smarter than a simple +1:

```
Start 1.1  Increment 1     ->  1.1, 2.1, 3.1 ...
Start 1.1  Increment 0.1   ->  1.1, 1.2, 1.3 ...
Start 1.1  Increment 1.1   ->  1.1, 2.2, 3.3 ...
```

So a 5x5 direct-select-style grid of 25 group buttons is one array plus one
increment setting, not 25 drags.

Also useful: **Quick Save** sets an undo restore point, and `[Undo] [Enter]`
returns to it. Worth clicking before any large change.

## TARGETTYPE codes

Determined by importing probe sheets and reading the type labels Eos renders.
Five probe rounds; the numbers are an undocumented internal enum, so check
`SHOWFILE_VERSION` (122 here) before trusting them on another release.

```
  0 None          14 Address        36 Pixel Map
  2 Cue           20 Channel        45 Fader
  3 Group         23 User           46 Motor
  4 Macro         24 Show Control   48 Relay
  9 Preset        29 Snapshot       51 Processor
 10 Sub           33 Magic Sheet    54 Video Stream
 13 Effect
```

**Palettes are ONE type with a sub-selector**, not four codes:

```
 TARGETTYPE 6 + TARGETLISTID 1=IP  2=FP  3=CP  4=BP
```

That took five probe sheets. Sweeping 0-87 with both ChannelButton and Button
objects showed IP at 6 and nothing at 5/7/8 — because every probe inherited
`TARGETLISTID="1"` from the template, so each palette test was implicitly asking
for *palette list 1*. One code plus an unvaried parameter, not a gap in the enum.

`TARGETLISTID` also qualifies **cues** — it is the cue list number.

Two further lessons from that hunt:

- **The object you probe with limits what you can discover.** A ChannelButton
  refuses palette targets, so 60 codes swept with the wrong object type
  produced a confident wrong answer.
- **Eos imports any TARGETTYPE without complaint** and re-exports it unchanged.
  A wrong code yields a sheet that imports "successfully" and silently does
  nothing. Generated sheets need visual confirmation the first time.

Not found anywhere in 0-87: Command, Scene, Console Button, Softkey, Zoom,
Selection, Cue-Active, Cue-Pending, Channel-by-Address. For compound actions,
point a button at a **Macro** (type 4).

## Object targets available

None, Address, Beam Palette, Channel, Channel (by Address), Color Palette, Cue,
Cue - Active, and more — so a sheet can trigger essentially any target type the
console has.

Object properties include outline/fill colour, **link to channel intensity**
(outline brightness follows the live DMX level) and **link to target colour**,
font, and type conversion for objects already placed.
