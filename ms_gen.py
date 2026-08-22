#!/usr/bin/env python3
"""
ms_gen - generate Eos magic sheets as .xml.

OSC cannot place magic sheet objects and cannot read a sheet's contents. But
Eos exports and imports magic sheets as XML (Operations Manual p.425), so a
sheet can be authored offline and imported in one action.

The schema is not published, so this works by CLONING a real exported item and
overriding position, target and text. That guarantees valid structure - every
attribute we do not understand is carried over untouched.

    <MAGICSHEET SHOWFILE_VERSION="122">
      <VIEW>
        <VIEWPORT POSX POSY WIDTH HEIGHT SCALE/>
        <BACKGROUND STARTCOLOR MODE/>
      </VIEW>
      <ETCGRAPHICSSCENE>
        <ITEMLIST>
          <ITEM KEY="ChannelButton" POSX POSY ROT>
            <ITEMDATA>
              <RECT X Y W H/> <PEN .../> <BRUSH COLOR/>
              <MAGICSHEET CMD ACCEPTSUSERINPUT PLACEMENT ...>
                <TARGET TARGETTYPE TARGETID .../>
                <LINKS PENLINK BRUSHLINK/>
                <TEXT STR FONTSIZE COLOR .../>
                <FIELDS><FIELD .../></FIELDS>

Object KEYs seen in the wild: ChannelButton, Button, Square, Fader, Symbol,
Truss, Pipe, Triangle, Pentagon.

TARGETTYPE codes, confirmed by importing a probe sheet and reading the type
labels Eos renders on each button:

     0  None        14  Address       36  Pixel Map
     2  Cue         20  Channel       45  Fader
     3  Group       23  User          46  Motor
     4  Macro       24  Show Control  48  Relay
     9  Preset      29  Snapshot      51  Processor
    10  Sub         33  Magic Sheet   54  Video Stream
    13  Effect

PALETTES are one type with a sub-selector, not four separate codes:

     TARGETTYPE 6 + TARGETLISTID 1=IP  2=FP  3=CP  4=BP

That took five probe sheets to find. Probing codes 0-87 with both ChannelButton
and Button objects showed IP at 6 and nothing at 5/7/8, because every probe
inherited TARGETLISTID="1" from the template - so every palette test was
implicitly asking for "palette list 1". One code and an unvaried parameter, not
a gap in the enum.

TARGETLISTID also qualifies CUES (it is the cue list number).

NOT FOUND anywhere in 0-87: Command, Scene, Console Button, Softkey, Zoom,
Selection, Cue-Active, Cue-Pending, Channel-by-Address. For compound actions,
point a button at a MACRO (type 4) instead.

NOTE: Eos imports ANY targettype without complaint and re-exports it unchanged,
so a wrong code produces a sheet that imports "successfully" and does nothing.
Generated sheets need visual confirmation the first time.
"""
import argparse
import copy
import xml.etree.ElementTree as ET

# Confirmed by importing a probe sheet and reading the rendered type labels.
TARGETTYPE = {
    "none":      0,
    "cue":       2,
    "group":     3,
    "macro":     4,
    "preset":    9,
    "sub":      10,
    "effect":   13,
    "address":  14,
    "channel":  20,
    "user":     23,
    "showcontrol": 24,
    "snapshot": 29,
    "magicsheet": 33,
    "pixelmap":   36,
    "fader":      45,
    "motor":      46,
    "relay":      48,
    "processor":  51,
    "videostream": 54,
    # Palettes are ONE type with a sub-selector, not four codes:
    #   TARGETTYPE 6 + TARGETLISTID 1=IP 2=FP 3=CP 4=BP
    "palette":     6,
}

PALETTE_LIST = {"ip": 1, "fp": 2, "cp": 3, "bp": 4}


def load(path):
    return ET.parse(path)


def items_of(tree):
    return tree.getroot().find("ETCGRAPHICSSCENE").find("ITEMLIST")


def find_template(tree, key):
    """Return a deep copy of the first ITEM with the given KEY."""
    for it in items_of(tree):
        if it.get("KEY") == key:
            return copy.deepcopy(it)
    raise KeyError(f"no ITEM with KEY={key!r} in the template file")


def set_item(item, x=None, y=None, w=None, h=None,
             targettype=None, targetid=None, text=None, cmd=None,
             fill=None, targetlistid=None):
    if x is not None:
        item.set("POSX", str(x))
    if y is not None:
        item.set("POSY", str(y))
    rect = item.find("ITEMDATA/RECT")
    if rect is not None:
        if w is not None:
            rect.set("W", str(w))
        if h is not None:
            rect.set("H", str(h))
    ms = item.find("ITEMDATA/MAGICSHEET")
    if ms is not None and cmd is not None:
        ms.set("CMD", cmd)
    tg = item.find("ITEMDATA/MAGICSHEET/TARGET")
    if tg is not None:
        if targettype is not None:
            tg.set("TARGETTYPE", str(targettype))
        if targetid is not None:
            tg.set("TARGETID", str(targetid))
        if targetlistid is not None:
            tg.set("TARGETLISTID", str(targetlistid))
    tx = item.find("ITEMDATA/MAGICSHEET/TEXT")
    if tx is not None and text is not None:
        tx.set("STR", text)
    br = item.find("ITEMDATA/BRUSH")
    if br is not None and fill is not None:
        br.set("COLOR", str(fill))
    return item


def new_sheet(template_tree, viewport=None):
    """Empty sheet reusing the template's VIEW block."""
    root = ET.Element("MAGICSHEET", {"SHOWFILE_VERSION": "122"})
    root.append(copy.deepcopy(template_tree.getroot().find("VIEW")))
    scene = ET.SubElement(root, "ETCGRAPHICSSCENE")
    ET.SubElement(scene, "ITEMLIST")
    return ET.ElementTree(root)


def add(tree, item):
    items_of(tree).append(item)
    return item


def grid(tree, template, entries, cols=5, x0=0, y0=0, dx=110, dy=70,
         targettype=20, w=100, h=60):
    """Lay entries out on a grid. entries = [(targetid, text), ...]"""
    for n, (tid, text) in enumerate(entries):
        it = copy.deepcopy(template)
        set_item(it,
                 x=x0 + (n % cols) * dx,
                 y=y0 + (n // cols) * dy,
                 w=w, h=h,
                 targettype=targettype, targetid=tid, text=text)
        add(tree, it)
    return tree


def save(tree, path):
    tree.write(path, encoding="UTF-8", xml_declaration=True)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True,
                    help="an exported magic sheet .xml to clone items from")
    ap.add_argument("--probe-sheet", metavar="OUT",
                    help="generate a sheet that maps unknown TARGETTYPE codes")
    ap.add_argument("--lo", type=int, default=0, help="probe range start")
    ap.add_argument("--hi", type=int, default=29, help="probe range end")
    a = ap.parse_args()

    tpl = load(a.template)

    if a.probe_sheet:
        # One channel button per candidate code, labelled with the code.
        # Import it, then re-export: whichever buttons resolved to a real
        # target reveal the mapping.
        btn = find_template(tpl, "ChannelButton")
        out = new_sheet(tpl)
        codes = list(range(a.lo, a.hi + 1))
        for n, c in enumerate(codes):
            it = copy.deepcopy(btn)
            set_item(it, x=(n % 6) * 150, y=(n // 6) * 95, w=140, h=80,
                     targettype=c, targetid=1, text=f"T{c}")
            add(out, it)
        save(out, a.probe_sheet)
        print(f"wrote {a.probe_sheet} - {len(codes)} probe buttons")
        return 0

    print("nothing to do; pass --probe-sheet OUT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
