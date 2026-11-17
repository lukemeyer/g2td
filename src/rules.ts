// The rules of the 2-wide-road tower defense, with no display or bridge in them,
// so the same code runs in the game (main.ts) and in the balance simulator
// (tools/balance.ts).
//
// The game moves in steps, and each step has three phases, one display frame each:
// enemies move one cell, the towers about to fire show it, then their shots land.
// Enemies walk their own lane cell by cell, so where an enemy is IS a cell.
//
// Two classes of tower stand in fixed slots along the road:
//   - triplines (laser, stasis): a thin line across a straight stretch. They act on
//     whatever is on the line, in both lanes.
//   - turrets (sniper, cannon): a 2x2 pad past a corner, in line with one straight
//     stretch, firing straight down it. Double-barrelled: one barrel per lane.
//
// The campaign is the maps in maps.json, played in order. useMap() makes one of them
// the current map: everything below that depends on the map (the road, its lanes,
// the slots, the waves) is rebuilt, and importers see the new values. The last map
// is the boss: a machine on the left with three arms, one road out of it, and a
// turret pad at the end of the road's first straight that shoots the arm on the road
// whenever that straight is empty. The arms take turns: each sends its own kind of
// bot, wave after wave, until it is destroyed; destroying all three wins.

import CAMPAIGN from "./maps.json" with { type: "json" };

export const W = 576, H = 288, CH = 27, COLS = 21, ROWS = 10;

// Columns are 20px glyphs plus one 5px space (the glasses font's only space glyph), so
// every gap is the same and every 2x2 pad is 45x47 (they alternated 5 and 10 px before,
// to average the rows' 27, which made pads 45 or 50 wide). The grid (520px) is centred,
// its left edge on the 5px text grid; roads entering or leaving at the sides run on
// out to the screen's edge.
export const GAP = 5;
export const X0 = Math.floor((W - (COLS * 20 + (COLS - 1) * GAP)) / 2 / 5) * 5;
export const X: number[] = [X0];
for (let c = 0; c < COLS; c++) X.push(X[c] + 20 + GAP);

export type Cell = [row: number, col: number];
export type Pt = [x: number, y: number];
export type Dir = [number, number];
export const key = ([r, c]: Cell) => r * COLS + c;
export const cellCenter = ([r, c]: Cell): Pt => [X[c] + 10, r * CH + 14];
export const dist = (a: Pt, b: Pt) => Math.hypot(a[0] - b[0], a[1] - b[1]);
export const dirOf = (a: Cell, b: Cell): Dir => [Math.sign(b[0] - a[0]), Math.sign(b[1] - a[1])];

// --- the maps --------------------------------------------------------------------

/** v: a tripline across a horizontal stretch at [row, col]; h: across a vertical one;
 *  t: a turret pad, top-left [row, col], facing [dr, dc], and on the boss map
 *  "boss" (reaches its whole straight, shoots the boss's arm when the straight is empty). */
type SlotSpec = ["v" | "h", number, number] | ["t", number, number, number, number, "boss"?];
/** What a boss arm sends: walkers in single file, floaters, or a swarm of walkers two
 *  abreast in packs. */
export type ArmKind = "walkers" | "floaters" | "swarm";
/** One of the boss's arms, in the order they take the road: its health in hits (every
 *  shot from the boss pad is one, whatever the turret), and its waves
 *  (the n-th sends count + (n-1) * more bots of bot + (n-1) * grow health). */
export interface ArmDef { kind: ArmKind; hp: number; count: number; more: number; bot: number; grow: number }
/** The boss: its cells, its arms (only the boss pad's shots hurt them), what each
 *  kill pays (reward), the credits after each wave (bonus), and more (turn) after the
 *  wave an arm was destroyed in. Half way through each wave it holds the rest back until
 *  the road is clear, then cools down for `hits` shots from the boss pad: the only time
 *  the arm can be hit. */
export interface BossDef {
    cells: [Cell, Cell]; reward: number; bonus: number; turn: number; hits: number;
    arms: ArmDef[];
}
export interface MapDef {
    id: string; name: string; theme: string; waves: number; credits: number; hp?: number; pace?: number;
    anchors?: Cell[]; lanes?: Cell[][]; slots?: SlotSpec[]; autoTrips?: boolean;
    /** Where the message box goes, [row, first column], when not where messageBox would put it. */
    msgBox?: Cell;
    boss?: BossDef;
    /** The random map (src/random_map.ts): made from a seed, endless waves. */
    random?: boolean;
}
export const MAPS = CAMPAIGN.maps as unknown as MapDef[];
export const START_LIVES = 20;
/** Lives back for clearing a map, up to START_LIVES. */
export const MAP_BONUS_LIVES = 5;

/** The current map and its place in the campaign. */
export let MAP: MapDef, MAP_INDEX = 0;
/** Each road's anchors: the top-left cell of the 2x2 road square at each turn. A road
 *  map has one road; the boss map two, out of the boss. */
export let ROADS: Cell[][];
/** The first road's anchors (the only road, on a road map). */
export let ANCHORS: Cell[];
/** Every lane, start to goal: each road's left lane, then its right. */
export let LANES: Cell[][];
export let ROAD: Set<number>;
/** The first road's centre line: the middle of each 2x2 square, one per step. */
export let SQUARES: Cell[];
export let ROAD_LEN: number;
export let ROAD_CELLS: RoadCell[];
export let SLOTS: Slot[];
/** Clearing this many waves wins the map; on the boss map the last never ends. */
export let WAVES: number;
export let KINDS_OF: Record<SlotClass, TowerKind[]>;
export let START_CREDITS: number;
let CENTRES: Pt[][], CUMS: number[][], ROAD_CELL: Map<number, RoadCell>;

/** A lane of a road as a list of cells, start to goal. `left` is the lane on the
 *  left of travel. */
