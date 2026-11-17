"""House-view sketches (docs/art.md, "House style"): each piece drawn in levels
on its exact display pixels, the layout and the parts that must survive, for klein's
`reference` workflow (tools/piece_gen.py) and as a candidate itself.

    .venv/bin/python -I tools/piece_sketches.py [id ...]    # art/work/<id>/sketch.png, art/work/sketches.png

The house view: almost straight down, a slight tilt toward the viewer. Top surfaces fill
the piece at their real depth (20 px a metre); the front shows as a strip along the
bottom edge, 3 px per metre of height. Light from directly above, no cast shadows, no
outlines. Values: silhouette edge 5+, surfaces mostly 7-10, seams 2-3 darker; the
material palettes below are where a sketch starts, and any level 1-14 may be used. Every sketch faces down the screen (its front strip at the bottom); the game turns it.

A piece that joins in a row is sketched as one cell: `row_from_single` builds the bank
from it (side edges cut where neighbours meet, the piece's rim carried across the
gaps with a seam two levels darker), seamless by construction. Tried on the lockers
(2026-10-30, art/work/locker-rows.png): a sketched row of three, cut at the cell lines
(`cut_row`), came back from klein as three boxes with dark gaps or mismatched ends, even
with lighter seams in the sketch. The locker keeps its three-locker sketch for the seeds
made from it; its single form is `--form single`.
"""
import math
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "art", "work")

# Material palettes (house style rule 9): hints for where each material sits, dark to light.
# A sketch starts from them and may use any level 1-14; the generated piece keeps its own greys.
METAL = (5, 7, 9, 11)
FABRIC = (5, 7, 9, 10)
PLASTIC = (5, 8, 10, 12)
COMPOSITE = (5, 7, 9, 11)
SCREEN = (2, 3, 11, 12)
PX_PER_M = 3          # front strip per metre of height


def footprint(cells):
    """Display pixels of a footprint: 20 a cell, 5 between cells across, 7 down."""
    w, h = cells
    return 20 * w + 5 * (w - 1), 20 * h + 7 * (h - 1)


class Grid:
    """A picture in levels, None see-through."""
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]

    def set(self, x, y, v):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h: self.px[y][x] = v

    def rect(self, x0, y0, x1, y1, v):
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1): self.set(x, y, v)
        return self

    def hline(self, x0, x1, y, v): return self.rect(x0, y, x1, y, v)

    def vline(self, x, y0, y1, v): return self.rect(x, y0, x, y1, v)

    def ellipse(self, cx, cy, rx, ry, v, inner=0.0):
        """Pixels whose centres lie inside the ellipse (and outside `inner` of it: a ring)."""
        for y in range(self.h):
            for x in range(self.w):
                d = math.hypot((x + 0.5 - cx) / rx, (y + 0.5 - cy) / ry)
                if inner <= d <= 1: self.px[y][x] = v
        return self

    def blob(self, cx, cy, rx, ry, angle, v):
        """A rotated ellipse (`angle` in degrees, 0 = rx along x): a leaf, a spoke."""
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        for y in range(self.h):
            for x in range(self.w):
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                u, w = dx * ca + dy * sa, -dx * sa + dy * ca
                if (u / rx) ** 2 + (w / ry) ** 2 <= 1: self.px[y][x] = v
        return self

    def cut_corners(self, x0, y0, x1, y1):
        """Round a box's corners by a pixel (house style rule 8)."""
        for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)): self.px[y][x] = None
        return self

    def crop(self, x0, x1):
        g = Grid(x1 - x0 + 1, self.h)
        g.px = [row[x0:x1 + 1] for row in self.px]
        return g

    def image(self, scale=1):
        """Greyscale + alpha, grey = level x 17 (the art pack's format), scaled by a whole block."""
        im = Image.new("LA", (self.w, self.h), (0, 0))
        for y, row in enumerate(self.px):
            for x, v in enumerate(row):
                if v is not None: im.putpixel((x, y), (v * 17, 255))
        return im.resize((self.w * scale, self.h * scale), Image.NEAREST) if scale > 1 else im

    def levels(self):
        return sorted({v for row in self.px for v in row if v is not None})


def front(height_m):
    """The front strip's rows for an object this tall (at least 1 for anything raised)."""
    return max(1, round(height_m * PX_PER_M)) if height_m > 0 else 0


# --- the pieces --------------------------------------------------------------------------

def couch():
    """The style anchor, the in-use Hab Ring couch (`couch-s1`) measured: 43x18 in a 45x20
    footprint, a backrest band along the top (6 rows) with a lit far lip, arms either side,
    two seat cushions split by a dark seam, soft highlights, a 2 px front strip (0.8 m)."""
    g = Grid(*footprint((2, 1)))
    lo, mid, body, top = FABRIC
    x0, x1, y0, y1 = 1, 43, 1, 18
    g.rect(x0, y0, x1, y1, mid)
    g.rect(x0 + 4, y0, x1 - 4, y0 + 5, body)                     # backrest
    g.hline(x0 + 4, x1 - 4, y0, top)                              # its lit far lip
    g.vline(22, y0, y0 + 5, lo)                                   # the backrest's seam
    g.hline(x0 + 4, x1 - 4, y0 + 6, lo)                           # backrest meets seat
    for a, b in ((x0 + 4, 21), (23, x1 - 4)):                    # seat cushions
        g.rect(a, y0 + 7, b, y1 - 3, body)
        g.rect(a + 2, y0 + 8, b - 3, y0 + 9, top)                 # soft highlight
    g.vline(22, y0 + 7, y1 - 2, lo)                               # the cushions' seam
    for a, b in ((x0, x0 + 3), (x1 - 3, x1)):                    # arms
        g.rect(a, y0 + 2, b, y1 - 2, body)
        g.hline(a, b, y0 + 2, top)
        g.rect(a, y1 - 1, b, y1, lo)                              # their fronts
    g.rect(x0 + 4, y1 - 1, x1 - 4, y1, lo)                        # the seat's front strip
    g.vline(x0 + 4, y0 + 6, y1, lo); g.vline(x1 - 4, y0 + 6, y1, lo)   # arms meet the seat
    return g.cut_corners(x0, y0 + 2, x1, y1)


def chair():
    """An armchair in the couch's style, one seat wide: a rounded backrest along the top,
    arms either side, one cushion with a soft highlight, a 2 px front strip."""
    g = Grid(20, 20)
    lo, mid, body, top = FABRIC
    g.rect(2, 2, 17, 18, mid)
    g.rect(5, 1, 14, 6, body); g.hline(6, 13, 1, top)             # backrest, its lit lip
    g.set(5, 1, None); g.set(14, 1, None)
    g.hline(5, 14, 7, lo)                                         # backrest meets seat
    g.rect(5, 8, 14, 16, body); g.rect(7, 9, 11, 10, top)         # cushion, highlight
    for a, b in ((2, 4), (15, 17)):                              # arms
        g.rect(a, 4, b, 16, body); g.hline(a, b, 4, top)
        g.rect(a, 17, b, 18, lo)
    g.rect(5, 17, 14, 18, lo)                                     # front strip
    g.vline(5, 7, 18, lo); g.vline(14, 7, 18, lo)                 # arms meet the seat
    return g.cut_corners(2, 4, 17, 18)


def barrel():
    """A plastic drum, 0.9 m: its round lid from above with a raised rim, two screw caps,
    and the side showing as a 3 px crescent below the lid with a ribbed band."""
    g = Grid(20, 20)
    lo, mid, body, top = PLASTIC
    cx, cy, r, f = 10, 9, 8.2, front(0.9)
    g.ellipse(cx, cy + f, r, r, lo)                               # the side, under the lid
    for y in range(int(cy), g.h):                                 # its ribbed band
        for x in range(g.w):
            if g.px[y][x] == lo and y == int(cy + r + f / 2): g.px[y][x] = mid
    g.ellipse(cx, cy, r, r, mid)                                  # the lid's rim
    g.ellipse(cx, cy, r - 1.6, r - 1.6, body)                     # the lid
    g.rect(5, 6, 6, 7, top); g.rect(13, 10, 14, 11, top)          # screw caps
    g.set(5, 8, lo); g.set(6, 8, lo); g.set(13, 12, lo); g.set(14, 12, lo)
    return g


def cargo_case():
    """A moulded supply case, 0.5 m: a ribbed lid with darker corner bumpers, a stencilled
    stripe across one end, two latches on the front edge, a 2 px front strip."""
    g = Grid(20, 20)
    lo, mid, body, top = COMPOSITE
    x0, y0, x1, y1 = 1, 3, 18, 17
    f = front(0.5)
    g.rect(x0, y0, x1, y1, body)
    for x in range(x0 + 4, x1 - 3, 3): g.vline(x, y0 + 2, y1 - f - 2, mid)     # ribs
    g.rect(x0 + 3, y0 + 1, x1 - 3, y0 + 1, top)                    # lit far lip of the lid
    g.rect(x0, y0, x0 + 2, y0 + 2, lo); g.rect(x1 - 2, y0, x1, y0 + 2, lo)     # bumpers
    g.rect(x0, y1 - f - 2, x0 + 2, y1, lo); g.rect(x1 - 2, y1 - f - 2, x1, y1, lo)
    g.rect(x0 + 3, y1 - f - 3, x1 - 3, y1 - f - 2, top)            # stencilled stripe
    g.rect(x0 + 3, y1 - f + 1, x1 - 3, y1, mid)                    # front strip
    g.rect(5, y1 - f + 1, 6, y1, top); g.rect(13, y1 - f + 1, 14, y1, top)     # latches
    return g.cut_corners(x0, y0, x1, y1)


def cargo_case_bold():
    """The cargo case with its detail drawn bold (prompt tests, 2026-10-31: klein's own
    added detail turns to speckle at 20 px, so it has to be in the sketch): ribs 5 levels
    under the lid with a lit edge, black bumpers with a lit corner, a bright stripe, latches
    lit on a dark plate."""
    g = Grid(20, 20)
    x0, y0, x1, y1 = 1, 3, 18, 17
    f = front(0.5)
    g.rect(x0, y0, x1, y1, 9)
    for x in range(x0 + 4, x1 - 3, 3): g.vline(x, y0 + 3, y1 - f - 4, 4); g.vline(x + 1, y0 + 3, y1 - f - 4, 11)   # ribs, lit edge
    g.hline(x0 + 3, x1 - 3, y0 + 1, 12)                             # lit far lip
    for bx, by in ((x0, y0), (x1 - 2, y0), (x0, y1 - f - 2), (x1 - 2, y1 - f - 2)):
        g.rect(bx, by, bx + 2, by + 2 + (f if by > y0 else 0), 3); g.set(bx + 1, by + 1, 11)     # bumpers
    g.rect(x0 + 3, y1 - f - 3, x1 - 3, y1 - f - 2, 13)              # stencilled stripe
    g.rect(x0 + 3, y1 - f + 1, x1 - 3, y1, 6)                       # front strip
    g.rect(4, y1 - f + 1, 7, y1, 3); g.rect(12, y1 - f + 1, 15, y1, 3)     # latch plates
    g.rect(5, y1 - f + 1, 6, y1, 13); g.rect(13, y1 - f + 1, 14, y1, 13)   # latches
    return g.cut_corners(x0, y0, x1, y1)


def workstation():
    """A rolling cart, 1.1 m: the monitor's back along the far edge with its screen facing
    the front (a dark strip with lit lines), a keyboard tray, the cart's front strip and
    four casters peeking out at the corners."""
    g = Grid(20, 20)
    lo, mid, body, top = METAL
    dk, scr, txt, hi = SCREEN
    f = front(1.1)
    g.rect(2, 3, 17, 16 - f, body)                                # the cart's top
    g.hline(2, 17, 3, top)
    g.rect(4, 2, 15, 5, mid); g.hline(4, 15, 2, top)               # the monitor from above
    g.rect(4, 6, 15, 8, scr); g.hline(5, 9, 7, txt); g.hline(11, 13, 7, hi)    # its screen
    g.rect(4, 10, 15, 12, mid)                                    # keyboard tray
    for x in range(5, 15, 2): g.set(x, 11, top)                   # keys
    g.rect(2, 17 - f, 17, 16, lo)                                 # front strip
    g.vline(9, 17 - f, 16, mid); g.vline(10, 17 - f, 16, mid)     # a drawer pull
    for x in (1, 17): g.rect(x, 17, x + 1, 18, lo)                # casters
    return g.cut_corners(2, 3, 17, 16)


def locker_row(n=3, seam=None, roof="panel"):
    """A bank of n 2 m lockers across n cells and the 5 px gaps between them: a 10 px top
    with a lit far lip and seams where lockers meet (level `seam` on the top, the darkest
    metal by default), a 6 px front with door seams, vents and handles. Cut into
    alone/start/middle/end and links by `cut_row`; one locker (n=1) is built into a row
    by `row_from_single`."""
    w = 20 * n + 5 * (n - 1)
    g = Grid(w, 20)
    lo, mid, body, top = METAL
    f = front(2.0)
    y0, y1 = 2, 17                  # 10 px top + 6 px front = 16 rows
    g.rect(1, y0, w - 2, y0 + 9, body)
    g.hline(1, w - 2, y0, top)                                    # lit far lip
    if roof == "panel":
        g.rect(3, y0 + 3, w - 4, y0 + 6, mid)                      # a recessed top panel
    else:
        # "bold": the roof's detail drawn with the contrast klein keeps (it smoothed a
        # panel two levels under the roof away): per locker a deep recessed panel (5) with
        # a lit lower rim, two dark vent slots in it, rivets at the roof's corners
        g.rect(1, y0 + 1, w - 2, y0 + 9, top - 1)
        for i in range(n):
            x = 25 * i
            g.rect(x + 3, y0 + 2, x + 16, y0 + 7, lo)
            g.hline(x + 3, x + 16, y0 + 8, top)
            for vy in (y0 + 3, y0 + 5):
                g.hline(x + 5, x + 8, vy, 2); g.hline(x + 11, x + 14, vy, 2)
            for rx in (x + 2, x + 17):
                g.set(rx, y0 + 1, 12); g.set(rx, y0 + 8, 12)
    g.rect(1, y1 - f + 1, w - 2, y1, mid)                          # the front
    for i in range(n):
        x = 25 * i
        g.vline(x + 10, y1 - f + 1, y1, lo)                       # between the two doors
        g.rect(x + 7, y1 - f + 2, x + 8, y1 - f + 3, top)         # handles
        g.rect(x + 12, y1 - f + 2, x + 13, y1 - f + 3, top)
        g.hline(x + 3, x + 6, y1 - 1, lo); g.hline(x + 14, x + 17, y1 - 1, lo)    # vents
        if i:                                                      # where two lockers meet
            g.vline(x - 3, y0 + 1, y0 + 9, lo if seam is None else seam)
            g.vline(x - 3, y0 + 10, y1, lo)
    g.cut_corners(1, y0, w - 2, y1)
    return g


# --- the shared furniture (phase 3) -------------------------------------------------------
# Drawn by the phase 2 rules: one cell for a row piece (its bank built by row_from_single,
# the piece reaching x 1..18 so the rim is at 2 and 17), detail meant to survive 4-5 levels
# off its surroundings, the front strip 3 px a metre along the bottom.

def office_chair():
    """A task chair, no arms (asked for by the user): a round padded back along the top with
    a lit lip, a round seat with a soft highlight and a seam, and below the seat, in the
    front strip, the gas stem and the star base's front spokes and casters."""
    g = Grid(20, 20)
    g.ellipse(10, 4, 5.4, 2.8, 10); g.hline(7, 12, 1, 13)            # round back, lit lip
    g.ellipse(10, 10, 5.8, 5.2, 9)                                   # round seat
    g.ellipse(9, 8.5, 2.6, 1.6, 11)                                   # its soft highlight
    g.hline(6, 13, 6, 4)                                              # back meets seat
    g.vline(9, 15, 16, 7); g.vline(10, 15, 16, 7)                     # gas stem
    g.hline(3, 16, 17, 6)                                             # the base's front spokes
    for x in (3, 9, 15): g.rect(x, 18, x + 1, 19, 10)                 # casters
    return g


def stool():
    """A round stool, 0.6 m: a padded round seat with a darker ring seam and a lit centre
    button, and below it in the front strip its legs (the user: legs from the bottom, not
    all round): two splayed legs with lit feet and the footrest bar between them."""
    g = Grid(20, 20)
    for y, (a, b) in zip(range(13, 19), ((6, 7), (6, 7), (5, 6), (5, 6), (4, 5), (4, 5))):   # legs, splaying
        g.rect(a, y, b, y, 6); g.rect(19 - b, y, 19 - a, y, 6)
    g.hline(6, 13, 16, 5)                                             # footrest bar
    g.rect(4, 19, 5, 19, 10); g.rect(14, 19, 15, 19, 10)              # feet
    g.ellipse(10, 9, 6.6, 6.0, 6)                                     # seat's side
    g.ellipse(10, 8, 6.6, 6.0, 10)                                    # seat
    g.ellipse(10, 8, 4.2, 3.8, 5, inner=0.72)                         # ring seam
    g.rect(9, 7, 10, 8, 13)                                           # button
    return g


def bench():
    """A padded bench, 0.45 m, joining into a long bench: a seat pad with two tufting
    buttons, a lit far edge, the metal frame's rim, a 1 px front strip."""
    g = Grid(20, 20)
    g.rect(1, 5, 18, 14, 7)                                        # frame
    g.rect(2, 6, 17, 13, 10); g.hline(2, 17, 6, 12)                 # pad, lit far edge
    for x in (6, 13): g.rect(x, 9, x + 1, 10, 5)                   # buttons
    g.hline(1, 18, 15, 5)                                          # front strip
    return g


