"""Generate pieces from their house-view sketches (docs/art.md, "Making a piece"):
klein's `reference` workflow on the sketch with the couch (the house style's anchor) as
the style reference, then the conversion into the sketch's exact box: snapped when klein drew on the grid, else
shrunk by detail-preserving downscaling (an average that keeps seams and caps; plain
averaging made the user's favorite couch), cut to a few shades of the piece's own and
cleaned of specks.
Each call is time-limited (tools/studio_gen.py).

    .venv/bin/python -I tools/piece_gen.py [--seeds 1,2,3,4] [--recipe B] [--block 16] [--form single]
        [--from <candidate>] [--style <png>] [--average] [--shades 7] id ...
    .venv/bin/python -I tools/piece_gen.py --derive <src id>:<candidate> id     # see derive()

Per piece in art/work/<id>/: sketch.png (a candidate itself), klein's input and its
arguments, raw/<recipe>-s<n>.png (a seed already there is kept), the conversions
<recipe>-s<n>[-<part>].png (re-made from the raw seed on every run), and candidates.json, which the art library lists for review
and "use" (vite.config.ts copies the chosen files into art/pack/ and rebuilds src/pack.ts).
"""
import json
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import grid_snap      # noqa: E402
import piece_sketches as ps   # noqa: E402

COUCH = os.path.join(ROOT, "art", "reference", "couch-s1.png")
MAX, MIN = 1024, 256  # Studio's largest and smallest sides; sides are multiples of 16

