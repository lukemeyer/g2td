"""Reading generated pixel art into the game's levels, shared by tools/import_sprites.py
(which builds src/sprites.ts) and tools/grid_snap.py (which converts generated pieces).
"""
from PIL import Image

LEVEL_MAX = 14   # the image's brightest level: the text the player reads (textColor 4) stays above it


def levels(im, top, gamma=1.0):
    """A greyscale image as levels 0..top; gamma above 1 darkens the mid-greys."""
    px = im.load()
    return [[round((px[x, y] / 255) ** gamma * top) for x in range(im.width)] for y in range(im.height)]


def background(im):
    """The background of a generated picture: the corners' colour, reaching the edge."""
    w, h = im.size
    px = im.load()
    bg = Image.new("L", (w, h), 0)
    bp = bg.load()
    corner = sorted(px[x, y] for x in (0, w - 1) for y in (0, h - 1))[2]
    todo = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while todo:
        x, y = todo.pop()
        if 0 <= x < w and 0 <= y < h and not bp[x, y] and abs(px[x, y] - corner) < 16:
            bp[x, y] = 255
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return bg


def pixel_art(path, n, gamma):
    """Generated pixel art read back on its n x n grid, background see-through."""
    im = Image.open(path).convert("L")
    fg = background(im).point(lambda v: 255 - v).resize((n, n), Image.NEAREST).load()
    px = im.resize((n, n), Image.NEAREST).load()
    return [[round((px[x, y] / 255) ** gamma * LEVEL_MAX) if fg[x, y] >= 128 else None for x in range(n)] for y in range(n)]


def cutout(im):
    """RGBA with the background (the corners' colour, reaching the edge) see-through."""
    g = im.convert("L")
    w, h = g.size
    px = g.load()
    corner = sorted(px[x, y] for x in (0, w - 1) for y in (0, h - 1))[2]
    seen = bytearray(w * h)
    todo = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while todo:
        x, y = todo.pop()
        if 0 <= x < w and 0 <= y < h and not seen[y * w + x] and abs(px[x, y] - corner) < 16:
            seen[y * w + x] = 1
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    a = Image.frombytes("L", (w, h), bytes(0 if v else 255 for v in seen))
    out = g.convert("LA"); out.putalpha(a)
    return out


def crop_to_ink(im):
    return im.crop(im.getchannel("A").getbbox())