def desk():
    """A desk, 0.75 m, joining into a long desk: a metal top with a lit far lip, a monitor
    from above at the back with its dark screen facing the front, a keyboard with keys, a
    mouse, a 2 px front strip with a drawer handle."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 14, 9); g.hline(1, 18, 3, 11)                 # top, lit lip
    g.rect(5, 4, 14, 5, 5); g.rect(5, 6, 14, 7, 2)                  # monitor, its screen
    g.hline(6, 11, 6, 12)                                          # a line of text on it
    g.rect(6, 10, 13, 11, 4)                                       # keyboard
    for x in range(7, 13, 2): g.set(x, 10, 9)                      # keys
    g.rect(15, 10, 16, 11, 13)                                     # mouse
    g.rect(1, 15, 18, 16, 6); g.rect(8, 15, 11, 15, 12)            # front strip, handle
    return g


def side_table():
    """A small round side table, 0.6 m: a round top with a darker rim and a cup on it (a lit
    rim round a dark inside), three legs splaying out past it with lit feet."""
    g = Grid(20, 20)
    for ang in (90, -30, 210):                                        # legs
        a = math.radians(ang)
        ex, ey = 10 + math.cos(a) * 8.6, 9.5 + math.sin(a) * 8.6
        g.blob((10 + ex) / 2, (9.5 + ey) / 2, 4.6, 1.0, ang, 6)
        g.rect(int(ex) - 1, int(ey) - 1, int(ex), int(ey), 10)          # feet
    g.ellipse(10, 9.5, 5.9, 5.9, 5)                                    # side, under the top
    g.ellipse(10, 8.5, 5.9, 5.9, 7)                                    # rim
    g.ellipse(10, 8.5, 4.6, 4.6, 10)                                   # top
    g.ellipse(11.5, 7.5, 2.4, 2.4, 13); g.ellipse(11.5, 7.5, 1.2, 1.2, 3)   # cup
    return g


def small_chair(g, cx, cy, side, seat=9, back=12, gap=4):
    """A dining chair round a table, its back on `side` (n, s, w, e, away from the table):
    a seat at 9 with a lit back band at 12 and a dark gap between them."""
    w, h = (9, 8) if side in "ns" else (8, 9)
    x0, y0 = cx - w // 2, cy - h // 2
    g.rect(x0, y0, x0 + w - 1, y0 + h - 1, seat).cut_corners(x0, y0, x0 + w - 1, y0 + h - 1)
    if side == "n": g.rect(x0, y0, x0 + w - 1, y0 + 1, back); g.hline(x0, x0 + w - 1, y0 + 2, gap)
    if side == "s": g.rect(x0, y0 + h - 2, x0 + w - 1, y0 + h - 1, back); g.hline(x0, x0 + w - 1, y0 + h - 3, gap)
    if side == "w": g.rect(x0, y0, x0 + 1, y0 + h - 1, back); g.vline(x0 + 2, y0, y0 + h - 1, gap)
    if side == "e": g.rect(x0 + w - 2, y0, x0 + w - 1, y0 + h - 1, back); g.vline(x0 + w - 3, y0, y0 + h - 1, gap)


def table_4():
    """A round table with four chairs pushed in, 2x2: the chairs' backs and the front of
    their seats showing round the top, the top with a darker rim and a lit bowl in the
    middle, and its legs showing below it at the front (the user: legs from the bottom)."""
    g = Grid(*footprint((2, 2)))
    for x in (13, 31):                                                # legs, below the top's front
        g.rect(x, 29, x + 1, 34, 6); g.rect(x, 35, x + 1, 35, 10)
    for cx, cy, side in ((22, 9, "n"), (22, 37, "s"), (10, 21, "w"), (35, 21, "e")):   # pushed in
        small_chair(g, cx, cy, side)
    g.ellipse(22.5, 22.5, 10.6, 10.6, 5)                               # side, under the top
    g.ellipse(22.5, 21.5, 10.6, 10.6, 7)                               # rim
    g.ellipse(22.5, 21.5, 9.0, 9.0, 10)                                # top
    g.ellipse(22.5, 21.5, 3.0, 3.0, 13); g.ellipse(22.5, 21.5, 1.5, 1.5, 6)   # a bowl
    return g


def table_6():
    """A long table across a 2x2 with three chairs pushed in on each long side (their backs
    and the front of their seats showing): a top with a lit far lip, a plate at each place,
    a runner, a 2 px front strip, and below it at the two ends the front legs with lit feet
    and floor between (the user: legs from the bottom)."""
    g = Grid(*footprint((2, 2)))
    for cx in (11, 22, 33):
        small_chair(g, cx, 12, "n"); small_chair(g, cx, 35, "s")
    g.rect(3, 15, 41, 29, 9); g.hline(3, 41, 15, 11)                  # top, lit lip
    g.rect(3, 30, 41, 31, 5)                                          # front strip
    for x in (3, 40):                                                 # front legs at the ends
        g.rect(x, 30, x + 1, 36, 6); g.rect(x, 37, x + 1, 37, 10)
    for cx in (11, 22, 33):
        g.rect(cx - 2, 17, cx + 1, 19, 13); g.rect(cx - 2, 25, cx + 1, 27, 13)   # plates
    g.hline(6, 38, 22, 7)                                             # a runner down the middle
    return g


# --- bold forms of the furniture picks (prompt tests, 2026-10-31) ----------------------------
# The same pieces with every detail 4-5 levels off what surrounds it and nothing carried by a
# lone pixel: on the Cargo Bay picks only detail drawn this way survived klein and the shrink.

def chair_bold():
    """The armchair, bold: a lit backrest with a dark seam under it, a cushion with a big
    highlight, arms with lit tops and dark seams where they meet the seat."""
    g = Grid(20, 20)
    g.rect(2, 2, 17, 18, 7)
    g.rect(5, 1, 14, 6, 11); g.hline(6, 13, 1, 13)                 # backrest, lit lip
    g.set(5, 1, None); g.set(14, 1, None)
    g.hline(5, 14, 7, 3)                                           # backrest meets seat
    g.rect(5, 8, 14, 16, 9); g.rect(7, 9, 12, 11, 12)               # cushion, highlight
    for a, b in ((2, 4), (15, 17)):                               # arms
        g.rect(a, 4, b, 16, 10); g.hline(a, b, 4, 13)
        g.rect(a, 17, b, 18, 4)
    g.rect(5, 17, 14, 18, 4)                                       # front strip
    g.vline(5, 7, 18, 3); g.vline(14, 7, 18, 3)                    # arms meet the seat
    return g.cut_corners(2, 4, 17, 18)


def office_chair_bold():
    """The task chair, bold: a lit round back, a dark gap, a round seat with a big
    highlight, a thick gas stem, the base's spokes and 2 px casters."""
    g = Grid(20, 20)
    g.ellipse(10, 4, 5.4, 2.8, 11); g.hline(7, 12, 1, 14)            # back, lit lip
    g.ellipse(10, 10, 5.8, 5.2, 8)                                   # seat
    g.ellipse(9.5, 9, 3.2, 2.2, 12)                                   # highlight
    g.hline(5, 14, 6, 3)                                              # back meets seat
    g.rect(9, 15, 10, 16, 5)                                          # gas stem
    g.hline(3, 16, 17, 8)                                             # spokes
    for x in (3, 9, 15): g.rect(x, 18, x + 1, 19, 12)                 # casters
    return g


def stool_bold():
    """The stool, bold: a seat with a thick dark ring seam and a lit button, a dark side,
    lit legs and feet below."""
    g = Grid(20, 20)
    for y, (a, b) in zip(range(13, 19), ((6, 7), (6, 7), (5, 6), (5, 6), (4, 5), (4, 5))):
        g.rect(a, y, b, y, 8); g.rect(19 - b, y, 19 - a, y, 8)
    g.hline(6, 13, 16, 7)                                             # footrest bar
    g.rect(4, 19, 5, 19, 12); g.rect(14, 19, 15, 19, 12)              # feet
    g.ellipse(10, 9, 6.6, 6.0, 4)                                     # seat's side
    g.ellipse(10, 8, 6.6, 6.0, 10)                                    # seat
    g.ellipse(10, 8, 4.4, 4.0, 4, inner=0.62)                         # ring seam, thick
    g.rect(9, 7, 10, 8, 14)                                           # button
    return g


def water_cooler_bold():
    """The water cooler, bold: a dark bottle rim round a bright bottle with a lit crescent
    and a dark cap, a dark plate behind a lit tap, a dark drip tray with a lit grille."""
    g = Grid(20, 20)
    g.rect(4, 4, 15, 13, 7); g.hline(4, 15, 4, 11)                    # cabinet top
    g.ellipse(10, 8.5, 5, 5, 3)                                       # bottle's rim
    g.ellipse(10, 8.5, 3.9, 3.9, 11)                                  # bottle
    g.ellipse(9, 7.5, 2.6, 2.6, 14, inner=0.6)                        # its lit crescent
    g.rect(9, 8, 10, 9, 3)                                            # cap
    g.rect(4, 14, 15, 17, 6)                                          # front
    g.rect(8, 14, 11, 15, 2); g.rect(9, 14, 10, 15, 13)               # tap on its plate
    g.rect(6, 16, 13, 17, 2); g.hline(7, 12, 16, 9)                   # drip tray, grille
    return g


def desk_bold():
    """The desk, bold: a lit lip, a monitor with a dark screen and two lit lines of text, a
    dark keyboard with lit rows of keys, a lit mouse on a dark pad, a front with a handle."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 14, 9); g.hline(1, 18, 3, 12)                 # top, lit lip
    g.rect(5, 4, 14, 5, 5); g.rect(5, 6, 14, 8, 2)                  # monitor, its screen
    g.hline(6, 11, 6, 13); g.hline(6, 9, 8, 11)                    # two lines of text
    g.rect(5, 10, 13, 12, 3)                                       # keyboard
    g.hline(6, 12, 10, 10); g.hline(6, 12, 12, 8)                  # rows of keys
    g.rect(14, 10, 17, 12, 4); g.rect(15, 10, 16, 11, 13)          # mouse on its pad
    g.rect(1, 15, 18, 16, 5); g.rect(8, 15, 11, 15, 13)            # front strip, handle
    return g


def table_4_bold():
    """The round table, bold: chairs with lit backs and dark gaps, a dark rim, a lit far
    edge on the top, a bright bowl with dark fruit, lit feet."""
    g = Grid(*footprint((2, 2)))
    for x in (13, 31):
        g.rect(x, 29, x + 1, 34, 6); g.rect(x, 35, x + 1, 35, 12)
    for cx, cy, side in ((22, 9, "n"), (22, 37, "s"), (10, 21, "w"), (35, 21, "e")):
        small_chair(g, cx, cy, side, seat=8, back=13, gap=2)
    g.ellipse(22.5, 22.5, 10.6, 10.6, 3)                               # side
    g.ellipse(22.5, 21.5, 10.6, 10.6, 5)                               # rim
    g.ellipse(22.5, 21.5, 9.0, 9.0, 10)                                # top
    g.ellipse(22.5, 20.5, 8.2, 7.6, 12, inner=0.86)                    # its lit far edge
    g.ellipse(22.5, 21.5, 3.4, 3.4, 14); g.ellipse(22.5, 21.5, 2.0, 2.0, 4)   # bowl
    return g


def table_6_bold():
    """The long table, bold: chairs with lit backs and dark gaps, a lit lip, plates with
    dark middles, a dark runner, a dark front strip, lit feet."""
    g = Grid(*footprint((2, 2)))
    for cx in (11, 22, 33):
        small_chair(g, cx, 12, "n", seat=8, back=13, gap=2); small_chair(g, cx, 35, "s", seat=8, back=13, gap=2)
    g.rect(3, 15, 41, 29, 9); g.hline(3, 41, 15, 12)
    g.rect(3, 30, 41, 31, 4)
    for x in (3, 40):
        g.rect(x, 30, x + 1, 36, 6); g.rect(x, 37, x + 1, 37, 12)
    for cx in (11, 22, 33):
        for y in (17, 25): g.rect(cx - 2, y, cx + 1, y + 2, 14); g.rect(cx - 1, y + 1, cx, y + 1, 7)   # plates
    g.rect(6, 21, 38, 23, 5)                                          # runner
    return g


def bunk():
    """A single bunk, 1x2 (2 m long): a metal frame on four legs whose lit tops show at the
    corners, a mattress, a pillow at the head with a seam, a blanket folded back with a lit
    fold and a dark stripe, and at the foot a front strip of the two legs with floor
    showing between them."""
    g = Grid(*footprint((1, 2)))
    g.rect(2, 2, 17, 42, 6)                                          # frame
    g.rect(4, 4, 15, 40, 9)                                          # mattress
    g.rect(5, 5, 14, 10, 12); g.hline(6, 13, 8, 8)                   # pillow, its seam
    g.rect(4, 18, 15, 40, 7); g.hline(4, 15, 18, 12)                  # blanket, lit fold
    g.rect(4, 29, 15, 30, 4)                                         # its stripe
    for x, y in ((1, 1), (17, 1), (1, 41), (17, 41)): g.rect(x, y, x + 1, y + 1, 11)   # leg tops
    g.hline(2, 17, 43, 5)                                            # the foot rail
    g.rect(1, 44, 2, 46, 7); g.rect(17, 44, 18, 46, 7)               # the legs, floor between
    return g


def cabinet():
    """A filing cabinet, 1.2 m, joining into a run: a metal top with a lit far lip and a
    stack of papers on it, a 4 px front with two drawers, their handles lit and the gap
    between them dark."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 13, 9); g.hline(1, 18, 3, 11)                  # top, lit lip
    g.rect(4, 6, 9, 10, 13); g.hline(4, 9, 10, 6)                   # papers, their edge
    g.rect(1, 14, 18, 17, 7)                                         # front
    g.hline(1, 18, 16, 3)                                            # between the drawers
    g.rect(8, 15, 11, 15, 12); g.rect(8, 17, 11, 17, 12)              # handles
    return g


def shelf():
    """Shelving, 2 m, joining into a run: its top board (0.4 m deep) with two boxes stored
    on top, and a 6 px front showing the shelves: lit edges, dark gaps with bottles and box
    fronts in them."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 10, 8); g.hline(1, 18, 3, 11)                  # top board, lit lip
    g.rect(3, 4, 8, 9, 12); g.vline(3, 4, 9, 6); g.hline(3, 8, 9, 6)   # a box on top
    g.rect(11, 5, 16, 9, 10); g.hline(11, 16, 7, 5)                  # another, taped
    g.hline(1, 18, 11, 11)                                           # top shelf's edge
    g.rect(1, 12, 18, 13, 3)                                         # gap with bottles
    for x in (3, 5, 7, 12, 14): g.rect(x, 12, x, 13, 10)
    g.hline(1, 18, 14, 9)                                            # next shelf's edge
    g.rect(1, 15, 18, 16, 3)                                         # gap with box fronts
    g.rect(3, 15, 7, 16, 7); g.rect(11, 15, 16, 16, 7)
    return g


def vending():
    """A vending machine, 1.8 m, joining into a row: a metal top with vent slots and a lit
    lip, a 5 px lit front with a dark product window (goods in it), a coin slot and a
    delivery slot."""
    g = Grid(20, 20)
    g.rect(1, 1, 18, 13, 8); g.hline(1, 18, 1, 11)                  # top, lit lip
    for y in (4, 7, 10): g.hline(4, 15, y, 3)                        # vent slots
    g.rect(1, 14, 18, 18, 12)                                        # lit front
    g.rect(3, 14, 12, 16, 3)                                         # product window
    for x in (4, 6, 8, 10): g.set(x, 15, 10)                         # goods
    g.rect(15, 15, 15, 16, 2)                                        # coin slot
    g.hline(3, 12, 18, 2)                                            # delivery slot
    return g


def water_cooler():
    """A water cooler, 1.3 m: a cabinet top with a lit lip, the water bottle from above (a
    bright round with a darker rim and a dark cap), a 4 px front with a lit tap and a dark
    drip tray."""
    g = Grid(20, 20)
    g.rect(4, 4, 15, 13, 8); g.hline(4, 15, 4, 10)                   # cabinet top
    g.ellipse(10, 8.5, 5, 5, 6)                                       # bottle's rim
    g.ellipse(10, 8.5, 3.9, 3.9, 12)                                  # bottle
    g.rect(9, 8, 10, 9, 4)                                            # cap
    g.rect(4, 14, 15, 17, 7)                                          # front
    g.rect(9, 14, 10, 15, 13)                                         # tap
    g.hline(7, 12, 17, 3)                                             # drip tray
    return g


def plant():
    """A potted plant, about 1 m: a round pot (smaller than its leaves, its lit rim showing
    between them, its side a crescent below) with five pointed leaves spreading from the
    centre past the rim, each with a lit midrib."""
    g = Grid(20, 20)
    g.ellipse(10, 13.5, 6.0, 5.0, 6)                                  # pot's side, below the rim
    g.ellipse(10, 11, 6.0, 5.0, 11)                                   # lit rim
    g.ellipse(10, 11, 4.4, 3.5, 2)                                    # soil
    for ang, ln in ((-90, 9), (-18, 8.5), (198, 8.5), (54, 5.5), (126, 5.5)):
        a = math.radians(ang)                                          # the two lower leaves short,
        cx, cy = 10 + math.cos(a) * ln / 2, 9 + math.sin(a) * ln / 2   # so the pot's front shows
        g.blob(cx, cy, ln / 2 + 0.6, 1.7, ang, 9)                       # leaf
        for k in range(1, int(ln)): g.set(10 + math.cos(a) * k, 9 + math.sin(a) * k, 13)   # midrib
    g.rect(9, 8, 10, 9, 6)                                             # the centre
    return g


def bin_():
    """A lidded waste bin, 0.7 m: a round lid with a darker rim, a dark swing slot and a
    lit handle bar, the side showing as a crescent under the lid."""
    g = Grid(20, 20)
    g.ellipse(10, 11, 7.2, 7.2, 5)                                     # side
    g.ellipse(10, 9, 7.2, 7.2, 7)                                      # rim
    g.ellipse(10, 9, 5.9, 5.9, 10)                                     # lid
    g.rect(6, 6, 13, 7, 3)                                             # swing slot
    g.rect(7, 10, 12, 11, 13)                                          # handle bar
    return g


def console():
    """A control console, 1 m, joining into a bank: a screen panel at the back (dark, with
    lit lines of text and a lit top lip), a sloped desk of buttons (lit and dark), a 3 px
    front strip with a dark knee gap."""
    g = Grid(20, 20)
    g.rect(1, 2, 18, 7, 2); g.hline(1, 18, 2, 10)                   # screen panel, lip
    g.hline(3, 10, 4, 12); g.hline(3, 7, 6, 11); g.hline(12, 16, 5, 11)   # text
    g.rect(1, 8, 18, 14, 8)                                         # sloped desk
    for y, xs in ((9, (3, 6, 9, 12, 15)), (12, (4, 7, 10, 13, 16))):
        for i, x in enumerate(xs): g.rect(x, y, x + 1, y + 1, 13 if i % 2 == 0 else 4)   # buttons
    g.rect(1, 15, 18, 17, 6); g.rect(6, 16, 13, 17, 3)              # front strip, knee gap
    return g


# --- the shared industrial pieces and decals (phase 3) ------------------------------------

def pipe():
    """A pipe, joining into runs, bends, tees and crosses (path): one straight segment east
    to west through the cell's middle, rows 7-12, lit along its top, dark at its edges, with
    a flanged fitting at the centre (columns 8-11) whose bolts are lit."""
    g = Grid(20, 20)
    for y, v in zip(range(7, 13), (5, 9, 12, 10, 8, 5)): g.hline(0, 19, y, v)
    g.rect(8, 6, 11, 13, 8); g.vline(8, 6, 13, 4); g.vline(11, 6, 13, 4)   # flange
    g.hline(8, 11, 6, 11)
    for x, y in ((9, 6), (10, 13)): g.set(x, y, 13)                  # bolts
    return g


def cable_tray():
    """A cable tray, joining like a pipe (path): one straight run, rows 6-13: lit side rails,
    a dark tray floor with three cables along it, and a bolted junction plate at the centre."""
    g = Grid(20, 20)
    g.hline(0, 19, 6, 11); g.hline(0, 19, 13, 9)                      # rails
    g.rect(0, 7, 19, 12, 3)                                           # tray floor
    g.hline(0, 19, 8, 9); g.hline(0, 19, 9, 7); g.hline(0, 19, 11, 8)  # cables
    g.rect(8, 6, 11, 13, 6); g.hline(8, 11, 6, 12)                    # junction plate
    g.set(9, 9, 13); g.set(10, 10, 13)                                # its bolts
    return g


def mat():
    """A rubber floor mat (grid decal, flat): a 3 px raised border, lit on its outer edge,
    round a ribbed inside; areas join into a big mat."""
    g = Grid(20, 20)
    for y in range(20):
        for x in range(20):
            d = min(x, y, 19 - x, 19 - y)
            g.px[y][x] = 8 if d == 0 else 6 if d < 3 else (5 if y % 3 == 0 else 3)
    return g


def hazard():
    """Hazard edging (grid decal): diagonal light and dark stripes in a 3 px band round an
    area, the floor showing inside; areas join into one marked zone."""
    g = Grid(20, 20)
    for y in range(20):
        for x in range(20):
            if min(x, y, 19 - x, 19 - y) < 3: g.px[y][x] = 12 if ((x + y) // 3) % 2 == 0 else 3
    return g


def grate():
    """A floor grate (grid decal): a 2 px frame, lit outside, round slots: dark 2 px slots
    between 1 px bars; areas join into a grated floor."""
    g = Grid(20, 20)
    for y in range(20):
        for x in range(20):
            d = min(x, y, 19 - x, 19 - y)
            g.px[y][x] = 10 if d == 0 else 7 if d < 2 else (8 if y % 3 == 2 else 2)
    return g


def scorch():
    """A blast mark (decal): a black heart, a sooty ring round it and lighter streaks
    thrown out from it, irregular."""
    g = Grid(20, 20)
    for ang, ln in ((10, 9), (70, 7), (130, 9), (200, 8), (250, 6), (310, 9)):
        a = math.radians(ang)
        g.blob(10 + math.cos(a) * ln / 2, 10 + math.sin(a) * ln / 2, ln / 2 + 0.5, 1.1, ang, 3)   # streaks
    g.ellipse(10, 10, 6.2, 5.4, 2)                                    # soot
    g.ellipse(10.5, 9.5, 3.6, 3.0, 0)                                  # heart
    g.set(8, 8, 4); g.set(12, 12, 4)
    return g



def hazard_bold(band=4):
    """Hazard edging drawn bolder: a 4 px band of 3 px diagonal stripes at 13 and 2."""
    g = Grid(20, 20)
    for y in range(20):
        for x in range(20):
            if min(x, y, 19 - x, 19 - y) < band: g.px[y][x] = 13 if ((x + y) // 3) % 2 == 0 else 2
    return g


def hatch():
    """A round floor hatch (decal): a lit rim with eight bolts, a dark seam inside it, a
    plate with a recessed cross of stiffeners and a lit lifting handle."""
    g = Grid(20, 20)
    g.ellipse(10, 10, 9.0, 9.0, 9)                                    # rim
    g.ellipse(10, 10, 6.6, 6.6, 2)                                    # seam
    g.ellipse(10, 10, 5.8, 5.8, 7)                                    # plate
    g.rect(9, 5, 10, 14, 5); g.rect(5, 9, 14, 10, 5)                  # stiffeners
    g.rect(8, 8, 11, 11, 7)
    g.hline(8, 11, 7, 12); g.vline(8, 7, 8, 12); g.vline(11, 7, 8, 12)   # handle
    for k in range(8):                                                # bolts
        a = math.radians(22.5 + 45 * k)
        g.set(9.5 + math.cos(a) * 7.8, 9.5 + math.sin(a) * 7.8, 13)
    return g


def drain():
    """A floor drain (decal): a small square plate with a lit frame and a dark seam round it,
    a grid of dark holes between lit bars, a dark sump showing through."""
    g = Grid(20, 20)
    g.rect(3, 3, 16, 16, 2)                                           # seam round it
    g.rect(4, 4, 15, 15, 10)                                          # frame
    g.rect(6, 6, 13, 13, 7)                                           # plate
    for y in (6, 9, 12):
        for x in (6, 9, 12): g.rect(x, y, x + 1, y + 1, 1)            # holes
    g.hline(4, 15, 4, 12)                                             # the frame's lit far edge
    return g


def floor_arrow():
    """A painted floor arrow (decal): a bold arrow pointing up the screen (the game turns
    it), its paint bright with worn pixels, the floor showing round it."""
    g = Grid(20, 20)
    for y in range(2, 10):                                            # head
        half = y - 2
        g.hline(10 - half - 1, 9 + half + 1, y, 12)
    g.rect(7, 10, 12, 17, 12)                                         # shaft
    for x, y in ((4, 9), (14, 8), (8, 13), (11, 16), (9, 4)): g.set(x, y, 8)   # worn paint
    return g

def case_stack():
    """Two moulded cases strapped together, 2x1: a big one and a smaller one beside it, both
    with ribbed lids and dark corner bumpers, two lit straps across both, a 2 px front."""
    g = Grid(*footprint((2, 1)))
    g.rect(1, 2, 24, 16, 9); g.rect(27, 5, 43, 16, 8)                 # the cases
    for x in range(4, 23, 3): g.vline(x, 4, 14, 7)                    # ribs
    for x in range(30, 42, 3): g.vline(x, 7, 14, 6)
    for x0, y0, x1, y1 in ((1, 2, 24, 16), (27, 5, 43, 16)):
        for cx, cy in ((x0, y0), (x1 - 1, y0), (x0, y1 - 1), (x1 - 1, y1 - 1)): g.rect(cx, cy, cx + 1, cy + 1, 4)   # bumpers
    g.hline(1, 24, 17, 6); g.hline(1, 24, 18, 5); g.hline(27, 43, 17, 5)     # front strips
    for x in (12, 35): g.vline(x, 2, 18, 12)                           # straps
    g.hline(25, 26, 10, 12)                                            # a strap joining them
    return g


def gas_cylinder():
    """A tall gas cylinder, 1.5 m: its domed top from above with a lit valve and a dark
    collar, and below it the body in a 5 px front strip with a bright hazard band."""
    g = Grid(20, 20)
    g.rect(5, 8, 14, 15, 7); g.ellipse(10, 15.5, 4.8, 2.0, 7)          # the body, below the top
    g.rect(5, 10, 14, 11, 12)                                          # hazard band
    g.ellipse(10, 7, 4.8, 4.8, 9)                                       # domed top
    g.ellipse(10, 7, 2.4, 2.4, 4)                                       # collar
    g.rect(9, 6, 10, 7, 13)                                             # valve
    g.vline(5, 8, 15, 5); g.vline(14, 8, 15, 6)
    return g


def tank():
    """A water or coolant tank, 1.5 m: a big round lid with a darker rim, a round hatch with a
    lit handle, a gauge, and the side in a 4 px front strip with two dark bands."""
    g = Grid(20, 20)
    g.ellipse(10, 11, 8.2, 7.6, 7)                                      # side, below the lid
    g.hline(3, 16, 15, 4); g.hline(4, 15, 17, 4)                        # bands
    g.ellipse(10, 7.5, 8.2, 6.8, 6)                                     # rim
    g.ellipse(10, 7.5, 6.8, 5.6, 9)                                     # lid
    g.ellipse(8, 7, 2.6, 2.4, 4); g.hline(7, 9, 7, 12)                  # hatch, its handle
    g.rect(13, 5, 14, 6, 13); g.set(13, 7, 3)                           # gauge
    return g


def tank_bold():
    """The tank with its detail drawn bold (see cargo_case_bold): a dark rim ringed with lit
    bolts, a lid with a lit far edge, a deep hatch with a bright handle, a gauge with a dark
    face, black bands on the side."""
    import math
    g = Grid(20, 20)
    g.ellipse(10, 11, 8.2, 7.6, 7)                                      # side
    g.hline(3, 16, 15, 2); g.hline(4, 15, 17, 2)                        # bands
    g.ellipse(10, 7.5, 8.2, 6.8, 4)                                     # rim
    g.ellipse(10, 7.5, 6.6, 5.4, 9)                                     # lid
    g.ellipse(10, 6.8, 6.0, 4.2, 10, inner=0.85)                        # its lit far edge
    for k in range(10):                                                 # bolts on the rim
        a = 2 * math.pi * k / 10
        g.set(10 + 7.4 * math.cos(a), 7.5 + 6.1 * math.sin(a), 12)
    g.ellipse(8, 7.5, 2.8, 2.6, 3); g.ellipse(8, 7.5, 1.6, 1.4, 6)      # hatch, recessed
    g.hline(7, 9, 7, 13)                                                # handle
    g.rect(12, 5, 14, 7, 2); g.set(13, 6, 13)                           # gauge
    return g


def tool_chest():
    """A tool chest, 1 m, joining into a run: a metal top with a lit lip and a wrench lying
    on it, a 3 px front of drawers, their gaps dark and their pulls lit."""
    g = Grid(20, 20)
    g.rect(1, 4, 18, 13, 9); g.hline(1, 18, 4, 11)                     # top, lit lip
    for k in range(7): g.set(5 + k, 10 - k // 2, 13)                    # a wrench
    g.rect(4, 10, 5, 11, 13); g.rect(11, 6, 12, 7, 13)
    g.rect(1, 14, 18, 16, 7)                                            # drawers
    g.hline(1, 18, 15, 3)
    g.rect(8, 14, 11, 14, 12); g.rect(8, 16, 11, 16, 12)                # pulls
    return g


def cable_reel():
    """A cable reel lying flat: a wide flange, the cable wound round it in lit turns with dark
    lines between, a dark hub with a lit spindle, the flange's edge as a crescent below."""
    g = Grid(20, 20)
    g.ellipse(10, 10.5, 8.4, 8.0, 5)                                    # flange's edge, below
    g.ellipse(10, 9.5, 8.4, 8.0, 7)                                     # flange
    g.ellipse(10, 9.5, 6.6, 6.2, 10)                                    # wound cable
    for r in (5.4, 3.9): g.ellipse(10, 9.5, r, r * 0.94, 5, inner=0.86)  # between the turns
    g.ellipse(10, 9.5, 2.6, 2.4, 3)                                      # hub
    g.rect(9, 9, 10, 10, 13)                                             # spindle
    return g


