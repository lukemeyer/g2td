// The map renderer (docs/art.md): the one drawing of a map's static image,
// used by the game, the map editor, the phone's Stats page and the art library, so they
// all show the same pixels. Everything comes from the art pack (src/pack.ts, built from
// art/pack/ by tools/pack_build.py) at its display size; nothing is scaled, pieces only
// turn in quarter turns.
//
// Order: floor tiles, decals, pieces (with their joins), placed walls, then the road:
// its wall kit in a ring round the road band, and the band itself at ROAD_LEVEL (it must
// match the text covers, so it stays a flat fill).

import { W, H, CH, COLS, ROWS, X0, GAP, key, ROAD, ROADS, dirOf } from "../rules.ts";
import { PACK, type Pic, type PieceDef, type MapArt } from "../pack.ts";
/** The pack this renderer draws from, for the dev tools: after src/pack.ts changes Vite can hand
 *  them a second copy of the module, and anything they add to that copy would never be drawn. */
export { PACK };

/** [row, col, pack id, variant, quarter turns clockwise], anchored at the top-left cell
 *  of the piece's (turned) footprint. */
export type Placed = [number, number, string, number, number];
/** A placed wall in the gap on one side of a cell. */
export type Edge = [number, number, "e" | "s" | "w" | "n"];
/** art/maps/<id>/layout.json, as the map editor writes it. */
export interface Layout {
    version: 2;
    /** Floor tiles per cell: a character per cell, `legend` naming its floor; '.' or a
     *  character not in the legend is the map's own floor. A row's first character is
     *  column `from` (-1, the left margin, since the editor reached the margins; 0 in
     *  layouts saved before). */
    floor?: { legend: Record<string, string>; rows: string[]; from?: number };
    pieces: Placed[];
    walls: Edge[];
}
export const EMPTY: Layout = { version: 2, pieces: [], walls: [] };

/** The road band's level: as bright as a textColor 0 glyph on the glasses. */
export const ROAD_LEVEL = 3;
const SEE = 255;

/** A column's left edge, also off the grid (the margins). */
export const xOf = (c: number) => X0 + c * (20 + GAP);
/** The columns a layout may use: the grid and a margin column on each side (whole cells
 *  on screen, though no road, slot or tower uses them). */
export const FIRST_COL = -1, LAST_COL = COLS;
/** A cell's key over the grid and its margins (rules' `key` wraps at the edges). */
export const cellKey = (r: number, c: number) => r * (COLS + 2) + c + 1;
/** The margin cells the road runs through, where it enters at column 0 or leaves at the
 *  last column running across, or leaves at column 0 running back (the boss map): the
 *  band runs on to the screen's edge there. */
export function roadMargins(): [number, number][] {
    const out: [number, number][] = [];
    for (const A of ROADS) {
        const n = A.length, d0 = dirOf(A[0], A[1]), d1 = dirOf(A[n - 2], A[n - 1]);
        if (A[0][1] === 0 && d0[1] > 0) out.push([A[0][0], FIRST_COL], [A[0][0] + 1, FIRST_COL]);
        if (A[n - 1][1] === COLS - 2 && d1[1] > 0) out.push([A[n - 1][0], LAST_COL], [A[n - 1][0] + 1, LAST_COL]);
        if (A[n - 1][1] === 0 && d1[1] < 0) out.push([A[n - 1][0], FIRST_COL], [A[n - 1][0] + 1, FIRST_COL]);
    }
    return out;
}
const yOf = (r: number) => r * CH + 4;

// --- pictures --------------------------------------------------------------------------

