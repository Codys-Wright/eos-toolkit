# Reading show data out of Eos over OSC

Eos exposes a complete read API for show data. It is documented in the
**Eos Family Show Control User Guide**, "Appendix: Advanced OSC". This is a
practical summary plus what we found that the guide does not cover.

## Connect

| Transport | Detail |
|---|---|
| **TCP 3032** | preferred. Always listening; the "OSC TCP Server Ports" field is for *extra* ports |
| Framing | OSC 1.0 = 4-byte big-endian length prefix (default). OSC 1.1 = SLIP |
| UDP | RX/TX ports set in Setup; drops and reorders — avoid for bulk reads |

Enable **OSC RX** and **OSC TX** in *Setup > System > Show Control > OSC*.
On Eos 2.x these did not exist; OSC was gated by `{String RX}`/`{String TX}`.
The **UDP Strings** tab is a different feature in 3.x and is irrelevant to OSC.

## The three-step handshake

```
/eos/get/version                -> /eos/out/get/version  "3.3.9.25"
/eos/get/<type>/count           -> /eos/out/get/<type>/count  <int>
/eos/get/<type>/index/<n>       -> /eos/out/get/<type>/<num>/list/<off>/<total>
```

Types: `patch cuelist cue/<list> group macro sub preset ip fp cp bp curve fx
snap pixmap ms`

Replies carry the target number **in the address**, so they are self-describing
— you never correlate reply to request. Fire everything, sort the mail after.

## The OSC List Convention

A reply too large for one packet splits across several, each tagged
`/list/<offset>/<total>`:

```
/eos/out/get/patch/1/1/list/0/20  = args[0..8]
/eos/out/get/patch/1/1/list/9/20  = args[9..19]
```

Reassemble by offset until you have `total` args. **Field order IS the schema** —
see `SCHEMA` in `eosdump.py`.

## Undocumented in the 2.x guide, present in 3.x

Eos 3.3 sends extra sub-replies the older spec never mentions:

```
/eos/out/get/patch/<ch>/<part>/augment3d/position   x,y,z + rotation
/eos/out/get/patch/<ch>/<part>/augment3d/beam       beam angle, etc.
```

**Parsers must peel *every* trailing non-numeric token**, not just one.
Peeling only one makes `augment3d` look like part of the channel number and
invents phantom channels. That is exactly what bit us: 71 real fixtures came
back as 142 records, half of them empty.

## What you can and cannot read

| Readable | Not readable |
|---|---|
| Labels on every target type | **Parameter VALUES inside a palette** |
| Group channel lists, exactly | Magic sheet contents |
| Which channels a palette covers | Which display/tab is focused |
| Effect metadata: type, entry, exit, duration, scale | Effect internals (steps, tables) |
| Cue times, block, link, mark, follow, fx list | Scene markers (no field in the cue reply) |
| Sub config, mode, times, fx list | |
| Full patch incl. manufacturer/model/address | |

### The side door for values

`get` never returns palette values — but you can **recall and observe**:

```
Group 7 Focus_Palette 1     then read  /eos/out/pantilt
  -> [panMin, panMax, tiltMin, tiltMax, panNow, tiltNow]
```

That turned "I cannot know where your lights point" into a measurement. We used
it to learn the rig's real working envelope before building a focus grid.

Note `/eos/out/color/hs` fires on **manual** colour changes but *not* on palette
recall, so the same trick does not work for colour.

## Live state (implicit output)

33 addresses stream continuously. Useful ones:

```
/eos/out/active/cue/text      "1/109 singing DSL & circle SR 3.0 100%"
/eos/out/pending/cue/text
/eos/out/previous/cue/text
/eos/out/cmd                  current command line (incl. "Please Confirm")
/eos/out/event/state          0=Blind 1=Live
/eos/out/show/name
/eos/out/event/show/saved     file path - the ONLY proof a save happened
/eos/out/softkey/1..12        best available proxy for "what page am I on"
/eos/out/pantilt              [panMin,panMax,tiltMin,tiltMax,pan,tilt]
```

`/eos/subscribe = 1` adds `/eos/out/notify/...` on every show-data change.