def generator():
    """A generator, 2x1, 1 m: a housing with a lit lip, an exhaust stack (a dark round with a
    lit rim), a control panel with lit lights, rows of dark vent slots, a 3 px front."""
    g = Grid(*footprint((2, 1)))
    g.rect(1, 2, 43, 14, 8); g.hline(1, 43, 2, 11)                      # housing
    g.ellipse(7, 7.5, 3.4, 3.4, 11); g.ellipse(7, 7.5, 2.0, 2.0, 2)     # exhaust stack
    g.rect(13, 5, 21, 11, 4)                                             # control panel
    for x, v in ((15, 13), (17, 12), (19, 13)): g.set(x, 7, v)           # its lights
    g.hline(15, 19, 9, 10)
    for y in (5, 7, 9, 11): g.hline(25, 40, y, 3)                        # vents
    g.rect(1, 15, 43, 17, 6); g.hline(1, 43, 16, 4)                       # front strip
    return g


def work_light():
    """A work light on a tripod, 2 m: its lamp head from above with a bright lens along its
    front, and below it the post and the tripod's legs splaying to lit feet."""
    g = Grid(20, 20)
    g.vline(9, 9, 16, 6); g.vline(10, 9, 16, 6)                          # post
    for y, (a, b) in zip(range(14, 19), ((8, 7), (7, 6), (6, 5), (5, 4), (4, 3))):   # legs
        g.set(a, y, 6); g.set(19 - a, y, 6)
    g.rect(3, 18, 4, 18, 10); g.rect(15, 18, 16, 18, 10)                 # feet
    g.rect(5, 2, 14, 7, 7); g.hline(5, 14, 2, 10)                        # lamp head
    g.rect(5, 8, 14, 9, 14)                                              # lens
    g.hline(7, 12, 4, 4)                                                 # cooling fins
    g.hline(7, 12, 6, 4)
    return g