# The house-view prompt (one for every piece). Recipes are kept by letter so seeds from
# an earlier wording stay comparable in the library.
RECIPES = {
    "A": ("Pixel art game object on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "a few flat grey shades on a pure black background. Seen from almost straight above with a slight tilt toward the viewer: "
          "the top surfaces fill the shape, and the front shows only as a narrow darker strip along the bottom edge. "
          "Light from directly above, no cast shadow, no black outline. The same view, scale and style as the couch in the second image. "
          "Follow the first image exactly: every block keeps its size, place and shade; add only soft shading and small surface detail. "
          "The object: {what}."),
    # A's barrels, cases and workstations tilted well forward and its lockers were drawn
    # from the front: B puts the camera overhead and limits the front to a sliver.
    "B": ("Pixel art game object on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "a few flat grey shades on a pure black background. Top-down view from a camera directly overhead looking straight down at the floor, "
          "like a top-down 2D game map: we see the top of the object; its front side shows only as a thin darker sliver along the bottom edge, "
          "its left and right sides are not visible at all, no perspective, no vanishing point. "
          "Light from directly above, no cast shadow, no black outline. The same overhead view and style as the couch in the second image. "
          "Follow the first image exactly: it is the object seen from above; every block keeps its size, place and shade; add only soft shading "
          "and small surface detail. The object, seen from above: {what}."),
    # B with the top's detail kept: klein smoothed the lockers' roof panel into a plain
    # surface on almost every B seed.
    "C": ("Pixel art game object on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "a few flat grey shades on a pure black background. Top-down view from a camera directly overhead looking straight down at the floor, "
          "like a top-down 2D game map: we see the top of the object; its front side shows only as a thin darker sliver along the bottom edge, "
          "its left and right sides are not visible at all, no perspective, no vanishing point. "
          "Light from directly above, no cast shadow, no black outline. The same overhead view and style as the couch in the second image. "
          "Follow the first image exactly: it is the object seen from above; every block keeps its size, place and shade. "
          "Keep every detail drawn on the top surface in the first image (panels, recesses, vents, slots, seams, rivets, rims) as clearly "
          "visible darker and lighter shapes in the same places; never smooth the top into a plain surface. Add only soft shading. "
          "The object, seen from above: {what}."),
    # More detail that survives the shrink (prompt tests on the Cargo Bay picks): B's camera,
    # with the detail asked for in whole blocks and strong contrast, never fine lines.
    "D": ("Pixel art game object on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "a few flat grey shades on a pure black background. Top-down view from a camera directly overhead looking straight down at the floor, "
          "like a top-down 2D game map: we see the top of the object; its front side shows only as a thin darker sliver along the bottom edge, "
          "its left and right sides are not visible at all, no perspective, no vanishing point. "
          "Light from directly above, no cast shadow, no black outline. The same overhead view and style as the second image. "
          "Follow the first image exactly: keep its outline, its size and every part in its place. "
          "Make the detail bold and chunky so it still reads at {w}x{h} pixels: every detail (ribs, latches, bumpers, panels, vents, bolts, "
          "hatches, lights) is a solid shape at least one whole block wide, several shades lighter or darker than the surface round it, "
          "with strong contrast between neighbouring parts; flat shading, no gradients, no thin lines, no texture noise. "
          "The object, seen from above: {what}."),
    # A refining pass: the first image is a picked candidate (--from), already the right
    # shape; ask only for crisper parts on it.
    "E": ("Pixel art game object on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "a few flat grey shades on a pure black background. Top-down view from a camera directly overhead looking straight down, "
          "like a top-down 2D game map, no perspective. Light from directly above, no cast shadow, no black outline. "
          "The first image is the finished object at low resolution, blurry. Redraw exactly the same object at the same size and place, "
          "crisp and clear: never change its outline and never move, add or remove a part. Sharpen every part: give each its own flat shade, "
          "a lit top edge and a dark lower edge, and add bold rivets, seams, grips and highlights where they belong, each at least one whole block, "
          "several shades off the surface round it. Flat shading, no gradients, no thin lines, no texture noise. "
          "The same style as the second image. The object, seen from above: {what}."),
    # The game sprites (enemies and the boss): D's bold detail, seen straight down with no
    # front side (they turn with the road), bright against a dark floor.
    "S": ("Pixel art game sprite on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "a few flat grey shades on a pure black background. Seen from directly above, like a top-down 2D game: no perspective, "
          "no side faces, no cast shadow, no black outline. A hostile robot that must stand out clearly against a dark floor: "
          "its body light grey, with strong contrast between neighbouring parts. "
          "Follow the first image exactly: keep its outline, its size and every part in its place. "
          "Make the detail bold and chunky so it still reads at {w}x{h} pixels: every detail (armour plates, seams, joints, sensors, "
          "vents, lights) is a solid shape at least one whole block wide, several shades lighter or darker than the surface round it; "
          "flat shading, no gradients, no thin lines, no texture noise. The same style as the second image. "
          "The robot, seen from above: {what}."),
    # The player's towers (turrets and tripline posts): S's wording for a defence machine.
    "U": ("Pixel art game sprite on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "a few flat grey shades on a pure black background. Seen from directly above, like a top-down 2D tower defense game: no perspective, "
          "no side faces, no cast shadow, no black outline. A sturdy armoured defence tower that must stand out clearly against a dark floor: "
          "bright metal, with strong contrast between neighbouring parts. "
          "Follow the first image exactly: keep its outline, its size and every part in its place, the barrels exactly where they are. "
          "Make the detail bold and chunky so it still reads at {w}x{h} pixels: every detail (armour plates, bolts, seams, vents, cooling fins, "
          "lights) is a solid shape at least one whole block wide, several shades lighter or darker than the surface round it; "
          "flat shading, no gradients, no thin lines, no texture noise. The same style as the second image. "
          "The tower, seen from above: {what}."),
    # The boss, which never turns: S with depth (the first boss seeds came back flat, nearly
    # copies of the sketch): the house view's tilt, rounded volume, shading.
    "T": ("Pixel art game boss sprite on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "many grey shades on a pure black background. Seen from above with a slight tilt toward the viewer, like the boss of a classic "
          "top-down 2D action game: rounded forms with real volume and depth, lit from directly above, every surface shaded from a bright "
          "top to a dark underside, the hull's side visible as a darker band along its bottom, parts nearer the viewer overlapping parts "
          "behind them. No cast shadow, no black outline. A menacing hostile machine that stands out clearly against a dark floor. "
          "Follow the first image exactly: keep its outline, its size and every part in its place. Give it rich, chunky detail that still "
          "reads at {w}x{h} pixels: armour plates with lit edges and dark seams, rivets, vents, cables, glowing lights, each detail at least "
          "one whole block, several shades off the surface round it; no thin lines, no texture noise. The same style as the second image. "
          "The machine, seen from above: {what}."),
    # The boss's arms, which the game turns to any of four sides: T's volume and detail,
    # but seen straight down and lit from directly above, so a turned arm still looks lit.
    "V": ("Pixel art game sprite on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, "
          "many grey shades on a pure black background. Seen from directly above, like a top-down 2D action game, lit from directly "
          "above: every rounded part bright along its middle and darker toward both of its sides, the same on both sides, so it looks "
          "right turned any way. No perspective, no cast shadow, no black outline. Part of a menacing machine boss that stands out "
          "clearly against a dark floor. Follow the first image exactly: keep its outline, its size and every part in its place. "
          "Give it rich, chunky detail that still reads at {w}x{h} pixels: armour plates with lit edges and dark seams, bolts, joints, "
          "glowing lights, each detail at least one whole block, several shades off the surface round it; no thin lines, no texture "
          "noise. The same style as the second image. Seen from above: {what}."),
}


