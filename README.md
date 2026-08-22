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
| [Command line traps](docs/command-line-traps.md) | **Start here.** 11 ways Eos accepts input that does not mean what it looks like |
| [OSC protocol](docs/osc-protocol.md) | Reading show data: handshake, list convention, what is and is not readable |
| [File format](docs/file-format.md) | `.esf3d` / `.esf2` anatomy, and why not to build on it |
| [What can be automated](docs/what-can-be-automated.md) | Capability matrix |
| [Authoring effects](docs/authoring-effects.md) | Creating and editing effects over OSC — and the one precondition nobody documents |

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
| `build_chases.py` | **designed FX as looping cue lists** — the workaround for GUI-only effect authoring |
| `build_popstars.py` | a full show: acts as cue blocks, sequenced by links |
| `rename_effects.py` | normalise every effect label |

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
over an existing sub does nothing. None of those produce an error. Every bug
this toolkit has hit was caught by reading back, and none would have been caught
any other way.

## Licence

MIT