function lane(anchors: Cell[], left: boolean): Cell[] {
    // At each anchor the lane turns in one cell of the 2x2 square. Horizontal travel
    // decides its row (left of → is the top row, left of ← the bottom), vertical
    // travel its column (left of ↓ is the east column, left of ↑ the west). At the two
    // ends the other axis is the square's trailing (start) or leading (goal) edge.
    const corners: Cell[] = anchors.map((a, i) => {
        const din = i > 0 ? dirOf(anchors[i - 1], a) : null;
        const dout = i < anchors.length - 1 ? dirOf(a, anchors[i + 1]) : null;
        let dr = -1, dc = -1;
        for (const d of [din, dout]) {
            if (!d) continue;
            if (d[0] === 0) dr = (d[1] > 0) === left ? 0 : 1;
            else dc = (d[0] > 0) === left ? 1 : 0;
        }
        if (dr < 0) dr = din ? (din[0] > 0 ? 1 : 0) : (dout![0] > 0 ? 0 : 1);
        if (dc < 0) dc = din ? (din[1] > 0 ? 1 : 0) : (dout![1] > 0 ? 0 : 1);
        return [a[0] + dr, a[1] + dc];
    });
    const out: Cell[] = [corners[0]];
    for (let i = 1; i < corners.length; i++) {
        let [r, c] = out[out.length - 1];
        const [r1, c1] = corners[i];
        while (r !== r1 || c !== c1) {
            if (r !== r1) r += Math.sign(r1 - r); else c += Math.sign(c1 - c);
            out.push([r, c]);
        }
    }
    return out;
}

function squaresOf(anchors: Cell[]): Cell[] {
    const out: Cell[] = [anchors[0]];
    for (let i = 1; i < anchors.length; i++) {
        const d = dirOf(anchors[i - 1], anchors[i]);
        let [r, c] = anchors[i - 1];
        while (r !== anchors[i][0] || c !== anchors[i][1]) { r += d[0]; c += d[1]; out.push([r, c]); }
    }
    return out;
}

export function pointAt(s: number, road = 0): Pt {
    const CENTRE = CENTRES[road], CUM = CUMS[road];
    s = Math.max(0, Math.min(CUM[CUM.length - 1], s));
    let i = 1;
    while (i < CUM.length - 1 && CUM[i] < s) i++;
    const f = (s - CUM[i - 1]) / (CUM[i] - CUM[i - 1] || 1);
    return [CENTRE[i - 1][0] + f * (CENTRE[i][0] - CENTRE[i - 1][0]), CENTRE[i - 1][1] + f * (CENTRE[i][1] - CENTRE[i - 1][1])];
}

/** How far along a road's centre line a point projects. */
export function progressOf(p: Pt, road = 0): number {
    const CENTRE = CENTRES[road], CUM = CUMS[road];
    let best = Infinity, at = 0;
    for (let i = 1; i < CENTRE.length; i++) {
        const [ax, ay] = CENTRE[i - 1], [bx, by] = CENTRE[i];
        const L = dist(CENTRE[i - 1], CENTRE[i]);
        const f = Math.max(0, Math.min(1, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / (L * L)));
        const d = dist(p, [ax + f * (bx - ax), ay + f * (by - ay)]);
        if (d < best) { best = d; at = CUM[i - 1] + f * L; }
    }
    return at;
}

/** A road cell, its lane (an index into LANES), its road, and its progress along that road. */
export interface RoadCell { cell: Cell; lane: number; road: number; t: number }

// --- slots ---------------------------------------------------------------------

export type SlotClass = "trip" | "turret";
export interface Slot {
    cls: SlotClass;
    /** Off-road cells it stands on: a tripline's two posts, or a turret's 2x2 pad. */
    cells: Cell[];
    /** Road cells it acts on: under a tripline, or down a turret's line of fire. */
    reach: Cell[];
    /** Turret only: how many cells past the pad's front edge each reach cell is (1 = adjacent). */
    depth: number[];
    /** Tripline: the line runs up and down (across a horizontal stretch). */
    vertical: boolean;
    /** Turret: the way it faces, as [dr, dc]. */
    face: Dir;
    /** Boss map: the boss pad reaches its whole straight and shoots the arm on the road
     *  when the straight is empty. */
    boss?: boolean;
    /** Progress along the road, for ordering the slots. */
    t: number;
    center: Pt;
}

/** A tripline across a horizontal stretch (road rows r, r+1) at column c. */
function tripV(r: number, c: number): Slot {
    const reach: Cell[] = [[r, c], [r + 1, c]];
    return { cls: "trip", cells: [[r - 1, c], [r + 2, c]], reach, depth: [], vertical: true, face: [0, 0], t: 0, center: [X[c] + 10, (r + 1) * CH] };
}
/** A tripline across a vertical stretch (road columns c, c+1) at row r. */
function tripH(r: number, c: number): Slot {
    const reach: Cell[] = [[r, c], [r, c + 1]];
    return { cls: "trip", cells: [[r, c - 1], [r, c + 2]], reach, depth: [], vertical: false, face: [0, 0], t: 0, center: [(X[c] + X[c + 1]) / 2 + 10, r * CH + 14] };
}
/** A turret on the 2x2 pad with top-left (r, c), facing `face`, reaching up to `far` cells. */
function turret(r: number, c: number, face: Dir, far = 4): Slot {
    const reach: Cell[] = [], depth: number[] = [];
    for (let k = 1; k <= far; k++)
        for (let i = 0; i < 2; i++) {
            const cell: Cell = face[0] === 0
                ? [r + i, face[1] > 0 ? c + 1 + k : c - k]
                : [face[0] > 0 ? r + 1 + k : r - k, c + i];
            if (ROAD.has(key(cell))) { reach.push(cell); depth.push(k); }
        }
    return {
        cls: "turret", cells: [[r, c], [r, c + 1], [r + 1, c], [r + 1, c + 1]], reach, depth, vertical: false, face, t: 0,
        center: [(X[c] + X[c + 1]) / 2 + 10, r * CH + 27.5],
    };
}

/** The slots in the order they stand along the road, for the cursor: each where the
 *  road cell it reaches nearest to it is (a turret pad past a corner stands at the
 *  corner, though its reach starts further back), road by road. Slot indices; SLOTS keeps its own order (towers fire in it). */
