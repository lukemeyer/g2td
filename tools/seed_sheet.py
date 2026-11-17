"""Each piece's sketch and its recipe B seeds as on the glasses (rows as a bank of
three), with what klein drew under each: the review sheet after a batch.

    .venv/bin/python -I tools/seed_sheet.py art/work/<name>.png id,id,... [prefix,prefix,...]

The prefixes pick the candidates shown (default B-); an exact name works too.
"""
import json, sys
from PIL import Image, ImageDraw, ImageFont
Z = 4
ids = sys.argv[2].split(",")
prefixes = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else ("B-",)
def lv(path):
    im = Image.open(path).convert("LA")
    return [[round(im.getpixel((x, y))[0] / 17) if im.getpixel((x, y))[1] >= 128 else None for x in range(im.width)] for y in range(im.height)]
def green(v):
    k = 0 if v <= 0 else round(255 * (v / 15) ** 0.55); return (k * 22 // 100, k, k * 22 // 100)
def picture(pid, cand, joins):
    if joins == "row":
        p = {k: lv(f"art/work/{pid}/{cand['parts'][k]}") for k in ("start", "link5", "middle", "end")}
        h = len(p["start"]); return [p["start"][y] + p["link5"][y] + p["middle"][y] + p["link5"][y] + p["end"][y] for y in range(h)]
    if joins == "path":  # each part on its own, a cell apart: end, straight, bend, tee, cross
        p = [lv(f"art/work/{pid}/{cand['parts'][k]}") for k in ("end", "straight", "bend", "tee", "cross")]
        return [sum((r[y] + [None] * 5 for r in p), [])[:-5] for y in range(20)]
    if joins == "grid":  # a 2x2 patch with its gaps, and a single tile beside it
        p = {k: lv(f"art/work/{pid}/{v}") for k, v in cand["parts"].items()}
        top = [p["glt"][y] + p["hl_t"][y] + p["grt"][y] for y in range(20)]
        mid = [p["vl_l"][y] + p["corner"][y] + p["vl_r"][y] for y in range(7)]
        bot = [p["glb"][y] + p["hl_b"][y] + p["grb"][y] for y in range(20)]
        rows = top + mid + bot
        return [r + [None] * 10 + (p["gss"][y] if y < 20 else [None] * 20) for y, r in enumerate(rows)]
    return lv(f"art/work/{pid}/{cand['parts']['body']}")
def draw(px):
    im = Image.new("RGB", ((len(px[0]) + 4) * Z, (len(px) + 4) * Z), green(1)); d = ImageDraw.Draw(im)
    for y, r in enumerate(px):
        for x, v in enumerate(r):
            if v is not None: d.rectangle([(x + 2) * Z, (y + 2) * Z, (x + 3) * Z - 1, (y + 3) * Z - 1], fill=green(v))
    return im
f = ImageFont.load_default(size=13); hf = ImageFont.load_default(size=17)
rows = []
for pid in ids:
    w = json.load(open(f"art/work/{pid}/candidates.json")); joins = w["piece"]["joins"]; cands = w["candidates"]
    cells = []
    for n in ["sketch"] + [n for n in cands if n.startswith(prefixes)]:
        c = cands[n]
        if not c.get("parts"): continue
        im = draw(picture(pid, c, joins))
        thumb = None
        if c.get("raw"): thumb = Image.open(f"art/work/{pid}/{c['raw']}").convert("RGB"); thumb.thumbnail((70, 70))
        cells.append((im, thumb, "sketch" if n == "sketch" else n.removeprefix("B-")))
    rows.append((pid, cells))
def cell_w(im, label): return max(im.width, 70, int(d0.textlength(label, font=f)))   # wide enough for the whole name
d0 = ImageDraw.Draw(Image.new("RGB", (1, 1)))
W = 150 + max(sum(cell_w(im, label) + 14 for im, _, label in cs) for _, cs in rows)
H = 10 + sum(max(im.height for im, _, _ in cs) + 100 for _, cs in rows)
sheet = Image.new("RGB", (W, H), (22, 24, 27)); d = ImageDraw.Draw(sheet); y = 10
for pid, cs in rows:
    d.text((10, y + 20), pid, fill=(230, 232, 236), font=hf); x = 150
    for im, thumb, label in cs:
        sheet.paste(im, (x, y))
        d.text((x, y + im.height + 4), label, fill=(170, 175, 185), font=f)     # the full name, then what klein drew
        if thumb: sheet.paste(thumb, (x, y + im.height + 22))
        x += cell_w(im, label) + 14
    y += max(im.height for im, _, _ in cs) + 100
sheet.save(sys.argv[1]); print(sheet.size)
