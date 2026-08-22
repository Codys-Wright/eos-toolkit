# Reference sources

The primary sources for this project. **None of these documents are committed
here** — they are ETC copyright. This file records exactly which document
answered what, and where to get it.

## Documents used

| Document | Where |
|---|---|
| **Eos Family v3.1.0 Operations Manual** (`EosFamily_v3.1.0_UserManual_RevA.pdf`) | [ETC manuals page](https://www.etcconnect.com/Products/Consoles/Eos-Consoles/All-Eos-Downloads/Manuals.aspx) |
| **Eos Family Keyboard Shortcuts** (`EosFamily_KeyboardShortcuts.pdf`) | ships with the app — `~/Documents/ETC/Eos/` on macOS |
| **Eos Family Show Control User Guide, Rev C** | [PDF mirror](https://media.musson.com/mti/docs/e/o/eosfamily_showcontrol_userguide_revc.pdf) |
| **Eos Family Online Help** (v3.3.x, HTML — most current) | [etcconnect.com WebDocs](https://www.etcconnect.com/WebDocs/Controls/EosFamilyOnlineHelp/en/Content/01_Welcome/WELCOME_TO_EOS.htm) |

The Show Control guide is **Rev C (2017, Eos 2.x era)**. Its OSC appendix is
still the best protocol reference, but it predates Eos 3.x — which is why
`augment3d/position` sub-replies aren't in it and caught our parser out.

## Which source answered what

| Topic | Source |
|---|---|
| OSC get/query protocol, list convention, reply schemas | Show Control guide, *Appendix: Advanced OSC* |
| OSC key names (`save_show`, `stepbased`, `bounce`…) | Show Control guide, *Appendix: Eos OSC Keys* |
| Mac hotkeys (**Effect = Alt+E**, Macro = M, Select = Ctrl+Enter) | Keyboard Shortcuts PDF |
| Macro Editor: `[Macro][Macro]`, `{Edit}`, `[Select]` to save | Operations Manual p.405–407 |
| Magic sheets export/import as **.xml** | Operations Manual p.425 |
| Magic sheet objects, targets, arrays, Quick Layout | Operations Manual p.416–427 |
| Scenes: `[Cue] <n> {Attribute} {Scene}` | Online Help, *Cues and Cue Lists > Cue Attributes > Scenes* |
| Augment3d position syntax, `[Thru]`, partial updates | Operations Manual p.459–460, *Entering Fixture Position & Orientation Data* |
| **Set Channel Locations From Magic Sheet** | Operations Manual p.471–472, *Augment3d with Magic Sheets & Pixel Maps* |
| Z is the height axis (floor points share a Z) | Operations Manual p.461, *FPE Points* |
| Patch = `;` | Keyboard Shortcuts PDF |
| Step effect attributes (Bounce/Build/Negative/Random) | Online Help + ETC community |
| Augment3d fixture placement syntax | Operations Manual p.458–459 |
| Renumbering hazards (FX un-stopping, timecode) | [ETC community thread 28557](https://community.etcconnect.com/control_consoles/eos-family-consoles/f/eos-family/28557/renumbering-cues-and-properties-links-fx-intensity-times-change) |

## Reading a manual PDF

```bash
pdftotext -layout "EosFamily_v3.1.0_UserManual_RevA.pdf" man.txt
grep -n -iE "macro editor" man.txt
```

`-layout` matters — without it the tables collapse and the key/command columns
become unreadable.

## What the manuals do NOT contain

Everything in [command-line-traps.md](command-line-traps.md) was found by
experiment, not documentation. The manual does not mention that `Save_Show`
only works as a key, that `Cuelist N Label` is reparsed as `Chan N Label`, that
`Record Sub` over an existing sub silently does nothing, that effect authoring
requires editor focus, or that magic sheet `TARGETTYPE` codes exist at all.


## Version traps

Two of the worst time sinks on this project were both **stale documents**, not
missing ones. Check the version before trusting a page.

- The **Show Control guide is Rev C (2017, Eos 2.x)**. Its OSC appendix is still
  the best protocol reference, but `augment3d` sub-replies postdate it.
- A **v2.7 hotkeys PDF** circulates on mirror sites. It is two major versions
  behind 3.3.9 — do not use it. The Keyboard Shortcuts PDF that ships with the
  installed app is version-matched and already on disk.
- Widely circulated hotkey tables are **Windows-oriented**. On macOS, Alt = Option,
  and a plain `e` is *Recall From*, not Effect.

Both times the answer was already on disk. Search the installed manuals before
searching the web:

```bash
pdftotext -layout ~/Downloads/EosFamily_v3.1.0_UserManual_RevA.pdf - | grep -n -i augment3d
```
