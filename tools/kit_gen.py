"""Floors, road-wall kits and placed-wall kits from klein (docs/art.md;
the user chose to try klein before drawing them in code). Each kit is sketched in code as a
patch bigger than one picture (a floor 3x3 plates, a road wall four periods long, a placed
wall a run of four), given to klein's `reference` workflow with the couch as the style
reference like the pieces (tools/piece_gen.py), shrunk back to the patch's pixels, and cut
into the renderer's pictures. What must repeat is taken from the sketch, so the pictures
meet seamlessly whatever klein drew: a floor's seams round each plate, a road wall's cut
at a stripe's edge, a wall's posts.

    .venv/bin/python -I tools/kit_gen.py [--seeds 1,2,3,4] kit ...     (--seeds '' only sketches)

Per kit in art/work/kits/<kit>/: sketch.png (and its cut pictures, sketch-<part>.png), klein's input and arguments, raw/s<n>.png,
the cut pictures s<n>-<part>.png (grey = level x 17, as the art pack takes them) and
mock-s<n>.png: the kit laid as the renderer lays it (floor, a road band with its walls,
a placed wall), on the glasses' curve, beside the sketch's own mock-up; candidates.json for
the art library's map pages, where "use" puts a kit into the pack as the map's own.
"""
import bisect
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import grid_snap               # noqa: E402
import piece_sketches as ps    # noqa: E402

OUT = os.path.join(ps.WORK, "kits")
COUCH = os.path.join(ROOT, "art", "reference", "couch-s1.png")
TW, TH = 25, 27                # a floor tile: a cell and the gaps right of it and below it
D = 7                          # road walls' depth
STYLE = ("Pixel art on a {w}x{h} pixel grid, every pixel one big square block, hard edges, no anti-aliasing, a few flat grey shades. "
         "Top-down view from a camera directly overhead, like a top-down 2D game map, no perspective. Light from directly above, no cast shadows. "
         "The same style as the second image. Follow the first image exactly: every seam, line, stripe and part keeps its size, place and shade; "
         "add only fine surface texture and soft shading inside the shapes. {what}")


# --- sketches ------------------------------------------------------------------------------

def floor_patch(tile, panel=(1, 1), n=3):
    """`n` x `n` plates of `panel` cells, each cell's tile drawn by tile(g, x0, y0, i, j):
    (i, j) its place in the plate."""
    pw, ph = panel
    g = ps.Grid(TW * pw * n, TH * ph * n)
    for r in range(ph * n):
        for c in range(pw * n): tile(g, c * TW, r * TH, c % pw, r % ph, pw, ph)
    return g


