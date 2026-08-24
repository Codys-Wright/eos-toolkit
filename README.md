# eos-toolkit

Read, drive and script an **ETC Eos** lighting console over OSC — plus the
hard-won documentation for how Eos actually behaves.

Python 3, standard library only. Nothing to install.

Built and verified against **Eos 3.3.9.25** (Nomad).

---

## Why this exists

Eos show files are a closed binary format and there is no open-source parser.
But Eos exposes a complete OSC API to the *running application*, which ETC
documents and supports. This toolkit uses that.

Along the way we hit a lot of behaviour that is undocumented, silently wrong, or
both. That is written down in [`docs/`](docs/) so nobody has to rediscover it.

## The one thing to know about effects

Everything in Eos is scriptable over OSC **except display navigation**.
`/eos/key/effect` reaches the command line but never moves the UI.

That matters for exactly one workflow: **effects**. Creating or editing an
effect requires the Effect editor to have focus. So:

```
1. Something must press [Effect] [Effect] to give the editor focus
2. A script then creates, types, builds steps, assigns
   channels and sets properties, all over OSC
```

On **macOS** step 1 can be automated too — `eos_focus.py` sends the gesture via
System Events, so no human is needed. It requires the Accessibility permission,
and note that the Mac hotkey is **Option+E**, not the Ctrl+E published in the
Windows hotkey tables.

With the editor closed, every effect write fails with
`Error: Effect Does Not Exist` — no other symptom. This single precondition is
undocumented by ETC and is the difference between "effects are impossible to
automate" and "effects are fully scriptable".

See [Authoring effects](docs/authoring-effects.md).

## Documentation

| | |
|---|---|
| [Command line traps](docs/command-line-traps.md) | **Start here.** 39 ways Eos accepts input that does not mean what it looks like |
| [OSC protocol](docs/osc-protocol.md) | Reading show data: handshake, list convention, what is and is not readable |
| [File format](docs/file-format.md) | `.esf3d` / `.esf2` anatomy, and why not to build on it |
| [What can be automated](docs/what-can-be-automated.md) | Capability matrix |
| [Authoring effects](docs/authoring-effects.md) | Creating and editing effects over OSC — and the one precondition nobody documents |
| [Magic sheets](docs/magic-sheets.md) | Why OSC can't touch them, and the XML import/export path that can |
| [Authoring macros](docs/authoring-macros.md) | Learn mode doesn't work; the OSC + synthesised-keystroke recipe that does |
| [XYZ focus](docs/xyz-focus.md) | Aiming movers at room coordinates instead of angles — the OSC-only syntax, the metres rule, and silent clamping |
| [Effects model](docs/effects-model.md) | How the effects engine actually works — types, attributes, and the two-level Rate/Scale trap |
| [Building a show](docs/building-a-show.md) | Recipes and traps for generating cues, groups, palettes, presets and subs at scale |
| [The Norco location](docs/norco-location.md) | The venue: room dimensions, the Augment3d scene, and where all 70 fixtures live |
| [The Norco rig, as it actually is](docs/norco-rig-facts.md) | Per-fixture control values, real DMX addressing, the fader map, and the house style — everything established against the venue console |
| [The portable FX library](docs/fx-library.md) | **The design that travels between rigs** — the canonical effect set, the blocks-of-eight fader model for the X-Touch, and the recording rules |
| [The busking fader system](docs/busking-faders.md) | Five fader pages, the `Fader P / F Sub N` mapping syntax, and the one thing no API can set |
| [The show cue list](docs/show-cues.md) | 18 song looks, group colour identities, and cue notes |

## Tools

### `eosdump.py` — snapshot a show

```bash
python3 eosdump.py                 # Nomad on this machine
python3 eosdump.py --host 10.101.90.101
```

Writes `show.json` (everything, structured) and `show.md` (readable digest:
patch, cue lists, groups, subs, palettes, effects, macros).

### `eos_mcp.py` — MCP server

Lets an AI assistant read and drive the console. Three safety tiers, fixed at
launch, no runtime escalation:

| Flags | Tools | Can change anything? |
|---|---|---|
| *(none)* | status, show data, ping | no |
| `--allow-control` | + cmd, key, at | yes — moves lights, runs cues |
| `--allow-control --allow-destructive` | + save | yes — Record/Update/Delete |

```bash
claude mcp add eos -- python3 /path/to/eos_mcp.py --allow-control
```

### Show builders

