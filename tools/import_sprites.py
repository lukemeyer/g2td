"""Import the generated art into src/sprites.ts.

    .venv/bin/python -I tools/import_sprites.py

Every picture is stored as rows of hex digits, one display level (0-15) per pixel;
'.' is see-through. Everything faces up (north), or right where it says; the game turns it.

Every sprite is the graphics remake's: the
user's picks from tools/piece_gen.py, already at their display pixels
(art/sprites/<id>.png, grey = level x 17), drawn as they are, never scaled.
- TURRET_ART: per turret, facing up and facing right, 45x47 (a pad), barrels on the lanes;
  facing up is the facing-right drawing fitted to the pad (piece_gen.py --derive). The
  game turns each a half turn for the other two facings and outlines it as it draws.
- POSTS: tower-laser and tower-stasis, 24x24, centred on each built tripline post,
  emitter at the top; outlined by the game.
- The enemies and the boss get a black outline here, inside their own box (a pixel all
  round, diagonals too):
  - WALKER: sprite-walker, and two walk poses made from it here by turning the legs
    about their hips (`stride`; the generated poses drew the legs differently).
  - FLOATER: sprite-floater (its shield doesn't show); SHADOWS (drawn here, its body
    moved down and right) under it at three heights, which the game never turns.
  - BOSS: sprite-boss-body, the mother drone's body at its exact 120x128 (5x5 cells):
    the hull, four legs to the corners and an arm socket on each side, where the game
    plugs in ARMS. (sprite-boss, the eight-legged boss with two ports, was the old pick.)
  - ARMS: arm-walkers, arm-floaters, arm-swarm and arm-stump, 32x22 pointing right (the
    collar on the left goes under the hull); the game turns each to its socket.

Writes src/sprites.ts, art/sprites/preview.png (every sprite enlarged) and the
high-res art with its background cut out for the phone's guide, public/guide/*.png.
The maps are drawn by src/render/map.ts from the art pack.
"""
import base64
import io
import math
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools"))
ART = os.path.join(ROOT, "art")
SPRITES = os.path.join(ART, "sprites")


def hexrows(grid):
    return ["".join("." if v is None else "%x" % v for v in row) for row in grid]


# --- sprites ----------------------------------------------------------------------

N = 20       # enemies: what one cell (and one cover, x 0-19, y 4-23) holds
POST = 24    # tripline posts: a little more than a cell, the most that fits between neighbours

# The user's picks, copied from the candidates tools/piece_gen.py made (art/work/<id>/,
# not kept in the repo) to art/sprites/<id>.png. Where each came from:
# sprite-walker S-s3, sprite-floater S-s3, sprite-boss-body Tb6-avg-10sh-s1 (provisional);
# tower-sniper-side U-s1, tower-cannon-side U-s3, tower-sniper and tower-cannon the same
# drawings fitted to the pad (piece_gen.py --derive); tower-laser U-s3, tower-stasis U-s4;
# arm-walkers, arm-floaters, arm-swarm V-avg-10sh-stspriteboss-s1, arm-stump V-avg-10sh-s4
# (provisional). To use a new pick, copy its picture over the one here.


def picked(pid):
    """A picked sprite in levels, None see-through."""
    im = Image.open(os.path.join(SPRITES, pid + ".png")).convert("LA")
    return [[round(g / 17) if a >= 128 else None for g, a in (im.getpixel((x, y)) for x in range(im.width))] for y in range(im.height)]


turrets = {k: {"up": picked(f"tower-{k}"), "side": picked(f"tower-{k}-side")} for k in ("sniper", "cannon")}
posts = {k: picked(f"tower-{k}") for k in ("laser", "stasis")}


# The walker's body (an ellipse over its shell) and the hip each leg turns about.
BODY = (9.5, 9.0, 6.5, 7.0)
HIPS = {(-1, -1): (5.0, 5.0), (1, -1): (14.0, 5.0), (-1, 1): (5.0, 14.0), (1, 1): (14.0, 14.0)}
SWING = 22   # degrees each leg swings from the drawing, forward or back