def canvas(g, b=16):
    """The sketch scaled by a whole block (`b`, or less to fit Studio), centred on a black
    canvas whose sides are multiples of 16 and at least MIN: (image, block, offset)."""
    while g.w * b > MAX or g.h * b > MAX: b -= 1
    W, H = max(MIN, -(-g.w * b // 16) * 16), max(MIN, -(-g.h * b // 16) * 16)
    ox, oy = (W - g.w * b) // 2, (H - g.h * b) // 2
    im = Image.new("L", (W, H), 0)
    sk = g.image(b)
    im.paste(sk.getchannel("L"), (ox, oy), sk.getchannel("A"))
    return im, b, (ox, oy)


def bbox(g):
    ys = [y for y in range(g.h) if any(v is not None for v in g.px[y])]
    xs = [x for x in range(g.w) if any(g.px[y][x] is not None for y in range(g.h))]
    return xs[0], ys[0], xs[-1], ys[-1]


SHADES = 7           # shades a converted piece keeps: the favorite couch had 6


def placed(grid, sketch):
    """The converted picture at the sketch's own place in its footprint, or None when its
    size isn't the sketch's drawn size (then it can't be cut at the cell lines)."""
    x0, y0, x1, y1 = bbox(sketch)
    if (len(grid[0]), len(grid)) != (x1 - x0 + 1, y1 - y0 + 1): return None
    g = ps.Grid(sketch.w, sketch.h)
    for y, row in enumerate(grid):
        for x, v in enumerate(row): g.px[y0 + y][x0 + x] = v
    return g


def parts_of(g, joins, name, out, border=None):
    """Save a picture as the parts the renderer takes: `body`, or the parts of a piece with
    joins (a row's, a path's or a grid decal's), built from it."""
    if joins != "none":
        files = {}
        for part, p in ps.join_parts(g, joins, border).items():
            f = f"{name}-{part}.png"
            p.image().save(os.path.join(out, f))
            files[part] = f
        return files
    g.image().save(os.path.join(out, name + ".png"))
    return {"body": name + ".png"}


def label_of(tag):
    """", block 8, single" for the tag "b8-single"."""
    return "".join(", block " + t[1:] if t.startswith("b") and t[1:].isdigit() else ", " + t for t in tag.split("-") if t)


def from_png(path):
    """A converted candidate back as a Grid (grey = level x 17, alpha cut at half)."""
    im = Image.open(path).convert("LA")
    g = ps.Grid(im.width, im.height)
    g.px = [[round(im.getpixel((x, y))[0] / 17) if im.getpixel((x, y))[1] >= 128 else None for x in range(im.width)] for y in range(im.height)]
    return g


def generate(pid, seeds, recipe="B", block=16, form=None, start=None, style=None, average=False, shades=SHADES):
    """`start`: a candidate's name (its body picture) to give klein instead of the sketch;
    `style`: another style reference than the couch, as a path; `average`: never snap (a
    seed on the grid snaps to one shade a block, which drops klein's shading inside the
    blocks: the boss's first seeds), shrinking it into the sketch's box instead; `shades`:
    how many it keeps."""
    make, cells, joins, what = ps.SKETCHES[pid]
    if form: make, cells, what = ps.FORMS[pid][form]      # another form of the sketch (piece_sketches.FORMS)
    sketch = make()
    first = from_png(os.path.join(ps.WORK, pid, start + ".png")) if start else sketch
    out = os.path.join(ps.WORK, pid)
    raw = os.path.join(out, "raw")
    os.makedirs(raw, exist_ok=True)
    cands_path = os.path.join(out, "candidates.json")
    cands = json.load(open(cands_path))["candidates"] if os.path.exists(cands_path) else {}
    skn = "sketch" + (f"-{form}" if form else "")
    # a piece klein draws turned (ps.TURN_AFTER) is saved turned a quarter clockwise
    final = (lambda g: ps.turn_cw(g)) if pid in ps.TURN_AFTER else (lambda g: g)
    final(sketch).image().save(os.path.join(out, skn + ".png"))
    cands[skn] = {"label": "the sketch" + (f", {form}" if form else ""), "method": "drawn", "parts": parts_of(final(sketch), joins, skn, out)}
    tag = ("" if block == 16 else f"b{block}") + (f"-{form}" if form else "")    # the block asked for; canvas may need a smaller one to fit
    if start: tag += "-from" + start.replace("-", "")
    if average: tag += "-avg"
    if shades != SHADES: tag += f"-{shades}sh"
    if style:      # named by its piece (art/work/<id>/raw/...) or its file
        d = os.path.dirname(style)
        tag += "-st" + (os.path.basename(os.path.dirname(d)) if os.path.basename(d) == "raw" else os.path.splitext(os.path.basename(style))[0]).replace("-", "")
    im, block, (ox, oy) = canvas(first, block)
    inp = os.path.join(out, f"input{tag}.png")
    im.save(inp)
    for seed in seeds:
        name = f"{recipe}{tag}-s{seed}"
        png = os.path.join(raw, name + ".png")
        if not os.path.exists(png):
            args = {"prompt": RECIPES[recipe].format(w=sketch.w, h=sketch.h, what=what), "workflow": "reference",
                    "init_image": {"path": inp}, "reference_images": [{"path": style or COUCH}],
                    "width": im.width, "height": im.height, "seed": seed}
            json.dump(args, open(os.path.join(raw, name + ".json"), "w"), indent=1)
            r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "studio_gen.py"), os.path.join(raw, name + ".json"), png,
                                "--timeout", "150"], capture_output=True, text=True)
            if r.returncode:
                print(f"  {pid} {name}: generation failed ({r.returncode}) {r.stderr[-200:]}")
                continue
        # back to the sketch's area, then its exact pixels
        # (snapped from the whole sketch area; averaged from exactly the sketch's drawn box,
        # one factor both ways, never stretched to what klein drew)
        crop, framed = os.path.join(raw, name + "-crop.png"), os.path.join(raw, name + "-frame.png")
        x0, y0, x1, y1 = bbox(sketch)
        box = (x1 - x0 + 1, y1 - y0 + 1)
        Image.open(png).crop((ox, oy, ox + sketch.w * block, oy + sketch.h * block)).save(crop)
        Image.open(png).crop((ox + x0 * block, oy + y0 * block, ox + (x1 + 1) * block, oy + (y1 + 1) * block)).save(framed)
        grid, rep = (None, {}) if average else grid_snap.convert(crop, cells, shades=shades, box=box)
        if not grid or rep.get("method") != "snap" or (len(grid[0]), len(grid)) != box:
            # not on the grid, or on it at another size than the sketch: average it into the sketch's box instead
            off = bool(grid) and rep.get("method") == "snap"
            tried = rep.get("snap_tried", rep if rep else None)
            grid, rep = grid_snap.average(framed, box, shades, frame=True)
            if off: rep["snapped_off_size"] = True
            if tried: rep["snap_tried"] = tried
        os.remove(crop); os.remove(framed)
        rep = {k: rep[k] for k in ("method", "sure", "size") if k in rep} | ({"sure": rep["snap_tried"].get("sure")} if "snap_tried" in rep else {})
        g = placed(grid, sketch) if grid else None
        if g is not None and pid in ps.MASKED:      # see-through where the sketch is (the conversion fills its box)
            g.px = [[v if k is not None else None for v, k in zip(row, krow)] for row, krow in zip(g.px, sketch.px)]
        if g is None:
            print(f"  {pid} {name}: {rep} doesn't match the sketch's size {bbox(sketch)}")
            cands[name] = {"label": f"recipe {recipe}{label_of(tag)}, seed {seed}", "raw": f"raw/{name}.png", **rep, "parts": None}
            continue
        cands[name] = {"label": f"recipe {recipe}{label_of(tag)}, seed {seed}", "raw": f"raw/{name}.png", **rep, "parts": parts_of(final(g), joins, name, out, ps.grid_border(sketch))}
        print(f"  {pid} {name}: {rep}")
    meta = {"id": pid, "size": list(ps.SKETCHES[pid][1]) if joins != "row" else [1, 1], "joins": joins, "what": what}
    if pid in ps.DECALS: meta["decal"] = True
    if pid in ps.OWN_MAP: meta["map"] = ps.OWN_MAP[pid]
    json.dump({"piece": meta, "candidates": cands}, open(cands_path, "w"), indent=1)