export interface Art { w: number; h: number; px: Uint8Array }
const decoded = new Map<Pic, Art[]>();
/** A pack picture as levels (SEE where see-through), turned `turns` quarter turns clockwise. */
export function artOf(pic: Pic, turns = 0): Art {
    let t = decoded.get(pic);
    if (!t) {
        const h = pic.length, w = pic[0].length, px = new Uint8Array(w * h);
        for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const ch = pic[y][x]; px[y * w + x] = ch === "." ? SEE : parseInt(ch, 16); }
        const a0: Art = { w, h, px };
        const turn = (a: Art): Art => {
            const out = new Uint8Array(a.px.length);
            for (let y = 0; y < a.h; y++) for (let x = 0; x < a.w; x++) out[x * a.h + (a.h - 1 - y)] = a.px[y * a.w + x];
            return { w: a.h, h: a.w, px: out };
        };
        t = [a0, turn(a0), turn(turn(a0)), turn(turn(turn(a0)))];
        decoded.set(pic, t);
    }
    return t[((turns % 4) + 4) % 4];
}
function blit(px: Uint8Array, a: Art, x0: number, y0: number, crop?: [number, number, number, number]) {
    const [cx, cy, cw, ch] = crop ?? [0, 0, a.w, a.h];
    for (let y = 0; y < ch; y++) {
        const yy = y0 + y;
        if (yy < 0 || yy >= H) continue;
        for (let x = 0; x < cw; x++) {
            const xx = x0 + x, v = a.px[(cy + y) * a.w + cx + x];
            if (v !== SEE && xx >= 0 && xx < W) px[yy * W + xx] = v;
        }
    }
}

// --- what a map uses ------------------------------------------------------------------

/** The map's art (pack.json "maps"), or the first one the pack has. */
export const artFor = (mapId: string): MapArt => PACK.maps[mapId] ?? Object.values(PACK.maps)[0];
/** The pieces this map can use: the shared ones ("maps" absent or "all") and its own. */
export function piecesFor(mapId: string): string[] {
    const own = artFor(mapId)?.pieces ?? ["*"];
    return Object.entries(PACK.pieces).filter(([id, p]) => own.includes("*") || own.includes(id) || !p.maps || p.maps.includes("all") || p.maps.includes(mapId)).map(([id]) => id);
}

// --- footprints ------------------------------------------------------------------------

export function footprint(def: PieceDef, r: number, c: number, turns: number): [number, number][] {
    let [w, h] = def.size;
    if (turns % 2) [w, h] = [h, w];
    const out: [number, number][] = [];
    for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) out.push([r + i, c + j]);
    return out;
}
/** The pixel box of a footprint: x0..x1, y0..y1 inclusive. */
export function boxOf(cells: [number, number][]): [number, number, number, number] {
    const rs = cells.map((q) => q[0]), cs = cells.map((q) => q[1]);
    return [xOf(Math.min(...cs)), yOf(Math.min(...rs)), xOf(Math.max(...cs)) + 19, yOf(Math.max(...rs)) + 19];
}
/** Where a picture sits in a box: centred (rounding down). */
const place = (a: Art, [x0, y0, x1, y1]: number[]) => [x0 + Math.floor((x1 - x0 + 1 - a.w) / 2), y0 + Math.floor((y1 - y0 + 1 - a.h) / 2)];

const DIRS: [number, number][] = [[0, 1], [1, 0], [0, -1], [-1, 0]];      // e s w n: a turn's local "right"

/** Draw the pieces: decals first, then the rest, each with the join parts its
 *  neighbours call for (pack piece "joins"):
 *  - row (1x1 pieces): joins its own kind along its local x (turned with it): "alone",
 *    "start", "middle", "end", and a "link5"/"link7" in the 5 or 7 px gap to the next;
 *  - grid (1x1, not turned): a 9-slice by its neighbours, "g<x><y>" with x in s/l/m/r and
 *    y in s/t/m/b, "hl_<y>"/"vl_<x>" in the gaps and "corner" where four meet;
 *  - path (1x1): "dot", "end", "straight", "bend", "tee", "cross" turned to meet its
 *    neighbours, the straight's middle filling the gaps.
 *  A part a piece lacks falls back to "body" (or its first part). */