export function standingOrder(): number[] {
    const at = SLOTS.map((s): [number, number] => {
        const near = s.reach.reduce((a, b) => (dist(cellCenter(b), s.center) < dist(cellCenter(a), s.center) ? b : a));
        const rc = ROAD_CELL.get(key(near))!;
        return [rc.road, rc.t];
    });
    return [...SLOTS.keys()].sort((a, b) => at[a][0] - at[b][0] || at[a][1] - at[b][1] || a - b);
}

/** The HUD box in the top-right corner: no road or slot may use these cells. The
 *  rest of row 0 is map. */
export const HUD_BOX = { row: 0, col: 17, rows: 2, cols: 4 };
export const inHudBox = ([r, c]: Cell) => r >= HUD_BOX.row && r < HUD_BOX.row + HUD_BOX.rows && c >= HUD_BOX.col && c < HUD_BOX.col + HUD_BOX.cols;
const onMap = ([r, c]: Cell) => r >= 0 && r < ROWS && c >= 0 && c < COLS;
/** The boss's cells, so nothing is built on it. */
const inBoss = ([r, c]: Cell) => !!MAP.boss && r >= MAP.boss.cells[0][0] && r <= MAP.boss.cells[1][0] && c >= MAP.boss.cells[0][1] && c <= MAP.boss.cells[1][1];
const free = (used: Set<number>) => (c: Cell) => onMap(c) && !ROAD.has(key(c)) && !used.has(key(c)) && !inHudBox(c) && !inBoss(c);

/** Slots for a map without a list: a turret pad past every corner (and the goal), in
 *  line with each stretch that meets there, then a tripline on every other cell of
 *  each straight. Pads first, then posts where they still fit. */
function autoSlots(pads: boolean, used = new Set<number>()): Slot[] {
    const out: Slot[] = [];
    const ok = free(used);
    const take = (s: Slot) => { out.push(s); for (const c of s.cells) used.add(key(c)); };
    for (const A of ROADS) {
        if (pads)
            for (let i = 1; i < A.length; i++)
                for (const j of [i - 1, i + 1]) {
                    if (j >= A.length) continue;
                    const d = dirOf(A[j], A[i]);                        // from the stretch towards the corner
                    const s = turret(A[i][0] + 2 * d[0], A[i][1] + 2 * d[1], [-d[0], -d[1]]);
                    if (s.cells.every(ok) && s.reach.length) take(s);
                }
        // Every cell of the straight in turn, at least 2 from the last one taken. Where
        // a post stands in a one-row gap (the road again past it), triplines go in pairs
        // instead, two side by side and then two cells left: the road sharing that gap
        // gets the cells left, in pairs too, so the cursor meets two of one road's
        // triplines, then two of the other's (asked for after 0.6.1: one by one,
        // alternating roads, was hard to follow on Regolith Mine and the boss map).
        for (let i = 0; i + 1 < A.length; i++) {
            const [[r0, c0], [r1, c1]] = [A[i], A[i + 1]];
            const [a, b] = r0 === r1 ? [Math.min(c0, c1), Math.max(c0, c1)] : [Math.min(r0, r1), Math.max(r0, r1)];
            for (let k = a + 2, last = -Infinity, run = 0; k < b; k++) {
                const s = r0 === r1 ? tripV(r0, k) : tripH(k, c0);
                if (!s.cells.every(ok)) continue;
                // the cell past each post, away from this road
                const past = s.cells.map(([r, c]): Cell => (s.vertical ? [2 * r - s.reach[r < s.reach[0][0] ? 0 : 1][0], c] : [r, 2 * c - s.reach[c < s.reach[0][1] ? 0 : 1][1]]));
                const packed = past.some((c) => onMap(c) && ROAD.has(key(c)));
                const gap = k - last;
                if (packed ? (run === 1 && gap === 1) || gap >= 3 : gap >= 2) { take(s); run = gap === 1 ? run + 1 : 1; last = k; }
            }
        }
    }
    return out;
}

/** Make map `index` the current one. */
export function useMap(index: number) {
    MAP_INDEX = Math.max(0, Math.min(MAPS.length - 1, index));
    MAP = MAPS[MAP_INDEX];
    ROADS = MAP.lanes ?? [MAP.anchors!];
    ANCHORS = ROADS[0];
    LANES = ROADS.flatMap((A) => [lane(A, true), lane(A, false)]);
    ROAD = new Set(LANES.flat().map(key));
    if ([...ROAD].some((k) => inHudBox([Math.floor(k / COLS), k % COLS]))) throw new Error(`${MAP.name}: the road runs into the HUD box`);
    CENTRES = ROADS.map((A) => squaresOf(A).map(([r, c]): Pt => [(X[c] + X[c + 1]) / 2 + 10, r * CH + 27.5]));
    CUMS = CENTRES.map((C) => { const cum = [0]; for (let i = 1; i < C.length; i++) cum.push(cum[i - 1] + dist(C[i - 1], C[i])); return cum; });
    SQUARES = squaresOf(ANCHORS);
    ROAD_LEN = Math.max(...CUMS.map((c) => c[c.length - 1]));
    ROAD_CELLS = LANES.flatMap((cells, ln) => cells.map((cell) => ({ cell, lane: ln, road: ln >> 1, t: progressOf(cellCenter(cell), ln >> 1) })));
    ROAD_CELL = new Map(ROAD_CELLS.map((rc) => [key(rc.cell), rc]));

    // Map rule: a turret pad sits past a corner, in line with exactly one straight
    // stretch, so it always fires down that stretch.
    const listed = (MAP.slots ?? []).map((s): Slot => {
        if (s[0] === "v") return tripV(s[1], s[2]);
        if (s[0] === "h") return tripH(s[1], s[2]);
        const [, r, c, dr, dc, role] = s as ["t", number, number, number, number, "boss"?];
        const slot = turret(r, c, [dr, dc], role === "boss" ? COLS : 4);
        if (role === "boss") slot.boss = true;
        return slot;
    });
    const used = new Set(listed.flatMap((s) => s.cells.map(key)));
    SLOTS = MAP.slots && !MAP.autoTrips ? listed : [...listed, ...autoSlots(!MAP.slots, used)];
    for (const s of SLOTS) s.t = Math.min(...s.reach.map((c) => ROAD_CELL.get(key(c))!.t)) + (s.cls === "trip" ? 0.5 : 0);
    SLOTS.sort((a, b) => a.t - b.t);
    const taken = new Set<number>();
    for (const s of SLOTS) {
        for (const c of s.cells) {
            if (!free(taken)(c)) throw new Error(`${MAP.name}: slot cell ${c} is off the map, on the road or the boss, in the HUD box, or taken`);
            taken.add(key(c));
        }
        if ((!s.reach.length || !s.reach.every((c) => ROAD.has(key(c))))) throw new Error(`${MAP.name}: slot at ${s.cells[0]} reaches no road`);
    }
    MSG_BOX = messageBox(taken);
    WAVES = MAP.boss ? Infinity : MAP.waves;
    START_CREDITS = MAP.credits;
    KINDS_OF = { trip: ["laser", "stasis"], turret: ["sniper", "cannon"] };
}
/** Where the message line goes on this map: a dark box over one row of cells (the
 *  game draws it into the map while building), `MSG_COLS` wide, on no tower slot, the
 *  HUD box, or the boss and its health bars; it may run into the margin columns (-1 and
 *  COLS). Nearest the top middle, on the road where it can be (nothing stands there
 *  while building). Narrower only where a map has no room. A map's `msgBox` puts it
 *  elsewhere (the user lined some up so it moves less between maps). */
