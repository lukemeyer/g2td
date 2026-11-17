"""Sketches at game size as on the glasses (rows as a bank of three, paths as their six
parts, grid decals as a 3x2 area), for checking before generating.

    .venv/bin/python -I tools/sketch_sheet.py art/work/<name>.png id,id,...
"""
import sys; sys.path.insert(0, "tools")
import piece_sketches as ps
from PIL import Image, ImageDraw, ImageFont
Z = 5
ids = sys.argv[2].split(",")
def green(v):
    k = 0 if v <= 0 else round(255 * (v / 15) ** 0.55); return (k * 22 // 100, k, k * 22 // 100)
def show(g):
    j = ps.SKETCHES[g[0]][2]
    if j in ("path", "grid"):
        P = ps.join_parts(ps.SKETCHES[g[0]][0](), j)
        if j == "path":    # end, straight, bend, tee, cross, dot side by side with a gap
            names = ["end", "straight", "bend", "tee", "cross", "dot"]
            px = [sum(([*P[n].px[y], None, None] for n in names), []) for y in range(20)]
        else:              # a 3x2 area: cells, links across, links down, corners
            def rowband(ys, h):
                return [P[f"gl{ys}"].px[y] + P[f"hl_{ys}"].px[y] + P[f"gm{ys}"].px[y] + P[f"hl_{ys}"].px[y] + P[f"gr{ys}"].px[y] for y in range(h)]
            def linkband():
                return [P["vl_l"].px[y] + P["corner"].px[y] + P["vl_m"].px[y] + P["corner"].px[y] + P["vl_r"].px[y] for y in range(7)]
            px = rowband("t", 20) + linkband() + rowband("b", 20)
    elif j == "row":
        p = ps.row_parts(ps.SKETCHES[g[0]][0]())
        h = p["start"].h; px = [p["start"].px[y] + p["link5"].px[y] + p["middle"].px[y] + p["link5"].px[y] + p["end"].px[y] for y in range(h)]
    else:
        px = ps.SKETCHES[g[0]][0]().px
    im = Image.new("RGB", ((len(px[0]) + 4) * Z, (len(px) + 4) * Z), green(1)); d = ImageDraw.Draw(im)
    for y, r in enumerate(px):
        for x, v in enumerate(r):
            if v is not None: d.rectangle([(x + 2) * Z, (y + 2) * Z, (x + 3) * Z - 1, (y + 3) * Z - 1], fill=green(v))
    return im
f = ImageFont.load_default(size=15)
ims = [(i, show((i,))) for i in ids]
W = 1500; x = y = 10; rowh = 0; places = []
for i, im in ims:
    if x + im.width > W: x = 10; y += rowh + 30; rowh = 0
    places.append((i, im, x, y)); x += im.width + 20; rowh = max(rowh, im.height)
sheet = Image.new("RGB", (W, y + rowh + 40), (22, 24, 27)); d = ImageDraw.Draw(sheet)
for i, im, x, y in places:
    sheet.paste(im, (x, y)); d.text((x, y + im.height + 4), f"{i} ({ps.SKETCHES[i][2] if ps.SKETCHES[i][2] != 'none' else 'single'})", fill=(200, 204, 212), font=f)
sheet.save(sys.argv[1]); print(sheet.size)