def derive(pid, src, cand, shades=SHADES):
    """Another piece's seed converted into this piece's sketch box: a turret facing up from
    its facing-right pick (klein drew that one facing up on the turned pad, 47x45; fitted
    by one factor into the 45x47 pad, the barrels land within half a pixel of the lanes),
    so both facings are one drawing. Saved as candidate `<src>-<cand>`."""
    make, cells, joins, what = ps.SKETCHES[src]
    first = make()                                # as klein saw it (TURN_AFTER pieces unturned)
    im, block, (ox, oy) = canvas(first, 16)
    x0, y0, x1, y1 = bbox(first)
    framed = os.path.join(ps.WORK, pid, "derive-frame.png")
    Image.open(os.path.join(ps.WORK, src, "raw", cand + ".png")).crop(
        (ox + x0 * block, oy + y0 * block, ox + (x1 + 1) * block, oy + (y1 + 1) * block)).save(framed)
    sketch = ps.SKETCHES[pid][0]()
    tx0, ty0, tx1, ty1 = bbox(sketch)
    grid, rep = grid_snap.average(framed, (tx1 - tx0 + 1, ty1 - ty0 + 1), shades, frame=True)
    os.remove(framed)
    g = placed(grid, sketch)
    name = f"{src}-{cand}"
    path = os.path.join(ps.WORK, pid, "candidates.json")
    data = json.load(open(path))
    data["candidates"][name] = {"label": f"{src} {cand}, fitted to this box", "raw": f"../{src}/raw/{cand}.png", "method": rep["method"],
                                "size": rep["size"], "parts": parts_of(g, "none", name, os.path.join(ps.WORK, pid))}
    json.dump(data, open(path, "w"), indent=1)
    print(f"  {pid} {name}: {rep['size']}")


