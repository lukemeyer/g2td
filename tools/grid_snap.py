"""Pixel-exact conversion (phase 2 of the graphics plan in CLAUDE.md): a generated
picture to its exact display pixels, never averaged. Two ways, `convert` picks:
snap, for art really on its grid (below), else reduce by mode (see `reduce`).

    .venv/bin/python -I tools/grid_snap.py <theme> <kind> [...]   # art/work/<theme>/snapped/<file>.png for every seed of each kind
    .venv/bin/python -I tools/grid_snap.py --file <png> <cells>    # one picture, a report

klein draws "pixel art on an NxN grid, every pixel a BxB block" only roughly: its blocks
drift a little from B and don't start at 0, so shrinking by a box filter (what the
assembler did) averages parts of two or more blocks into every screen pixel, the grey
mush and specks the art library flags. Instead:

1. Find the grid klein really drew: the pitch and offset whose block boundaries catch
   the most of the picture's edges, across and down, near the size asked for.
2. Read each block by its most common grey over its inside (its edges skipped), never an
   average.
3. See-through: the blocks of the corners' colour that reach the picture's edge.
4. Round the greys to a palette: the piece's own few shades (k-means, `shades` of them),
   each then put on the game's levels linearly, so near-equal greys don't make specks.
5. Clean up: a pixel 2+ levels off all four neighbours, where three or four of those
   agree, takes their level (a lone speck, which the glasses can't show anyway).
6. Crop to what is drawn: whole pixels only; the assembler centres it in its footprint.

The result is greyscale + alpha with the grey on the game's levels (level x 255 / 14), the
format the art pack (art/pack/) takes.
"""
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVEL_MAX = 14       # greys onto levels linearly, grey x 14 / 255 (as the favorite couch was); 15 stays the text's


def edges(g, w, h):
    """How much the grey changes across each column boundary and each row boundary."""
    px = g.load()
    gx = [0.0] * (w + 1)
    gy = [0.0] * (h + 1)
    for y in range(h):
        for x in range(1, w):
            gx[x] += abs(px[x, y] - px[x - 1, y])
    for y in range(1, h):
        for x in range(w):
            gy[y] += abs(px[x, y] - px[x, y - 1])
    return gx, gy


def find_grid(profile, size, want):
    """The pitch and offset of `want` blocks across `size` px whose boundaries catch the
    most edge (a boundary at x is between pixels x-1 and x), and how sure: the edge on the
    boundaries over the edge on the average column."""
    mean = sum(profile) / max(1, len(profile) - 1) or 1
    best = (0, size / want, 0.0)
    pitch0 = size / want
    for k in range(-12, 13):                               # pitches within 12% of the asked size
        p = pitch0 * (1 + k / 100)
        for o10 in range(0, int(p * 10)):
            o = o10 / 10
            xs = [round(o + i * p) for i in range(want + 1)]
            xs = [x for x in xs if 0 < x < size]
            if len(xs) < want * 0.6: continue
            score = sum(profile[x] for x in xs) / len(xs) / mean
            if score > best[0]: best = (score, p, o)
    return best


