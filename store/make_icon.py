"""The store icon: three drones in formation (picked by the user 2026-11-17), 24x24 in 2x2 blocks of #F4F4F4 on transparent,
as the hub asks.

    .venv/bin/python -I store/make_icon.py
"""
from PIL import Image

G = """
#...#.......
.###........
.#.#........
.###...#...#
#...#...###.
........#.#.
........###.
#...#..#...#
.###........
.#.#........
.###........
#...#.......
""".split()

im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
for y, row in enumerate(G):
    for x, ch in enumerate(row):
        if ch == "#":
            for dy in (0, 1):
                for dx in (0, 1): im.putpixel((2 * x + dx, 2 * y + dy), (0xF4, 0xF4, 0xF4, 255))
im.save("store/icon.png")
