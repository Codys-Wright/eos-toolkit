# The `.esf3d` / `.esf2` show file

## Container

Both are **ZIP archives**. Rename to `.zip` and unzip.

```
version.json     86 B     plain JSON: format GUID + version, e.g. "3.3.9.25"
showdat.dat      ~3 MB    the show itself - proprietary binary
showlog.log      ~25 KB   binary command/event log
working.a3d      ~1 KB    Augment3d scene - ITSELF a nested ZIP of JSON
```

`.esf3d` carries `working.a3d`; `.esf2` is the same file without it. Saving from
a show with no Augment3d data yields `.esf2`.

`working.a3d` unzips to `Scene/Scene.json` and `Scene/Primitive.json` — fully
readable geometry with quaternions, euler angles and ARGB hex colours. That
layer can be read *and* edited safely.

## `showdat.dat`

Hand-rolled tag-length-value stream. 120-byte header (`78 00 00 00`), then
records. Strings are **UTF-16LE**, length-prefixed. Floats are IEEE-754.

Extracting strings recovers a surprising amount:

```python
import re
d = open('showdat.dat','rb').read()
strings = [m.decode('utf-16-le')
           for m in re.findall(rb'(?:[\x20-\x7e]\x00){3,}', d)]
```

That yields the patch (manufacturer, model, mode notes), all target labels,
gobo/colour wheel slot names, and console profile.

## What you CANNOT get from the file

**Parameter values are not recoverable next to their labels.** We tested this
with perfect ground truth — we had just written 150 colour palettes with known
RGB — and searched +/-4KB around each label for IEEE floats and for integers at
percent, 8-bit, 16-bit and per-mille scaling. Nothing.

Eos stores parameter data in a separate table keyed by UID, away from the label.
Recovering it means reverse-engineering the record grammar.

**Do not build tooling on this file.** Use OSC for live data, or export CSV /
USITT ASCII from the Browser for values.

## Related open source

There is **no** open-source `.esf3d` parser. What exists:

- [ETCLabs/EosSyncLib](https://github.com/ETCLabs/EosSyncLib) — C++, MIT, live show data over OSC
- [claudeheintz/lxascii](https://github.com/claudeheintz/lxascii) — Java USITT ASCII parser
- [mikacousin/olc](https://github.com/mikacousin/olc) — Python, reads ASCII show files
- [open-stage/python-mvr](https://github.com/open-stage/python-mvr), `pygdtf` — MVR/GDTF

The ecosystem routed *around* the format: everyone talks to the running
application over OSC, which ETC documents and supports.