if __name__ == "__main__":
    args, seeds, recipe, block, form, start, style = sys.argv[1:], [1, 2, 3, 4], "B", 16, None, None, None
    if "--derive" in args:      # --derive <src id>:<candidate> <id>
        i = args.index("--derive"); src, cand = args[i + 1].split(":"); del args[i:i + 2]
        for pid in args: derive(pid, src, cand)
        sys.exit()
    average = "--average" in args
    if average: args.remove("--average")
    shades = SHADES
    if "--shades" in args: i = args.index("--shades"); shades = int(args[i + 1]); del args[i:i + 2]
    if "--from" in args: i = args.index("--from"); start = args[i + 1]; del args[i:i + 2]
    if "--style" in args: i = args.index("--style"); style = os.path.abspath(args[i + 1]); del args[i:i + 2]
    if "--form" in args: i = args.index("--form"); form = args[i + 1]; del args[i:i + 2]
    if "--block" in args: i = args.index("--block"); block = int(args[i + 1]); del args[i:i + 2]
    if "--seeds" in args: i = args.index("--seeds"); seeds = [int(s) for s in args[i + 1].split(",")]; del args[i:i + 2]
    if "--recipe" in args: i = args.index("--recipe"); recipe = args[i + 1]; del args[i:i + 2]
    for pid in args or list(ps.SKETCHES):
        print(pid)
        generate(pid, seeds, recipe, block, form, start, style, average, shades)