export let MSG_BOX: { row: number; col: number; cols: number };
export const MSG_COLS = 11;
function messageBox(slots: Set<number>): { row: number; col: number; cols: number } {
    const onMap = (c: number) => c >= 0 && c < COLS;
    const blocked = (r: number, c: number) => (onMap(c) && slots.has(key([r, c]))) || (r < HUD_BOX.row + HUD_BOX.rows && c >= HUD_BOX.col)
        || (!!MAP.boss && r <= MAP.boss.cells[1][0] + 2 && c <= MAP.boss.cells[1][1] + 2);
    if (MAP.msgBox) {
        const [row, col] = MAP.msgBox;
        if (Array.from({ length: MSG_COLS }, (_, k) => col + k).some((c) => c < -1 || c > COLS || blocked(row, c)))
            throw new Error(`${MAP.name}: the message box at ${MAP.msgBox} covers a slot, the HUD or the boss, or is off the map`);
        return { row, col, cols: MSG_COLS };
    }
    for (let n = MSG_COLS; n >= 6; n--) {
        let best: { row: number; col: number; cols: number } | null = null, cost = Infinity;
        for (let r = 0; r < ROWS; r++)
            for (let c = -1; c + n <= COLS + 1; c++) {
                const cells = Array.from({ length: n }, (_, k) => c + k);
                if (cells.some((cc) => blocked(r, cc))) continue;
                const off = Math.abs(c + n / 2 - COLS / 2), road = cells.filter((cc) => onMap(cc) && ROAD.has(key([r, cc]))).length;
                const k = r + off / 4 - road / 4;
                if (k < cost) { cost = k; best = { row: r, col: c, cols: n }; }
            }
        if (best) return best;
    }
    return { row: ROWS - 1, col: 0, cols: COLS };
}

useMap(0);

// --- rules ---------------------------------------------------------------------
// Tuned with tools/balance.ts; see the notes there for what each number is aiming at.

export type TowerKind = "laser" | "stasis" | "sniper" | "cannon";
export const TOWERS: Record<TowerKind, { name: string; glyph: string; cls: SlotClass; cost: number; cooldown: number; range: number }> = {
    laser: { name: "Laser", glyph: "┃", cls: "trip", cost: 40, cooldown: 2, range: 0 },
    stasis: { name: "Stasis", glyph: "▒", cls: "trip", cost: 35, cooldown: 1, range: 0 },
    sniper: { name: "Sniper", glyph: "◎", cls: "turret", cost: 70, cooldown: 2, range: 4 },
    cannon: { name: "Cannon", glyph: "●", cls: "turret", cost: 90, cooldown: 2, range: 2 },
};
export const LASER_DAMAGE = 12, SNIPER_DAMAGE = 15, CANNON_DAMAGE = 14;
const DAMAGE: Record<TowerKind, number> = { laser: LASER_DAMAGE, stasis: 0, sniper: SNIPER_DAMAGE, cannon: CANNON_DAMAGE };
/** A stasis line slows what crosses it to this speed, for this many steps. */
export const SLOW_FACTOR = 1 / 3, SLOW_STEPS = 7;

export type EnemyKind = "beetle" | "shield";
/** `speed` is cells per step. */
export const ENEMIES: Record<EnemyKind, { hp: number; speed: number; reward: number; harm: number; gap: number; shield: boolean }> = {
    beetle: { hp: 4, speed: 1, reward: 2, harm: 1, gap: 2, shield: false },
    shield: { hp: 10, speed: 2 / 3, reward: 5, harm: 2, gap: 3, shield: true },
};

export function waveOf(n: number): EnemyKind[] {
    const count = Math.round(8 + 2 * n);
    const shieldEvery = n < 3 ? 0 : n < 5 ? 3 : 2; // none, then 1 in 3, then 1 in 2
    return Array.from({ length: count }, (_, i): EnemyKind => (shieldEvery && i % shieldEvery === shieldEvery - 1 ? "shield" : "beetle"));
}
/** Enemy health grows faster than linearly, so a fixed set of towers runs out eventually. */
export const hpScale = (n: number) => 1 + 1.4 * (n - 1) + 0.08 * (n - 1) ** 2;
/** A road map's waves climb the difficulty curve (waveOf, hpScale) PACE steps at a
 *  time from step 1, so its few waves reach what the old 10-wave game did late on. */
export const levelOf = (n: number) => 1 + (n - 1) * (MAP.pace ?? 1);
export const waveBonus = (n: number) => (MAP.boss ? MAP.boss.bonus : 20 + 6 * levelOf(n));
/** Every SWARM_EVERY-th wave of a road map is a swarm: walkers only, two abreast (one
 *  in each lane) and close behind each other, in packs. The cannon's job: its splash
 *  catches a pack where a sniper takes one walker a shot. */
