"""Code-drawn plain floors: plates over w x h cells with one thin seam round each, no
inner seams or texture. Written into the art pack and made the map's floor.

    .venv/bin/python -I tools/floor_plain.py
    .venv/bin/python -I tools/pack_build.py

Made after 0.6.1, when the user found Hydroponics' picked floor (hy-tile s3: every cell
four tiles, a 5-7 px dark gap round each cell, drains) too busy: "simpler, with less
gaps". The renderer dims every floor (FLOOR_DIM in src/render/map.ts), so these levels
are drawn as the other tiles are, before that.
"""
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "art", "pack")
TW, TH = 25, 27    # a floor tile: a cell and the gaps right of it and below it

# id: (map, panel [w, h] in cells, body level, lit edge level, seam level)
FLOORS = {"hy-plate": ("hydroponics", (2, 2), 3, 5, 1)}


def plate_tiles(panel, body, lit, seam):
    """The panel's tiles, row by row: one plate over the panel, lit along its top and
    left edges, a 1 px seam along its bottom and right."""
    pw, ph = panel
    W, H = pw * TW, ph * TH
    tiles = []
    for j in range(ph):
        for i in range(pw):
            im = Image.new("LA", (TW, TH))
            for y in range(TH):
                for x in range(TW):
                    X, Y = i * TW + x, j * TH + y
                    v = seam if X == W - 1 or Y == H - 1 else lit if X == 0 or Y == 0 else body
                    im.putpixel((x, y), (v * 17, 255))
            tiles.append(im)
    return tiles


pack = json.load(open(os.path.join(PACK, "pack.json")))
for fid, (map_id, panel, body, lit, seam) in FLOORS.items():
    os.makedirs(os.path.join(PACK, fid), exist_ok=True)
    names = []
    for n, im in enumerate(plate_tiles(panel, body, lit, seam)):
        names.append(f"{fid}/tile{n}.png")
        im.save(os.path.join(PACK, names[-1]))
    pack["floors"][fid] = {"from": "tools/floor_plain.py", "tile": names, "panel": list(panel)}
    m = pack["maps"][map_id]
    m["floor"] = fid
    if fid not in m["floors"]: m["floors"].insert(0, fid)
    print(f"{fid}: {len(names)} tiles, the floor of {map_id}")
with open(os.path.join(PACK, "pack.json"), "w") as fh:
    json.dump(pack, fh, indent=1)
    fh.write("\n")
