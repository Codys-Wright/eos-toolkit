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

TARGETTYPE codes confirmed so far:
     0  None (decorative)
    20  Channel
     4  Macro (inferred: id 5 matched the show's Macro 5)
     2  unknown - seen on Buttons
    45  unknown - seen on Faders
Run `python3 ms_gen.py --probe-sheet out.xml` to generate a sheet that maps the
remaining codes: import it, then re-export and read which targets resolved.
"""
import argparse
import copy
import xml.etree.ElementTree as ET

TARGETTYPE = {"none": 0, "channel": 20, "macro": 4}


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
             fill=None):
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
    a = ap.parse_args()

    tpl = load(a.template)

    if a.probe_sheet:
        # One channel button per candidate code, labelled with the code.
        # Import it, then re-export: whichever buttons resolved to a real
        # target reveal the mapping.
        btn = find_template(tpl, "ChannelButton")
        out = new_sheet(tpl)
        codes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
                 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
        entries = [(1, f"T{c}") for c in codes]
        for n, c in enumerate(codes):
            it = copy.deepcopy(btn)
            set_item(it, x=(n % 6) * 120, y=(n // 6) * 80, w=110, h=65,
                     targettype=c, targetid=1, text=f"TYPE {c}")
            add(out, it)
        save(out, a.probe_sheet)
        print(f"wrote {a.probe_sheet} - {len(codes)} probe buttons")
        return 0

    print("nothing to do; pass --probe-sheet OUT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