export const SWARM_EVERY = 4;
export const SWARM = { pack: 5, packGap: 4, count: 2, hp: 1 };
export const isSwarm = (n: number) => !MAP.boss && n % SWARM_EVERY === 0;
/** A swarm on difficulty step `level`: SWARM.count times an ordinary wave's enemies,
 *  rounded to whole pairs, in packs of SWARM.pack pairs a step apart. */
export const swarmSize = (level: number) => 2 * Math.round((waveOf(level).length * SWARM.count) / 2);

// --- state -----------------------------------------------------------------------

export interface Enemy {
    kind: EnemyKind; hp: number; maxHp: number;
    /** The cells it walks, index into them, and that cell. */
    path: RoadCell[]; i: number; cell: Cell; t: number;
    /** Movement owed, in cells; a whole cell moves it. */
    acc: number;
    slow: number; dead: boolean;
    /** A floater's shield: it takes the next damaging hit, whatever its strength,
     *  and goes. `popped` is the step it went. */
    shield: boolean; popped: number;
    /** The last tower that damaged it, which gets the kill. */
    lastHit?: TowerKind;
}
export interface Built { kind: TowerKind; cooldown: number }
/** One tower firing this step: picked in the aim phase, landed in the hit phase. */
export interface Shot {
    slot: number; kind: TowerKind;
    /** Everything it hits (all of them, for a tripline or a cannon's splash). */
    targets: Enemy[];
    /** Turret: the enemy it aims at, the barrel (0 or 1) on that enemy's lane, the
     *  cells the shot flies over before reaching it, and the cells its splash covers. */
    target?: Enemy; barrel: number; path: Cell[]; splash: Cell[];
    /** At the boss's arm (its straight empty): `path` runs the whole straight. */
    boss?: boolean;
}
/** One enemy to come: its kind, health, the steps to wait before the next (0: in the
 *  same step), on the boss map or in a swarm its lane (an index into LANES), and on the
 *  boss map whether the boss cools down after it. */
interface Spawn { kind: EnemyKind; hp: number; gap: number; lane?: number; cool?: boolean }

export type Phase = 0 | 1 | 2;
export const MOVE = 0, AIM = 1, HIT = 2;

export interface Game {
    credits: number; lives: number; wave: number; waveActive: boolean; over: boolean;
    /** The map is won: all WAVES cleared, or every boss arm destroyed (`over` is set too). */
    won: boolean;
    /** Slots built since the last wave started: they can still be taken back. */
    fresh: Set<number>;
    spawnQueue: Spawn[]; spawnWait: number; steps: number; phase: Phase;
    enemies: Enemy[]; built: Map<number, Built>;
    /** Lane flips: progress values where the beetle and shield lanes trade places. */
    beetleStartLane: number; flips: number[];
    /** Each kind's walk from the entry to the goal, cell by cell, with the flips applied. */
    paths: Record<EnemyKind, RoadCell[]>;
    /** The boss's arms' health (none off the boss map), the arm on the road, the quarter
     *  turns the boss has made (it turns the next living arm to the road after every
     *  wave), and how many waves each arm has sent. */
    arms: number[]; arm: number; turns: number; armWaves: number[];
    /** The arm on the road was destroyed this wave: main.ts blows it up on screen and clears this. */
    broke: boolean;
    /** The boss's cooldown half way through a wave: it sends nothing until the road is
     *  clear and the boss pad has hit the arm this many more times. */
    cool: number;
    seed: number;
    /** A message for the HUD, set by the rules (wave cleared). */
    note: string;
    shots: Shot[];
    /** This step's marks cut into enemies, by cell. */
    engrave: Map<number, string>;
    /** One entry per wave started, for the phone's stats page. */
    history: WaveStats[];
}

export interface WaveStats {
    wave: number;
    /** How many enemies the wave sends. */
    enemies: number;
    kills: Record<TowerKind, number>; damage: Record<TowerKind, number>;
    /** Enemies slowed by stasis, shields broken, damage done to the boss's arms. */
    slowed: number; shields: number; boss: number;
    leaked: number; earned: number;
}
const perTower = () => ({ laser: 0, stasis: 0, sniper: 0, cannon: 0 });
export const killsOf = (h: WaveStats) => Object.values(h.kills).reduce((a, b) => a + b, 0);

/** A new game on the current map, with `lives` carried in from the last one. */
export function newGame(seed = 12345, lives = START_LIVES): Game {
    const g: Game = {
        credits: START_CREDITS, lives, wave: 0, waveActive: false, over: false, won: false, fresh: new Set(),
        spawnQueue: [], spawnWait: 0, steps: 0, phase: MOVE, enemies: [], built: new Map(),
        beetleStartLane: 0, flips: [], paths: { beetle: [], shield: [] },
        arms: MAP.boss ? MAP.boss.arms.map((a) => a.hp) : [], arm: 0, turns: 0, armWaves: MAP.boss ? MAP.boss.arms.map(() => 0) : [], broke: false, cool: 0,
        seed, note: "", shots: [], engrave: new Map(), history: [],
    };
    rollFlips(g);
    return g;
}

/** A game between waves as plain JSON, enough to carry on from: main.ts saves it at
 *  the end of every wave and after every build, and resumes it on launch. A wave cut
 *  short (the app closed, the connection lost) starts again from this. */
export interface SavedGame {
    v: 1; map: string; wave: number; lives: number; credits: number; steps: number;
    /** [slot, kind, cooldown] per tower; the slots still fresh (taken back for a refund). */
    built: [number, TowerKind, number][]; fresh: number[];
    seed: number; lane: number; flips: number[];
    arms: number[]; turns: number; armWaves: number[]; history: WaveStats[];
}

export function saveGame(g: Game): SavedGame {
    return {
        v: 1, map: MAP.id, wave: g.wave, lives: g.lives, credits: g.credits, steps: g.steps,
        built: [...g.built].map(([s, b]) => [s, b.kind, b.cooldown]), fresh: [...g.fresh],
        seed: g.seed, lane: g.beetleStartLane, flips: [...g.flips],
        arms: [...g.arms], turns: g.turns, armWaves: [...g.armWaves], history: g.history,
    };
}

/** A saved game on the current map, or null if it isn't one (another map, another
 *  version, a wave past the last, a tower on a slot that can't take it). */
