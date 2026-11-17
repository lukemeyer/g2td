# Art: the renderer, the pack, the house style and how new art is made

Everything on the map is drawn from small pictures at their exact display size, in the
glasses' grey levels (0-15), and never scaled.

## The renderer (`src/render/map.ts`)

`drawMap(mapId, layout)` makes a map's static 576x288 image in levels, in this order:

1. **Floor:** the map's floor tiles, one per cell plus its gap strips, painted per cell in
   the editor. The renderer draws every floor darker (`FLOOR_DIM`).
2. **Floor decals:** flat pieces such as mats, hazard markings, grates and dust.
3. **Pieces:** copied 1:1 from the pack, turned in quarter turns, with their join parts.
4. **Placed walls:** the map's wall kit in the gaps between cells.
5. **Road:** the road-wall kit along the road (7 px), then the solid road band at level 3.
   The band stays in code so it matches the text covers.

**Joins:** every piece is placed one cell (or footprint) at a time. A piece may carry a
link strip for the 5 px gap across and the 7 px gap down, plus end caps, and for paths
bends and tees. The renderer picks the right part for each cell:
- a neighbour of the same piece gets the link, so a row of lockers is seamless;
- a piece with no neighbour gets the end cap;
- a path gets the bend or tee that matches its neighbours.

Grid pieces (mats, planters) join both ways, like a 9-slice. A piece without join parts
stands alone.

The game (`main.ts` `mapLevels`), the map editor, the phone's Stats page and the art
library all draw maps through this one module. The game then draws towers, marks and the
baked-in enemies over a copy.

## The art pack (`art/pack/`)

- **Pictures:** one PNG per picture at display size, grey + alpha, grey = level x 17.
  `shared/` holds the generic set; `<map>/` holds each map's own. A kit is a folder of its
  parts.
- **Manifest:** `pack.json` lists each piece: its footprint, whether it is a decal, which
  maps may use it, its join parts and variants. It also gives each map its floors, road
  wall and wall kit.
- **Build:** `tools/pack_build.py` bundles the pack into `src/pack.ts` and checks that
  pictures fit their footprints (floor tiles are 25x27).
- **Layouts:** `art/maps/<id>/layout.json` (version 2) has a `floor` legend and rows of
  characters per cell, `pieces` as [row, col, id, variant, quarter turns], and `walls` as
  [row, col, e|s|w|n]. `src/render/layouts.ts` bundles them. Edit them in the map editor.

## House style

One view for every object, rotatable, modelled on the Hab Ring couch
(`art/reference/couch-s1.png`, the style reference for every generation).

1. **One view:** top-down with a slight tilt toward the viewer. Top surfaces fill the
   piece. The front shows as a strip along the bottom edge, as tall as the object's real
   height at **3 px per metre**:

   | Object | Height | Front strip |
   |---|---|---|
   | rug | 0 | 0 |
   | couch back | 0.8 m | 2 px |
   | cabinet | 1.2 m | 4 px |
   | vending machine | 1.8 m | 5-6 px |
   | locker | 2 m | 6 px (a 10 px top over a 6 px front, in a 20x20 cell) |

   Tops are drawn at their real depth (20 px per metre). Tall parts (backrests, locker
   tops, tank lids) get a lit lip on their far edge. Every piece can turn all four ways.
2. **Light from directly above,** so it's right whichever way a piece turns. Top surfaces
   are brightest; seams and the front strip darker.
3. **No cast shadows.** The front strip grounds the piece.
4. **Value ladder** (guides, not limits; a piece may use 1-14):
   - silhouette edge at 5 or above on the level 1 floor (0 doesn't show);
   - main surfaces mostly 7-10;
   - seams 2-3 levels darker than the parts they split;
   - highlights up to 14. Level 15 is the text's (text colour 4).

   On the glasses, steps between levels are large up to 6 and small above it, so
   neighbouring parts above 7 need 2+ levels between them.
5. **Scale:** a cell is about 1 m. A couch is 2 cells; a chair, crate or locker 1. A piece
   fills 70-95% of its footprint.
6. **Legs** show only below a piece, in its front strip. Legs splayed out on every side
   read as spokes.
7. **Detail that survives:** features of at least 2 px, 1 px seams only with 2+ levels of
   contrast, texture only as soft one-level patches. In the sketch, detail meant to survive
   is drawn 4-5 levels off what surrounds it, or klein smooths it away.
8. **Edges:** no black outlines on pieces. Corners may be cut by a pixel.
9. **Materials:** palettes as hints: metal 5/7/9/11, fabric 5/7/9/10, plants 5/8/10/12,
   screens 2-3 with text at 11-12. No wood: it's a moon base.

**Game sprites** put visibility first. Bodies sit at 8-12. Enemies are seen through holes
in the road's level 3 cover, so their edges stay at 8 or above. The game gives towers a
dark halo (`outlined` in main.ts); enemies and the boss get a black outline baked in by
`import_sprites.py`.

## Making a piece

All the tools are in `tools/`. Python tools need Pillow from the venv (`.venv/bin/python -I`).
Generation needs Unsloth Studio running with FLUX.2-klein-4B loaded (see CLAUDE.md).
Generated work goes to `art/work/<id>/` (ignored by git).

1. **Sketch** the piece in code in the house view (`piece_sketches.py`, `SKETCHES`; other
   forms in `FORMS`, such as `bold` and `depth`). Check it with `sketch_sheet.py`.
   - Pieces that join are sketched as one cell and their parts built from it
     (`row_from_single`, `path_from_straight`, `grid_from_single`), seamless by
     construction.
   - Draw detail bold, in shapes of 2 px or more.
2. **Seeds:** `piece_gen.py [--recipe B] [--seeds 1,2,3,4] [--form bold] <id>`. It runs
   klein `reference` with the sketch and the couch as the style reference. Every call is
   time-limited (`studio_gen.py`): Studio generations can hang. Seeds already made are
   kept and only reconverted.
   - Recipe B is the pieces' prompt; S, T, U and V were the sprites', towers' and boss
     arms'. `--average --shades 10` and a smaller `--block` suit big sprites.
   - Pieces in `MASKED` are cut back to the sketch's pixels. A grid tile's border is
     read from its sketch (`grid_border`).
3. **Convert:** the conversion snaps to the grid when klein drew on it. Otherwise it
   fits what klein drew into the sketch's box by one factor, centred, with
   detail-preserving downscaling, then cuts it to a few shades and removes specks.
4. **Look:** `seed_sheet.py art/work/<name>.png id,...` puts a batch's seeds side by side.
5. **Pick** in the art library (`npm run dev`, then `/tools/art-library/?map=<id>`,
   Candidates, "use"). That copies the candidate into the pack and rebuilds `src/pack.ts`.
   Reviews (★, redo) are saved to `art/reviews.json`, which is also ignored by git.

Floors, road walls and wall kits work the same way through `kit_gen.py` (`art/work/kits/`)
and the library's map pages. `floor_plain.py` draws plain plate floors in code.

**Game sprites:** the picks are `art/sprites/<id>.png`. To change one, generate with
`piece_gen.py`, copy the chosen picture over its file, and run
`.venv/bin/python -I tools/import_sprites.py`. That writes `src/sprites.ts` (don't edit
it by hand), `art/sprites/preview.png` and the phone guide's pictures in `public/guide/`.
Turrets are drawn facing right and derived facing up (`piece_gen.py --derive`); the boss's
arm sockets are read off its body picture (`SOCKETS` in main.ts).