def cb_plate(g, x0, y0, i, j, pw, ph):
    """Cargo Bay's steel deck, 2x2-cell plates: dark plate (3) with a raised tread of
    short lit 2 px bars (5), staggered, a dark seam (1) round each plate in the gaps with a
    lit lip (5) above and left of it, bright rivets (7) at the plate's corners."""
    for y in range(TH):
        for x in range(TW):
            X, Y = i * TW + x, j * TH + y                             # in the plate
            bar = (Y % 4 == 1 and (X // 4) % 2 == 0) or (Y % 4 == 3 and (X // 4) % 2 == 1)
            g.px[y0 + y][x0 + x] = 5 if bar and X % 4 < 2 else 3
    if i == pw - 1: g.rect(x0 + 22, y0, x0 + 22, y0 + TH - 1, 1); g.rect(x0 + 21, y0, x0 + 21, y0 + TH - 1, 2)
    if j == ph - 1: g.rect(x0, y0 + 23, x0 + TW - 1, y0 + 23, 1); g.rect(x0, y0 + 22, x0 + TW - 1, y0 + 22, 2)
    if i == 0: g.rect(x0, y0, x0, y0 + TH - 1, 5)
    if j == 0: g.rect(x0, y0, x0 + TW - 1, y0, 5)
    for cx, cy in ((x0 + 2 if i == 0 else None, y0 + 2 if j == 0 else None), (x0 + 18 if i == pw - 1 else None, y0 + 19 if j == ph - 1 else None),
                   (x0 + 2 if i == 0 else None, y0 + 19 if j == ph - 1 else None), (x0 + 18 if i == pw - 1 else None, y0 + 2 if j == 0 else None)):
        if cx is not None and cy is not None: g.rect(cx, cy, cx + 1, cy + 1, 7)


def hr_deck(g, x0, y0, i, j, pw, ph):
    """Hab Ring's deck, one panel a cell: a dark panel (2) with an inset middle (3) framed
    by a lit lip (4), a dark seam (1) in the gaps, two bolts (6)."""
    g.rect(x0, y0, x0 + TW - 1, y0 + TH - 1, 2)
    g.rect(x0 + 4, y0 + 4, x0 + 17, y0 + 18, 3); g.hline(x0 + 4, x0 + 17, y0 + 4, 4); g.vline(x0 + 4, y0 + 4, y0 + 18, 4)
    g.rect(x0 + 22, y0, x0 + 22, y0 + TH - 1, 1); g.rect(x0, y0 + 23, x0 + TW - 1, y0 + 23, 1)
    g.rect(x0 + 1, y0 + 1, x0 + 2, y0 + 2, 6); g.rect(x0 + 19, y0 + 20, x0 + 20, y0 + 21, 6)


def cb_barrier(period=24):
    """Cargo Bay's road wall, four periods: a crash barrier, row 0 by the road: a dark foot,
    the barrier's face in bold stripes (6 px, 13 against 2), a lit top, its back in shadow."""
    g = ps.Grid(period * 4, D)
    for x in range(g.w):
        for d in range(D):
            g.px[d][x] = 4 if d == 0 else 3 if d == D - 1 else 11 if d == D - 2 else (13 if (x // 6) % 2 == 0 else 2)
    return g


def hr_bulkhead(period=25):
    """Hab Ring's road wall, four periods: a panelled bulkhead, row 0 by the road: a dark
    foot, panels (8) with a bright light strip (14) along them, a dark seam between panels
    every period, a lit top, its back in shadow."""
    g = ps.Grid(period * 4, D)
    for x in range(g.w):
        for d in range(D):
            g.px[d][x] = 3 if d == 0 else 2 if d == D - 1 else 11 if d == D - 2 else 14 if d == 2 else 8
        if x % period in (0, 1): g.rect(x, 1, x, D - 3, 3)
    return g


def wall_run(post, rail, n=4):
    """A placed wall: posts (5x7) and rails (20x7) in a run of `n` rails."""
    g = ps.Grid(5 + 25 * n, 7)
    for k in range(n + 1): post(g, 25 * k)
    for k in range(n): rail(g, 25 * k + 5)
    return g


def cb_fence_post(g, x0):
    g.rect(x0, 0, x0 + 4, 6, 11); g.hline(x0, x0 + 4, 0, 13); g.rect(x0 + 1, 2, x0 + 3, 4, 6); g.hline(x0, x0 + 4, 6, 4)


def cb_fence_rail(g, x0):
    """A steel fence: two lit rails (rows 1 and 5) with dark mesh between."""
    g.rect(x0, 2, x0 + 19, 4, 3)
    for x in range(x0, x0 + 20, 2): g.rect(x, 2, x, 4, 6)
    g.hline(x0, x0 + 19, 1, 12); g.hline(x0, x0 + 19, 5, 9)


def hr_wall_post(g, x0):
    g.rect(x0, 0, x0 + 4, 6, 10); g.hline(x0, x0 + 4, 0, 12); g.rect(x0 + 1, 3, x0 + 3, 3, 4)


def hr_wall_rail(g, x0):
    """A panel wall: a lit top, a panel with a bright light strip, a dark base."""
    g.rect(x0, 0, x0 + 19, 6, 8); g.hline(x0, x0 + 19, 0, 11); g.rect(x0, 3, x0 + 19, 3, 14); g.rect(x0, 5, x0 + 19, 6, 4)


def tiled(period, draw, n=4):
    """A road wall `n` periods long, one period drawn by draw(g) on a period-wide grid (so
    shapes that cross its ends repeat exactly)."""
    one = ps.Grid(period, D); draw(one)
    g = ps.Grid(period * n, D)
    g.px = [row * n for row in one.px]
    return g


def cell_hash(x0, y0, k=0):
    return ((x0 // TW) * 73 + (y0 // TH) * 151 + k * 37) % 997


# Regolith Mine: rough rock, a rock face, rock-filled steel cages.

def rm_rock(g, x0, y0, i, j, pw, ph):
    """Regolith Mine's floor, the moon's rock: dark rock (2), a few darker cracks (1) and
    pebbles (2-3 px, lit 4-5 on a dark foot), placed differently in every cell; the gaps
    plain rock, so cells meet without a seam."""
    g.rect(x0, y0, x0 + TW - 1, y0 + TH - 1, 2)
    h = cell_hash(x0, y0)
    for k in range(3):                                                # pebbles
        px_, py = x0 + 2 + (h * (k + 3) + k * 7) % 15, y0 + 2 + (h * (k + 5) + k * 11) % 16
        g.rect(px_, py + 1, px_ + 2, py + 2, 1); g.rect(px_, py, px_ + 1, py + 1, 5 if k else 4)
    if h % 2:                                                         # a crack
        cx, cy = x0 + 3 + h % 9, y0 + 4 + h % 7
        for t in range(9): g.set(cx + t, cy + (t * (1 if h % 4 == 1 else -1)) // 3, 1)


def rm_face(g):
    """Regolith Mine's road wall, a rough rock face, row 0 by the road: rocks of several
    sizes (bodies 6-8, lit faces 11, dark gaps 2), a dark foot by the road."""
    g.rect(0, 0, g.w - 1, D - 1, 3)
    for cx, cy, rx, ry, v in ((3, 3, 4.4, 3.2, 7), (11, 4, 4.8, 3.4, 6), (19, 3, 4.2, 3.0, 8), (25 + 3, 3, 4.4, 3.2, 7)):
        g.blob(cx, cy, rx, ry, 0, 2); g.blob(cx, cy, rx - 1, ry - 1, 0, v); g.blob(cx - 1, cy + 1, rx * 0.5, ry * 0.4, 0, 11)
    g.hline(0, g.w - 1, 0, 2)


def rm_cage_post(g, x0):
    g.rect(x0, 0, x0 + 4, 6, 12); g.hline(x0, x0 + 4, 0, 14); g.rect(x0 + 1, 2, x0 + 3, 4, 7)


def rm_cage_rail(g, x0):
    """A gabion: a steel cage (lit frame 10) full of rocks (lit 8-11 on dark 2)."""
    g.rect(x0, 0, x0 + 19, 6, 2)
    for k, (cx, v) in enumerate(((3, 8), (8, 11), (13, 7), (17, 10))):
        g.rect(x0 + cx - 2, 2 + k % 2, x0 + cx + 1, 4 + k % 2, v)
    g.hline(x0, x0 + 19, 0, 10); g.hline(x0, x0 + 19, 6, 6)


# Reactor: steel grating, a run of coolant pipes, a safety rail.

def re_grate(g, x0, y0, i, j, pw, ph):
    """Reactor's floor, 2x1-cell grating plates: lit bars (5) over dark slots (1, 2 px), a
    frame (4) round the plate, a dark seam (1) in the gaps, bolts (7) at its corners."""
    for y in range(TH):
        for x in range(TW):
            X = i * TW + x
            g.px[y0 + y][x0 + x] = 1 if (X % 4 >= 2 and 3 <= y <= 18) else 5
    g.rect(x0, y0, x0 + TW - 1, y0 + 2, 4); g.rect(x0, y0 + 19, x0 + TW - 1, y0 + 21, 4)
    if i == 0: g.rect(x0, y0, x0 + 2, y0 + 21, 4); g.rect(x0, y0 + 1, x0 + 1, y0 + 2, 7); g.rect(x0, y0 + 19, x0 + 1, y0 + 20, 7)
    if i == pw - 1:
        g.rect(x0 + 18, y0, x0 + 21, y0 + 21, 4); g.rect(x0 + 19, y0 + 1, x0 + 20, y0 + 2, 7); g.rect(x0 + 19, y0 + 19, x0 + 20, y0 + 20, 7)
        g.rect(x0 + 22, y0, x0 + TW - 1, y0 + TH - 1, 1)
    g.rect(x0, y0 + 22, x0 + TW - 1, y0 + TH - 1, 1)


def re_pipes(g):
    """Reactor's road wall, two coolant pipes along the road, row 0 by the road: a dark foot,
    a thin pipe (lit 12 over 8), a dark gap, a fat pipe (13 over 9 over 6), bright flange
    rings across both once a period."""
    for x in range(g.w):
        for d, v in enumerate((2, 12, 8, 3, 13, 9, 6)): g.px[d][x] = v
    g.rect(10, 1, 11, 6, 14); g.vline(12, 1, 6, 4)


def re_rail_post(g, x0):
    g.rect(x0, 0, x0 + 4, 6, 11); g.hline(x0, x0 + 4, 0, 14); g.rect(x0 + 1, 2, x0 + 3, 4, 5)


def re_rail_rail(g, x0):
    """A safety rail: a lit top rail, a kick plate in bold hazard stripes (13 against 2)."""
    g.hline(x0, x0 + 19, 0, 12); g.hline(x0, x0 + 19, 1, 4)
    for x in range(20):
        for y in range(2, 6): g.set(x0 + x, y, 13 if ((x + y) // 3) % 2 == 0 else 2)
    g.hline(x0, x0 + 19, 6, 4)


# Hydroponics: wet tiles, glass with an irrigation pipe, a trellis of leaves.

def hy_tile(g, x0, y0, i, j, pw, ph):
    """Hydroponics' floor, wet tiles: four dark tiles (3) a cell with lit edges (5) and dark
    joints (1), a dark seam in the gaps; a drain (a dark ring round 4) in some cells."""
    g.rect(x0, y0, x0 + TW - 1, y0 + TH - 1, 1)
    for tx, ty in ((0, 0), (11, 0), (0, 11), (11, 11)):
        g.rect(x0 + tx, y0 + ty, x0 + tx + 9, y0 + ty + 9, 3); g.hline(x0 + tx, x0 + tx + 9, y0 + ty, 5)
    if cell_hash(x0, y0) % 3 == 0:
        g.rect(x0 + 7, y0 + 7, x0 + 13, y0 + 13, 1); g.rect(x0 + 8, y0 + 8, x0 + 12, y0 + 12, 4); g.rect(x0 + 10, y0 + 8, x0 + 10, y0 + 12, 1)


def hy_glass(g):
    """Hydroponics' road wall, a glass screen, row 0 by the road: a dark foot, dark glass (4)
    with a bright diagonal glint, a frame bar (11) between panes once a period, a lit top,
    the irrigation pipe (8) behind it."""
    for x in range(g.w):
        for d, v in enumerate((3, 4, 4, 4, 4, 12, 8)): g.px[d][x] = v
    for k in range(4): g.rect(6 + k, 4 - k, 7 + k, 4 - k, 13)
    g.rect(0, 1, 1, 5, 11)


def hy_trellis_post(g, x0):
    g.rect(x0, 0, x0 + 4, 6, 9); g.hline(x0, x0 + 4, 0, 12); g.rect(x0 + 2, 1, x0 + 2, 5, 4)


def hy_trellis_rail(g, x0):
    """A trellis: a dark trough (4) along the bottom, leaf clumps (lit 12, 9) climbing a dark
    mesh (2) above it."""
    g.rect(x0, 0, x0 + 19, 5, 2); g.hline(x0, x0 + 19, 6, 5)
    for cx, cy, v in ((3, 2, 12), (8, 3, 9), (13, 2, 12), (17, 3, 9)):
        g.rect(x0 + cx - 1, cy - 1, x0 + cx + 1, cy + 1, v); g.set(x0 + cx, cy - 2, v)


# The Airlock: chevron tread plates, a blast wall in hazard stripes, a cable run.

def al_plate(g, x0, y0, i, j, pw, ph):
    """The Airlock's floor, heavy plates one a cell: a dark plate (2) with chevrons of 2 px
    tread (4), a lit lip (5) on its top and left, bolts (6), a dark seam (1) in the gaps."""
    g.rect(x0, y0, x0 + TW - 1, y0 + TH - 1, 2)
    for y in range(3, 19):
        for x in range(2, 20):
            if (x + abs(y - 10)) % 6 < 2 and x % 10 < 8: g.set(x0 + x, y0 + y, 4)
    g.hline(x0, x0 + 21, y0, 5); g.vline(x0, y0, y0 + 21, 5)
    g.rect(x0 + 22, y0, x0 + TW - 1, y0 + TH - 1, 1); g.rect(x0, y0 + 22, x0 + TW - 1, y0 + TH - 1, 1)
    for bx, by in ((2, 2), (18, 2), (2, 19), (18, 19)): g.rect(x0 + bx, y0 + by, x0 + bx + 1, y0 + by + 1, 6)


def al_blast(g):
    """The Airlock's road wall, a blast wall, row 0 by the road: a dark foot, bold diagonal
    hazard stripes (13 against 3), a dark band, a lit top, its back in shadow."""
    for x in range(g.w):
        for d in range(D):
            g.px[d][x] = 2 if d == 0 else 4 if d == 4 else 12 if d == 5 else 3 if d == 6 else (13 if ((x + d) // 6) % 2 == 0 else 3)


def al_cable_post(g, x0):
    g.rect(x0, 0, x0 + 4, 6, 10); g.hline(x0, x0 + 4, 0, 13); g.rect(x0 + 1, 1, x0 + 3, 5, 5)


def al_cable_rail(g, x0):
    """A cable run: three thick cables (lit 12, 7, 10, dark gaps 2) bound by bright ties."""
    for y, v in ((0, 2), (1, 12), (2, 2), (3, 7), (4, 2), (5, 10), (6, 3)): g.hline(x0, x0 + 19, y, v)
    for x in (6, 15): g.rect(x0 + x, 0, x0 + x + 1, 6, 14)


# kit: (map, kind, sketch, details, what)
KITS = {
    "cb-plate": ("cargo-bay", "floor", lambda: floor_patch(cb_plate, (2, 2)), {"panel": (2, 2)},
                 "Seamless steel deck floor plates of a cargo bay seen straight down, each plate framed by a dark seam with rivets at its corners, a worn diamond tread across it."),
    "hr-deck": ("hab-ring", "floor", lambda: floor_patch(hr_deck, (1, 1), 4), {"panel": (1, 1)},
                "Seamless square deck panels of a space station's living quarters seen straight down, each with an inset middle, two bolts and dark seams between."),
    "cb-barrier": ("cargo-bay", "road", cb_barrier, {"period": 24},
                   "A long yellow-and-black striped steel crash barrier lying left to right, seen straight down: bold diagonal stripes on its face, a lit top edge."),
    "hr-bulkhead": ("hab-ring", "road", hr_bulkhead, {"period": 25},
                    "A long corridor bulkhead wall lying left to right seen straight down: metal panels with a bright light strip along them, dark seams between panels, a lit top edge."),
    "cb-fence": ("cargo-bay", "wall", lambda: wall_run(cb_fence_post, cb_fence_rail), {},
                 "A steel mesh fence lying left to right seen straight down: square posts, two lit rails with dark mesh between."),
    "hr-panel": ("hab-ring", "wall", lambda: wall_run(hr_wall_post, hr_wall_rail), {},
                 "A low interior panel wall lying left to right seen straight down: square pillars, panels with a bright light strip along them."),
    "rm-rock": ("regolith-mine", "floor", lambda: floor_patch(rm_rock, (1, 1), 4), {"panel": (1, 1), "spread": True, "seams": False},
                "Seamless rough moon rock floor of a mine seen straight down: dark grey stone with small pebbles and thin cracks."),
    "rm-face": ("regolith-mine", "road", lambda: tiled(25, rm_face), {"period": 25},
                "A rough rock face of a mine tunnel lying left to right seen straight down: rocks of several sizes with lit tops and dark gaps between."),
    "rm-cage": ("regolith-mine", "wall", lambda: wall_run(rm_cage_post, rm_cage_rail), {},
                "A low wall of steel cages filled with rocks lying left to right seen straight down: bright steel posts, rocks inside a steel frame."),
    "re-grate": ("reactor", "floor", lambda: floor_patch(re_grate, (2, 1)), {"panel": (2, 1)},
                 "Seamless steel floor grating plates of a reactor deck seen straight down: lit bars over dark slots, a frame and bolts round each plate, dark seams."),
    "re-pipes": ("reactor", "road", lambda: tiled(25, re_pipes), {"period": 25},
                 "Two coolant pipes lying left to right side by side seen straight down: a thin pipe and a fat pipe, shaded round, bright bolted flange rings across them."),
    "re-rail": ("reactor", "wall", lambda: wall_run(re_rail_post, re_rail_rail), {},
                "A steel safety railing lying left to right seen straight down: square posts, a lit top rail, a kick plate with bold hazard stripes."),
    "hy-tile": ("hydroponics", "floor", lambda: floor_patch(hy_tile, (1, 1), 4), {"panel": (1, 1), "spread": True},
                "Seamless wet square floor tiles of a hydroponics farm seen straight down: dark tiles with lit edges, dark joints, round floor drains."),
    "hy-glass": ("hydroponics", "road", lambda: tiled(25, hy_glass), {"period": 25},
                 "A long glass screen wall lying left to right seen straight down: dark glass panes with bright glints, frame bars between panes, a pipe behind it."),
    "hy-trellis": ("hydroponics", "wall", lambda: wall_run(hy_trellis_post, hy_trellis_rail), {},
                   "A low plant trellis lying left to right seen straight down: posts, leafy vines climbing a mesh above a trough."),
    "al-plate": ("airlock", "floor", lambda: floor_patch(al_plate, (1, 1), 4), {"panel": (1, 1)},
                 "Seamless heavy steel floor plates of an airlock seen straight down: chevron tread, a lit lip, four bolts each, dark seams."),
    "al-blast": ("airlock", "road", lambda: tiled(24, al_blast), {"period": 24},
                 "A heavy blast wall lying left to right seen straight down: bold diagonal yellow-and-black hazard stripes on its face, a lit top edge."),
    "al-cable": ("airlock", "wall", lambda: wall_run(al_cable_post, al_cable_rail), {},
                 "A run of thick power cables lying left to right seen straight down: three cables bound by bright ties, clamps at the ends."),
}


# --- generating and cutting ------------------------------------------------------------------

def to_levels(grid_im, sketch, box, spread=False):
    """klein's picture (the sketch's area, opaque) shrunk to `box` by detail-preserving
    downscaling, its greys put on the sketch's own levels by rank (a floor drawn in 1-5
    stays a dark floor whatever klein's brightness). With `spread` they go evenly over the
    sketch's range of levels instead (its median grey to the sketch's main level, its 2nd
    and 98th percentile greys to the sketch's lowest and highest level): for a sketch that is nearly all one level (the rock floor), whose own
    mix would flatten everything klein added back to that level."""
    greys = grid_snap.detail_preserving(grid_im.convert("L").convert("LA"), box, 1.0)
    vals = sorted(v for row in greys for v in row)
    lv = sorted(v for row in sketch.px for v in row if v is not None)
    if spread:
        g0, gm, g1 = vals[len(vals) // 50], vals[len(vals) // 2], vals[-len(vals) // 50 - 1]
        l0, lm, l1 = lv[0], lv[len(lv) // 2], lv[-1]

        def lin(v):          # median grey to the sketch's main level, the tails out to its ends
            t = (v - gm) / max(1, (gm - g0) if v < gm else (g1 - gm))
            return max(l0, min(l1, round(lm + t * ((lm - l0) if v < gm else (l1 - lm)))))
        return [[lin(v) for v in row] for row in greys]

    def level(v):            # the sketch's level at this grey's rank (quantile matching)
        i = (bisect.bisect_left(vals, v) + bisect.bisect_right(vals, v)) // 2
        return lv[min(len(lv) - 1, i * len(lv) // len(vals))]
    return [[level(v) for v in row] for row in greys]


def cut_floor(px, sketch, det):
    """A plate's tiles from the middle plate of the n x n patch, row by row (one-cell plates:
    the middle four, as variants); the seam band round each plate (the last 5 columns and
    7 rows of its last cells: the gaps) taken from the sketch, so plates meet seamlessly,
    unless the kit has `seams` off (a floor with no seams, the rock: all klein's)."""
    pw, ph = det["panel"]
    n = len(px[0]) // (TW * pw)
    X0, Y0 = (n // 2) * TW * pw, (n // 2) * TH * ph
    one = pw * ph == 1
    if one: X0, Y0, pw, ph = X0 - TW, Y0 - TH, 2, 2              # one-cell plates: the middle four as variants
    tiles = []
    for j in range(ph):
        for i in range(pw):
            t = ps.Grid(TW, TH)
            for y in range(TH):
                for x in range(TW):
                    X, Y = X0 + i * TW + x, Y0 + j * TH + y
                    seam = det.get("seams", True) and (((i == pw - 1 or one) and x >= 20) or ((j == ph - 1 or one) and y >= 20))
                    t.px[y][x] = sketch.px[Y][X] if seam else px[Y][X]
            tiles.append(t)
    return {f"tile{k}": t for k, t in enumerate(tiles)}


def cut_road(px, sketch, det):
    """One period of the strip from its middle, cut where a period starts (a stripe's or a
    panel's edge, so the repeat hides the cut); the corner from each depth row's middle
    level, as the placeholder kit's corner is drawn."""
    P = det["period"]
    strip = ps.Grid(P, D)
    strip.px = [row[P:2 * P] for row in px]
    prof = [sorted(row)[len(row) // 2] for row in strip.px]
    corner = ps.Grid(D, D)
    corner.px = [[prof[max(x, y)] for x in range(D)] for y in range(D)]
    return {"strip": strip, "corner": corner}


def cut_wall(px, sketch, det):
    """A rail from the run's middle (h), the post between two rails (node), and v the rail
    turned to run down the screen, its middle 5 columns."""
    h = ps.Grid(20, 7); h.px = [row[55:75] for row in px]
    node = ps.Grid(5, 7); node.px = [row[50:55] for row in px]
    v = ps.Grid(5, 20); v.px = [[h.px[1 + x][19 - y] for x in range(5)] for y in range(20)]
    return {"h": h, "v": v, "node": node}


CUT = {"floor": cut_floor, "road": cut_road, "wall": cut_wall}


# --- the mock-up ---------------------------------------------------------------------------

def green(v):
    k = 0 if v is None or v <= 0 else round(255 * (v / 15) ** 0.55); return (k * 22 // 100, k, k * 22 // 100)


def mock(parts, kind, det, path, Z=4):
    """The kit as the renderer lays it, at x`Z`: a floor 6x4 cells; a road wall along both
    sides of a road band, a corner round its end; a placed wall across three cells."""
    W, H = 6 * TW, 4 * TH
    px = [[1] * W for _ in range(H)]
    if kind == "floor":
        pw, ph = det["panel"]
        tiles = [parts[k] for k in sorted(parts)]
        for r in range(4):
            for c in range(6):
                t = tiles[(r % ph) * pw + (c % pw)] if pw * ph > 1 else tiles[(r * 7 + c * 13) % len(tiles)]
                for y in range(TH):
                    for x in range(TW): px[r * TH + y][c * TW + x] = t.px[y][x]
    if kind == "road":
        s, cor = parts["strip"], parts["corner"]
        y0, y1, xe = 2 * TH - 7, 3 * TH, 4 * TW            # the band: rows y0..y1-1, x 0..xe-1
        for y in range(H):
            for x in range(W):
                if y0 <= y < y1 and x < xe: px[y][x] = 3; continue
                dy = y0 - y if y < y0 else y - y1 + 1 if y >= y1 else 0
                dx = x - xe + 1 if x >= xe else 0
                if dx == 0 and 1 <= dy <= D: px[y][x] = s.px[dy - 1][x % s.w]
                elif dy == 0 and 1 <= dx <= D: px[y][x] = s.px[dx - 1][y % s.w]
                elif 1 <= dx <= D and 1 <= dy <= D: px[y][x] = cor.px[dy - 1][dx - 1]
    if kind == "wall":
        h, v, node = parts["h"], parts["v"], parts["node"]
        def blit(p, X, Y):
            for y, row in enumerate(p.px):
                for x, val in enumerate(row):
                    if val is not None and 0 <= Y + y < H and 0 <= X + x < W: px[Y + y][X + x] = val
        for c in range(1, 4): blit(h, c * TW, 1 * TH + 20)
        for r in range(2, 4): blit(v, 3 * TW + 20, r * TH)
        for c in range(1, 4): blit(node, c * TW - 5, 1 * TH + 20)
        for r in (1, 2, 3): blit(node, 3 * TW + 20, r * TH + 20)
    im = Image.new("RGB", (W * Z, H * Z)); d = ImageDraw.Draw(im)
    for y in range(H):
        for x in range(W): d.rectangle([x * Z, y * Z, x * Z + Z - 1, y * Z + Z - 1], fill=green(px[y][x]))
    im.save(path)


def canvas(g):
    b = 16
    while g.w * b > 1024 or g.h * b > 1024: b -= 1
    W, H = max(256, -(-g.w * b // 16) * 16), max(256, -(-g.h * b // 16) * 16)
    ox, oy = (W - g.w * b) // 2, (H - g.h * b) // 2
    im = Image.new("L", (W, H), 0)
    sk = g.image(b)
    im.paste(sk.getchannel("L"), (ox, oy), sk.getchannel("A"))
    return im, b, (ox, oy)


def generate(kit, seeds):
    _, kind, make, det, what = KITS[kit]
    sketch = make()
    out = os.path.join(OUT, kit); raw = os.path.join(out, "raw")
    os.makedirs(raw, exist_ok=True)
    sketch.image().save(os.path.join(out, "sketch.png"))
    parts = CUT[kind]([row[:] for row in sketch.px], sketch, det)
    for name, p in parts.items(): p.image().save(os.path.join(out, f"sketch-{name}.png"))
    mock(parts, kind, det, os.path.join(out, "mock-sketch.png"))
    cands = {"sketch": {"label": "sketch", "parts": {n: f"sketch-{n}.png" for n in parts}}}
    write_candidates(kit, cands)                      # what's made so far, should a seed hang
    im, b, (ox, oy) = canvas(sketch)
    inp = os.path.join(out, "input.png"); im.save(inp)
    for seed in seeds:
        png = os.path.join(raw, f"s{seed}.png")
        if not os.path.exists(png):
            args = {"prompt": STYLE.format(w=sketch.w, h=sketch.h, what=what), "workflow": "reference",
                    "init_image": {"path": inp}, "reference_images": [{"path": COUCH}],
                    "width": im.width, "height": im.height, "seed": seed}
            json.dump(args, open(os.path.join(raw, f"s{seed}.json"), "w"), indent=1)
            r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "studio_gen.py"), os.path.join(raw, f"s{seed}.json"), png,
                                "--timeout", "150"], capture_output=True, text=True)
            if r.returncode:
                print(f"  {kit} s{seed}: generation failed ({r.returncode}) {r.stderr[-200:]}"); continue
        area = Image.open(png).crop((ox, oy, ox + sketch.w * b, oy + sketch.h * b))
        px = to_levels(area, sketch, (sketch.w, sketch.h), det.get("spread", False))
        parts = CUT[kind](px, sketch, det)
        for name, p in parts.items(): p.image().save(os.path.join(out, f"s{seed}-{name}.png"))
        mock(parts, kind, det, os.path.join(out, f"mock-s{seed}.png"))
        cands[f"s{seed}"] = {"label": f"seed {seed}", "raw": f"raw/s{seed}.png", "parts": {n: f"s{seed}-{n}.png" for n in parts}}
        print(f"  {kit} s{seed}: {', '.join(parts)}")
    write_candidates(kit, cands)


def write_candidates(kit, cands):
    """candidates.json for the art library: the kit's map, kind and details, and each
    candidate's parts (the sketch's own first)."""
    m, kind, _, det, what = KITS[kit]
    path = os.path.join(OUT, kit, "candidates.json")
    if os.path.exists(path): cands = json.load(open(path))["candidates"] | cands   # a rerun of some seeds keeps the others
    json.dump({"kit": {"map": m, "kind": kind, **det, "what": what}, "candidates": cands}, open(path, "w"), indent=1)


if __name__ == "__main__":
    args, seeds = sys.argv[1:], [1, 2, 3, 4]
    if "--seeds" in args: i = args.index("--seeds"); seeds = [int(s) for s in args[i + 1].split(",") if s]; del args[i:i + 2]
    for kit in args or list(KITS):
        print(kit)
        generate(kit, seeds)