def snap(path, cells=(1, 1), shades=5, sure=1.6):
    """The picture's exact pixels (rows of levels, None see-through) and a report. `cells`
    is its footprint in cells: 20 px a cell, 25 a cell plus its gap across, 27 down."""
    im = Image.open(path).convert("L")
    w, h = im.size
    want_w, want_h = 20 * cells[0] + 5 * (cells[0] - 1), 20 * cells[1] + 7 * (cells[1] - 1)
    gx, gy = edges(im, w, h)
    sx, px_, ox = find_grid(gx, w, want_w)
    sy, py_, oy = find_grid(gy, h, want_h)
    p = im.load()

    # 2. each block's most common grey inside it (greys in steps of 4)
    cols = [(round(ox + i * px_), round(ox + (i + 1) * px_)) for i in range(-1, want_w + 1)]
    rows = [(round(oy + j * py_), round(oy + (j + 1) * py_)) for j in range(-1, want_h + 1)]
    # blocks cut by the picture's edge count when most of them is inside (klein's grid is
    # often shifted a few px, so the first and last blocks are partly off the picture)
    cols = [(max(0, a), min(w, b)) for a, b in cols if min(w, b) - max(0, a) >= px_ * 0.6]
    rows = [(max(0, a), min(h, b)) for a, b in rows if min(h, b) - max(0, a) >= py_ * 0.6]
    grid = []
    for y0, y1 in rows:
        line = []
        for x0, x1 in cols:
            mx, my = max(1, (x1 - x0) // 5), max(1, (y1 - y0) // 5)
            count = {}
            for y in range(y0 + my, y1 - my):
                for x in range(x0 + mx, x1 - mx):
                    v = p[x, y] // 4
                    count[v] = count.get(v, 0) + 1
            line.append(max(count, key=count.get) * 4 + 2 if count else 0)
        grid.append(line)
    gh, gw = len(grid), len(grid[0])

    # 3. see-through: the corners' grey, reaching the edge
    corner = sorted([grid[0][0], grid[0][-1], grid[-1][0], grid[-1][-1]])[2]
    bg = [[False] * gw for _ in range(gh)]
    todo = [(x, y) for x in range(gw) for y in (0, gh - 1)] + [(x, y) for y in range(gh) for x in (0, gw - 1)]
    while todo:
        x, y = todo.pop()
        if 0 <= x < gw and 0 <= y < gh and not bg[y][x] and abs(grid[y][x] - corner) < 20:
            bg[y][x] = True
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    # 4. the piece's own shades (k-means on the drawn blocks), each on the game's levels
    vals = [grid[y][x] for y in range(gh) for x in range(gw) if not bg[y][x]]
    if not vals: return None, {"error": "nothing drawn"}
    centres = palette(vals, shades)
    level = lambda v: round(min(centres, key=lambda c: abs(c - v)) / 255 * LEVEL_MAX)
    out = [[None if bg[y][x] else level(grid[y][x]) for x in range(gw)] for y in range(gh)]

    # 5. lone specks take their neighbours' level
    fixed = despeck(out)

    # 6. crop to what is drawn
    ys = [y for y in range(gh) if any(v is not None for v in out[y])]
    xs = [x for x in range(gw) if any(out[y][x] is not None for y in range(gh))]
    out = [row[xs[0]:xs[-1] + 1] for row in out[ys[0]:ys[-1] + 1]]
    report = {"pitch": [round(px_, 2), round(py_, 2)], "offset": [ox, oy], "grid": [gw, gh], "sure": round(min(sx, sy), 2),
              "shades": [round(c / 255 * LEVEL_MAX) for c in sorted(centres)], "specks_fixed": fixed, "size": [len(out[0]), len(out)]}
    report["ok"] = report["sure"] >= sure and gw >= want_w - 1 and gh >= want_h - 1
    return out, report


def palette(vals, shades):
    """The piece's own shades: k-means on its drawn greys."""
    vals = sorted(vals)
    centres = [vals[min(len(vals) - 1, int((i + 0.5) * len(vals) / shades))] for i in range(shades)]
    for _ in range(12):
        groups = [[] for _ in centres]
        for v in vals: groups[min(range(len(centres)), key=lambda i: abs(centres[i] - v))].append(v)
        centres = [sum(g) / len(g) if g else c for g, c in zip(groups, centres)]
    return sorted(centres)


def despeck(out):
    """A pixel 2+ levels off all four neighbours, three or four of which agree, takes
    their level. Returns how many changed."""
    gh, gw, fixed = len(out), len(out[0]), 0
    for y in range(gh):
        for x in range(gw):
            v = out[y][x]
            if v is None: continue
            nb = [out[yy][xx] for xx, yy in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if 0 <= xx < gw and 0 <= yy < gh]
            nb = [q for q in nb if q is not None]
            if len(nb) == 4 and all(abs(q - v) >= 2 for q in nb):
                top = max(set(nb), key=nb.count)
                if nb.count(top) >= 3: out[y][x] = top; fixed += 1
    return fixed


def reduce(path, cells=(1, 1), shades=5, samples=6, box=None):
    """For art that isn't on its grid (klein's "pixel art" is often 3-4 px fine, an object
    far bigger than its footprint in pixels): cut out, cropped to what is drawn, then each
    display pixel takes the shade that covers most of its area (samples x samples points),
    of the piece's own palette, never a mean, so detail too fine to show drops out instead
    of averaging to grey. Sized to fit the footprint (one factor, no stretch), or to fill
    `box` exactly (w, h: a sketch's drawn size, so the piece keeps the sketch's place)."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from pixel_art import crop_to_ink, cutout
    la = crop_to_ink(cutout(Image.open(path)))
    if box: fx, fy = box[0] / la.width, box[1] / la.height
    else:
        fit = (20 * cells[0] + 5 * (cells[0] - 1), 20 * cells[1] + 7 * (cells[1] - 1))
        fx = fy = min(fit[0] / la.width, fit[1] / la.height)
    tw, th = max(1, round(la.width * fx)), max(1, round(la.height * fy))
    p = la.load()
    cents = palette([p[x, y][0] for y in range(la.height) for x in range(la.width) if p[x, y][1] >= 128], shades)
    shade = lambda v: min(range(len(cents)), key=lambda i: abs(cents[i] - v))
    out = []
    for j in range(th):
        row = []
        for i in range(tw):
            count, see = {}, 0
            for sy in range(samples):
                for sx in range(samples):
                    x = min(la.width - 1, int((i + (sx + 0.5) / samples) / fx))
                    y = min(la.height - 1, int((j + (sy + 0.5) / samples) / fy))
                    g, a = p[x, y]
                    if a < 128: see += 1; continue
                    k = shade(g); count[k] = count.get(k, 0) + 1
            row.append(None if see * 2 > samples * samples or not count else round(cents[max(count, key=count.get)] / 255 * LEVEL_MAX))
        out.append(row)
    fixed = despeck(out)
    return out, {"method": "mode", "scale": [round(fx, 4), round(fy, 4)], "size": [tw, th], "shades": [round(c / 255 * LEVEL_MAX) for c in cents], "specks_fixed": fixed, "ok": True}


def detail_preserving(la, box, lam=1.0):
    """Detail-preserving image downscaling (Weber, Waechter, Amend, Guthe, Goesele 2016):
    each output pixel a weighted mean of the source pixels under it, a pixel's weight how
    far its grey stands from the smoothed box average, to the power `lam`. 0 is plain
    averaging; at 1 thin seams, caps and lit lips pull their pixel toward themselves
    instead of being averaged away, while flat areas stay soft. Greys (None see-through,
    where most of a pixel's area is)."""
    W, H = la.size
    w, h = box
    L, A = la.getchannel("L").load(), la.getchannel("A").load()
    s = la.resize(box, Image.BOX)
    SL, SA = s.getchannel("L").load(), s.getchannel("A").load()
    avg = [[SL[x, y] if SA[x, y] >= 128 else None for x in range(w)] for y in range(h)]
    out = [[None] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if avg[y][x] is None: continue
            # the guide: the box average smoothed by [1 2 1] x [1 2 1] over opaque neighbours
            gs = gn = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = min(h - 1, max(0, y + dy)), min(w - 1, max(0, x + dx))
                    if avg[yy][xx] is None: continue
                    k = (2 - abs(dx)) * (2 - abs(dy)); gs += k * avg[yy][xx]; gn += k
            g = gs / gn
            sw = sv = 0.0
            for sy in range(y * H // h, max(y * H // h + 1, (y + 1) * H // h)):
                for sx in range(x * W // w, max(x * W // w + 1, (x + 1) * W // w)):
                    if A[sx, sy] < 128: continue
                    wt = (abs(L[sx, sy] - g) / 255) ** lam
                    sw += wt; sv += wt * L[sx, sy]
            out[y][x] = sv / sw if sw else g
    return out


def average(path, box, shades=7, lam=1.0, frame=False):
    """The conversion for pieces (tools/piece_gen.py): cut out, cropped to what is drawn,
    shrunk to `box` (w, h) (with `frame`, by one factor to fit inside it, centred:
    filling the box both ways stretched a piece klein drew narrower or taller than its
    sketch, and klein often draws a piece smaller than its sketch) by detail-preserving downscaling (`lam` 0 is the old
    assembler's plain averaging, which made the user's favorite couch; 1, chosen with the
    user, keeps its soft one-level steps and brings back seams and caps), each grey onto
    levels linearly (grey x 14 / 255), cut to the piece's own `shades` (k-means) and lone
    specks cleaned, so busy pieces don't turn to mush."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from pixel_art import crop_to_ink, cutout
    la = crop_to_ink(cutout(Image.open(path)))
    if frame:
        f = min(box[0] / la.width, box[1] / la.height)
        fit = (max(1, min(box[0], round(la.width * f))), max(1, min(box[1], round(la.height * f))))
        inner = detail_preserving(la, fit, lam)
        dx, dy = (box[0] - fit[0]) // 2, (box[1] - fit[1]) // 2
        greys = [[None] * box[0] for _ in range(box[1])]
        for y, row in enumerate(inner): greys[dy + y][dx:dx + fit[0]] = row
    else: greys = detail_preserving(la, box, lam)
    vals = [v for row in greys for v in row if v is not None]
    cents = palette(vals, shades)
    near = lambda v: min(cents, key=lambda c: abs(c - v))
    out = [[None if v is None else max(1, min(LEVEL_MAX, round(near(v) / 255 * LEVEL_MAX))) for v in row] for row in greys]
    fixed = despeck(out)
    return out, {"method": "detail-preserving" if lam else "average", "lambda": lam, "size": list(box),
                 "shades": sorted({v for r in out for v in r if v is not None}), "specks_fixed": fixed, "ok": True}


def convert(path, cells=(1, 1), shades=5, box=None):
    """Snap when the picture really is on its grid (sure, and the pitch within 4% of the
    size asked for); else average into `box` when one is given (tools/piece_gen.py), or
    reduce by mode."""
    if os.path.basename(path).startswith("d_"): return None, {"method": "drawn"}
    grid, rep = snap(path, cells, shades)
    want = (Image.open(path).width / (20 * cells[0] + 5 * (cells[0] - 1)))
    if grid and rep["ok"] and abs(rep["pitch"][0] / want - 1) < 0.04 and abs(rep["pitch"][1] / want - 1) < 0.04:
        rep["method"] = "snap"
        return grid, rep
    out, r2 = average(path, box, shades) if box else reduce(path, cells, shades)
    r2["snap_tried"] = rep
    return out, r2


def save(grid, path):
    """Greyscale + alpha, grey = level x 17, as the art pack takes it."""
    im = Image.new("LA", (len(grid[0]), len(grid)), (0, 0))
    p = im.load()
    for y, row in enumerate(grid):
        for x, v in enumerate(row):
            if v is not None: p[x, y] = (v * 17, 255)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def snap_kinds(theme, kinds, shades=5):
    """Every seed of each piece kind (its files' stems) into art/work/<theme>/snapped/."""
    d = os.path.join(ROOT, "art", "work", theme)
    zones = json.load(open(os.path.join(d, "picks.json")))["zones"]
    reports = {}
    for kind in kinds:
        spec = zones[kind]
        files, size = (spec, (1, 1)) if isinstance(spec, list) else (spec["files"], tuple(spec["size"]))
        # the kind's own seeds, and its sketch-led seeds (g_<kind>, tools/piece_sketches.py)
        stems = {f.rsplit("-s", 1)[0] for f in files if "/" not in f and not f.startswith("d_")} | {f"g_{kind}"}
        for f in sorted(os.listdir(os.path.join(d, "raw"))):
            if not f.endswith(".png") or f.rsplit("-s", 1)[0] not in stems: continue
            grid, rep = convert(os.path.join(d, "raw", f), size, shades)
            if grid: save(grid, os.path.join(d, "snapped", f))
            reports[f] = rep
            print(theme, kind, f, rep)
    path = os.path.join(d, "snapped", "reports.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(reports)
    json.dump(old, open(path, "w"), indent=1)
    return reports


if __name__ == "__main__":
    if sys.argv[1] == "--file":
        cells = tuple(int(v) for v in sys.argv[3].split("x")) if len(sys.argv) > 3 else (1, 1)
        print(convert(sys.argv[2], cells)[1])
    else:
        snap_kinds(sys.argv[1], sys.argv[2:])