export function drawPieces(px: Uint8Array, pieces: Placed[]) {
    // every piece on a cell: a decal and a piece may share one (a pipe over a catwalk),
    // and each must still find its own kind there to join
    const at = new Map<number, Placed[]>();
    for (const p of pieces) {
        const def = PACK.pieces[p[2]];
        if (def) for (const [r, c] of footprint(def, p[0], p[1], p[4])) { const k = cellKey(r, c); at.set(k, [...(at.get(k) ?? []), p]); }
    }
    const same = (r: number, c: number, p: Placed, turned: boolean) =>
        (at.get(cellKey(r, c)) ?? []).some((q) => q[2] === p[2] && (!turned || q[4] % 4 === p[4] % 4) && q[0] === r && q[1] === c);
    const part = (def: PieceDef, name: string, v: number): Pic | null => {
        const pics = def.parts[name] ?? def.parts.body ?? Object.values(def.parts)[0];
        return pics?.length ? pics[((v % pics.length) + pics.length) % pics.length] : null;
    };
    const order = [...pieces].sort((a, b) => Number(!PACK.pieces[a[2]]?.decal) - Number(!PACK.pieces[b[2]]?.decal));
    for (const p of order) {
        const [r, c, id, v, turns] = p, def = PACK.pieces[id];
        if (!def) continue;
        const q = ((turns % 4) + 4) % 4, box = boxOf(footprint(def, r, c, q));
        const draw = (name: string, t = q) => {
            const pic = part(def, name, v);
            if (!pic) return null;
            const a = artOf(pic, t), [x, y] = place(a, box);
            blit(px, a, x, y);
            return { a, x, y };
        };
        if (def.joins === "row" && def.size[0] === 1 && def.size[1] === 1) {
            const [dr, dc] = DIRS[q];
            const R = same(r + dr, c + dc, p, true), L = same(r - dr, c - dc, p, true);
            const drawn = draw(!L && !R ? "alone" : !L ? "start" : !R ? "end" : "middle");
            if (drawn && R) {
                // the link, in the gap towards the next one: 5 px across, 7 down
                const across = dr === 0, pic = part(def, across ? "link5" : "link7", v);
                if (pic) {
                    const a = artOf(pic, q);
                    const lx = across ? (dc > 0 ? xOf(c) + 20 : xOf(c) - 5) : drawn.x;
                    const ly = across ? drawn.y : dr > 0 ? yOf(r) + 20 : yOf(r) - 7;
                    blit(px, a, lx, ly);
                }
            }
        } else if (def.joins === "grid") {
            const N = same(r - 1, c, p, false), S = same(r + 1, c, p, false), E = same(r, c + 1, p, false), Wn = same(r, c - 1, p, false);
            const xs = !Wn && !E ? "s" : !Wn ? "l" : !E ? "r" : "m", ys = !N && !S ? "s" : !N ? "t" : !S ? "b" : "m";
            draw(`g${xs}${ys}`, 0);
            const blitPart = (name: string, x: number, y: number) => { const pic = def.parts[name]?.[0]; if (pic) blit(px, artOf(pic), x, y); };
            if (E) blitPart(`hl_${ys}`, xOf(c) + 20, yOf(r));
            if (S) blitPart(`vl_${xs}`, xOf(c), yOf(r) + 20);
            if (E && S && same(r + 1, c + 1, p, false)) blitPart("corner", xOf(c) + 20, yOf(r) + 20);
        } else if (def.joins === "path") {
            const n = same(r - 1, c, p, false), e = same(r, c + 1, p, false), s = same(r + 1, c, p, false), w = same(r, c - 1, p, false);
            const arms = [e, s, w, n], k = arms.filter(Boolean).length;
            let name = "dot", t = 0;
            if (k === 1) { name = "end"; t = arms.indexOf(true); }
            else if (k === 2 && e === w) { name = "straight"; t = e ? 0 : 1; }
            else if (k === 2) { name = "bend"; t = [0, 1, 2, 3].find((i) => arms[i] && arms[(i + 1) % 4])!; }
            else if (k === 3) { name = "tee"; t = [1, 2, 3, 0][arms.indexOf(false)]; }
            else if (k === 4) name = "cross";
            draw(name, t);
            const straight = part(def, "straight", v);
            if (straight) {
                if (e) { const a = artOf(straight, 0), [, y] = place(a, box); blit(px, a, xOf(c) + 20, y, [0, 0, 5, a.h]); }
                if (s) { const a = artOf(straight, 1), [x] = place(a, box); blit(px, a, x, yOf(r) + 20, [0, 0, a.w, 7]); }
            }
        } else draw("body");
    }
}

// --- floor, walls ----------------------------------------------------------------------