export function loadGame(s: Partial<SavedGame> | null): Game | null {
    const int = (n: unknown, lo: number, hi: number): n is number => Number.isInteger(n) && (n as number) >= lo && (n as number) <= hi;
    if (!s || s.v !== 1 || s.map !== MAP.id || !int(s.wave, 0, WAVES - 1) || !int(s.lives, 1, 99) || !int(s.credits, 0, 1e6)) return null;
    if (!Array.isArray(s.built) || !Array.isArray(s.fresh) || !Array.isArray(s.flips) || !Array.isArray(s.history)) return null;
    if (!s.built.every(([i, k]) => int(i, 0, SLOTS.length - 1) && KINDS_OF[SLOTS[i].cls].includes(k))) return null;
    if (!s.fresh.every((i) => s.built!.some(([j]) => j === i)) || !s.flips.every((f) => typeof f === "number")) return null;
    const g = newGame(s.seed, s.lives);
    g.wave = s.wave; g.credits = s.credits; g.steps = s.steps ?? 0;
    g.built = new Map(s.built.map(([i, kind, cooldown]) => [i, { kind, cooldown: int(cooldown, 0, 9) ? cooldown : 0 }]));
    g.fresh = new Set(s.fresh);
    g.seed = int(s.seed, 0, 0x7fffffff) ? s.seed : g.seed;
    if (!MAP.boss) { g.beetleStartLane = s.lane === 1 ? 1 : 0; g.flips = s.flips; layPaths(g); }
    if (MAP.boss) {
        const arms = MAP.boss.arms;
        if (!Array.isArray(s.arms) || s.arms.length !== arms.length || !s.arms.every((a, i) => int(a, 0, arms[i].hp)) || !s.arms.some((a) => a > 0)) return null;
        g.arms = s.arms;
        if (!int(s.turns, 0, 1e6) || !Array.isArray(s.armWaves) || s.armWaves.length !== arms.length || !s.armWaves.every((n) => int(n, 0, 1e6))) return null;
        g.turns = s.turns; g.armWaves = s.armWaves;
        const k = armAt(g, 0);
        if (k < 0 || !g.arms[k]) return null;
        g.arm = k;
    }
    g.history = s.history;
    return g;
}