def stride(a, p):
    """A walk pose from one drawing: every leg (what lies outside the body) turns about
    its hip, front-left and back-right forward (feet up the picture, the way it walks)
    when p is 1 and the other pair back, the opposite way when p is -1. Klein drew each
    pose's legs differently, which flickered; a pixel's shift barely showed."""
    cx, cy, rx, ry = BODY
    inside = lambda x, y: math.hypot((x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry) <= 1
    quad = lambda x, y: (1 if x + 0.5 > cx else -1, 1 if y + 0.5 > cy else -1)
    out = [[v if inside(x, y) else None for x, v in enumerate(row)] for y, row in enumerate(a)]
    for y in range(N):
        for x in range(N):
            if inside(x, y): continue
            q = quad(x, y)
            hx, hy = HIPS[q]
            # forward when the pair's turn is p: clockwise moves a left foot up, a right one down
            t = math.radians(-q[0] * SWING * (p if q[0] == q[1] else -p))
            dx, dy = x + 0.5 - hx, y + 0.5 - hy           # the drawing's pixel this one comes from
            sx, sy = hx + dx * math.cos(t) + dy * math.sin(t), hy - dx * math.sin(t) + dy * math.cos(t)
            ix, iy = math.floor(sx), math.floor(sy)
            if 0 <= ix < N and 0 <= iy < N and a[iy][ix] is not None and not inside(ix, iy) and quad(ix, iy) == q:
                out[y][x] = a[iy][ix]
    return out


def outline(a):
    """A black pixel all round the sprite (diagonals too), inside its own box."""
    h, w = len(a), len(a[0])
    on = lambda x, y: 0 <= x < w and 0 <= y < h and a[y][x] is not None
    return [[v if v is not None else (0 if any(on(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)) else None)
             for x, v in enumerate(row)] for y, row in enumerate(a)]


walker = picked("sprite-walker")
walk = [outline(stride(walker, 1)), outline(walker), outline(stride(walker, -1))]
float_ = picked("sprite-floater")

# The floater's shield doesn't show (the user dropped its ○ ring after it never read
# right on the glasses): no disc under the sprite any more.


def shadow(h):
    """Under a floater h px up: its own outline moved h px down and right, where the
    floater isn't. Never turned (the light comes from one side)."""
    on = lambda x, y: 0 <= x < N and 0 <= y < N and float_[y][x] is not None
    return [[1 if on(x - h, y - h) and not on(x, y) else None for x in range(N)] for y in range(N)]


shadows = [shadow(h) for h in (1, 2, 3)]
float_ = outline(float_)

boss = outline(picked("sprite-boss-body"))
arms = {k: outline(picked(f"arm-{k}")) for k in ("walkers", "floaters", "swarm", "stump")}


# --- the phone's guide -----------------------------------------------------------

# The sprites enlarged for the phone page (public/ is served as is).
GUIDE = os.path.join(ROOT, "public", "guide")
os.makedirs(GUIDE, exist_ok=True)
for name, rows, z in (("walker", walker, 8), ("floater", float_, 8), ("boss", boss, 2), ("sniper", turrets["sniper"]["up"], 4),
                      ("cannon", turrets["cannon"]["up"], 4), ("laser", posts["laser"], 6), ("stasis", posts["stasis"], 6)):
    h, w = len(rows), len(rows[0])
    im = Image.new("LA", (w, h), (0, 0))
    for y, row in enumerate(rows):
        for x, v in enumerate(row):
            if v is not None: im.putpixel((x, y), (v * 17, 255))
    im.resize((w * z, h * z), Image.NEAREST).save(os.path.join(GUIDE, f"{name}.png"), optimize=True)


# --- output ----------------------------------------------------------------------

def block(rows, indent):
    return [indent + f'"{r}",' for r in rows]


def record(name, doc, items, keys):
    out = [f"/** {doc} */", f"export const {name}: Record<{' | '.join(repr(k).replace(chr(39), chr(34)) for k in keys)}, string[]> = {{"]
    for k, rows in items.items():
        out.append(f"    {k}: [")
        out += block(hexrows(rows), "        ")
        out.append("    ],")
    return out + ["};", ""]


def frames(name, doc, fs):
    out = [f"/** {doc} */", f"export const {name}: string[][] = ["]
    for f in fs:
        out += ["    ["] + block(hexrows(f), "        ") + ["    ],"]
    return out + ["];", ""]


ts = ["// Generated by tools/import_sprites.py from art/. Do not edit.",
      "// One hex digit per pixel (display level 0-15), '.' see-through. Everything faces up.", ""]
ts += frames("WALKER", "The walking drone's three trot poses, 20x20. Played 0, 1, 2, 1 cell by cell.", walk)
ts += ["/** The floating drone, 20x20 (its shield doesn't show). */", "export const FLOATER: string[] = ["]
ts += block(hexrows(float_), "    ") + ["];", ""]
ts += frames("SHADOWS", "Its shadow at three heights (1-3 px), played 0, 1, 2, 1 so it bobs. Never turned.", shadows)
ts += record("POSTS", "Tripline posts, 24x24, emitter at the top: the game turns it to face the road.", posts, ("laser", "stasis"))
ts += ["/** Turrets at a pad's 45x47, barrels on the lanes: facing up and facing right. Drawn as they are, a half turn for down and left. */",
       'export const TURRET_ART: Record<"sniper" | "cannon", { up: string[]; side: string[] }> = {']
for k, v in turrets.items():
    ts.append(f"    {k}: {{")
    for f in ("up", "side"): ts += [f"        {f}: ["] + block(hexrows(v[f]), "            ") + ["        ],"]
    ts.append("    },")
ts += ["};", ""]
ts += [f"/** The mother drone's body, {len(boss[0])}x{len(boss)} (its 5x5 cells): hull, four legs, an arm socket on each side. Drawn as it is. */", "export const BOSS: string[] = ["]
ts += block(hexrows(boss), "    ") + ["];", ""]
ts += record("ARMS", "The boss's arms and a destroyed arm's stump, 32x22, pointing right (the collar on the left goes under the hull): the game turns each to its socket.",
             arms, ("walkers", "floaters", "swarm", "stump"))
with open(os.path.join(ROOT, "src", "sprites.ts"), "w") as fh:
    fh.write("\n".join(ts))


# --- preview ---------------------------------------------------------------------

Z = 6
small = walk + [float_] + shadows + list(posts.values())
im = Image.new("L", (len(small) * (POST * Z + 6) + 6, POST * Z + 12 + 47 * 3 + 6), 3 * 17)
for i, s in enumerate(small):
    for y, row in enumerate(s):
        for x, v in enumerate(row):
            if v is not None:
                im.paste(v * 17, (6 + i * (POST * Z + 6) + x * Z, 6 + y * Z, 6 + i * (POST * Z + 6) + (x + 1) * Z, 6 + (y + 1) * Z))
for i, rows in enumerate(f for t in turrets.values() for f in t.values()):
    t = Image.new("L", (len(rows[0]), len(rows)), 3 * 17)
    t.putdata([3 * 17 if v is None else v * 17 for row in rows for v in row])
    im.paste(t.resize((t.width * 3, t.height * 3), Image.NEAREST), (6 + i * (45 * 3 + 6), POST * Z + 12))
im.save(os.path.join(SPRITES, "preview.png"))
print("wrote src/sprites.ts and art/sprites/preview.png")