/** Floor tiles (25x27: a cell and the gaps right of it and below it) over the whole
 *  screen, the margins too; a cell's tile from the layout, else the map's floor; the
 *  variant picked by the cell, so it doesn't change as the map is edited. A floor with a
 *  `panel` [w, h] is one plate over w x h cells, its tiles row by row, each cell taking
 *  the tile of its place in the plate. Drawn dimmed (FLOOR_DIM). */
export function drawFloor(px: Uint8Array, mapId: string, layout: Layout) {
    const art = artFor(mapId), legend = layout.floor?.legend ?? {}, rows = layout.floor?.rows ?? [], from = layout.floor?.from ?? 0;
    for (let r = -1; r <= ROWS; r++)
        for (let c = -1; c <= COLS + 1; c++) {
            const ch = r >= 0 && r < ROWS && c >= FIRST_COL && c <= LAST_COL && c >= from ? rows[r]?.[c - from] : undefined;
            const f = PACK.floors[(ch && legend[ch]) || art?.floor] ?? Object.values(PACK.floors)[0];
            if (!f) continue;
            const mod = (a: number, n: number) => ((a % n) + n) % n;
            const tile = f.panel ? f.tile[mod(r, f.panel[1]) * f.panel[0] + mod(c, f.panel[0])] : f.tile[mod(r * 7 + c * 13, f.tile.length)];
            blit(px, dimmed(artOf(tile)), xOf(c), yOf(r));
        }
}

/** Floors are drawn darker than their tiles (asked for after 0.6.1): each level through
 *  FLOOR_DIM, so the ground sits under the road (3) and the pieces stand out. Levels 1
 *  and 2 meet, which also quietens busy floors. */
const FLOOR_DIM = [0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8, 9, 9];
const dimCache = new WeakMap<Art, Art>();
function dimmed(a: Art): Art {
    let d = dimCache.get(a);
    if (!d) { d = { w: a.w, h: a.h, px: a.px.map((v) => (v === SEE ? SEE : FLOOR_DIM[v])) }; dimCache.set(a, d); }
    return d;
}

/** Placed walls from the map's wall kit: "h" in the gap under a cell, "v" in the gap
 *  right of it, "node" where gaps cross, at both ends of every wall. */
export function drawWalls(px: Uint8Array, mapId: string, walls: Edge[]) {
    const kit = PACK.walls[artFor(mapId)?.walls] ?? Object.values(PACK.walls)[0];
    if (!kit) return;
    const h = artOf(kit.h), v = artOf(kit.v), node = artOf(kit.node);
    for (const [r0, c0, side] of walls) {
        // w and n walls are the e and s walls of the cell before
        const [r, c, s] = side === "w" ? [r0, c0 - 1, "e"] : side === "n" ? [r0 - 1, c0, "s"] : [r0, c0, side];
        if (s === "s") { blit(px, h, xOf(c), yOf(r) + 20); blit(px, node, xOf(c) - 5, yOf(r) + 20); blit(px, node, xOf(c) + 20, yOf(r) + 20); }
        else { blit(px, v, xOf(c) + 20, yOf(r)); blit(px, node, xOf(c) + 20, yOf(r) - 7); blit(px, node, xOf(c) + 20, yOf(r) + 20); }
    }
}

// --- the road ------------------------------------------------------------------------

/** The road band: road cells and the gaps between neighbouring ones, run on through the
 *  margin to the screen's edge where a road enters or leaves at the side (roadMargins). Per map, cached. */