const rnd = (g: Game) => (g.seed = (g.seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;

/** Re-roll where the lanes flip: 1-3 places on straight stretches, spread out, and
 *  never the same as the last wave's, so each kind's path changes every wave. The
 *  boss map has no flips: its waves are scripted. */
export function rollFlips(g: Game) {
    if (MAP.boss) return;
    const before = `${g.beetleStartLane} ${g.flips}`;
    for (let tries = 0; tries < 20; tries++) {
        rollOnce(g);
        if (`${g.beetleStartLane} ${g.flips}` !== before) break;
    }
}

function rollOnce(g: Game) {
    g.beetleStartLane = rnd(g) < 0.5 ? 0 : 1;
    const straight: number[] = [];
    for (let i = 2; i < SQUARES.length - 2; i++) {
        const a = dirOf(SQUARES[i - 1], SQUARES[i]), b = dirOf(SQUARES[i], SQUARES[i + 1]);
        if (a[0] === b[0] && a[1] === b[1]) straight.push(i);
    }
    const want = 1 + Math.floor(rnd(g) * 3);
    const picked: number[] = [];
    for (let tries = 0; picked.length < want && tries < 200; tries++) {
        const i = straight[Math.floor(rnd(g) * straight.length)];
        if (picked.every((j) => Math.abs(i - j) >= 5)) picked.push(i);
    }
    // Halfway between two squares, so no cell sits exactly on a flip.
    const CUM = CUMS[0];
    g.flips = picked.sort((a, b) => a - b).map((i) => (CUM[i] + CUM[i + 1]) / 2);
    layPaths(g);
}

/** Each kind walks its lane in the lane's own order and crosses over at a flip. */
function layPaths(g: Game) {
    for (const kind of ["beetle", "shield"] as EnemyKind[]) {
        const bounds = [-Infinity, ...g.flips, Infinity];
        g.paths[kind] = [];
        for (let s = 0; s + 1 < bounds.length; s++) {
            const ln = (g.beetleStartLane + s + (kind === "beetle" ? 0 : 1)) % 2;
            for (const cell of LANES[ln]) {
                const rc = ROAD_CELL.get(key(cell))!;
                if (rc.lane === ln && rc.t >= bounds[s] && rc.t < bounds[s + 1]) g.paths[kind].push(rc);
            }
        }
    }
}

const beetleLaneAt = (g: Game, t: number) => (g.beetleStartLane + g.flips.filter((f) => f <= t).length) % 2;
/** Which kind walks this cell in the wave under way, or else the next (the map is
 *  drawn before a wave starts): swarms send walkers only, and on the boss map the arm
 *  on the road decides. */
export const kindOfCell = (g: Game, rc: RoadCell): EnemyKind =>
    MAP.boss ? (armOf(g).kind === "floaters" ? "shield" : "beetle")
    : isSwarm(g.waveActive ? g.wave : g.wave + 1) || rc.lane === beetleLaneAt(g, rc.t) ? "beetle" : "shield";

export const isOn = (e: Enemy, cells: Cell[]) => cells.some((c) => c[0] === e.cell[0] && c[1] === e.cell[1]);
/** The road cells a turret of this kind reaches from its slot (all of a tripline's,
 *  and all of the boss pad's). */
export const reachOf = (s: Slot, kind: TowerKind) =>
    s.cls === "trip" || s.boss ? s.reach : s.reach.filter((_, i) => s.depth[i] <= TOWERS[kind].range);

/** The boss's arm on the road. */
export const armOf = (g: Game) => MAP.boss!.arms[g.arm];
/** The boss's arm sockets are quarter turns clockwise from east (the road); arm k starts
 *  k quarters anticlockwise of east, so the next arm waits in the north socket, and the
 *  fourth socket (south at first) is empty. */
export const socketOf = (g: Game, k: number) => (4 - k + g.turns) % 4;
/** The arm in a socket, or -1 if it is empty. */
const armAt = (g: Game, socket: number) => MAP.boss!.arms.findIndex((_, k) => socketOf(g, k) === socket);
/** After every wave the boss turns a quarter clockwise, and on past the empty socket and
 *  destroyed arms, until a living arm faces the road. */
function turnBoss(g: Game) {
    do g.turns++; while (!(g.arms[armAt(g, 0)] > 0));
    g.arm = armAt(g, 0);
}
/** Swarm pairs: each pair leaves together (gap 0 to its second), the next a step
 *  behind, in packs of SWARM.pack pairs SWARM.packGap steps apart. */
const pairs = (n: number, hp: number): Spawn[] => Array.from({ length: n }, (_, p) => [0, 1].map((lane) => ({
    kind: "beetle" as const, hp, lane, gap: lane === 0 ? 0 : (p + 1) % SWARM.pack ? 1 : SWARM.packGap,
}))).flat();

/** The next wave of the boss's arm on the road: walkers in single file, alternating
 *  lanes, a gap of 2, 1, 3, 3 between them (the 1 lets one slip past a laser that just
 *  fired); floaters alternating lanes; or a swarm of pairs. Half way through, the boss
 *  cools down. */
function bossWave(g: Game): Spawn[] {
    const a = armOf(g), n = ++g.armWaves[g.arm];
    const count = a.count + (n - 1) * a.more, hp = a.bot + (n - 1) * a.grow;
    const kind: EnemyKind = a.kind === "floaters" ? "shield" : "beetle";
    const out: Spawn[] = a.kind === "swarm" ? pairs(Math.round(count / 2), hp)
        : Array.from({ length: count }, (_, k) => ({ kind, hp, lane: k % 2, gap: kind === "shield" ? ENEMIES.shield.gap : [2, 1, 3, 3][k % 4] }));
    // After the middle pair, or the middle bot.
    out[a.kind === "swarm" ? 2 * Math.floor(out.length / 4) - 1 : Math.floor(out.length / 2) - 1].cool = true;
    return out;
}

export function startWave(g: Game): boolean {
    if (g.over || g.waveActive) return false;
    g.wave++;
    g.waveActive = true;
    g.fresh.clear();
    g.broke = false;
    g.cool = 0;
    if (MAP.boss) g.spawnQueue = bossWave(g);
    else {
        const scale = hpScale(levelOf(g.wave)) * (MAP.hp ?? 1);
        if (isSwarm(g.wave)) g.spawnQueue = pairs(swarmSize(levelOf(g.wave)) / 2, Math.round(ENEMIES.beetle.hp * scale * SWARM.hp));
        else g.spawnQueue = waveOf(levelOf(g.wave)).map((kind) => ({ kind, hp: Math.round(ENEMIES[kind].hp * scale), gap: ENEMIES[kind].gap }));
    }
    g.history.push({ wave: g.wave, enemies: g.spawnQueue.length, kills: perTower(), damage: perTower(), slowed: 0, shields: 0, boss: 0, leaked: 0, earned: 0 });
    g.spawnWait = 0;
    g.phase = MOVE;
    return true;
}

/** Build a tower; returns why not, or null. Between waves only, and never on a built slot. */
export function buy(g: Game, slot: number, kind: TowerKind): string | null {
    if (g.waveActive) return "Build between waves";
    if (g.built.has(slot)) return "Slot taken";
    if (!KINDS_OF[SLOTS[slot].cls].includes(kind)) return "Wrong slot";
    const cost = TOWERS[kind].cost;
    if (g.credits < cost) return `Need $${cost - g.credits} more`;
    g.credits -= cost;
    g.built.set(slot, { kind, cooldown: 0 });
    g.fresh.add(slot);
    return null;
}

/** Take back a tower built since the last wave started, for its full cost. */
export function unbuild(g: Game, slot: number): string | null {
    if (g.waveActive) return "Build between waves";
    if (!g.fresh.has(slot)) return "Built in an earlier wave";
    g.credits += TOWERS[g.built.get(slot)!.kind].cost;
    g.built.delete(slot);
    g.fresh.delete(slot);
    return null;
}

export interface PhaseResult { cleared?: boolean; over?: boolean; leaked?: number }

/** Run the current phase and advance to the next. */
export function stepPhase(g: Game): PhaseResult {
    if (!g.waveActive || g.over) return {};
    const phase = g.phase;
    g.phase = ((phase + 1) % 3) as Phase;
    if (phase === MOVE) return move(g);
    if (phase === AIM) { aim(g); return {}; }
    return hit(g);
}

function move(g: Game): PhaseResult {
    g.steps++;
    g.shots = [];
    g.engrave = new Map();
    g.enemies = g.enemies.filter((e) => !e.dead);
    let leaked = 0;
    for (const e of g.enemies) {
        e.acc += ENEMIES[e.kind].speed * (e.slow > 0 ? SLOW_FACTOR : 1);
        if (e.slow > 0) e.slow--;
        while (e.acc >= 1 && !e.dead) {
            e.acc -= 1;
            if (e.i + 1 >= e.path.length) {
                // Reached the goal.
                e.dead = true;
                g.lives -= ENEMIES[e.kind].harm;
                leaked += ENEMIES[e.kind].harm;
                g.history[g.history.length - 1].leaked++;
            } else {
                e.i++;
                e.cell = e.path[e.i].cell;
                e.t = e.path[e.i].t;
            }
        }
    }
    g.enemies = g.enemies.filter((e) => !e.dead);

    g.spawnWait--;
    // With nothing on the boss pad the cooldown ends as the road clears.
    if (g.cool > 0 && !g.enemies.length && !SLOTS.some((s, i) => s.boss && g.built.has(i))) g.cool = 0;
    while (g.spawnQueue.length && g.spawnWait <= 0 && !g.cool) {
        const s = g.spawnQueue.shift()!;
        const path = s.lane === undefined ? g.paths[s.kind] : LANES[s.lane].map((c) => ROAD_CELL.get(key(c))!);
        g.enemies.push({
            kind: s.kind, hp: s.hp, maxHp: s.hp, path, i: 0, cell: path[0].cell, t: path[0].t, acc: 0, slow: 0, dead: false,
            shield: ENEMIES[s.kind].shield, popped: -1,
        });
        g.spawnWait = s.gap;
        if (s.cool) g.cool = MAP.boss!.hits;
    }

    if (g.lives <= 0) {
        g.lives = 0; g.over = true; g.waveActive = false;
        return { over: true, leaked };
    }
    if (!g.spawnQueue.length && !g.enemies.length) {
        g.waveActive = false;
        if (g.wave >= WAVES) {
            g.over = g.won = true;
            g.note = `All ${WAVES} waves cleared!`;
            return { cleared: true, leaked };
        }
        const bonus = waveBonus(g.wave);
        g.credits += bonus;
        g.history[g.history.length - 1].earned += bonus;
        g.note = `Wave ${g.wave} cleared +$${bonus}`;
        // The boss turns its next arm to the road.
        if (MAP.boss) {
            const extra = g.arms[g.arm] ? 0 : MAP.boss.turn;
            g.credits += extra;
            g.history[g.history.length - 1].earned += extra;
            turnBoss(g);
            g.note = `${ARM_TITLES[armOf(g).kind]} incoming! +$${bonus + extra}`;
        }
        rollFlips(g);
        return { cleared: true, leaked };
    }
    return { leaked };
}

/** Pick what fires this step. Nothing moves until the next step, so the picks hold. */
function aim(g: Game) {
    for (const [i, b] of g.built) {
        if (b.cooldown > 0) { b.cooldown--; continue; }
        const s = SLOTS[i], reach = reachOf(s, b.kind);
        const on = g.enemies.filter((e) => isOn(e, reach));
        // The boss pad hits the arm only in the boss's cooldown, with the whole road clear.
        if (!on.length && !(s.boss && g.cool > 0 && !g.enemies.length)) continue;
        b.cooldown = TOWERS[b.kind].cooldown - 1;
        if (s.cls === "trip") { g.shots.push({ slot: i, kind: b.kind, targets: on, barrel: 0, path: [], splash: [] }); continue; }
        if (!on.length) {
            // At the arm on the road, from alternate barrels: the shot runs the barrel's
            // whole row.
            const barrel = g.steps % 2;
            const row = (c: Cell) => (s.face[0] === 0 ? c[0] === s.cells[0][0] + barrel : c[1] === s.cells[0][1] + barrel);
            g.shots.push({ slot: i, kind: b.kind, targets: [], barrel, path: s.reach.filter(row), splash: [], boss: true });
            continue;
        }
        const target = on.reduce((a, e) => (e.t > a.t ? e : a)); // furthest along
        const barrel = s.face[0] === 0 ? target.cell[0] - s.cells[0][0] : target.cell[1] - s.cells[0][1];
        // The shot flies down the target's lane, over the cells before it.
        const same = (c: Cell) => (s.face[0] === 0 ? c[0] === target.cell[0] : c[1] === target.cell[1]);
        const d = s.depth[s.reach.findIndex((c) => c[0] === target.cell[0] && c[1] === target.cell[1])];
        const path = s.reach.filter((c, k) => s.depth[k] < d && same(c));
        if (b.kind === "sniper") {
            g.shots.push({ slot: i, kind: b.kind, targets: [target], target, barrel, path, splash: [] });
        } else {
            // Splash: the target's cell and every road cell touching it, diagonals too.
            const near = (c: Cell) => Math.abs(c[0] - target.cell[0]) <= 1 && Math.abs(c[1] - target.cell[1]) <= 1;
            const splash = ROAD_CELLS.map((rc) => rc.cell).filter(near);
            const targets = g.enemies.filter((e) => near(e.cell));
            g.shots.push({ slot: i, kind: b.kind, targets, target, barrel, path, splash });
        }
    }
}

function hit(g: Game): PhaseResult {
    const h = g.history[g.history.length - 1];
    for (const shot of g.shots) {
        const s = SLOTS[shot.slot];
        if (shot.boss) { h.boss += wearArm(g); continue; }
        // Each hit is cut into the enemy's core: the laser's line, the stasis field,
        // a sniper's cross, a cannon's ╳. A shield takes the first damaging hit
        // instead (stasis passes through it).
        const mark = { laser: s.vertical ? "┃" : "━", stasis: "▒", sniper: "┼", cannon: "╳" }[shot.kind];
        for (const e of shot.targets) {
            if (shot.kind === "stasis") { e.slow = SLOW_STEPS; h.slowed++; }
            else if (e.shield) { e.shield = false; e.popped = g.steps; h.shields++; continue; }
            else {
                h.damage[shot.kind] += Math.min(DAMAGE[shot.kind], Math.max(0, e.hp));
                e.hp -= DAMAGE[shot.kind];
                e.lastHit = shot.kind;
            }
            g.engrave.set(key(e.cell), mark);
        }
    }
    const b = MAP.boss;
    for (const e of g.enemies)
        if (!e.dead && e.hp <= 0) {
            e.dead = true;
            const reward = b ? b.reward : ENEMIES[e.kind].reward;
            g.credits += reward;
            if (e.lastHit) h.kills[e.lastHit]++;
            h.earned += reward;
        }
    if (b && g.arms.every((a) => a <= 0)) {
        g.waveActive = false; g.over = g.won = true;
        g.note = "Boss Bot destroyed!";
        return { cleared: true };
    }
    return {};
}

/** Each arm's bots by name at the start of a message: "Walkers incoming!", "Start wave 4 · SWARM". */
export const ARM_TITLES: Record<ArmKind, string> = { walkers: "Walkers", floaters: "Drones", swarm: "SWARM" };
/** What the player calls each arm's bots (the floater is a "Drone" to the player). */
export const ARM_NAMES: Record<ArmKind, string> = { walkers: "walkers", floaters: "drones", swarm: "swarm" };

/** Hit the arm on the road once, a hit of the boss's cooldown used; when the arm goes,
 *  the bots it still had to send go with it. */
function wearArm(g: Game): number {
    g.cool = Math.max(0, g.cool - 1);
    if (g.arms[g.arm] <= 0) return 0;
    if (!--g.arms[g.arm]) { g.spawnQueue = []; g.broke = true; g.cool = 0; }
    return 1;
}