def fire_point():
    """A fire point: an extinguisher on a stand. The extinguisher's top from above (a bright
    round with a dark lever and hose), the stand's plate round it, two short legs below."""
    g = Grid(20, 20)
    g.rect(4, 4, 15, 15, 5); g.hline(4, 15, 4, 8)                         # stand plate
    g.ellipse(10, 9, 4.0, 4.0, 11)                                        # extinguisher
    g.rect(9, 6, 10, 9, 3); g.rect(10, 6, 13, 6, 3)                        # lever
    for k in range(4): g.set(6 - k // 2, 10 + k, 3)                        # hose
    g.rect(4, 16, 5, 18, 6); g.rect(14, 16, 15, 18, 6)                     # legs
    return g


def bot_wreck(kind="walker"):
    """A destroyed bot (the fighting on the way to the Airlock), on a sooty patch: a walker's
    torn body and two legs thrown apart, a floater's cracked shell and a broken fin, or
    scattered parts. Bright edges where metal is torn, a spark or two."""
    g = Grid(20, 20)
    g.ellipse(10, 10.5, 8.0, 6.6, 2)                                       # soot under it
    if kind == "walker":
        g.blob(9, 9, 5.0, 3.6, -20, 8)                                      # body
        g.blob(8, 8, 2.4, 1.4, -20, 3)                                      # torn open
        g.blob(15, 13, 3.6, 0.9, 40, 9); g.blob(4, 14, 3.4, 0.9, -60, 9)     # legs
        g.set(11, 7, 13); g.set(6, 10, 13)
    elif kind == "floater":
        g.ellipse(10, 9.5, 5.6, 5.6, 8)                                     # shell
        g.blob(11, 10, 3.0, 1.6, 30, 3)                                     # cracked open
        g.blob(9, 8, 2.6, 0.6, -40, 3)                                      # a crack
        g.blob(16, 15, 2.6, 1.2, 20, 10)                                    # a fin
        g.set(7, 7, 13); g.set(13, 12, 13)
    else:
        for cx, cy, rx, ry, a, v in ((6, 7, 2.6, 1.6, 10, 8), (13, 6, 2.0, 1.4, -30, 9), (8, 13, 3.0, 1.2, 50, 7),
                                     (14, 13, 2.2, 2.0, 0, 8), (10, 10, 3.6, 0.6, -10, 10)):
            g.blob(cx, cy, rx, ry, a, v)
        g.set(13, 6, 13); g.set(8, 13, 12)
    return g


def conveyor():
    """A conveyor, joining into a run: a dark belt with lit ribs across it every 3 px between
    lit side rails, a lit roller drum at each end of a run, a 2 px front strip."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 14, 4)                                              # belt
    for x in range(3, 17, 3): g.vline(x, 4, 13, 7)                      # ribs
    g.hline(1, 18, 3, 11); g.hline(1, 18, 14, 10)                       # side rails
    g.vline(1, 3, 14, 12); g.vline(18, 3, 14, 12)                       # end drums
    g.rect(1, 15, 18, 16, 6)                                            # front strip
    return g



# --- Cargo Bay's own pieces (phase 4) -----------------------------------------------------

def container():
    """A freight container, 2x1, 2.6 m: a corrugated roof (ribs every 2 px, 4 levels apart)
    with dark corner castings and a lit far lip, the long side in an 8 px front strip,
    corrugated too, the door end's lit lock rods at its right end."""
    g = Grid(*footprint((2, 1)))
    f = front(2.6)
    y0, y1 = 1, 18
    yt = y1 - f                                                       # last roof row
    g.rect(1, y0, 43, yt, 8)
    for x in range(3, 42, 2): g.vline(x, y0 + 1, yt - 1, 4)           # roof ribs
    g.hline(1, 43, y0, 11)                                            # lit far lip
    for cx, cy in ((1, y0), (42, y0), (1, yt - 1), (42, yt - 1)): g.rect(cx, cy, cx + 1, cy + 1, 3)   # castings
    g.rect(1, yt + 1, 43, y1, 6)                                      # long side
    for x in range(2, 36, 2): g.vline(x, yt + 1, y1, 3)               # its corrugation
    g.rect(36, yt + 1, 43, y1, 7)                                     # door end
    for x in (38, 41): g.vline(x, yt + 1, y1, 12)                     # lock rods
    g.hline(37, 42, yt + 4, 10)                                       # a handle bar
    return g.cut_corners(1, y0, 43, y1)


def container_stack():
    """Two containers, 2x2, crosswise (redrawn bold: klein drew the first sketch as two side
    by side): a dark lower one lying left to right across the middle, its ribs running down
    the screen, and a bright upper one laid on it the other way, from the top edge to the
    bottom, its ribs running across, so the two read as crossed; the upper one's door end
    with lit lock rods in the front strip, the lower one's long side in shadow."""
    g = Grid(*footprint((2, 2)))
    f = front(2.6)
    # the lower one: roof rows 12-29, dark, ribs down the screen; its long side below
    g.rect(0, 12, 44, 29, 6)
    for x in range(2, 44, 2): g.vline(x, 13, 28, 2)
    g.hline(0, 44, 12, 9)
    g.rect(0, 30, 44, 29 + f, 4)
    for x in range(1, 44, 2): g.vline(x, 30, 29 + f, 1)
    # the upper one, the other way: roof rows 0-37, bright, ribs across; its door end below
    x0, x1 = 14, 30
    yb = 46 - f
    g.rect(x0, 0, x1, yb, 11)
    for y in range(2, yb, 2): g.hline(x0 + 2, x1 - 2, y, 7)           # ribs, across
    g.vline(x0, 0, yb, 13); g.vline(x1, 0, yb, 8)                     # its lit and shaded rails
    for cx, cy in ((x0, 0), (x1 - 1, 0), (x0, yb - 1), (x1 - 1, yb - 1)): g.rect(cx, cy, cx + 1, cy + 1, 3)
    g.rect(x0, yb + 1, x1, 46, 9)                                     # door end
    for x in (x0 + 3, x0 + 6, x1 - 6, x1 - 3): g.vline(x, yb + 1, 46, 14)   # lock rods
    g.vline((x0 + x1) // 2, yb + 1, 46, 3)                            # between the doors
    return g


def pallet():
    """An empty composite pallet, 0.15 m: lit deck slats across it with dark gaps, the three
    runners under the deck showing in the gaps, a 1 px front with the runners' ends."""
    g = Grid(20, 20)
    g.rect(2, 3, 17, 16, 2)                                           # gaps (floor under it)
    for y in range(3, 16, 3):
        g.rect(2, y, 17, y + 1, 9); g.hline(2, 17, y, 11)             # slats, lit far edges
    for x in (2, 9, 16):                                              # runners in the gaps
        for y in range(5, 16, 3): g.rect(x, y, x + 1, y, 5)
    g.hline(2, 17, 17, 4)                                             # front
    for x in (2, 9, 16): g.rect(x, 17, x + 1, 17, 7)
    return g


def pallet_load():
    """Cases strapped on a pallet, 1.2 m: two cases' lids from above (ribbed, dark corner
    bumpers), a lit strap round both, the pallet's slats showing at the edges, a 4 px front
    of case sides above the pallet's 1 px edge."""
    g = Grid(20, 20)
    f = front(1.2)
    g.rect(1, 2, 18, 18, 4)                                           # the pallet under it
    for y in (2, 5, 8): g.hline(1, 18, y, 9)
    for x0, x1 in ((2, 9), (10, 17)):                                 # the cases' lids
        g.rect(x0, 3, x1, 16 - f, 9)
        for x in range(x0 + 2, x1 - 1, 2): g.vline(x, 5, 14 - f, 7)
        for cx, cy in ((x0, 3), (x1, 3), (x0, 16 - f), (x1, 16 - f)): g.set(cx, cy, 4)
        g.rect(x0, 17 - f, x1, 16, 6)                                 # their sides
    g.vline(9, 3, 16, 3)                                              # between them
    g.rect(2, 8, 17, 8, 13)                                           # strap over the lids
    g.vline(13, 17 - f, 16, 13)                                       # and down the front
    g.hline(1, 18, 17, 5); g.hline(1, 18, 18, 7)                      # the pallet's edge
    return g


def pallet_rack():
    """A pallet rack bay, 2 m, joining into a run: lit beams along the back and front, dark
    uprights at the corners, a loaded pallet in the bay (two case lids and a strap), the
    front in a 6 px strip: beam faces and the next shelf's load in shadow."""
    g = Grid(20, 20)
    f = front(2.0)
    yt = 17 - f
    g.rect(1, 2, 18, yt, 3)                                           # the bay, in shadow
    g.rect(3, 4, 16, yt - 2, 8)                                       # the load on top
    g.vline(9, 4, yt - 2, 4); g.vline(10, 4, yt - 2, 4)
    g.hline(3, 16, 7, 12)                                             # its strap
    g.hline(1, 18, 2, 11); g.hline(1, 18, 3, 9)                       # back beam
    g.hline(1, 18, yt, 11)                                            # front beam
    for x in (1, 17): g.rect(x, 2, x + 1, 17, 6)                      # uprights
    g.rect(3, yt + 1, 16, 15, 5)                                      # front: the shelf below
    g.rect(5, yt + 2, 14, 14, 7)
    g.hline(1, 18, 16, 10); g.hline(1, 18, 17, 6)                     # the lower beam's face
    return g


def dock_edge():
    """A loading dock's edge, 1.2 m, joining into a run (redrawn bold: the first stripe was
    lost on most seeds): the dock floor with a lit far seam, a 5 px hazard band of 4 px
    stripes, 14 against 1, along its edge, then its face in a 4 px front strip with two
    black rubber bumpers lit on top."""
    g = Grid(20, 20)
    f = front(1.2)
    yt = 18 - f
    g.rect(0, 2, 19, yt, 6); g.hline(0, 19, 2, 9)                     # dock floor
    for y in range(yt - 4, yt + 1):                                   # hazard band
        for x in range(20): g.px[y][x] = 14 if ((x + y) // 4) % 2 == 0 else 1
    g.rect(0, yt + 1, 19, 18, 5)                                      # the face
    for x in (3, 13): g.rect(x, yt + 1, x + 3, 18, 1); g.hline(x, x + 3, yt + 1, 9)   # bumpers
    return g


# --- Hab Ring's own pieces (phase 4) ------------------------------------------------------
# Drawn bold from the start (the prompt tests, 2026-10-31): detail 4-5 levels off what
# surrounds it, in shapes of 2 px or more; lone pixels turn to noise.

def bunk_double():
    """A double bed, 2x2 (redone after the user's redo, low detail): a dark outline; a padded
    headboard along the top (a lit far lip, two buttoned panels); two plump pillows, each lit
    on top and shaded along its bottom with a dark crease; the sheet's turned-down band (lit)
    over a quilted duvet (dark stitch lines every 6 px both ways, a lit puff in each square),
    a lit fold where it hangs over the foot; the bed's side and two legs in the front strip."""
    g = Grid(*footprint((2, 2)))
    g.rect(0, 0, 44, 43, 2)                                           # outline
    g.rect(1, 1, 43, 6, 6); g.hline(1, 43, 1, 11)                     # headboard, lit lip
    for x0 in (3, 23): g.rect(x0, 3, x0 + 18, 5, 9); g.rect(x0 + 8, 3, x0 + 9, 4, 3)   # its panels, buttons
    g.rect(1, 7, 43, 41, 8)                                           # mattress
    for x0 in (3, 23):                                                # pillows
        g.rect(x0, 8, x0 + 18, 15, 12); g.hline(x0 + 1, x0 + 17, 8, 14)
        g.rect(x0, 14, x0 + 18, 15, 7); g.rect(x0 + 8, 10, x0 + 10, 11, 8)   # shaded bottom, crease
        g.set(x0, 8, 8); g.set(x0 + 18, 8, 8); g.set(x0, 15, 8); g.set(x0 + 18, 15, 8)
    g.rect(1, 17, 43, 20, 13); g.hline(1, 43, 21, 4)                  # turned-down sheet, its shadow
    g.rect(1, 22, 43, 38, 9)                                          # duvet
    for y in range(22, 39, 6): g.hline(1, 43, y + 5, 5)               # stitch lines across
    for x in range(7, 43, 6): g.vline(x, 22, 38, 5)                   # and down
    for y in range(22, 38, 6):
        for x in range(2, 42, 6): g.rect(x + 1, y + 1, x + 2, y + 2, 12)   # a lit puff per square
    g.rect(1, 39, 43, 40, 12)                                         # the fold over the foot
    g.rect(1, 41, 43, 43, 5); g.hline(1, 43, 43, 3)                   # the bed's side
    g.rect(1, 44, 3, 46, 7); g.rect(41, 44, 43, 46, 7)                # legs
    return g


def bedside():
    """A bedside cabinet, 0.6 m: a top with a lit lip, a round lamp (a bright shade with a
    dark heart), a book, a 2 px front with a lit drawer pull."""
    g = Grid(20, 20)
    g.rect(3, 4, 16, 15, 8); g.hline(3, 16, 4, 12)                    # top, lit lip
    g.ellipse(7.5, 9.5, 3.4, 3.4, 13); g.ellipse(7.5, 9.5, 1.5, 1.5, 4)   # lamp shade
    g.rect(11, 7, 15, 13, 4); g.vline(11, 7, 13, 11)                  # a book, its lit spine
    g.rect(3, 16, 16, 17, 5); g.rect(8, 16, 11, 16, 13)               # front, pull
    return g


def galley(kind="plain"):
    """A galley counter, 0.9 m, joining into a kitchen run: a dark backsplash along the
    far edge, a top with a lit lip, a 3 px front of cupboard doors with lit handles; on top
    a sink (a dark basin with a lit rim and tap), a hob (four dark burner rings with lit
    middles), or a fridge instead (1.8 m: a plain top with vent slots, a 5 px lit front)."""
    g = Grid(20, 20)
    if kind == "fridge":
        g.rect(1, 2, 18, 12, 9); g.hline(1, 18, 2, 12)
        for y in (5, 8): g.rect(4, y, 15, y, 4)                        # vent slots
        g.rect(1, 13, 18, 17, 12); g.hline(1, 18, 15, 6)               # front, door seam
        g.rect(15, 13, 16, 14, 3); g.rect(15, 16, 16, 17, 3)           # handles
        return g
    g.rect(1, 2, 18, 3, 4)                                            # backsplash
    g.rect(1, 4, 18, 14, 9); g.hline(1, 18, 4, 12)                    # top, lit lip
    if kind == "sink":
        g.rect(4, 6, 15, 13, 12); g.rect(5, 7, 14, 12, 3)              # basin, lit rim
        g.rect(9, 5, 10, 7, 13)                                        # tap
        g.rect(8, 10, 11, 11, 6)                                       # drain
    if kind == "hob":
        for cx, cy in ((6, 7.5), (13, 7.5), (6, 11.5), (13, 11.5)):
            g.ellipse(cx, cy, 2.6, 2.0, 3); g.rect(int(cx) - 1, int(cy) - 1, int(cx), int(cy), 11)
    g.rect(1, 15, 18, 17, 6); g.vline(9, 15, 17, 3); g.vline(10, 15, 17, 3)   # doors
    g.rect(6, 15, 7, 16, 13); g.rect(12, 15, 13, 16, 13)              # handles
    return g


def basin():
    """A wash basin counter, 0.9 m, joining into a washroom counter: a pale top with a lit
    lip, an oval dark basin with a bright rim, a tap at its back, a 4 px dark front with
    the lit U-bend pipe in it."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 13, 10); g.hline(1, 18, 3, 13)                   # top
    g.ellipse(9.5, 8.5, 6.2, 4.0, 13); g.ellipse(9.5, 8.8, 4.8, 2.8, 3)   # basin, rim
    g.rect(9, 4, 10, 6, 6)                                            # tap
    g.rect(1, 14, 18, 17, 5)                                          # front, under the counter
    g.rect(9, 14, 10, 17, 11); g.rect(8, 17, 11, 17, 11)              # U-bend
    return g


def shower():
    """A shower stall: a lit frame, a dark ribbed tray with a bright drain ring, the shower
    head at the back, the glass door along the front, lit, with a dark handle."""
    g = Grid(20, 20)
    g.rect(1, 1, 18, 18, 11); g.hline(1, 18, 1, 13)                   # frame
    g.rect(3, 3, 16, 15, 4)                                           # tray
    for y in range(5, 15, 3): g.hline(4, 15, y, 6)                    # its ribs
    g.ellipse(9.5, 9.5, 2.4, 2.4, 12); g.rect(9, 9, 10, 10, 1)        # drain
    g.rect(8, 2, 11, 3, 13)                                           # shower head
    g.rect(1, 16, 18, 18, 9); g.hline(1, 18, 16, 13)                  # glass door
    g.rect(13, 17, 14, 18, 3)                                         # handle
    return g


def toilet():
    """A toilet: the cistern along the back (a lit lip, a dark flush button), the bowl below
    it, a bright seat ring round dark water, a 1 px front."""
    g = Grid(20, 20)
    g.rect(4, 2, 15, 6, 10); g.hline(4, 15, 2, 13)                    # cistern
    g.rect(8, 3, 11, 5, 3)                                            # flush button
    g.ellipse(9.5, 11.5, 5.4, 6.0, 12)                                # seat
    g.ellipse(9.5, 11.8, 3.2, 3.9, 3)                                 # water
    g.hline(6, 13, 18, 6)                                             # front
    return g


def treadmill():
    """A treadmill, 1x2 (redone after the user's redo, low detail and style): a dark outline;
    the console at the head (a rounded lit housing, a dark screen with bright digit blocks,
    two lit buttons); handlebars curving down both sides from it; the motor hood (lit, a dark
    vent grille); the belt dark with lit slats between grippy side decks (lit edges, dark
    tread marks); the rear roller cap lit; the feet in the front strip."""
    g = Grid(*footprint((1, 2)))
    g.rect(1, 0, 18, 8, 2)                                            # console's outline
    g.rect(2, 1, 17, 7, 10); g.hline(3, 16, 1, 13)                    # housing, lit top
    g.rect(4, 2, 15, 5, 2)                                            # screen
    for x in (5, 8, 11): g.rect(x, 3, x + 1, 4, 14)                   # its digits
    g.rect(4, 6, 5, 7, 13); g.rect(14, 6, 15, 7, 13)                  # buttons
    for x in (0, 18):                                                 # handlebars
        g.rect(x, 3, x + 1, 20, 12); g.vline(x + (1 if x == 0 else 0), 3, 20, 7)
    g.rect(2, 9, 17, 14, 2); g.rect(3, 9, 16, 13, 11)                 # motor hood
    for x in range(5, 15, 3): g.rect(x, 10, x + 1, 12, 4)             # its vents
    g.rect(1, 15, 18, 43, 2)                                          # deck outline
    for x0 in (2, 15):                                                # side decks
        g.rect(x0, 15, x0 + 2, 42, 7); g.vline(x0 if x0 == 2 else x0 + 2, 15, 42, 11)
        for y in range(17, 42, 5): g.hline(x0, x0 + 2, y, 4)          # tread marks
    g.rect(5, 15, 14, 42, 2)                                          # belt
    for y in range(16, 42, 3): g.hline(6, 13, y, 6)                   # its slats
    g.rect(5, 41, 14, 42, 10)                                         # rear roller cap
    g.rect(1, 43, 18, 44, 5)                                          # front
    g.rect(2, 45, 4, 46, 8); g.rect(15, 45, 17, 46, 8)                # feet
    return g


def weight_rack():
    """A dumbbell rack, 1 m, joining into a run: a dark frame, two dumbbells on the top
    tier (bright discs on lit bars), a 3 px front with the lower tier's discs."""
    g = Grid(20, 20)
    g.rect(1, 4, 18, 14, 4); g.hline(1, 18, 4, 9)                     # frame
    for y in (6, 10):
        g.rect(4, y, 15, y + 1, 9)                                    # bar
        g.rect(2, y - 1, 5, y + 2, 13); g.rect(14, y - 1, 17, y + 2, 13)   # discs
    g.rect(1, 15, 18, 17, 3)                                          # front, the lower tier
    for x in (3, 7, 12, 16): g.rect(x - 1, 15, x, 17, 10)
    return g


def weight_bench():
    """A weight bench, 1x2 (redone after the user's redo, low detail and style): a barbell
    across the head (a lit bar with knurled dark grips, two plates each end: dark discs with
    lit rims and a bright hub) resting on J-hook uprights; the padded backrest and seat (two
    pads, each lit on top, shaded down its sides, a dark rolled edge), a dark hinge between;
    the steel frame showing round them, a wide foot bar; legs in the front strip."""
    g = Grid(*footprint((1, 2)))
    for x in (3, 15): g.rect(x, 1, x + 1, 10, 8); g.rect(x - 1, 4, x + 2, 5, 11)   # uprights, J-hooks
    g.rect(0, 3, 19, 6, 2)                                            # bar's shadow / outline
    g.rect(0, 4, 19, 5, 13)                                           # bar
    for x in (6, 8, 11, 13): g.rect(x, 4, x, 5, 6)                    # knurled grips
    for x0 in (0, 16):                                                # plates
        g.rect(x0, 0, x0 + 3, 9, 3); g.rect(x0, 0, x0 + 3, 0, 10); g.rect(x0, 9, x0 + 3, 9, 6)
        g.vline(x0 + (3 if x0 == 0 else 0), 0, 9, 10); g.rect(x0 + 1, 4, x0 + 2, 5, 14)
    g.rect(4, 11, 15, 43, 6)                                          # frame
    for y0, y1 in ((12, 30), (33, 41)):                               # backrest, seat
        g.rect(5, y0, 14, y1, 2)                                      # rolled edge
        g.rect(6, y0 + 1, 13, y1 - 1, 9); g.rect(7, y0 + 1, 12, y1 - 2, 12); g.hline(7, 12, y0 + 1, 14)
    g.rect(6, 31, 13, 32, 3); g.rect(9, 31, 10, 32, 10)               # hinge
    g.rect(2, 42, 17, 43, 8); g.hline(2, 17, 42, 11)                  # foot bar
    g.rect(2, 44, 17, 44, 4)                                          # front
    g.rect(2, 45, 4, 46, 7); g.rect(15, 45, 17, 46, 7)                # legs
    return g


def boulder(kind="medium"):
    """A boulder: one rock (medium or small), or a pair, drawn by `rock`."""
    g = Grid(20, 20)
    if kind == "small": rock(g, 10, 11, 5.0, 4.2, 10)
    elif kind == "pair": rock(g, 7, 8, 5.6, 4.8, -15); rock(g, 14, 14, 4.4, 3.8, 20)
    else: rock(g, 10, 10, 8.0, 6.6, 8)
    return g


def boulder_big():
    """A big boulder, 2x2: one great rock split by two dark cracks into lit and shaded
    faces, a small rock at its foot."""
    g = Grid(*footprint((2, 2)))
    rock(g, 21, 21, 19, 16, 5)
    for k in range(14): g.rect(14 + k, 10 + k // 2, 15 + k, 10 + k // 2, 3)     # cracks
    for k in range(10): g.rect(28 - k // 3, 22 + k, 29 - k // 3, 22 + k, 3)
    g.blob(30, 14, 6, 4, 20, 12)                                      # a second lit face
    rock(g, 38, 40, 5, 4, 0)
    return g


def rubble(kind="a"):
    """An ore pile: a heap of rocks of several sizes, ore glints (2 px, bright) among them;
    `b` a smaller, flatter heap."""
    g = Grid(20, 20)
    if kind == "b":
        g.ellipse(10, 12, 8.2, 5.4, 4)
        for cx, cy, r in ((6, 11, 3.0), (11, 10, 3.6), (15, 13, 2.8), (9, 14, 2.6)): rock(g, cx, cy, r, r * 0.85, 0, 9)
        for x, y in ((12, 13), (5, 13)): g.rect(x, y, x + 1, y + 1, 14)
        return g
    g.ellipse(10, 11, 9.0, 7.4, 4)                                    # the heap's base
    for cx, cy, r in ((6, 8, 3.4), (13, 7, 3.8), (10, 12, 4.2), (4, 13, 2.8), (16, 13, 3.0)):
        rock(g, cx, cy, r, r * 0.85, 0, 9)
    for x, y in ((9, 6), (14, 11), (6, 14)): g.rect(x, y, x + 1, y + 1, 14)    # ore glints
    return g


def ore_vein():
    """An ore vein (decal, flat): dark cracks across the floor with clusters of bright
    crystals along them."""
    g = Grid(20, 20)
    for k in range(17): g.rect(1 + k, 14 - (k * 2) // 3, 2 + k, 15 - (k * 2) // 3, 2)   # the crack
    g.rect(9, 9, 10, 17, 2)                                           # a branch
    for x, y, w, h in ((4, 10, 3, 2), (11, 6, 2, 3), (14, 4, 3, 2), (8, 14, 2, 3)):
        g.rect(x, y, x + w - 1, y + h - 1, 13); g.hline(x, x + w - 1, y + h - 1, 9)   # crystals
    return g


def ore_cart():
    """An ore cart, 1 m: a steel box with a lit rim heaped with rocks and ore glints, its
    side in a 3 px front strip with two dark wheels."""
    g = Grid(20, 20)
    f = front(1.0)
    yt = 17 - f
    g.rect(2, 3, 17, yt, 11); g.rect(4, 5, 15, yt - 2, 3)             # rim, the box's inside
    for cx, cy, r in ((7, 8, 2.6), (12, 8, 2.8), (9, 11, 2.6), (14, 12, 2.2)): rock(g, cx, cy, r, r, 0, 9)
    g.rect(6, 6, 7, 7, 14); g.rect(12, 11, 13, 12, 14)                # glints
    g.rect(2, yt + 1, 17, 17, 6); g.hline(2, 17, yt + 1, 9)           # side
    for x in (4, 13): g.rect(x, 17, x + 2, 18, 2)                     # wheels
    return g


def rail():
    """A mine rail, joining into tracks (path): one straight run east to west, rows 6-13:
    dark sleepers across it every 4 px, two lit rails (rows 7-8 and 11-12), a fishplate
    joint at the centre."""
    g = Grid(20, 20)
    for x in range(1, 20, 4): g.rect(x, 6, x + 1, 13, 5)              # sleepers
    for y in (7, 11): g.hline(0, 19, y, 13); g.hline(0, 19, y + 1, 9)   # rails
    g.rect(8, 7, 11, 8, 6); g.rect(8, 11, 11, 12, 6)                  # fishplates
    return g


def drill_rig():
    """A drill rig, 2x2: a platform with a lit lip, the mast's lattice from above (a bright
    frame, dark inside, a cross of braces), the drill head ring at its foot, an engine box
    with vent slots, the platform's face in a 4 px front strip with lit bolts."""
    g = Grid(*footprint((2, 2)))
    f = front(1.3)
    yt = 46 - f
    g.rect(1, 3, 43, yt, 6); g.hline(1, 43, 3, 10)                    # platform
    g.rect(8, 6, 26, 24, 12); g.rect(10, 8, 24, 22, 3)                # mast frame
    for k in range(15): g.rect(10 + k, 8 + k, 11 + k, 8 + k, 9); g.rect(23 - k, 8 + k, 24 - k, 8 + k, 9)   # braces
    g.ellipse(17, 32, 6, 5, 13); g.ellipse(17, 32, 3.4, 2.8, 2)       # drill head
    g.rect(31, 8, 41, 30, 9); g.hline(31, 41, 8, 12)                  # engine box
    for y in range(12, 29, 4): g.rect(33, y, 39, y + 1, 3)            # vents
    g.rect(1, yt + 1, 43, 46, 4)                                      # face
    for x in range(4, 43, 8): g.rect(x, yt + 2, x + 1, yt + 3, 11)    # bolts
    return g


def strut(kind="single"):
    """A steel prop, 3 m (tall: its height in a 9 px front strip): a bright top plate, the
    column below it with a lit left edge, a base plate; `pair` two of them braced."""
    g = Grid(20, 20)
    xs = (7,) if kind == "single" else (3, 12)
    for x in xs:
        g.rect(x - 1, 2, x + 6, 7, 12); g.hline(x - 1, x + 6, 2, 14)  # top plate
        g.rect(x + 1, 8, x + 4, 16, 7); g.vline(x + 1, 8, 16, 11)     # column
        g.rect(x - 1, 17, x + 6, 18, 5)                               # base plate
    if kind == "pair":
        for k in range(7): g.rect(8 + k, 9 + k, 9 + k, 9 + k, 9)      # a brace
    return g


def hopper():
    """An ore hopper, 2x1, 2 m: a square bright rim, its sloped sides stepping down in
    darker bands to a dark mouth heaped with ore, the conveyor's end at its foot in the
    6 px front strip: a dark ribbed belt between lit rails."""
    g = Grid(*footprint((2, 1)))
    f = front(2.0)
    yt = 18 - f
    g.rect(6, 0, 38, yt, 12)                                          # rim
    for i, v in enumerate((9, 7, 5)): g.rect(8 + i * 2, 2 + i, 36 - i * 2, yt - 1 - i, v)   # sloped sides
    g.rect(14, 5, 30, yt - 4, 2)                                      # mouth
    for cx in (17, 22, 27): rock(g, cx, 7, 2.4, 2.0, 0, 9)
    g.rect(20, 6, 21, 7, 14)
    g.rect(0, yt + 1, 44, 18, 2)                                      # belt
    for x in range(1, 44, 3): g.vline(x, yt + 1, 18, 5)               # its ribs
    g.hline(0, 44, yt + 1, 11)                                        # rail
    return g


# --- Reactor's own pieces (phase 4) -------------------------------------------------------

PIPE_PROFILE = (5, 9, 12, 10, 8, 5)     # the pipe's rows 7-12, top to bottom (pipe())


def reactor_vessel():
    """A reactor vessel, 2x2: a round dome with a lit crescent, a dark rim ringed with
    bright bolts, a central hatch (a dark ring, a lit handle), the side below the rim in a
    5 px front strip with two dark bands."""
    g = Grid(*footprint((2, 2)))
    g.ellipse(22.5, 26, 21, 19, 6)                                    # side
    g.hline(3, 41, 40, 3); g.hline(5, 39, 43, 3)                      # bands
    g.ellipse(22.5, 21, 21, 19, 4)                                    # rim
    g.ellipse(22.5, 21, 17, 15, 9)                                    # dome
    g.ellipse(20, 17, 13, 10, 12, inner=0.8)                          # lit crescent
    for k in range(16):                                               # bolts
        a = 2 * math.pi * k / 16
        x, y = 22.5 + 19 * math.cos(a), 21 + 17 * math.sin(a)
        g.rect(int(x), int(y), int(x) + 1, int(y) + 1, 12)
    g.ellipse(22.5, 21, 6, 5.4, 3); g.ellipse(22.5, 21, 3.6, 3.2, 8)   # hatch
    g.rect(20, 20, 25, 21, 14)                                        # its handle
    return g


def pump():
    """A pump on a base plate, its pipe stubs reaching both edges in the pipe's profile so
    it sits in a pipe run: a motor with dark cooling fins and a lit top, the round pump
    casing with a bright eye, a 2 px base."""
    g = Grid(20, 20)
    for y, v in zip(range(7, 13), PIPE_PROFILE): g.hline(0, 19, y, v)  # pipe stubs
    g.rect(2, 3, 9, 15, 8); g.hline(2, 9, 3, 12)                      # motor
    for x in (3, 5, 7): g.rect(x, 5, x, 14, 4)                         # fins
    g.ellipse(14, 9.5, 4.6, 4.6, 10); g.ellipse(14, 9.5, 2.2, 2.2, 3)  # casing
    g.rect(13, 8, 14, 9, 14)                                          # its eye
    g.rect(1, 16, 18, 17, 5)                                          # base
    return g


def valve():
    """A valve where two pipes cross: the four arms in the pipe's profile reaching the
    edges, a bright hand wheel over the crossing (a lit rim, dark spokes, a hub)."""
    g = Grid(20, 20)
    for y, v in zip(range(7, 13), PIPE_PROFILE): g.hline(0, 19, y, v)
    for x, v in zip(range(7, 13), PIPE_PROFILE): g.vline(x, 0, 19, v)
    g.ellipse(10, 10, 7.4, 7.4, 13); g.ellipse(10, 10, 5.6, 5.6, 4)   # wheel rim
    g.rect(9, 3, 10, 16, 11); g.rect(3, 9, 16, 10, 11)                # spokes
    g.rect(8, 8, 11, 11, 6); g.rect(9, 9, 10, 10, 14)                 # hub
    return g


def turbine():
    """A turbine, 2x1: a long housing lying left to right shaded like a pipe (a lit band
    along its top), bright flange rings across it, the shaft and coupling at the right end,
    its base in a 2 px front strip."""
    g = Grid(*footprint((2, 1)))
    for y, v in zip(range(2, 16), (4, 7, 9, 11, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4)): g.hline(2, 36, y, v)
    for x in (2, 12, 24, 35): g.rect(x, 1, x + 1, 16, 13); g.vline(x + 1, 1, 16, 7)   # flanges
    g.rect(37, 7, 41, 10, 9); g.hline(37, 41, 7, 12)                  # shaft
    g.rect(41, 5, 43, 12, 6); g.vline(41, 5, 12, 11)                  # coupling
    g.rect(0, 17, 44, 18, 5)                                          # base
    return g


def heat_exchanger():
    """A heat exchanger, 2x1: a finned block (2 px lit fins on dark gaps) in a frame with a
    lit lip, flanged pipe stubs at both ends in the pipe's profile, a 3 px front strip."""
    g = Grid(*footprint((2, 1)))
    for y, v in zip(range(7, 13), PIPE_PROFILE): g.hline(0, 44, y, v)  # pipe through
    g.rect(6, 2, 38, 15, 6); g.hline(6, 38, 2, 11)                    # frame
    for x in range(8, 37, 4): g.rect(x, 4, x + 1, 13, 12); g.rect(x + 2, 4, x + 3, 13, 3)   # fins
    for x in (4, 39): g.rect(x, 5, x + 1, 14, 9); g.hline(x, x + 1, 5, 13)   # flanges
    g.rect(6, 16, 38, 18, 4)                                          # front
    return g


def control_panel(kind="gauges"):
    """A control panel, 1.2 m, joining into a panel bank: a sloped desk with a lit lip and,
    on it, two round gauges (a dark rim, a lit face, a dark needle) and a row of lit
    buttons; or (`levers`) three levers, lit knobs on dark slots; a 4 px front."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 13, 7); g.hline(1, 18, 3, 11)                    # desk
    if kind == "levers":
        for x in (4, 9, 14):
            g.rect(x, 5, x + 1, 11, 2); g.rect(x - 1, 6 if x != 9 else 9, x + 2, 7 if x != 9 else 10, 13)
    else:
        for cx in (6, 13):
            g.ellipse(cx, 7.5, 3.6, 3.6, 3); g.ellipse(cx, 7.5, 2.4, 2.4, 12)
            g.rect(cx, 6, cx, 7, 2)                                   # needle
        for x in range(3, 17, 4): g.rect(x, 11, x + 1, 12, 13)        # buttons
    g.rect(1, 14, 18, 17, 4); g.hline(1, 18, 14, 6)                   # front
    return g


def catwalk():
    """A catwalk (grid decal, flat): a 4 px frame, lit on its outer edge, round a grating
    of dark 2 px squares between lit bars (period 3, so the 12 px inside holds it evenly);
    areas join into a walkway."""
    g = Grid(20, 20)
    for y in range(20):
        for x in range(20):
            d = min(x, y, 19 - x, 19 - y)
            g.px[y][x] = 12 if d == 0 else 8 if d < 4 else (2 if ((x - 4) % 3 and (y - 4) % 3) else 9)
    return g


# --- Hydroponics' own pieces (phase 4) ----------------------------------------------------

def rosette(g, cx, cy, r, n=5, turn=0, leaf=12, rib=6):
    """A plant from above (bold): `n` broad pointed leaves round a centre, each bright with
    a darker base toward the heart, the soil showing between them, a dark heart."""
    for k in range(n):
        a = math.radians(turn + 360 * k / n)
        g.blob(cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55, r * 0.55, max(1.4, r * 0.32), math.degrees(a), leaf)
    for k in range(n):
        a = math.radians(turn + 360 * k / n)
        g.blob(cx + math.cos(a) * r * 0.3, cy + math.sin(a) * r * 0.3, r * 0.25, max(1.0, r * 0.18), math.degrees(a), rib)
    g.rect(int(cx) - 1, int(cy) - 1, int(cx), int(cy), 3)
    return g


def grow_bed(kind="leafy"):
    """A grow bed, 0.6 m, joining into a long bed: a trough with a lit rim, dark soil, two
    plants (rosettes, or `herbs`: rows of small bright clumps), a 2 px front."""
    g = Grid(20, 20)
    g.rect(1, 2, 18, 15, 6); g.hline(1, 18, 2, 10)                    # trough rim
    g.rect(3, 4, 16, 13, 1)                                           # soil
    if kind == "herbs":
        for y in (6, 10):
            for x in range(4, 16, 4): g.rect(x, y, x + 2, y + 1, 12); g.set(x + 1, y + 1, 7)
    else:
        rosette(g, 6, 8.5, 5.0, 5, -90); rosette(g, 13.5, 8.5, 5.0, 5, -54)
    g.rect(1, 16, 18, 17, 5)                                          # front
    return g


def raised_planter():
    """A raised planter (grid decal): a 4 px lit rim round dark soil with leaf clumps every
    6 px (so the 12 px inside holds them evenly); areas join into shaped beds."""
    g = Grid(20, 20)
    for y in range(20):
        for x in range(20):
            d = min(x, y, 19 - x, 19 - y)
            g.px[y][x] = 12 if d == 0 else 9 if d < 3 else 5 if d < 4 else 1
    for cy in (7, 13):
        for cx in (7, 13): g.rect(cx - 2, cy, cx + 1, cy, 12); g.rect(cx - 1, cy - 2, cx, cy + 2, 12); g.rect(cx - 1, cy, cx, cy, 8)   # leaf clumps
    return g


def planter(kind="box"):
    """A planter: a square box with a lit rim, dark soil and a big rosette spilling past it;
    or (`pot`) a round pot with spiky grass."""
    g = Grid(20, 20)
    if kind == "pot":
        g.ellipse(10, 11, 7.2, 6.6, 4); g.ellipse(10, 10, 7.2, 6.6, 8); g.ellipse(10, 10, 5.6, 5.0, 1)   # pot, rim, soil
        for ang in range(0, 360, 30):                                 # a tuft of grass blades all round
            a = math.radians(ang + 15)
            for t in range(1, 9):
                v = 14 if t > 5 else 12
                g.set(10 + math.cos(a) * t, 10 + math.sin(a) * t, v); g.set(10 + math.cos(a) * t + 0.7 * math.sin(a), 10 + math.sin(a) * t - 0.7 * math.cos(a), v)
        g.rect(9, 9, 10, 10, 3)
        return g
    g.rect(3, 4, 16, 16, 6); g.hline(3, 16, 4, 10); g.rect(5, 6, 14, 14, 1)   # box, soil
    rosette(g, 9.5, 10, 7.0, 5, -90)
    g.rect(3, 17, 16, 18, 5)                                          # front
    return g


def seed_tray():
    """Seed trays on a bench, joining into a run: the bench top with a lit lip, a tray of
    four dark cells each with a bright two-leaved sprout, a 2 px bench front."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 15, 7); g.hline(1, 18, 3, 11)                    # bench top
    g.rect(3, 5, 16, 14, 10)                                          # tray
    for x0, y0 in ((4, 6), (10, 6), (4, 10), (10, 10)):
        g.rect(x0, y0, x0 + 4, y0 + 2, 2)                             # cell
        g.rect(x0 + 1, y0, x0 + 1, y0 + 1, 13); g.rect(x0 + 3, y0, x0 + 3, y0 + 1, 13); g.rect(x0 + 2, y0 + 1, x0 + 2, y0 + 2, 9)
    g.rect(1, 16, 18, 17, 4)                                          # bench front
    return g


def dwarf_tree():
    """A dwarf tree: a round crown of leaf clumps (each lit on top, dark between them),
    the pot's rim and front showing below it."""
    g = Grid(20, 20)
    g.rect(5, 15, 14, 18, 7); g.hline(5, 14, 15, 11)                  # pot
    g.ellipse(10, 9, 8.6, 7.6, 3)                                     # crown's shade
    for cx, cy in ((6, 6), (13, 6), (10, 10), (5, 11), (15, 11), (9, 4)):
        g.ellipse(cx, cy, 3.4, 3.0, 8); g.ellipse(cx - 0.6, cy - 0.8, 2.0, 1.6, 12)
    return g


def nutrient_mixer():
    """A nutrient mixer: a round tank with a lit crescent and a dark lid ring, a dial (a dark
    rim, a lit face, a needle), a hose out, a 2 px base."""
    g = Grid(20, 20)
    g.ellipse(9, 9, 6.8, 6.8, 5); g.ellipse(9, 9, 5.6, 5.6, 9)        # tank, lid ring
    g.ellipse(8, 7.5, 4.0, 3.2, 12, inner=0.6)                        # crescent
    g.rect(8, 8, 10, 10, 3)                                           # filler cap
    g.ellipse(16, 14, 3.0, 3.0, 2); g.ellipse(16, 14, 1.8, 1.8, 13); g.rect(16, 13, 16, 14, 2)   # dial
    for k in range(6): g.rect(14 - k, 15 + k // 2, 15 - k, 16 + k // 2, 7)   # hose
    g.rect(2, 17, 15, 18, 5)                                          # base
    return g


def grow_light():
    """A grow light, joining into a long bar: plants below in shadow, a bright light bar
    across the middle in a dark frame, its two hangers lit."""
    g = Grid(20, 20)
    g.rect(1, 2, 18, 17, 2)                                           # bed in the dark
    for cx in (5, 14): rosette(g, cx, 5, 4.0, 5, 0, leaf=6, rib=3); rosette(g, cx, 14, 4.0, 5, 30, leaf=6, rib=3)
    g.rect(0, 7, 19, 12, 4); g.rect(0, 8, 19, 11, 14)                 # bar, its light
    for x in (4, 15): g.rect(x, 6, x + 1, 13, 9)                      # hangers
    return g


# --- the Airlock's own pieces (phase 4) ------------------

def slab(g, cx, cy, w, h, angle, v):
    """A rotated rectangle (a door leaf, a hull panel, a strut): pixels whose centres fall
    inside it."""
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    for y in range(g.h):
        for x in range(g.w):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            if abs(dx * ca + dy * sa) <= w / 2 and abs(-dx * sa + dy * ca) <= h / 2: g.px[y][x] = v
    return g


def stripes(g, x0, y0, x1, y1, period=4, hi=14, lo=1):
    """A band of bold diagonal hazard stripes."""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1): g.set(x, y, hi if ((x + y) // period) % 2 == 0 else lo)
    return g


def airlock_door():
    """The great outer door, 2x2, breached: the bulkhead's top with a lit lip and bright
    rivets, a dark breach through it with torn, jagged edges, the bulkhead's face below in
    a 9 px front strip with a hazard band, and one door leaf torn off, bent and lying on
    the floor in front."""
    g = Grid(*footprint((2, 2)))
    g.rect(0, 1, 44, 12, 8); g.hline(0, 44, 1, 12)                    # bulkhead top
    for x in (3, 9, 34, 40): g.rect(x, 5, x + 1, 6, 13)               # rivets
    g.rect(0, 13, 44, 21, 5)                                          # its face
    stripes(g, 0, 18, 44, 21)
    for y in range(1, 22):                                            # the breach, jagged
        w = 7 + (y * 7) % 4
        g.rect(22 - w, y, 22 + w - (y % 3), y, 1)
    for y in range(2, 22, 3): g.rect(22 - 7 - (y * 7) % 4 - 1, y, 22 - 7 - (y * 7) % 4, y, 12)   # its torn lit edge
    slab(g, 24, 34, 26, 8, -14, 9)                                    # the torn-off leaf
    slab(g, 24, 34, 26, 2, -14, 13)                                   # its lit ridge
    slab(g, 24, 37, 24, 2, -14, 4)                                    # its shaded edge
    return g


def inner_door(kind="sealed"):
    """An inner bulkhead door, 2x1: the bulkhead's top with a lit lip, its face in a 9 px
    front strip with the door: two leaves with a dark seam, warning lights either side,
    a hazard sill; `forced` the leaves pried apart on a dark, jagged gap."""
    g = Grid(*footprint((2, 1)))
    g.rect(0, 1, 44, 8, 8); g.hline(0, 44, 1, 12)                     # top
    g.rect(0, 9, 44, 18, 5)                                           # face
    g.rect(10, 9, 34, 16, 9); g.hline(10, 34, 9, 12)                  # door
    if kind == "forced":
        for y in range(9, 17): g.rect(19 - (y % 2), y, 25 + (y % 3), y, 1)
    else:
        g.rect(22, 9, 23, 16, 3)                                      # seam
    for x in (5, 38): g.rect(x, 10, x + 2, 12, 14); g.rect(x, 13, x + 2, 13, 3)   # warning lights
    stripes(g, 10, 17, 34, 18, period=3)
    return g


def suit_rack(kind="suit"):
    """An EVA suit on its rack, 2 m, joining into a suit bay: the rack rail along the back,
    the helmet from above (bright, a dark visor facing the front), the shoulders and the
    life-support pack with lit vents, the legs and boots in the 6 px front strip;
    `empty` the rack's hooks and a helmet on the shelf."""
    g = Grid(20, 20)
    g.rect(1, 2, 18, 3, 4); g.hline(1, 18, 2, 9)                      # rack rail
    if kind == "empty":
        for x in (4, 14): g.rect(x, 4, x + 1, 7, 11)                  # hooks
        g.ellipse(9.5, 9, 3.6, 3.4, 13); g.rect(7, 10, 12, 11, 2)     # a helmet
        g.rect(1, 13, 18, 18, 3)
        return g
    g.rect(3, 4, 16, 12, 10); g.hline(3, 16, 4, 12)                   # shoulders and pack
    g.rect(6, 5, 13, 8, 6); g.rect(7, 6, 12, 6, 12)                   # pack, its vents
    g.ellipse(9.5, 9.5, 3.4, 3.0, 13); g.rect(7, 10, 12, 11, 2)       # helmet, visor
    g.rect(4, 13, 15, 16, 9); g.vline(9, 13, 16, 4); g.vline(10, 13, 16, 4)   # legs
    g.rect(4, 17, 8, 18, 5); g.rect(11, 17, 15, 18, 5)                # boots
    return g


def helmet_shelf():
    """A shelf of helmets and gloves, 1.5 m, joining into a run: the top with a lit lip, two
    bright helmets with dark visors, a pair of gloves, a 5 px front of shelves."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 12, 6); g.hline(1, 18, 3, 10)                    # top
    for cx in (5.5, 14.5): g.ellipse(cx, 7.5, 3.4, 3.2, 13); g.rect(int(cx) - 2, 9, int(cx) + 2, 10, 2)
    g.rect(9, 4, 10, 7, 9)                                            # gloves
    g.rect(1, 13, 18, 17, 3); g.hline(1, 18, 15, 8)                   # shelves
    for x in (3, 8, 13): g.rect(x, 13, x + 2, 14, 11)
    return g


def o2_rack():
    """A rack of oxygen bottles, 1.5 m, joining into a run (redone after the user's redo, low
    detail): three big bottles in a row, each from above a round shoulder (a dark rim, a lit
    crescent) with its valve (a dark body under a bright hand wheel ring); a lit strap across
    them; the frame's rail behind; the bottles' sides in a 5 px front strip, round-shaded (lit
    left of centre, dark at their edges) with a bright band, dark gaps between them."""
    g = Grid(20, 20)
    g.rect(0, 2, 19, 3, 5); g.hline(0, 19, 2, 9)                      # the frame's back rail
    for cx in (3, 9.5, 16):
        g.ellipse(cx, 8, 3.4, 3.4, 3)                                 # shoulder's dark rim
        g.ellipse(cx, 8, 2.6, 2.6, 8)                                 # shoulder
        g.ellipse(cx - 0.8, 7.2, 1.8, 1.4, 12)                        # lit crescent
        g.ellipse(cx, 8, 1.6, 1.6, 14); g.ellipse(cx, 8, 0.8, 0.8, 2)  # hand wheel, valve body
    g.rect(0, 12, 19, 13, 11); g.hline(0, 19, 13, 6)                  # strap
    for x0 in (0, 7, 13):                                             # sides
        for x, v in zip(range(x0, x0 + 6), (5, 10, 12, 9, 7, 4)): g.vline(x, 14, 18, v)
    for x in (6, 12): g.vline(x, 14, 18, 2)                           # gaps between bottles
    g.rect(0, 16, 19, 16, 14); g.vline(6, 16, 16, 2); g.vline(12, 16, 16, 2)   # the band
    return g


def decon_booth():
    """A decontamination booth, 1x2, 2 m: a lit frame, a grated floor (dark slots), two
    bright spray rings, the door in the 6 px front strip with a dark window and a handle."""
    g = Grid(*footprint((1, 2)))
    g.rect(1, 1, 18, 40, 11); g.hline(1, 18, 1, 13)                   # frame
    g.rect(3, 3, 16, 38, 5)                                           # floor
    for y in range(5, 38, 3): g.rect(4, y, 15, y, 2)                  # grate slots
    for cy in (12, 28): g.ellipse(9.5, cy, 6.4, 3.6, 13, inner=0.65)  # spray rings
    g.rect(1, 41, 18, 46, 8); g.rect(5, 42, 14, 44, 2)                # door, window
    g.rect(15, 44, 16, 45, 13)                                        # handle
    return g


def pressure_console(kind="gauges"):
    """A pressure console, 1.2 m, joining into a console bank: a sloped desk with a lit lip,
    two pressure gauges and a big bright cycle switch on a dark collar; or (`screen`) a dark
    screen with lit bars and the switch; a 4 px front."""
    g = Grid(20, 20)
    g.rect(1, 3, 18, 13, 7); g.hline(1, 18, 3, 11)                    # desk
    if kind == "screen":
        g.rect(3, 5, 11, 11, 2)
        for i, w in enumerate((6, 4, 7)): g.rect(4, 6 + 2 * i, 4 + w - 1, 6 + 2 * i, 12)
    else:
        for cx in (5, 10): g.ellipse(cx, 7, 2.4, 2.4, 3); g.ellipse(cx, 7, 1.4, 1.4, 12)
    g.ellipse(15, 8.5, 3.0, 3.0, 2); g.ellipse(15, 8.5, 2.0, 2.0, 14)  # cycle switch
    g.rect(1, 14, 18, 17, 4); g.hline(1, 18, 14, 6)                   # front
    return g


def beacon():
    """A rotating warning beacon on a post, 2 m: a bright dome in a dark cage of bars on a
    lit collar, the post below it in the 6 px front strip, a base plate."""
    g = Grid(20, 20)
    g.rect(5, 2, 14, 11, 6); g.hline(5, 14, 2, 10)                    # collar
    g.ellipse(9.5, 6.5, 4.0, 4.0, 14)                                 # dome
    g.rect(9, 2, 10, 11, 3); g.rect(5, 6, 14, 7, 3)                   # cage bars
    g.rect(9, 12, 10, 16, 8); g.vline(9, 12, 16, 11)                  # post
    g.rect(5, 17, 14, 18, 5)                                          # base
    return g


def rover():
    """A moon rover, 2x2, driving left to right, in the house view (redone after the user's
    redo, wrong perspective): the deck from above in the top part, its side in a 9 px front
    strip. On the deck: the cab at the left under a rounded dark glass canopy with a lit
    glint, a seat behind it, a ribbed cargo bed at the right, the antenna mast with a bright
    dish, the far wheels' tops showing above the deck's edge. In the front strip: the side
    panel (lit top edge, a dark sill) and two big round wheels (dark tyres with lit tread
    blocks, bright hubs) reaching the bottom."""
    g = Grid(*footprint((2, 2)))
    for x in (5, 31): g.rect(x, 3, x + 9, 6, 4); g.hline(x, x + 9, 3, 7)   # far wheels' tops
    g.rect(1, 6, 43, 34, 2)                                           # deck outline
    g.rect(2, 7, 42, 33, 8); g.hline(2, 42, 7, 12)                    # deck, lit far edge
    g.ellipse(11, 20, 9, 10, 2); g.ellipse(11, 20, 8, 9, 4)           # canopy
    g.ellipse(9, 16, 4, 3, 12)                                        # glint
    g.rect(21, 13, 25, 27, 6); g.hline(21, 25, 13, 10)                # seat
    g.rect(27, 10, 41, 31, 5)                                         # cargo bed
    for x in range(28, 41, 3): g.rect(x, 11, x, 30, 2)                # ribs
    g.rect(38, 8, 39, 12, 9); g.ellipse(36, 9, 3.2, 2.2, 14)          # mast, dish
    g.rect(1, 35, 43, 40, 9); g.hline(1, 43, 35, 13); g.rect(1, 41, 43, 41, 3)   # side panel, sill
    for cx in (10, 35):                                               # near wheels
        g.ellipse(cx, 40, 6.6, 6.6, 2)
        for k in range(8):
            a = math.radians(22.5 + 45 * k)
            g.rect(int(cx + 5 * math.cos(a)) - 1, int(40 + 5 * math.sin(a)) - 1, int(cx + 5 * math.cos(a)), int(40 + 5 * math.sin(a)), 8)
        g.ellipse(cx, 40, 2.6, 2.6, 12); g.rect(cx - 1, 39, cx, 40, 14)
    return g


def cargo_sled():
    """A towed cargo sled, 2x1: a tow bar to the left, a flat bed with lit runners, three
    cases on it (ribbed lids, dark bumpers) under a bright strap, a 2 px front."""
    g = Grid(*footprint((2, 1)))
    g.rect(0, 8, 6, 9, 12)                                            # tow bar
    g.rect(6, 2, 44, 15, 5); g.hline(6, 44, 2, 9)                     # bed
    for x0, x1 in ((8, 18), (20, 30), (32, 42)):
        g.rect(x0, 4, x1, 13, 9)
        for x in range(x0 + 2, x1 - 1, 2): g.vline(x, 5, 12, 6)
        for cx, cy in ((x0, 4), (x1 - 1, 4), (x0, 12), (x1 - 1, 12)): g.rect(cx, cy, cx + 1, cy + 1, 3)
    g.rect(6, 8, 44, 9, 13)                                           # strap
    g.rect(6, 16, 44, 17, 4); g.hline(6, 44, 18, 11)                  # front, runners
    return g


def hose_reel():
    """An air hose on a reel: the flange's edge as a crescent below, the hose wound round
    in bright turns with dark lines between, a dark hub, the nozzle lying out to the side."""
    g = Grid(20, 20)
    g.ellipse(9.5, 10.5, 8.2, 7.8, 4)                                 # flange
    for r, v in ((7.2, 12), (6.0, 5), (5.0, 12), (3.8, 5), (2.8, 12)): g.ellipse(9.5, 9.5, r, r * 0.95, v)
    g.ellipse(9.5, 9.5, 1.8, 1.8, 2)                                  # hub
    g.rect(15, 15, 18, 17, 13); g.rect(18, 14, 19, 18, 6)             # nozzle
    return g


def debris(kind="mixed"):
    """Debris from the breach: a bent hull panel (ribbed, a torn edge) and a broken strut
    (lit, shaded underside); `panel` one big panel; `struts` broken struts crossed."""
    g = Grid(20, 20)
    if kind in ("mixed", "panel"):
        big = kind == "panel"
        slab(g, 9, 9, 14 if big else 11, 10 if big else 8, 18, 9)
        for k in (-3, 0, 3): slab(g, 9 + k * 0.95, 9 + k * 0.3, 1.6, 9 if big else 7, 18, 5)   # ribs
        for y in range(3, 15, 3): g.rect(15 + (y % 2), y, 16 + (y % 2), y + 1, 1)   # torn edge
    if kind in ("mixed", "struts"):
        slab(g, 12, 14, 16, 2, -30, 12); slab(g, 12.6, 15.2, 16, 1.2, -30, 3)
        if kind == "struts": slab(g, 9, 9, 15, 2, 35, 12); slab(g, 9.5, 10.2, 15, 1.2, 35, 3)
    return g


def dust_drift(kind="a"):
    """Moon dust blown in (grid decal, flat): a pale drift with ripples, darker at its
    border; areas join into one drift. Ripples every 7 px so the 14 px inside holds them;
    `b` the ripples the other way."""
    g = Grid(20, 20)
    for y in range(20):
        for x in range(20):
            d = min(x, y, 19 - x, 19 - y)
            k = (x + y) if kind == "a" else (x - y + 20)
            g.px[y][x] = 5 if d == 0 else 7 if d < 3 else (12 if k % 7 < 2 else 9)
    return g


def cut_row(g):
    """A sketched row cut into the row-join parts the renderer takes: start, middle and end
    from the first, a middle and the last cell; link5 from the gap after the first cell;
    alone from start's left half and end's right half; link7 (for a turned row) from link5
    with its middle column repeated."""
    start, middle, end = g.crop(0, 19), g.crop(25, 44), g.crop(g.w - 20, g.w - 1)
    link5 = g.crop(20, 24)
    alone = Grid(20, 20)
    alone.px = [s[:10] + e[10:] for s, e in zip(start.px, end.px)]
    link7 = Grid(7, 20)
    link7.px = [row[:3] + [row[2]] * 2 + row[3:] for row in link5.px]
    return {"alone": alone, "start": start, "middle": middle, "end": end, "link5": link5, "link7": link7}


def row_from_single(g):
    """One generated piece built into the row-join parts: `alone` as it is; `start`, `middle`
    and `end` with the side edges that meet a neighbour cut off and the row's own surface
    filled out to the cell's edge; links of that surface with a seam two levels darker
    down the middle, so neighbours meet as one bank. The surface is each row's level just
    inside the piece's side edges (its rim), so it carries the piece's top, lip and front
    strip across the gap and a framed top stays framed in each cell, without repeating a
    handle, a vent or a panel."""
    xs = [x for x in range(g.w) if any(g.px[y][x] is not None for y in range(g.h))]
    xl, xr = xs[0], xs[-1]
    fill = []
    for row in g.px:
        # the rim just inside the piece's two side edges, so a framed top (a locker's roof
        # panel) stays framed in each cell; its median where the rim isn't drawn
        rim = [v for v in (row[xl + 1], row[xr - 1]) if v is not None]
        inside = sorted(v for v in row[xl + 2:xr - 1] if v is not None)
        fill.append(round(sum(rim) / len(rim)) if rim else inside[len(inside) // 2] if inside else None)
    seam = [None if v is None else max(1, v - 2) for v in fill]

    def build(left_edge, right_edge):
        out = Grid(20, g.h)
        for y, row in enumerate(g.px):
            for x in range(20):
                if (x <= xl and not left_edge) or (x >= xr and not right_edge): out.px[y][x] = fill[y]
                else: out.px[y][x] = row[x]
        return out

    def link(w):
        out = Grid(w, g.h)
        out.px = [[None if f is None else (s if x == w // 2 else f) for x in range(w)] for f, s in zip(fill, seam)]
        return out
    return {"alone": g, "start": build(True, False), "middle": build(False, False), "end": build(False, True),
            "link5": link(5), "link7": link(7)}


def row_parts(g):
    """A row piece's parts: cut from a sketched row, or built from a single piece."""
    return row_from_single(g) if g.w == 20 else cut_row(g)


def turned(g, t):
    """A 20x20 picture turned t quarter turns clockwise (as the renderer turns parts)."""
    out = g
    for _ in range(t % 4):
        r = Grid(out.h, out.w)
        r.px = [[out.px[out.h - 1 - x][y] for x in range(out.h)] for y in range(out.w)]
        out = r
    return out


def path_from_straight(g):
    """A path piece's parts (dot, end, straight, bend, tee, cross: each drawn with its arms
    east, then south, west, north, as the renderer turns them) built from one straight
    segment running east-west through the cell's middle with a fitting at its centre
    (rows 7-12 and columns 7-12: the renderer's links are cropped from the straight, so
    the arms meet the next cell exactly). An arm is the straight's east half turned to
    its side; the hub is the straight's middle columns, the fitting."""
    east = Grid(20, 20)
    east.px = [[v if x >= 10 else None for x, v in enumerate(row)] for row in g.px]
    hub = Grid(20, 20)
    hub.px = [[v if 7 <= x <= 12 else None for x, v in enumerate(row)] for row in g.px]

    def build(arms):
        out = Grid(20, 20)
        for t in arms:
            a = turned(east, t)
            for y in range(20):
                for x in range(20):
                    if a.px[y][x] is not None: out.px[y][x] = a.px[y][x]
        for y in range(20):
            for x in range(20):
                if hub.px[y][x] is not None: out.px[y][x] = hub.px[y][x]
        return out
    return {"dot": build([]), "end": build([0]), "straight": g, "bend": build([0, 1]), "tee": build([0, 1, 2]), "cross": build([0, 1, 2, 3])}


def grid_border(g):
    """A grid tile's border: where a see-through middle starts (the hazard band), else 3."""
    return next((x for x in range(10) if g.px[10][x] is None), 3)


def grid_from_single(g, border=None):
    """A grid decal's parts (the renderer's 9-slice: g<x><y> with x in s/l/m/r and y in
    s/t/m/b by which neighbours it has, hl_<y> in the 5 px gap across, vl_<x> in the 7 px
    gap down, corner where four meet; never turned) from one bordered tile: each part takes
    the tile's border on the sides with no neighbour and its inside, repeated, elsewhere.
    The border is `grid_border` of the tile unless given (piece_gen gives the sketch's:
    a seed's band can have see-through specks)."""
    if border is None: border = grid_border(g)
    inside = 20 - 2 * border

    def src(i, n, lo, hi):
        if lo and i < border: return i
        if hi and i >= n - border: return 20 - (n - i)
        return border + (i % inside)

    def part(w, h, xs, ys):
        out = Grid(w, h)
        l, r = xs in "sl", xs in "sr"
        t, b = ys in "st", ys in "sb"
        out.px = [[g.px[src(y, h, t, b)][src(x, w, l, r)] for x in range(w)] for y in range(h)]
        return out
    parts = {f"g{x}{y}": part(20, 20, x, y) for x in "slmr" for y in "stmb"}
    parts |= {f"hl_{y}": part(5, 20, "m", y) for y in "stmb"}
    parts |= {f"vl_{x}": part(20, 7, x, "m") for x in "slmr"}
    parts["corner"] = part(5, 7, "m", "m")
    return parts


def join_parts(g, joins, border=None):
    """The parts the renderer takes for a piece with joins, built from its one picture
    (`border`: a grid tile's, see grid_from_single)."""
    if joins == "grid": return grid_from_single(g, border)
    return {"row": row_parts, "path": path_from_straight}[joins](g)


# --- game sprites (docs/art.md, "House style") -------------------------------
# Seen straight down (they turn with the road, so no front strip), facing up. Visibility
# first: bodies at 9-13, every edge 8 or more (they're seen through holes in the road's
# level 3 cover), detail 4-5 levels off its surroundings in shapes of 2 px or more, and a
# pixel kept free all round for the black outline the game draws.

def seg(g, x0, y0, x1, y1, w, v):
    """A thick line: the pixels whose centres lie within w/2 of the segment."""
    dx, dy = x1 - x0, y1 - y0
    n = dx * dx + dy * dy or 1
    for y in range(g.h):
        for x in range(g.w):
            t = max(0.0, min(1.0, ((x + 0.5 - x0) * dx + (y + 0.5 - y0) * dy) / n))
            if math.hypot(x + 0.5 - x0 - t * dx, y + 0.5 - y0 - t * dy) <= w / 2: g.px[y][x] = v
    return g


def sprite_walker():
    """The walking bot (the rules' "beetle"), 20x20 facing up: an armoured round shell
    (radius under 7, which tools/import_sprites.py's trot keeps still) split by a dark
    seam into two back plates, a bright head plate with a dark visor and a lit sensor,
    and four two-jointed legs out to the corners (moved a pixel for each trot pose)."""
    g = Grid(20, 20)
    cx, cy = 10, 10
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        hip = (cx + sx * 4.5, cy + sy * 4)
        knee = (cx + sx * 7.2, cy + sy * 5.3)
        foot = (cx + sx * 7.6, cy + sy * 7.8)
        seg(g, *hip, *knee, 2.2, 9)
        seg(g, *knee, *foot, 2.0, 10)
        g.rect(knee[0] - 0.5 * (1 + sx), knee[1] - 0.5 * (1 + sy), knee[0] + 0.5 * (1 - sx), knee[1] + 0.5 * (1 - sy), 13)   # knee joint
    g.ellipse(cx, cy, 6.4, 6.6, 8)                               # shell rim
    g.ellipse(cx, cy + 0.5, 5.4, 5.4, 11)                        # back plates
    g.vline(9, 9, 15, 5); g.vline(10, 9, 15, 5)                  # the plates' seam
    g.rect(6, 11, 7, 12, 6); g.rect(12, 11, 13, 12, 6)           # vents
    g.ellipse(cx, 7, 4.6, 3.4, 13)                               # head plate
    g.rect(7, 6, 12, 7, 3)                                       # visor
    g.rect(9, 6, 10, 7, 14)                                      # sensor
    return g


def sprite_floater():
    """The floating drone (the rules' "shield"), 20x20 facing up: a round hull, four
    rotor pods on short arms at the diagonals (lit rings, dark hubs), a bright dome in
    the middle with a dark visor and a lit sensor at the front."""
    g = Grid(20, 20)
    cx, cy = 10, 10
    pods = [(cx + sx * 5.2, cy + sy * 5.2) for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1))]
    for px_, py_ in pods: seg(g, cx, cy, px_, py_, 2.4, 8)       # arms
    for px_, py_ in pods:
        g.ellipse(px_, py_, 3.1, 3.1, 12)                        # rotor ring
        g.ellipse(px_, py_, 1.6, 1.6, 4)                         # hub
    g.ellipse(cx, cy, 5.2, 5.2, 9)                               # hull
    g.ellipse(cx, cy, 3.6, 3.6, 5)                               # dome's seam
    g.ellipse(cx, cy, 2.8, 2.8, 13)                              # dome
    g.rect(8, 7, 11, 8, 3)                                       # visor
    g.rect(9, 7, 10, 8, 14)                                      # sensor
    return g


def sprite_boss():
    """The mother drone, the Airlock's boss, 5x5 cells (120x128) facing right where the
    lanes leave it: a big round armoured hull of eight plates split by dark seams, a
    glowing core in rings, eight jointed arms spread round it ending in claws, and two
    emitter ports on its right edge at the lanes' centres (y 23 and 104), fed by thick
    conduits from the hull."""
    w, h = footprint((5, 5))
    g = Grid(w, h)
    cx, cy, R = 58, 64, 30
    for py in (23, 104):                                         # conduits and ports
        seg(g, cx + R * 0.6, cy + (py - cy) * 0.45, w - 14, py, 7, 7)
        seg(g, cx + R * 0.6, cy + (py - cy) * 0.45, w - 14, py, 3, 11)
        g.rect(w - 18, py - 8, w - 2, py + 8, 10)                # port housing
        g.rect(w - 18, py - 8, w - 2, py - 7, 13)                # its lit edge
        g.rect(w - 9, py - 4, w - 2, py + 4, 4)                  # muzzle
        g.rect(w - 6, py - 2, w - 2, py + 2, 14)                 # aperture
    for a in (0, 58, 100, 140, 180, 220, 260, 302):              # arms
        t = math.radians(a)
        def at(r, da=0.0):
            return cx + r * math.cos(t + math.radians(da)), cy + r * math.sin(t + math.radians(da))
        sh, el, cl = at(R - 2), at(R + 11, 16), at(R + 20, 4)
        seg(g, *sh, *el, 6, 9)
        seg(g, *el, *cl, 5, 10)
        g.ellipse(*el, 3.2, 3.2, 13); g.ellipse(*el, 1.4, 1.4, 5)          # elbow
        for d in (-22, 22):                                      # claw
            tip = (cl[0] + 4 * math.cos(t + math.radians(d)), cl[1] + 5 * math.sin(t + math.radians(d)))
            seg(g, *cl, *tip, 2.4, 12)
    g.ellipse(cx, cy, R, R, 8)                                   # hull rim
    g.ellipse(cx, cy, R - 3, R - 3, 11)                          # armour plates
    for k in range(8):                                           # their seams
        t = math.radians(22.5 + 45 * k)
        seg(g, cx + 12 * math.cos(t), cy + 12 * math.sin(t), cx + (R - 3) * math.cos(t), cy + (R - 3) * math.sin(t), 2, 5)
        vx, vy = cx + (R - 9) * math.cos(t + math.radians(22.5)), cy + (R - 9) * math.sin(t + math.radians(22.5))
        g.rect(vx - 1, vy - 1, vx + 1, vy + 1, 6)                # a vent on each plate
    g.ellipse(cx, cy, 15, 15, 4)                                 # core housing
    g.ellipse(cx, cy, 12, 12, 12)                                # core ring
    g.ellipse(cx, cy, 8.5, 8.5, 3)
    g.ellipse(cx, cy, 6, 6, 14)                                  # the glowing core
    g.ellipse(cx, cy, 2.5, 2.5, 10)
    return g


def sprite_boss_depth(legs=(0, 58, 100, 140, 180, 220, 260, 302), ports=True, sockets=False):
    """The mother drone with depth (asked for after the flat first seeds): the house view's
    slight tilt, light from above. The hull a dome, lit toward the top, its side a dark band
    below with running lights; the core recessed, its upper inner wall in shadow; arms with
    lit tops over dark undersides, ball elbows lit from above, the upper arms behind the
    hull and the lower ones in front of it; ports as boxes with a lit top and a dark face.
    Same box and port places as sprite_boss. `legs`: the arms' angles; `ports`: the two
    emitter ports; `sockets`: an empty arm socket on each side (the body the game puts
    the arms in, sprite-boss-body)."""
    w, h = footprint((5, 5))
    g = Grid(w, h)
    cx, cy, rx, ry, side = BOSS_BODY if sockets else (58, 58, 31, 27, 7)

    def limb(x0, y0, x1, y1, wd, top):
        seg(g, x0, y0 + 2, x1, y1 + 2, wd, 4)                     # underside
        seg(g, x0, y0, x1, y1, wd - 1, top)                      # top
        seg(g, x0, y0 - (wd - 1) / 2 + 0.8, x1, y1 - (wd - 1) / 2 + 0.8, 1.4, top + 3)   # lit edge

    def ball(x, y, r):
        g.ellipse(x, y + 1, r, r, 5)
        g.ellipse(x, y, r, r, 9)
        g.ellipse(x - r * 0.3, y - r * 0.35, r * 0.55, r * 0.55, 13)

    def arm(a):
        t = math.radians(a)
        at = lambda r, da=0.0: (cx + r * math.cos(t + math.radians(da)), cy + r * 0.92 * math.sin(t + math.radians(da)))
        sh, el, cl = at(rx - 4), at(rx + 10, 16), at(rx + 20, 4)
        limb(*sh, *el, 7, 9)
        limb(*el, *cl, 5, 10)
        ball(*el, 3.4)
        for d in (-24, 24):                                      # claw
            tip = (cl[0] + 5 * math.cos(t + math.radians(d)), cl[1] + 5 * math.sin(t + math.radians(d)))
            limb(*cl, *tip, 3, 11)

    for py in (23, 104) if ports else ():                        # conduits and ports
        x0, y0 = cx + rx * 0.7, cy + (py - cy) * 0.4
        limb(x0, y0, w - 16, py, 8, 8)
        g.rect(w - 19, py - 9, w - 2, py + 9, 6)                 # port: its face
        g.rect(w - 19, py - 9, w - 2, py + 3, 10)                # its top
        g.rect(w - 19, py - 9, w - 2, py - 8, 13)                # lit far edge
        g.rect(w - 8, py - 4, w - 2, py + 5, 3)                  # muzzle
        g.rect(w - 5, py - 2, w - 2, py + 3, 14)                 # aperture
    upper = [a for a in legs if math.sin(math.radians(a)) < 0.3]
    lower = [a for a in legs if a not in upper]
    for a in upper: arm(a)                                       # behind the hull
    g.ellipse(cx, cy + side, rx, ry, 5)                          # the hull's side
    for k in range(-4, 5):                                       # running lights along it
        x = cx + k * rx * 0.2
        y = cy + side + ry * math.sqrt(max(0.0, 1 - (k * 0.2) ** 2)) - 3
        g.rect(x - 1, y, x, y + 1, 12)
    g.ellipse(cx, cy, rx, ry, 8)                                 # dome rim
    for i, (v, k) in enumerate(((9, 0.92), (10, 0.78), (11, 0.6), (12, 0.4))):   # the dome, lit toward the top
        g.ellipse(cx, cy - (1 - k) * ry * 0.55, rx * k, ry * k, v)
    for k in range(8):                                           # plate seams
        t = math.radians(22.5 + 45 * k)
        seg(g, cx + 14 * math.cos(t), cy + 12 * math.sin(t), cx + (rx - 2) * math.cos(t), cy + (ry - 2) * math.sin(t), 2, 5)
    g.ellipse(cx, cy, 15, 13, 3)                                 # the core's recess
    g.ellipse(cx, cy + 2, 12, 10, 7)                             # its lit lower wall
    g.ellipse(cx, cy + 2, 9, 7.5, 13)                            # the glowing core
    g.ellipse(cx, cy + 2, 5, 4, 14)
    g.ellipse(cx - 3, cy - 1, 1.6, 1.4, 14)
    for a in lower: arm(a)                                       # in front of the hull
    if sockets:                                                  # an arm socket on each side: a dark ring, a lit rim
        for x, y in ((cx + rx - 2, cy), (cx, cy + ry + side - 2), (cx - rx + 2, cy), (cx, cy - ry + 2)):
            g.ellipse(x, y, 5, 5, 4); g.ellipse(x, y, 5, 5, 11, inner=0.75); g.ellipse(x, y, 2.2, 2.2, 2)
    return g


# The boss body's hull in its 120x128 box: centre, radii and the depth of its side band
# below (main.ts puts the arms' sockets on its edges: keep them in step, BOSS_BODY there).
BOSS_BODY = (60, 60, 31, 27, 7)
ARM_W, ARM_H = 32, 22


def boss_arm(kind):
    """One of the mother drone's three arms (or a destroyed arm's stump), pointing right
    from the hull, ARM_W x ARM_H: the game puts it in a socket on the hull's east, south,
    west or north side and turns it to match (the boss turns its next arm to the road
    every wave), so it is drawn straight down, lit from directly above: every rounded part
    bright along its middle and dark along both sides, the same whichever way it turns.
    Its first few columns go under the hull. At the tip, what it sends: walkers, a big
    two-fingered claw; floaters, a launch ring; the swarm, a pod of four launch tubes.
    The stump: the shoulder only, torn off at a jagged end, with sparking wires."""
    g = Grid(ARM_W, ARM_H)
    cy = ARM_H / 2

    def limb(x0, x1, wd, v):                    # a rounded bar along the arm, lit along its middle
        seg(g, x0, cy, x1, cy, wd, v - 4)
        seg(g, x0, cy, x1, cy, wd - 2, v)
        seg(g, x0, cy, x1, cy, max(1.2, wd - 6), v + 3)

    def ball(x, r, v):
        g.ellipse(x, cy, r, r, v - 4)
        g.ellipse(x, cy, r - 1.2, r - 1.2, v)
        g.ellipse(x, cy, r * 0.4, r * 0.4, v + 4)

    g.rect(0, cy - 6, 4, cy + 5, 5)               # the socket collar
    g.rect(0, cy - 5, 3, cy + 4, 8)
    if kind == "stump":
        seg(g, 12, cy - 1, 18, cy - 3, 1.5, 12)    # wires hanging out
        seg(g, 12, cy + 1, 17, cy + 4, 1.5, 11)
        limb(2, 13, 9, 6)
        for y, cut in zip(range(int(cy - 4), int(cy + 5)), (13, 11, 12, 10, 12, 11, 13, 11, 12)):   # the torn end
            for x in range(cut, 14): g.set(x, y, 3 if x == cut else None)
        g.set(19, cy - 4, 14); g.set(18, cy + 5, 14)   # sparks
        return g
    limb(2, 14, 9, 9)                             # upper arm
    limb(15, 22, 7, 9)                            # forearm
    ball(14.5, 5, 9)                              # elbow, over both
    if kind == "walkers":                         # a claw: wrist block and two curved fingers
        g.rect(20, cy - 4, 23, cy + 3, 6); g.rect(21, cy - 3, 22, cy + 2, 11)
        for sgn in (-1, 1):
            pts = [(23, cy + sgn * 2.5), (27, cy + sgn * 6.5), (31, cy + sgn * 4)]
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                seg(g, ax, ay, bx, by, 3.4, 7); seg(g, ax, ay, bx, by, 1.6, 12)
            g.set(31, cy + sgn * 4 - (1 if sgn > 0 else 0), 14)
    elif kind == "floaters":                      # a launch ring with a glowing middle
        g.ellipse(25.5, cy, 6.5, 6.5, 6)
        g.ellipse(25.5, cy, 5.5, 5.5, 12, inner=0.55)
        g.ellipse(25.5, cy, 3, 3, 2)
        g.ellipse(25.5, cy, 1.2, 1.2, 14)
    else:                                          # the swarm: a pod of four launch tubes
        g.rect(20, cy - 8, 31, cy + 7, 5)
        g.rect(21, cy - 7, 30, cy + 6, 10)
        for tx in (22, 27):
            for ty in (cy - 6, cy + 1):
                g.rect(tx, ty, tx + 2, ty + 2, 2)
                g.set(tx + 1, ty + 1, 13)
    return g


def turn_cw(g):
    """A quarter turn clockwise."""
    t = Grid(g.h, g.w)
    t.px = [[g.px[g.h - 1 - x][y] for x in range(g.h)] for y in range(g.w)]
    return t


def rrect(g, x0, y0, x1, y1, r, v, width=None):
    """A rounded box in continuous coordinates (pixel centres at +0.5), filled, or a band
    `width` wide just inside its edge."""
    def d(x, y):          # distance outside the rounded box (negative inside)
        qx, qy = max(x0 + r - x, 0, x - (x1 - r)), max(y0 + r - y, 0, y - (y1 - r))
        return math.hypot(qx, qy) - r
    for y in range(g.h):
        for x in range(g.w):
            e = d(x + 0.5, y + 0.5)
            if e <= 0 and (width is None or e > -width): g.px[y][x] = v
    return g


def tower(kind, side=False, turned=True):
    """A turret on its 2x2 pad (45x47), facing up, or facing right (`side`: drawn facing up
    on the pad turned, 47x45, then turned a quarter clockwise; `turned` False leaves it
    facing up, for klein, which lost the twin barrels of a sketch facing right). Its barrels run down the
    lanes (the cells' centres, 25 or 27 px apart), and a dark groove on the base lies where
    the game draws the firing ring (a rounded square through the cells' centres), lit by it
    where nothing covers it. Round parts are shaded as domes and barrels as cylinders (lit
    down the middle, dark edges), light from above.
    Sniper (redrawn 2026-11-01): a round turntable, a yoke across it carrying two long slim
    barrels with cooling rings and counterweights, a small domed head with a lens and a scope.
    Cannon: a square armoured base with cut corners, two short fat barrels with slotted muzzle
    brakes coming out of a big dome with a hatch, vents at the back."""
    W, H = (47, 45) if side else (45, 47)
    g = Grid(W, H)
    lx = (10, W - 10)                     # the lanes (cell centres) across
    ry = (10, H - 10)                     # the ring's ends down
    cx, cy = W / 2, H / 2

    def dome(x, y, rx, ry_, levels):
        """Rings from the rim in, each a little up: lit toward the top."""
        for i, v in enumerate(levels):
            k = 1 - i / len(levels)
            g.ellipse(x, y - (1 - k) * ry_ * 0.25, rx * k, ry_ * k, v)

    def barrel(x, y0, y1, wd, body, lit, edge):
        a = x - wd // 2
        g.rect(a, y0, a + wd - 1, y1, body)
        g.vline(a, y0, y1, edge); g.vline(a + wd - 1, y0, y1, edge)
        g.rect(x - 1, y0, x - 1 + max(0, wd // 3 - 1), y1, lit)

    groove = lambda: rrect(g, lx[0] - 1, ry[0] - 1, lx[1] + 1, ry[1] + 1, 7, 3, width=2)
    if kind == "sniper":
        g.ellipse(cx, cy, cx - 0.5, cy - 0.5, 5)                         # turntable rim
        g.ellipse(cx, cy, cx - 2.5, cy - 2.5, 8)
        for k in range(8):                                               # its bolts
            t = math.radians(22.5 + 45 * k)
            bx, by = cx + (cx - 4) * math.cos(t), cy + (cy - 4) * math.sin(t)
            g.rect(bx - 1, by - 1, bx, by, 12)
        groove()
        g.rect(lx[0] - 3, 20, lx[1] + 2, 27, 11)                         # the yoke
        g.hline(lx[0] - 3, lx[1] + 2, 20, 13); g.hline(lx[0] - 3, lx[1] + 2, 27, 5)
        for x in lx:
            g.rect(x - 4, 28, x + 3, 34, 9); g.hline(x - 4, x + 3, 34, 5)   # counterweight
            barrel(x, 0, 31, 5, 11, 13, 6)
            g.rect(x - 4, 0, x + 3, 2, 13); g.rect(x - 1, 0, x, 1, 2)       # muzzle, bore
            for y in (8, 14): g.rect(x - 4, y, x + 3, y + 1, 7)             # cooling rings
        g.rect(cx - 1, 34, cx, 41, 6)                                    # cables to the back
        g.rect(cx - 3, 5, cx + 2, 19, 5)                                 # scope, its dark edge
        g.rect(cx - 2, 5, cx + 1, 18, 11); g.vline(cx - 1, 6, 17, 13)
        g.rect(cx - 2, 5, cx + 1, 6, 14)                                 # its lens
        dome(cx, 24, 7, 7, (6, 10, 12, 13))                              # head
        g.rect(cx - 1, 24, cx, 25, 3)                                    # sensor
    else:
        k = 9
        for y in range(H):                                               # armoured base, cut corners
            for x in range(W):
                xx, yy = x + 0.5, y + 0.5
                e = min(xx, W - xx) + min(yy, H - yy)
                if e >= k: g.px[y][x] = 5
                if e >= k + 3 and 2 < xx < W - 2 and 2 < yy < H - 2: g.px[y][x] = 8
        for bx, by in ((5, 9), (W - 7, 9), (5, H - 11), (W - 7, H - 11)):   # rivets
            g.rect(bx, by, bx + 1, by + 1, 12)
        groove()
        for y in (40, 43): g.rect(cx - 8, y, cx + 7, y + 1, 3)           # vents at the back
        for x in lx:
            barrel(x, 2, 24, 8, 10, 13, 5)
            g.rect(x - 5, 1, x + 4, 7, 12)                               # muzzle brake
            g.rect(x - 5, 3, x - 4, 5, 3); g.rect(x + 3, 3, x + 4, 5, 3)    # its slots
            g.rect(x - 2, 1, x + 1, 2, 2)                                # bore
        dome(cx, 27, 15, 14, (6, 9, 11, 12, 13))                         # the dome
        g.ellipse(cx, 28, 4, 4, 5)                                       # hatch
        g.rect(cx - 3, 27, cx + 2, 28, 10); g.rect(cx - 1, 25, cx, 30, 10)
    return turn_cw(g) if side and turned else g


def post(kind):
    """A tripline post, 24x24 (a little more than a cell), its emitter at the top: the game
    turns it to face the road. Laser: a square armoured pylon, a bright power cell, a
    nozzle. Stasis: a round pylon, coil rings round a glowing core, a dish."""
    g = Grid(24, 24)
    if kind == "laser":
        g.rect(1, 5, 22, 22, 6)                                          # rim
        g.rect(2, 6, 21, 21, 9)                                          # body
        g.hline(2, 21, 6, 12)                                            # lit far edge
        g.rect(3, 9, 4, 18, 5); g.rect(19, 9, 20, 18, 5)                 # vents
        g.rect(7, 9, 16, 18, 4)                                          # power cell's frame
        g.rect(8, 10, 15, 17, 13)                                        # power cell
        g.rect(10, 12, 13, 15, 14)
        g.rect(7, 0, 16, 5, 11)                                          # nozzle
        g.rect(7, 4, 16, 5, 6)
        g.rect(10, 0, 13, 2, 14)                                         # aperture
    else:
        g.ellipse(12, 14, 11, 9.5, 6)                                    # rim
        g.ellipse(12, 14, 10, 8.5, 9)                                    # body
        g.ellipse(12, 14, 7.5, 6.5, 12)                                  # coil
        g.ellipse(12, 14, 6, 5, 4)
        g.ellipse(12, 14, 4, 3.4, 13)                                    # core
        g.ellipse(12, 14, 2, 1.7, 14)
        g.ellipse(12, 2.5, 7.5, 4.5, 11)                                 # dish
        g.ellipse(12, 2.5, 5, 2.5, 5)
        g.rect(11, 5, 12, 6, 8)                                          # its mount
    return g


# id: (sketch, cells of the sketch, joins, what it is, for the prompt)
SKETCHES = {
    "couch": (couch, (2, 1), "none", "a two-seat fabric couch: backrest along the top, two seat cushions, padded arms"),
    "chair": (chair, (1, 1), "none", "a padded fabric armchair: backrest along the top, one seat cushion, padded arms"),
    "barrel": (barrel, (1, 1), "none", "a plastic drum seen from above: round lid with a raised rim and two screw caps, ribbed side"),
    "cargo-case": (cargo_case, (1, 1), "none", "a moulded plastic supply case: ribbed lid, rubber corner bumpers, a stencilled stripe, two latches on the front"),
    "workstation": (workstation, (1, 1), "none", "a computer workstation on a rolling cart: monitor at the back, keyboard tray, small casters"),
    "office-chair": (office_chair, (1, 1), "none", "a task chair without arms: a round padded back along the top, a round padded seat, under the seat the gas stem and the five-star base with casters"),
    "stool": (stool, (1, 1), "none", "a round padded stool: round seat with a ring seam and a centre button, its legs and footrest bar showing below the seat"),
    "bench": (bench, (1, 1), "row", "a padded bench seat on a metal frame, with two tufting buttons"),
    "desk": (desk, (1, 1), "row", "an office desk: metal top, a computer monitor at the back with its screen facing the front, a keyboard and a mouse"),
    "side-table": (side_table, (1, 1), "none", "a small round side table with a cup on it, three legs splaying out past its top"),
    "table-4": (table_4, (2, 2), "none", "a round dining table with a bowl in the middle, four chairs pushed in under it, one on each side, their backs showing, the table legs showing below its front edge"),
    "table-6": (table_6, (2, 2), "none", "a long dining table with a plate at each place, three chairs pushed in under each long side, their backs showing, its two front legs showing below the front edge at the ends"),
    "bunk": (bunk, (1, 2), "none", "a single bed on a metal frame with four legs: mattress, a pillow at the head, a blanket folded back, the legs showing at the corners and the foot"),
    "cabinet": (cabinet, (1, 1), "row", "a metal filing cabinet with a stack of papers on top and two drawers with handles on the front"),
    "shelf": (shelf, (1, 1), "row", "a tall metal shelving unit with two boxes on top, its shelves along the front holding bottles and boxes"),
    "vending": (vending, (1, 1), "row", "a vending machine: metal top with vent slots, a lit front with a dark product window, a coin slot and a delivery slot"),
    "water-cooler": (water_cooler, (1, 1), "none", "a water cooler: a round water bottle on top of a small cabinet, a tap and a drip tray on the front"),
    "plant": (plant, (1, 1), "none", "a potted plant: a round pot with a light rim and dark soil, five pointed leaves with light midribs spreading from the centre past the rim, the rim showing between the leaves"),
    "bin": (bin_, (1, 1), "none", "a round lidded waste bin: a swing slot and a handle bar on the lid"),
    "console": (console, (1, 1), "row", "a control console: a dark screen with lines of text at the back, a sloped desk of buttons in front of it"),
    "pipe": (pipe, (1, 1), "path", "a straight metal pipe running left to right across the middle, a bolted flange fitting at its centre"),
    "cable-tray": (cable_tray, (1, 1), "path", "a straight metal cable tray running left to right: two side rails, cables lying in it, a bolted junction plate at the centre"),
    "mat": (mat, (1, 1), "grid", "a square rubber floor mat, flat on the floor: a raised border round a ribbed middle"),
    "hazard": (hazard, (1, 1), "grid", "hazard markings painted flat on the floor: a band of diagonal light and dark stripes round a square, plain floor inside"),
    "grate": (grate, (1, 1), "grid", "a square metal floor grate, flat in the floor: a frame round rows of dark slots"),
    "scorch": (scorch, (1, 1), "none", "a black scorch mark flat on the floor from a blast: a black centre, sooty streaks thrown out round it"),
    "case-stack": (case_stack, (2, 1), "none", "two moulded plastic supply cases side by side, a big one and a smaller one, strapped together with two straps: ribbed lids, rubber corner bumpers"),
    "gas-cylinder": (gas_cylinder, (1, 1), "none", "a tall gas cylinder standing upright: its domed top with a valve, a bright hazard band round its body"),
    "tank": (tank, (1, 1), "none", "a round water tank: a big lid with a round hatch and a gauge, bands round its side"),
    "tool-chest": (tool_chest, (1, 1), "row", "a metal tool chest with a wrench lying on top and drawers with pulls on the front"),
    "cable-reel": (cable_reel, (1, 1), "none", "a big cable reel lying flat: a wide round flange, cable wound round it, a hub in the middle"),
    "generator": (generator, (2, 1), "none", "a portable power generator: a metal housing with an exhaust stack, a small control panel with lights and rows of vent slots"),
    "work-light": (work_light, (1, 1), "none", "a work floodlight on a tripod: the lamp head with a bright lens facing the front, its post and tripod legs below"),
    "fire-point": (fire_point, (1, 1), "none", "a fire extinguisher standing on a small metal stand: its round top with a lever and a hose"),
    "bot-wreck": (bot_wreck, (1, 1), "none", "the wreck of a destroyed walking robot on a scorched patch of floor: its torn open body and two broken legs thrown apart"),
    "conveyor": (conveyor, (1, 1), "row", "a conveyor belt running left to right: a dark ribbed belt between two side rails, a roller drum at each end"),
    "hatch": (hatch, (1, 1), "none", "a round metal floor hatch, flat in the floor: a bolted rim, a plate with a cross of stiffeners and a lifting handle"),
    "drain": (drain, (1, 1), "none", "a small square floor drain, flat in the floor: a frame round a plate with a grid of dark holes"),
    "floor-arrow": (floor_arrow, (1, 1), "none", "a bold arrow painted flat on the floor pointing up, the paint a little worn"),
    "container": (container, (2, 1), "none", "a steel shipping container seen from above: its corrugated roof with corner castings, its long corrugated side along the bottom edge, the door end with lock rods at the right"),
    "container-stack": (container_stack, (2, 2), "none", "two steel shipping containers stacked in a cross, seen from above: a dark lower one lying left to right across the middle, and a bright upper one on top of it turned ninety degrees, running from the top edge to the bottom edge, its door end with lock rods facing the front"),
    "pallet": (pallet, (1, 1), "none", "an empty composite pallet seen from above: deck slats across it with gaps, runners underneath showing in the gaps"),
    "pallet-load": (pallet_load, (1, 1), "none", "two moulded supply cases strapped together on a pallet, seen from above: ribbed lids with corner bumpers, a strap over both"),
    "pallet-rack": (pallet_rack, (1, 1), "row", "a bay of an industrial pallet rack seen from above: beams along the back and front, uprights at the corners, a loaded pallet on top, the shelf below in shadow along the front"),
    "dock-edge": (dock_edge, (1, 1), "row", "the edge of a loading dock seen from above: the dock floor, a wide band of bold bright and black diagonal hazard stripes along its edge, its face along the bottom with two black rubber bumpers"),
    "bunk-double": (bunk_double, (2, 2), "none", "a double bed on a metal frame seen from above: two pillows at the head, a blanket folded back with a stripe, the legs at the corners and the foot rail"),
    "bedside": (bedside, (1, 1), "none", "a small bedside cabinet seen from above: a round lamp shade and a book on its top, a drawer with a pull on the front"),
    "galley": (galley, (1, 1), "row", "a kitchen counter seen from above: a backsplash along the back, a plain worktop, cupboard doors with handles along the front"),
    "basin": (basin, (1, 1), "row", "a washroom counter with a wash basin seen from above: an oval basin with a tap at its back, the U-bend pipe below the front"),
    "shower": (shower, (1, 1), "none", "a shower stall seen from above: a ribbed shower tray with a round drain, the shower head at the back, a glass door with a handle along the front"),
    "toilet": (toilet, (1, 1), "none", "a toilet seen from above: the cistern along the back with a flush button, the bowl with its seat in front of it"),
    "treadmill": (treadmill, (1, 2), "none", "a treadmill seen from above: the console with a screen at the head, handrails along both sides, a long ribbed running belt"),
    "weight-rack": (weight_rack, (1, 1), "row", "a dumbbell rack seen from above: dumbbells with big round weights lying on its top tier, the lower tier along the front"),
    "weight-bench": (weight_bench, (1, 2), "none", "a weight bench seen from above: a barbell with weight plates across the head on two uprights, a long padded bench, its legs at the foot"),
    "boulder": (boulder, (1, 1), "none", "a moon rock boulder seen from above: rough faceted stone with a lit top face, dark cracks and a shaded foot"),
    "boulder-big": (boulder_big, (2, 2), "none", "a huge moon rock boulder seen from above: rough faceted stone split by dark cracks into lit and shaded faces, a small rock at its foot"),
    "rubble": (rubble, (1, 1), "none", "a heap of broken ore rocks seen from above: rocks of several sizes with lit faces and bright glinting ore crystals"),
    "ore-vein": (ore_vein, (1, 1), "none", "an ore vein flat in a rock floor: a dark crack with clusters of bright crystals along it"),
    "ore-cart": (ore_cart, (1, 1), "none", "a steel mine cart full of ore rocks seen from above: a bright rim round the heap of rocks with glinting ore, its side and wheels along the bottom"),
    "rail": (rail, (1, 1), "path", "a straight mine railway track running left to right seen from above: two bright steel rails on dark sleepers"),
    "drill-rig": (drill_rig, (2, 2), "none", "a mining drill rig seen from above: a platform with the lattice mast seen from above, the round drill head, an engine box with vents, the platform's bolted edge along the bottom"),
    "strut": (strut, (1, 1), "none", "a steel mine prop holding up the roof seen from above: a bright top plate, the steel column standing below it, a base plate on the floor"),
    "hopper": (hopper, (2, 1), "none", "an ore hopper seen from above: a square funnel with sloped sides down to a dark mouth heaped with ore, a conveyor belt at its foot"),
    "reactor-vessel": (reactor_vessel, (2, 2), "none", "a round nuclear reactor vessel seen from above: a big dome with a ring of bolts round its rim, a round hatch in the middle, bands round its side"),
    "pump": (pump, (1, 1), "none", "an industrial pump seen from above: an electric motor with cooling fins and a round pump casing, pipe stubs reaching out left and right, on a base plate"),
    "valve": (valve, (1, 1), "none", "a big valve where two pipes cross seen from above: a round hand wheel with spokes over the crossing of the pipes"),
    "turbine": (turbine, (2, 1), "none", "a steam turbine seen from above: a long round housing lying left to right with bolted flange rings, its shaft and coupling at the right end, on a base"),
    "heat-exchanger": (heat_exchanger, (2, 1), "none", "a heat exchanger seen from above: a block of many bright cooling fins in a frame, a pipe through it with bolted flanges at both ends"),
    "control-panel": (control_panel, (1, 1), "row", "a reactor control panel seen from above: a sloped desk with two round gauges and a row of buttons"),
    "catwalk": (catwalk, (1, 1), "grid", "a metal catwalk flat on the floor seen from above: a frame round a grating of dark square holes"),
    "grow-bed": (grow_bed, (1, 1), "row", "a hydroponic grow bed seen from above: a trough with a rim, dark soil, two big leafy plants with pointed leaves"),
    "raised-planter": (raised_planter, (1, 1), "grid", "a raised planter bed seen from above: a wide rim round dark soil with small leafy plants"),
    "planter": (planter, (1, 1), "none", "a square planter box seen from above: a rim round dark soil, a big plant with six pointed leaves spilling over it"),
    "seed-tray": (seed_tray, (1, 1), "row", "seedling trays on a bench seen from above: a tray of four dark cells, a bright two-leaved sprout in each"),
    "dwarf-tree": (dwarf_tree, (1, 1), "none", "a small potted tree seen from above: a round crown of leafy clumps, the pot showing below it"),
    "nutrient-mixer": (nutrient_mixer, (1, 1), "none", "a small nutrient mixing tank seen from above: a round tank with a filler cap, a round dial gauge, a hose"),
    "grow-light": (grow_light, (1, 1), "row", "a bright grow light bar seen from above hanging over plants in shadow: a glowing light strip in a dark frame with two hangers"),
    "airlock-door": (airlock_door, (2, 2), "none", "a huge breached airlock door seen from above: a thick riveted bulkhead with a jagged dark hole torn through it, hazard stripes along its face, the torn-off bent door leaf lying on the floor in front"),
    "inner-door": (inner_door, (2, 1), "none", "a sealed inner bulkhead door seen from above: the bulkhead's top, its face along the bottom with two door leaves, warning lights either side, a hazard striped sill"),
    "suit-rack": (suit_rack, (1, 1), "row", "a space suit hanging on a rack seen from above: the bright helmet with a dark visor, the shoulders and life-support backpack, the legs and boots along the bottom"),
    "helmet-shelf": (helmet_shelf, (1, 1), "row", "a shelf of space helmets seen from above: two bright helmets with dark visors and a pair of gloves on top, shelves along the front"),
    "o2-rack": (o2_rack, (1, 1), "row", "a rack of three big oxygen bottles seen from above: round bottle shoulders with bright valve hand wheels, a strap across them, the round bottles' sides with a bright band along the bottom"),
    "decon-booth": (decon_booth, (1, 2), "none", "a decontamination booth seen from above: a frame round a grated floor, two spray rings, a door with a window along the bottom"),
    "pressure-console": (pressure_console, (1, 1), "row", "an airlock pressure console seen from above: a sloped desk with two pressure gauges and a big round cycle switch"),
    "beacon": (beacon, (1, 1), "none", "a rotating warning beacon on a post seen from above: a bright dome in a cage of bars, the post and base plate below it"),
    "rover": (rover, (2, 2), "none", "a moon rover driving left to right seen from above with a slight tilt: a cab under a round dark glass canopy, a seat, a ribbed cargo bed, an antenna dish, its side panel and two big round wheels along the bottom"),
    "cargo-sled": (cargo_sled, (2, 1), "none", "a towed cargo sled seen from above: a tow bar, a flat bed on runners, three supply cases strapped on it"),
    "hose-reel": (hose_reel, (1, 1), "none", "an air hose wound on a reel seen from above: bright turns of hose round a dark hub, the nozzle lying out to the side"),
    "debris": (debris, (1, 1), "none", "debris from a hull breach on the floor seen from above: a bent ribbed hull panel with a torn edge and a broken steel strut"),
    "dust-drift": (dust_drift, (1, 1), "grid", "a drift of pale moon dust flat on the floor seen from above, with wind ripples"),
    "tower-sniper": (lambda: tower("sniper"), (2, 2), "none", "a sniper turret seen from directly above, barrels pointing up the picture: a round turntable with bolts, a yoke across it carrying two long slim barrels with cooling rings, bright muzzles and counterweights, a small domed head with a scope pointing forward between them"),
    "tower-sniper-side": (lambda: tower("sniper", True, False), (2, 2), "none", "a sniper turret seen from directly above, barrels pointing up the picture: a round turntable with bolts, a yoke across it carrying two long slim barrels with cooling rings, bright muzzles and counterweights, a small domed head with a scope pointing forward between them"),
    "tower-cannon": (lambda: tower("cannon"), (2, 2), "none", "a heavy cannon turret seen from directly above, barrels pointing up the picture: a square armoured base with cut corners and rivets, two short fat barrels with slotted muzzle brakes coming out of a big shaded dome with a hatch, vents at the back"),
    "tower-cannon-side": (lambda: tower("cannon", True, False), (2, 2), "none", "a heavy cannon turret seen from directly above, barrels pointing up the picture: a square armoured base with cut corners and rivets, two short fat barrels with slotted muzzle brakes coming out of a big shaded dome with a hatch, vents at the back"),
    "tower-laser": (lambda: post("laser"), (1, 1), "none", "a laser emitter post seen from directly above, emitter pointing up the picture: a square armoured pylon with vents, a glowing power cell in a dark frame, a nozzle at the top with a bright aperture"),
    "tower-stasis": (lambda: post("stasis"), (1, 1), "none", "a stasis field emitter post seen from directly above, emitter pointing up the picture: a round pylon with glowing coil rings round a bright core, a dish emitter at the top"),
    "sprite-walker": (sprite_walker, (1, 1), "none", "a small four-legged walking robot: a round armoured shell split into two back plates, a bright head plate with a dark visor and a glowing sensor at the front, four jointed legs reaching out to the corners"),
    "sprite-floater": (sprite_floater, (1, 1), "none", "a small hovering quadcopter drone: a round hull with a bright dome and a dark visor with a glowing sensor at the front, four rotor pods on short arms with bright rotor rings and dark hubs"),
    "arm-walkers": ((lambda: boss_arm("walkers")), (1, 1), "none", "a heavy jointed mechanical arm of a huge robot reaching to the right: a socket collar, a thick upper arm, a big ball elbow, a forearm ending in a large two-fingered steel claw"),
    "arm-floaters": ((lambda: boss_arm("floaters")), (1, 1), "none", "a heavy jointed mechanical arm of a huge robot reaching to the right: a socket collar, a thick upper arm, a big ball elbow, a forearm ending in a round drone launch ring with a glowing middle"),
    "arm-swarm": ((lambda: boss_arm("swarm")), (1, 1), "none", "a heavy jointed mechanical arm of a huge robot reaching to the right: a socket collar, a thick upper arm, a big ball elbow, a forearm ending in a square launcher pod of four dark launch tubes"),
    "arm-stump": ((lambda: boss_arm("stump")), (1, 1), "none", "the stump of a destroyed mechanical arm of a huge robot: a socket collar and a short dark upper arm torn off at a jagged end, bright sparking wires hanging out"),
    "sprite-boss-body": ((lambda: sprite_boss_depth(legs=(45, 135, 225, 315), ports=False, sockets=True)), (5, 5), "none", "a huge hovering mother drone with real volume: a shaded armoured dome hull lit from above, its side a dark band with running lights below it, a glowing core sunk in a recess, four jointed mechanical legs reaching out to the corners with lit tops and dark undersides and ball elbows, ending in claws, the upper legs behind the hull and the lower legs in front of it, and four round empty arm sockets on its rim, one on each side"),
    "sprite-boss": (sprite_boss, (5, 5), "none", "a huge hovering mother drone: a big round armoured hull of eight plates around a glowing core in rings, eight jointed mechanical arms spread round it ending in claws, two heavy emitter ports on the right edge fed by thick conduits"),
    "locker": (locker_row, (3, 1), "row", "the flat steel roofs of three tall lockers standing side by side, which fill most of the picture, with only a thin strip of their doors (handles, vents) along the bottom edge"),
}


# Flat pieces drawn under everything else, never in the way (the pack's "decal").
DECALS = {"mat", "hazard", "grate", "scorch", "hatch", "drain", "floor-arrow", "ore-vein", "catwalk", "dust-drift"}

# Pieces whose converted seeds are cut back to the sketch's own pixels: the conversion fills
# the sketch's box, and klein draws something inside a see-through middle (the hazard's
# first seeds came back as solid plates, their stripes softened into them).
MASKED = {"hazard", "floor-arrow", "ore-vein"}
# The game sprites (tools/import_sprites.py takes the picked ones): masked too, so the
# legs, arms and see-through gaps stay where the game expects them.
SPRITES = {"sprite-walker", "sprite-floater", "sprite-boss", "sprite-boss-body", "arm-walkers", "arm-floaters", "arm-swarm", "arm-stump"} | {f"tower-{k}" for k in ("sniper", "sniper-side", "cannon", "cannon-side", "laser", "stasis")}
MASKED |= SPRITES
# Sketched (and generated) facing up, saved turned a quarter clockwise (tools/piece_gen.py).
TURN_AFTER = {"tower-sniper-side", "tower-cannon-side"}

# A map's own pieces (phase 4; the rest are the shared set), for the art library's pages.
OWN_MAP = {i: "cargo-bay" for i in ("container", "container-stack", "pallet", "pallet-load", "pallet-rack", "dock-edge")}
OWN_MAP |= {i: "hab-ring" for i in ("bunk-double", "bedside", "galley", "basin", "shower", "toilet", "treadmill", "weight-rack", "weight-bench")}
OWN_MAP |= {i: "regolith-mine" for i in ("boulder", "boulder-big", "rubble", "ore-vein", "ore-cart", "rail", "drill-rig", "strut", "hopper")}
OWN_MAP |= {i: "reactor" for i in ("reactor-vessel", "pump", "valve", "turbine", "heat-exchanger", "control-panel", "catwalk")}
OWN_MAP |= {i: "hydroponics" for i in ("grow-bed", "raised-planter", "planter", "seed-tray", "dwarf-tree", "nutrient-mixer", "grow-light")}
OWN_MAP |= {i: "airlock" for i in ("airlock-door", "inner-door", "suit-rack", "helmet-shelf", "o2-rack", "decon-booth", "pressure-console", "beacon", "rover", "cargo-sled", "hose-reel", "debris", "dust-drift")}

# Other forms of a piece's sketch to try (tools/piece_gen.py --form): name: (sketch, cells, what).
FORMS = {
    "sprite-boss": {"depth": (sprite_boss_depth, (5, 5), "a huge hovering mother drone with real volume: a shaded armoured dome hull lit from above, its side a dark band with running lights below it, a glowing core sunk in a recess, eight jointed mechanical arms with lit tops and dark undersides and ball elbows, the upper arms behind the hull and the lower arms in front of it, ending in claws, two heavy emitter ports on the right edge fed by thick conduits")},
    "inner-door": {"forced": ((lambda: inner_door("forced")), (2, 1), "an inner bulkhead door forced half open seen from above: the bulkhead's top, its face along the bottom with the door leaves pried apart on a dark jagged gap, warning lights either side, a hazard striped sill")},
    "suit-rack": {"empty": ((lambda: suit_rack("empty")), (1, 1), "an empty space suit rack seen from above: the rail with two hooks, one bright helmet with a dark visor")},
    "pressure-console": {"screen": ((lambda: pressure_console("screen")), (1, 1), "an airlock pressure console seen from above: a sloped desk with a dark screen of bright bars and a big round cycle switch")},
    "debris": {"panel": ((lambda: debris("panel")), (1, 1), "a big bent hull panel from a breach lying on the floor seen from above: ribbed, with a torn edge"),
               "struts": ((lambda: debris("struts")), (1, 1), "broken steel struts from a breach lying crossed on the floor seen from above")},
    "dust-drift": {"b": ((lambda: dust_drift("b")), (1, 1), "a drift of pale moon dust flat on the floor seen from above, with wind ripples")},
    "grow-bed": {"herbs": ((lambda: grow_bed("herbs")), (1, 1), "a hydroponic grow bed seen from above: a trough with a rim, dark soil, two rows of small bright herb clumps")},
    "planter": {"pot": ((lambda: planter("pot")), (1, 1), "a round plant pot seen from above: a rim round dark soil, spiky grass leaves fanning out")},
    "control-panel": {"levers": ((lambda: control_panel("levers")), (1, 1), "a reactor control panel seen from above: a sloped desk with three big levers in dark slots")},
    "boulder": {"small": ((lambda: boulder("small")), (1, 1), "a small moon rock seen from above: rough faceted stone with a lit top face and a shaded foot"),
                "pair": ((lambda: boulder("pair")), (1, 1), "two moon rocks side by side seen from above: rough faceted stones with lit top faces and shaded feet")},
    "rubble": {"b": ((lambda: rubble("b")), (1, 1), "a low spread of broken ore rocks seen from above: a few rocks with lit faces and bright glinting ore")},
    "strut": {"pair": ((lambda: strut("pair")), (1, 1), "two steel mine props side by side seen from above, braced together: bright top plates, the columns standing below them")},
    "galley": {k: ((lambda k=k: galley(k)), (1, 1), w) for k, w in (
        ("sink", "a kitchen counter with a sink seen from above: a backsplash along the back, a deep dark sink basin with a bright rim and a tap, cupboard doors with handles along the front"),
        ("hob", "a kitchen counter with a cooking hob seen from above: a backsplash along the back, four round dark burner rings, cupboard doors with handles along the front"),
        ("fridge", "a tall fridge seen from above: its plain top with vent slots, its bright front door with handles along the bottom edge"))},
    "chair": {"bold": (chair_bold, (1, 1), "a padded fabric armchair seen from above: a lit backrest along the top, a deep seam, one seat cushion with a big highlight, padded arms with lit tops")},
    "office-chair": {"bold": (office_chair_bold, (1, 1), "a task chair without arms seen from above: a round padded back with a lit edge, a dark gap, a round padded seat with a highlight, under the seat the gas stem and the five-star base with bright casters")},
    "stool": {"bold": (stool_bold, (1, 1), "a round padded stool seen from above: a round seat with a deep dark ring seam and a bright centre button, its legs and footrest bar showing below the seat")},
    "water-cooler": {"bold": (water_cooler_bold, (1, 1), "a water cooler seen from above: a round bright water bottle with a dark rim and cap on a small cabinet, a bright tap on a dark plate and a dark drip tray on the front")},
    "desk": {"bold": (desk_bold, (1, 1), "an office desk seen from above: metal top, a monitor at the back with a dark screen showing bright lines of text, a dark keyboard with rows of keys, a bright mouse on a dark pad")},
    "table-4": {"bold": (table_4_bold, (2, 2), "a round dining table seen from above with a bright bowl in the middle, four chairs pushed in under it, one on each side, their bright backs showing, the table legs showing below its front edge")},
    "table-6": {"bold": (table_6_bold, (2, 2), "a long dining table seen from above with a bright plate at each place and a dark runner, three chairs pushed in under each long side, their bright backs showing, its two front legs showing below the front edge at the ends")},
    "cargo-case": {
        "bold": (cargo_case_bold, (1, 1), "a moulded plastic supply case seen from above: a lid with deep dark ribs, black rubber corner bumpers, "
                 "a bright stencilled stripe, two bright latches on dark plates on the front"),
    },
    "tank": {
        "bold": (tank_bold, (1, 1), "a round water tank seen from above: a dark rim ringed with bolts, a big lid with a deep round hatch "
                 "and a bright handle, a gauge, dark bands round its side"),
    },
    "hazard": {
        "bold": (hazard_bold, (1, 1), "hazard markings painted flat on the floor: a wide band of bold diagonal bright and black stripes round a square, plain floor inside"),
    },
    "bot-wreck": {
        "floater": (lambda: bot_wreck("floater"), (1, 1), "the wreck of a destroyed floating drone on a scorched patch of floor: its round shell cracked open, a broken fin beside it"),
        "parts": (lambda: bot_wreck("parts"), (1, 1), "scattered parts of destroyed robots on a scorched patch of floor: torn metal panels, a bent rod, broken pieces"),
    },
    "locker": {
        # one locker, built into a bank by row_from_single
        "single": (lambda: locker_row(1), (1, 1), "the flat steel roof of one tall locker, which fills most of the picture, with only a thin "
                                                  "strip of its double doors (handles, vents) along the bottom edge"),
        # one locker with its roof's detail drawn bold (klein smoothed the plain panel away)
        "bold": (lambda: locker_row(1, roof="bold"), (1, 1), "the steel roof of one tall locker seen from above, which fills most of the picture: "
                 "a deep recessed panel with two dark ventilation slots and a rivet in each corner; only a thin strip of its double doors "
                 "(handles, vents) along the bottom edge"),
        # three, the seams between them on the top only one level under the top's panel
        "light": (lambda: locker_row(3, seam=METAL[2]), (3, 1), "the flat steel roofs of three tall lockers standing side by side as one "
                  "continuous bank, which fill most of the picture, with only a thin strip of their doors (handles, vents) along the bottom edge"),
    },
}


def sheet(ids):
    """Every sketch at x6 on the floor's level 1 with its levels listed: art/work/sketches.png."""
    from PIL import ImageDraw
    Z, pad = 6, 10
    pics = [(i, SKETCHES[i][0]()) for i in ids]
    W = sum(g.w * Z + pad for _, g in pics) + pad
    out = Image.new("L", (W, 20 * Z + 40), 17)
    d = ImageDraw.Draw(out)
    x = pad
    for i, g in pics:
        im = g.image(Z)
        out.paste(im.getchannel("L"), (x, 24), im.getchannel("A"))
        d.text((x, 4), f"{i} {g.levels()}", fill=200)
        x += g.w * Z + pad
    out.save(os.path.join(WORK, "sketches.png"))


if __name__ == "__main__":
    ids = sys.argv[1:] or list(SKETCHES)
    for i in ids:
        os.makedirs(os.path.join(WORK, i), exist_ok=True)
        SKETCHES[i][0]().image().save(os.path.join(WORK, i, "sketch.png"))
    sheet(ids)
    print(len(ids), "sketches; art/work/sketches.png")