const bands = new Map<string, Uint8Array>();
function bandOf(mapId: string): Uint8Array {
    let band = bands.get(mapId);
    if (band) return band;
    band = new Uint8Array(W * H);
    const fill = (x0: number, y0: number, x1: number, y1: number) => {
        for (let y = Math.max(0, y0); y <= Math.min(H - 1, y1); y++) band!.fill(1, y * W + Math.max(0, x0), y * W + Math.min(W - 1, x1) + 1);
    };
    for (const k of ROAD) {
        const r = Math.floor(k / COLS), c = k % COLS;
        const right = c + 1 < COLS && ROAD.has(key([r, c + 1])), down = ROAD.has(key([r + 1, c]));
        const x1 = right ? xOf(c + 1) - 1 : xOf(c) + 19, y1 = down ? yOf(r + 1) - 1 : yOf(r) + 20;
        fill(xOf(c), yOf(r), x1, yOf(r) + 20);
        fill(xOf(c), yOf(r), xOf(c) + 19, y1);
        if (right && down && ROAD.has(key([r + 1, c + 1]))) fill(xOf(c), yOf(r), x1, y1);
    }
    for (const A of ROADS) {
        const n = A.length, d0 = dirOf(A[0], A[1]), d1 = dirOf(A[n - 2], A[n - 1]);
        if (A[0][1] === 0 && d0[1] > 0) fill(0, yOf(A[0][0]), xOf(0) - 1, yOf(A[0][0] + 1) + 20);
        if (A[n - 1][1] === COLS - 2 && d1[1] > 0) fill(xOf(COLS - 1) + 20, yOf(A[n - 1][0]), W - 1, yOf(A[n - 1][0] + 1) + 20);
        if (A[n - 1][1] === 0 && d1[1] < 0) fill(0, yOf(A[n - 1][0]), xOf(0) - 1, yOf(A[n - 1][0] + 1) + 20);
    }
    bands.set(mapId, band);
    return band;
}

/** The road walls: a ring `width` px deep round the band, from the map's road kit. A
 *  pixel beside a straight edge takes the strip (x along the edge, its row by depth,
 *  row 0 touching the band); one off a corner of the band takes the corner picture. */
function drawRoad(px: Uint8Array, mapId: string) {
    const band = bandOf(mapId);
    const kit = PACK.roads[artFor(mapId)?.road] ?? Object.values(PACK.roads)[0];
    if (kit) {
        const D = kit.width, strip = artOf(kit.strip), corner = artOf(kit.corner);
        const inBand = (x: number, y: number) => x >= 0 && x < W && y >= 0 && y < H && band[y * W + x] === 1;
        // Chebyshev distance to the band (up to D), level by level from it
        const dist = new Uint8Array(W * H).fill(255);
        let front: number[] = [];
        for (let i = 0; i < W * H; i++) if (band[i]) { dist[i] = 0; front.push(i); }
        for (let d = 1; d <= D && front.length; d++) {
            const next: number[] = [];
            for (const i of front) {
                const x = i % W, y = (i - x) / W;
                for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
                    const xx = x + dx, yy = y + dy, j = yy * W + xx;
                    if (xx >= 0 && xx < W && yy >= 0 && yy < H && dist[j] === 255) { dist[j] = d; next.push(j); }
                }
            }
            front = next;
        }
        for (let i = 0; i < W * H; i++) {
            const d = dist[i];
            if (d === 0 || d === 255) continue;
            const x = i % W, y = (i - x) / W;
            let v: number | undefined;
            if (inBand(x, y + d) || inBand(x, y - d)) v = strip.px[(d - 1) * strip.w + (x % strip.w)];
            else if (inBand(x + d, y) || inBand(x - d, y)) v = strip.px[(d - 1) * strip.w + (y % strip.w)];
            else {
                // off a corner: how far across and down to the band's corner
                let ax = d, ay = d;
                for (let k = 1; k <= d; k++) {
                    if (inBand(x + k, y + d) || inBand(x - k, y + d) || inBand(x + k, y - d) || inBand(x - k, y - d)) { ax = Math.min(ax, k); }
                    if (inBand(x + d, y + k) || inBand(x - d, y + k) || inBand(x + d, y - k) || inBand(x - d, y - k)) { ay = Math.min(ay, k); }
                }
                v = corner.px[(Math.min(D, ay) - 1) * corner.w + (Math.min(D, ax) - 1)];
            }
            if (v !== undefined && v !== SEE) px[i] = v;
        }
    }
    for (let i = 0; i < W * H; i++) if (band[i]) px[i] = ROAD_LEVEL;
}

// --- a map ---------------------------------------------------------------------------

/** A map's static image, 576x288 levels: floor, decals and pieces, placed walls, and
 *  with `road` (the current map in rules.ts, useMap) its road walls and band. */
export function drawMap(mapId: string, layout: Layout, road = true): Uint8Array {
    const px = new Uint8Array(W * H);
    drawFloor(px, mapId, layout);
    drawPieces(px, layout.pieces ?? []);
    drawWalls(px, mapId, layout.walls ?? []);
    if (road) drawRoad(px, mapId);
    return px;
}