Each is idempotent and re-runnable: edit the data at the top, re-run, console
matches. All verify by reading state back, and all save via the key that works.

| Script | Builds |
|---|---|
| `build_colors.py` | colour palette library, 5x5 pages incl. blackbody colour temperature |
| `build_groups.py` | group library laid out as direct-select pages |
| `build_fx.py` | FX submaster bank (effect + group + rate/scale overrides) |
| `build_presets.py` | preset library — complete recallable looks |
| `build_focus_intensity.py` | focus grids inside the rig's measured envelope, + intensity balance page |
| `build_xyz_focus.py` | focus palettes as Augment3d **XYZ coordinates** — convergence points plus per-fixture spreads (straight, crossed, fanned) |
| `build_chases.py` | **designed FX as looping cue lists** — the workaround for GUI-only effect authoring |
| `build_popstars.py` | a full show: acts as cue blocks, sequenced by links. **Writes the same cue numbers as `build_song_looks.py`** — run it first, then re-run the looks |
| `rename_effects.py` | normalise every effect label |
| `build_macros.py` | one-press FX macros — group + effect in a single button |
| `build_fx_presets.py` | FX submasters pairing each effect with its group |
| `move_effects.py` | renumber a block of effects, verifying each before deleting |
| `ms_gen.py` / `build_magic_sheets.py` | generate magic sheets as importable XML |

### Venue and rig

| Script | Builds |
|---|---|
| `a3d_room.py` | the whole Augment3d room from two numbers — stage width and depth in feet. Edits `working.a3d` in an extracted show; see [The Norco location](docs/norco-location.md) |
| `build_rig_positions.py` | positions and aims all 70 fixtures over OSC, then verifies every one by read-back |
| `build_busking_faders.py` | five pages of busking faders — subs, contents, labels and times |
| `build_song_looks.py` | a full stage look per song cue, with vibe notes — edit the DESIGN table and re-run |
| `verify_looks.py` | proves each of the 50 complete looks holds its designed colour on every zone, plus the right mover position |
| `verify_presets.py` | recalls each mover preset and reads pan/tilt back — the only way to catch a preset that stored a level and dropped its focus palette |
| `build_show.py` | the show's cue list from the run sheet — acts, videos, links |
| `build_song_sections.py` | section cues inside each song, timed from the song's BPM |
| `build_all.py` | builds every song in order — **pausable and resumable** |
| `build_face_light.py` | the white bank: cold-white faders that decide who the audience can see |
| `verify_show.py` | checks every cue's label, link and block flag against the run sheet |
| `verify_presets.py` | recalls each mover preset and reads pan/tilt back |
| `verify_looks.py` | proves each complete look holds its colour on every zone |
| `verify_faders.py` | reads the OSC fader bank and compares it to the builder's table |
| `check_remote.py` | compares a networked console against this machine, section by section |
| `gobo_walk.py` | puts four gobo slots on four movers at once so they can be named |
| `test_effects.py` | runs every effect and reports which are **hollow** — a correct label with an empty step table reads as healthy over OSC |
| `verify_song_looks.py` | proves every song cue holds its designed colour — clears the stage, learns reference hues from the console, samples one zone at a time |

## Tests

No console required — they stand up a fake Eos that speaks the documented
protocol, including deliberately split replies.

```bash
python3 test_fake_eos.py    # dump path
python3 test_mcp.py         # MCP protocol + safety gates
```

## The one rule

**After every write, read the state back.**

Eos rarely errors on input it does not understand. `Save_Show` typed on the
command line vanishes. `Cuelist N Label` becomes `Chan N Label`. `Record Sub`
over an existing sub does nothing. `Group 10 Effect` stops no effects while
`Chan 1 Thru 101 Effect` stops them all. None of those produce an error. Every
bug this toolkit has hit was caught by reading back, and none would have been
caught any other way.

## The other rule

**Clear the stage before you record.**

`Record` stores every parameter that is not at its default — so a running cue,
a live effect and yesterday's manual data are all *inputs* to it. Read-back
cannot save you here: the target records successfully and reads back as
perfectly valid, it just contains the wrong values.

```
Go_To_Cue Out              release the cue list
Chan 1 Thru 101 Effect     stop effects - the Chan form, never the Group form
Group 10 Sneak Time 0      clear manual data - "Sneak Time 0" alone is a no-op
```

Those three lines are the preamble in every builder that records. See traps
25, 26 and 29.

## Licence

MIT

