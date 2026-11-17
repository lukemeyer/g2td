// Tower defense on the 2-wide road: the display, the map image, and input.
// The rules live in rules.ts, shared with the balance simulator (tools/balance.ts).
//
// The image holds everything that only changes between waves: scenery, the road,
// the towers, and an enemy sprite in every road cell, turned to face the way its
// lane runs. One dim text layer covers every road cell with █ except where an enemy
// is, so a revealed cell IS the enemy.
//
// Each step of a wave is three frames: enemies move, the towers about to fire show
// it (a lit tripline, a turret's ring and a cannon's round in the barrel), then the
// shots land (a thick line over whatever is caught on a tripline, a tracer or a blast
// down a turret's lane), each cut into the enemy it hits.
//
// Text layers, back to front: cover (█ on empty road), idle (the thin lines of built triplines,
// over the covers), fx (placed on a 5px grid, so a sniper's line can stop half way
// into its target), offset (half a row lower: the parts of vertical lines that
// cross a row gap), engrave (dim, cut into enemies), the HUD box in the top-right
// corner, and the message line (top or bottom). The cursor and turret rings are on
// fx. A blank text container behind the image takes the input.
//
// The maps come one after another (rules.ts useMap): clearing one loads the next,
// with the towers gone and the lives carried over. The last is the boss.

import { waitForEvenAppBridge, OsEventTypeList } from "@evenrealities/even_hub_sdk";
import { getTextWidth } from "@evenrealities/pretext";
import { encodeGreyPng } from "./png";
import { initPhone, showMap, showStats } from "./phone.ts";
import { CAMPAIGN_LEN, RANDOM_INDEX, newRandomMap } from "./random_map.ts";
import { WALKER, FLOATER, SHADOWS, POSTS, TURRET_ART, BOSS, ARMS } from "./sprites.ts";
import { drawMap, EMPTY } from "./render/map.ts";
import { LAYOUTS } from "./render/layouts.ts";
import {
    W, H, CH, COLS, ROWS, GAP, X0, X, key, HUD_BOX, ROADS, LANES, ROAD_CELLS, SLOTS, TOWERS, KINDS_OF, AIM, HIT,
    MAPS, MAP, MAP_INDEX, useMap, MAP_BONUS_LIVES, newGame, startWave, waveOf, stepPhase, buy, unbuild, kindOfCell, reachOf, isSwarm,
    killsOf, WAVES, START_LIVES, standingOrder, saveGame, loadGame, armOf, socketOf, ARM_NAMES, ARM_TITLES, MSG_BOX,
    type Game, type Slot, type TowerKind, type SavedGame, type ArmKind, type Pt,
} from "./rules.ts";

const BLOCK = "█", HOLE = "　";
/** One frame, counted from the start of the last one (drawing included); a step is three. */
const TICK_MS = 250;
/** Game speed: frames during a wave come TICK_MS / speed apart. 2x is the normal
 *  pace (the user found 1x slow on the glasses); Fast Mode in the long-press menu
 *  toggles 4x. */
const NORMAL_SPEED = 2, FAST_SPEED = 4;
let speed = NORMAL_SPEED;
/** A Fast Mode note shows on the message line even during a wave (bottom row), until it goes. */
const FAST_NOTE = /^Fast Mode /;

let NEXT = SLOTS.length; // the "next wave" item sits after the last slot
/** The slots in the cursor's order: as they stand along the road (rules.ts standingOrder). */
let ORDER: number[] = [];

let g: Game;
let mode: "browse" | "select" | "over" | "confirm" | "map";
/** Restart asks first (it was easy to hit in the menu): the answer (no, the
 *  default; this map; all maps from the first), and the mode to go back to on no.
 *  The game waits meanwhile. */
const RESTART = ["NO", "THIS MAP", "ALL MAPS"];
let restartYes = 0, beforeConfirm: typeof mode = "browse";
/** "Choose map" in the menu: the map the message line offers (swipe), started with full lives on a tap. */
let pickMap = 0;
/** The lives this map was entered with: a retry starts with them again (at least 6). */
let entryLives = START_LIVES, testedW = false;
let sel: number, opt: number, tick = 0;
/** The phase whose result is on screen, or -1 between waves. */
let shown = -1;

/** Start map `index` with `lives`, and keep the place for next time. */
function startMap(index: number, lives: number) {
    useMap(index);
    layoutMap();
    entryLives = lives;
    restart();
    g.note = MAP.random ? "Random · ∞ waves" : MAP.boss ? `${MAP.name} · ${ARM_NAMES[armOf(g).kind]} incoming!` : `Map ${MAP_INDEX + 1} · ${MAP.name}`;
    keepPlace(MAP_INDEX, entryLives);
    persist();
}

/** The map that comes after this one is won, and the lives to start it with. */
const nextMap = (): [number, number] =>
    MAP_INDEX < CAMPAIGN_LEN - 1 ? [MAP_INDEX + 1, Math.min(START_LIVES, g.lives + MAP_BONUS_LIVES)] : [0, START_LIVES];

/** Where the campaign is: the map, and the lives it was entered with. */
const keepPlace = (index: number, lives: number) => save("g2td.campaign", `${index},${lives}`);

/** Keep the game between waves, to carry on from on launch: after every wave and
 *  every build. A wave cut short (the app closed, the connection lost) starts again
 *  from here. */
function persist() {
    if (!g.waveActive && !g.over) save("g2td.game", JSON.stringify(saveGame(g)));
}

/** Carry on with the saved game, if it is one on this map. */
function resume(text: string) {
    let s: SavedGame | null = null;
    try { s = JSON.parse(text); } catch { /* none saved */ }
    const kept = loadGame(s);
    if (!kept) { console.log(`no saved game to resume (${text.length} bytes)`); return; }
    g = kept;
    g.note = `${MAP.name} · resumed`;
    console.log(`resumed ${MAP.id} after wave ${g.wave}`);
}

function restart(test = true) {
    g = newGame(Date.now() & 0x7fffffff, Math.max(6, entryLives));
    mode = "browse"; sel = NEXT; opt = 0; shown = -1;
    // Testing in the simulator: ?w=6 starts the first map before wave 6 with every slot built.
    const w = Number(new URLSearchParams(location.search).get("w"));
    if (w > 1 && test && !testedW) {
        testedW = true;
        g.wave = w - 1;
        g.credits = 10000;
        SLOTS.forEach((s, i) => buy(g, i, KINDS_OF[s.cls][i % KINDS_OF[s.cls].length]));
        g.credits = 0;
    }
}

/** What a tap on the slot under the cursor offers: the kinds for a free slot; for a
 *  tower built since the last wave started, "remove" (full refund) and "cancel". */
const options = (): string[] => (g.fresh.has(sel) ? ["remove", "cancel"] : [...KINDS_OF[SLOTS[sel].cls], "cancel"]);

// --- text layers -------------------------------------------------------------------

/** One row of 20px glyphs on the column grid. */
function gridRow(get: (c: number) => string | undefined): string {
    let last = -1;
    for (let c = 0; c < COLS; c++) if (get(c) !== undefined) last = c;
    let line = "";
    for (let c = 0; c <= last; c++) {
        line += get(c) ?? HOLE;
        if (c < last) line += " ".repeat(GAP / 5);
    }
    return last < 0 ? "" : " ".repeat(X0 / 5) + line;
}
const grid = (cells: Map<number, string>, from = 0) =>
    Array.from({ length: ROWS }, (_, r) => (r < from ? "" : gridRow((c) => cells.get(r * COLS + c)))).join("\n") || " ";

/**
 * Rows of 20px glyphs placed anywhere on a 5px grid (spaces are 5px), for strokes
 * that belong in the gaps between cells. A glyph that would overlap the one before
 * it in its row is dropped; at the same x, the one added first wins.
 */
function placed(rows: [x: number, glyph: string][][]): string {
    return rows.map((row) => {
        let out = "", at = 0;
        for (const [x, ch] of [...row].sort((a, b) => a[0] - b[0])) {
            if (x < at) continue;
            for (; at + 20 <= x; at += 20) out += HOLE;
            for (; at < x; at += 5) out += " ";
            out += ch;
            at = x + 20;
        }
        return out;
    }).join("\n") || " ";
}

/** The live enemies by the cell they are on. */
const liveByCell = () => new Map(g.enemies.filter((e) => !e.dead).map((e) => [key(e.cell), e]));

/** █ over every road cell with no enemy. (A floater's shield doesn't show: a ○ ring
 *  in the cover, then on the fx layer, never read right on the glasses.) */
function coverLayer() {
    const open = liveByCell();
    const rows = Array.from({ length: ROWS }, () => [] as [number, string][]);
    const boxed = msgShown();
    for (const rc of ROAD_CELLS) {
        const e = open.get(key(rc.cell)), [r, c] = rc.cell;
        if (boxed && inMsgBox(r, c)) continue;
        if (!e) rows[r].push([X[c], BLOCK]);
    }
    return placed(rows);
}

const lineGlyph = (s: Slot, thick: boolean) => (s.vertical ? (thick ? "┃" : "│") : (thick ? "━" : "─"));

/** The thin line of every built tripline, so it shows across the covered road. */
function idleLayer() {
    const cells = new Map<number, string>();
    const boxed = msgShown();
    for (const [i] of g.built) if (SLOTS[i].cls === "trip")
        for (const c of SLOTS[i].reach) if (!(boxed && inMsgBox(...c))) cells.set(key(c), lineGlyph(SLOTS[i], false));
    return grid(cells);
}

function fxLayer() {
    const cells = marks();
    const rows = Array.from({ length: ROWS }, () => [] as [number, string][]);
    if (shown === AIM || shown === HIT) {
        for (const shot of g.shots) {
            const s = SLOTS[shot.slot];
            if (s.cls === "trip") {
                // Lit, then firing: a thick line (or the stasis field) over whatever is caught.
                const glyph = shown === AIM ? lineGlyph(s, false) : shot.kind === "stasis" ? "▒" : lineGlyph(s, true);
                for (const c of s.reach) cells.set(key(c), glyph);
            } else if (shot.boss) {
                // At the arm: down the whole straight, a thin line as it aims, then a thick
                // one bursting on the boss's edge where the shot meets it.
                for (const c of shot.path) cells.set(key(c), shown === AIM ? "─" : "━");
                if (shown === HIT) cells.set(key([shot.path[0][0], MAP.boss!.cells[1][1]]), "※");
            } else if (shown === AIM) {
                // A cannon's round leaves the barrel on the target's lane; a sniper only
                // shows its line when it fires.
                if (shot.kind === "cannon") cells.set(key(shot.path[0] ?? shot.target!.cell), "●");
            } else if (shot.kind === "sniper") {
                for (const c of shot.path) cells.set(key(c), s.face[0] === 0 ? "─" : "│");
                // Half a line into the target, from the side the shot comes in: a ─
                // moved half a cell (5px steps), or a │ on the offset layer. The font
                // has no ╴╶╵╷.
                const [r, c] = shot.target!.cell;
                if (s.face[1] > 0) rows[r].push([X[c] - 5, "─"]);
                else if (s.face[1] < 0) rows[r].push([X[c] + 5, "─"]);
            } else {
                const hitCells = new Set(shot.targets.map((e) => key(e.cell)));
                for (const c of shot.splash) if (!hitCells.has(key(c))) cells.set(key(c), "※");
            }
        }
    }
    for (const e of g.enemies) if (e.dead) cells.set(key(e.cell), "◌");
    for (const [k, ch] of cells) rows[Math.floor(k / COLS)].push([X[k % COLS], ch]);
    armBars(rows, false);
    // An arm blowing up: bursts over it while its picture changes.
    if (boom) for (const [x, y, ch] of BOOM[boom.frame]) rows[Math.floor((boom.at[1] + y) / CH)].push([Math.round((boom.at[0] + x - 10) / 5) * 5, ch]);
    return placed(rows);
}

/** Half a row lower (offset row r spans from the middle of row r to the middle of
 *  row r+1): a vertical laser in the gap between the rows its line crosses, and a
 *  vertical sniper shot's half line into its target. */
function offsetLayer() {
    const rows = Array.from({ length: ROWS }, () => [] as [number, string][]);
    if (shown === HIT)
        for (const shot of g.shots) {
            const s = SLOTS[shot.slot];
            if (shot.kind === "laser" && s.vertical) rows[s.reach[0][0]].push([X[s.reach[0][1]], "┃"]);
            if (shot.kind === "sniper" && s.face[0] !== 0 && shot.target) {
                const [r, c] = shot.target!.cell;
                const row = s.face[0] > 0 ? r - 1 : r; // coming down from above, or up from below
                if (row >= 0) rows[row].push([X[c], "│"]);
            }
        }
    armBars(rows, true);
    return placed(rows);
}

/** Each living arm's health beside it, wherever the boss has turned it: three ━ (one per
 *  hit left, as arms take three), a thin ─ for each hit taken. The east and west arms' bars are on the offset
 *  layer (half a row lower), the others on fx. */
function armBars(rows: [number, string][][], offset: boolean) {
    if (MAP.boss) MAP.boss.arms.forEach((a, k) => {
        if (!g.arms[k]) return;
        const [row, xs, half] = armBar(socketOf(g, k));
        if (half === offset) xs.forEach((x, i) => rows[row].push([x, i < Math.ceil(g.arms[k] * 3 / a.hp) ? "━" : "─"]));
    });
}

const engraveLayer = () => grid(g.engrave);

/** Every free slot in road order, then "next wave". Slots built in earlier waves are
 *  skipped; ones built since the last wave started can still be changed. */
const stops = () => ORDER.filter((i) => !g.built.has(i) || g.fresh.has(i)).concat(NEXT);

// Numbers in the box keep their width as they change, so nothing after them moves:
// `pad` is the spaces (5 px) that make a number up to `width` digits' worth, set
// outside the number and its symbol. (Fullwidth digits, the docs' fix for the
// proportional font, are 20 px apiece and read as "2 0".)
const SPACE_PX = getTextWidth(" ");
const pad = (n: number, width: number) =>
    " ".repeat(Math.max(0, Math.round((getTextWidth("0".repeat(width)) - getTextWidth(String(n))) / SPACE_PX)));

/** The HUD box: lives (a ╳ for a moment when one is lost) and credits; then the
 *  wave about to come, or during a wave the enemies killed out of all of it. */
let livesSeen = 0, lostAt = -1e9;
function boxLayer() {
    if (g.lives < livesSeen) lostAt = performance.now();
    livesSeen = g.lives;
    const heart = performance.now() - lostAt < 1500 ? "╳" : "♥";
    let second: string;
    if (g.waveActive) {
        const h = g.history[g.history.length - 1], killed = killsOf(h);
        // Fast Mode toggled mid-wave: said here for a moment (the message box is only
        // drawn between waves).
        second = FAST_NOTE.test(g.note) ? (speed === FAST_SPEED ? "FAST ON" : "FAST OFF") : `BOTS ${pad(killed, 2)}${killed}/${h.enemies}`;
    } else if (MAP.boss && mode !== "over") {
        second = ARM_HUD[armOf(g).kind];
    } else {
        const n = mode === "over" ? g.wave : g.wave + 1;
        second = isFinite(WAVES) ? `WAVE ${pad(n, 2)}${n}/${WAVES}` : `WAVE ${pad(n, 2)}${n}/∞`;
    }
    return ` ${heart}${g.lives}${pad(g.lives, 2)}  ${pad(g.credits, 3)}$${g.credits}\n ${second}`;
}
/** The box hugs its widest lines: full lives, $999, the last wave, and the biggest
 *  wave's enemy count, plus the border and a little room on the right. */
const ARM_HUD: Record<ArmKind, string> = { walkers: "WALKERS", floaters: "DRONES", swarm: "SWARM" };
const BOX_W = 6 + Math.max(...[` ♥${START_LIVES}  $999`, " WAVE 10/10", ` BOTS ${waveOf(10).length}/${waveOf(10).length}`, " BOTS 99/∞", ...Object.values(ARM_HUD).map((t) => ` ${t}`)].map(getTextWidth));

/** What is selected or going on, in one line. */
function message() {
    if (mode === "confirm") return `Restart? ↕ ${RESTART[restartYes]}`;
    if (mode === "map") return `Map ↕ ${pickMap + 1} ${MAPS[pickMap].name}`;
    if (mode === "over") {
        if (!g.won) return "GAME OVER · Tap to retry";
        if (MAP_INDEX < CAMPAIGN_LEN - 1) return "Map cleared! · tap";
        return "BASE SAVED! · replay";
    }
    if (mode === "select") {
        const o = options()[opt];
        const b = g.built.get(sel);
        if (o === "cancel") return "↕ Cancel · tap";
        if (o === "remove") return `↕ ╳ ${TOWERS[b!.kind].name} · +$${TOWERS[b!.kind].cost}`;
        const t = TOWERS[o as TowerKind];
        return `↕ ${t.name} ${t.glyph} $${t.cost} · ${g.credits < t.cost ? `╳ $${t.cost - g.credits}` : "tap"}`;
    }
    if (g.note) return g.note;
    if (startWhenDrawn) return `Wave ${g.wave + 1} incoming${isSwarm(g.wave + 1) ? ": SWARM!" : ""}`;
    if (sel === NEXT) return MAP.boss ? `Start wave ${g.wave + 1} · ${ARM_TITLES[armOf(g).kind]}` : `Start wave ${g.wave + 1}${isFinite(WAVES) ? `/${WAVES}` : ""}${isSwarm(g.wave + 1) ? " · SWARM!" : ""}`;
    if (g.fresh.has(sel)) return `${TOWERS[g.built.get(sel)!.kind].name}, removable`;
    const s = SLOTS[sel];
    return `${s.cls === "trip" ? "Tripline" : "Turret"} · tap to build`;
}

/** The message line: bright text in a dark box the map draws while building (rules'
 *  MSG_BOX, one row of cells, the same place every time on a map), and while Restart or
 *  Choose map is open (the map is drawn again with the box then, even mid-wave: the game
 *  waits). As a wave is sent the box stays until its tile is the last to change. During
 *  a wave there is no box and no message (Fast Mode says so in the HUD). */
const boxShown = () => (!g.waveActive && !startWhenDrawn) || mode === "confirm" || mode === "map";
const msgShown = () => boxShown() || startWhenDrawn;
const inMsgBox = (r: number, c: number) => r === MSG_BOX.row && c >= MSG_BOX.col && c < MSG_BOX.col + MSG_BOX.cols;
/** The box on screen: the cells' row, from just left of its first cell to just right of its last. */
const msgRect = () => {
    const x0 = Math.max(0, X0 + MSG_BOX.col * 25 - 3), x1 = Math.min(W - 1, X0 + (MSG_BOX.col + MSG_BOX.cols) * 25 - 3), y0 = MSG_BOX.row * CH, y1 = y0 + CH - 1;
    return { x0, x1, y0, y1 };
};
function msgLayer() {
    if (!msgShown()) return " ";
    const say = message(), { x0, x1 } = msgRect();
    return "\n".repeat(MSG_BOX.row) + " ".repeat(Math.max(0, Math.round(((x0 + x1) / 2 - getTextWidth(say) / 2) / SPACE_PX))) + say;
}

/** The cursor on the selected slot (and its reach while choosing), and the rings of
 *  turrets about to fire: drawn on the fx layer (they never share a cell with a shot). */
function marks() {
    const cells = new Map<number, string>();
    if (g.waveActive && (shown === AIM || shown === HIT)) {
        // A firing turret's ring: four rounded corners through its pad's cell centres.
        for (const shot of g.shots) {
            const s = SLOTS[shot.slot];
            if (s.cls === "turret") ["╭", "╮", "╰", "╯"].forEach((ch, k) => cells.set(key(s.cells[k]), ch));
        }
    } else if (!g.waveActive && mode === "browse" && sel === NEXT) {
        // Start Wave: the cursor on the road's first cell, both lanes, as if it were the
        // first stop along the road (swiping on from it goes to the first slot).
        if (tick % 4 < 3) for (const lane of LANES) cells.set(key(lane[0]), "◇");
    } else if (!g.waveActive && mode !== "over" && sel !== NEXT) {
        const s = SLOTS[sel];
        if (mode === "select" && options()[opt] !== "cancel")
            for (const c of reachOf(s, options()[opt] as TowerKind)) cells.set(key(c), "∴");
        if (tick % 4 < 3 || mode === "select") {
            if (s.cls === "turret") ["┏", "┓", "┗", "┛"].forEach((ch, k) => cells.set(key(s.cells[k]), ch));
            else for (const c of s.cells) cells.set(key(c), "◇");
        }
    }
    return cells;
}

// Back to front. textColor is brightness 0..4; a dim layer over a sprite cuts into it.
// Everything the player reads (shots, cursor, HUD, messages) is at 4, the
// brightest; the image keeps 0-14 below it (see LEVEL_MAX in tools/import_sprites.py).
const LAYERS = [
    { id: 1, name: "cover", y: 0, textColor: 0, content: coverLayer },
    { id: 2, name: "idle", y: 0, textColor: 1, content: idleLayer },
    { id: 3, name: "fx", y: 0, textColor: 4, content: fxLayer },
    { id: 5, name: "offset", y: 13, textColor: 4, content: offsetLayer },
    { id: 6, name: "engrave", y: 0, textColor: 0, content: engraveLayer },
    // Takes the input. A swipe scrolls (and bounces) the capturing container's text,
    // so it holds only a space, behind the map image.
    { id: 7, name: "input", y: 0, textColor: 0, content: () => " " },
    { id: 8, name: "box", y: 0, textColor: 4, content: boxLayer },
    { id: 9, name: "msg", y: 0, textColor: 4, content: msgLayer },
];
// The box: a rounded 1px frame just tall enough for two lines (27px each) inside it.
const BOX_X = W - BOX_W, BOX_H = 2 * CH + 2;
if (BOX_X < X[HUD_BOX.col]) throw new Error("the HUD box is wider than its cells");

// --- the image ---------------------------------------------------------------------

// Enemy sprites come from tools/import_sprites.py, facing up, 20x20 (what a cover
// hides). Every road cell gets its sprite turned to the way its lane runs
// there, and the frames play 0, 1, 2, 1 cell by cell, so a walker trots and a
// floater's shadow bobs as it steps along the lane.
const FRAME_ORDER = [0, 1, 2, 1];
/** A sprite decoded once from its rows of hex digits: a level per pixel, SEE where it
 *  is see-through ('.'). */
type Art = { w: number; h: number; px: Uint8Array };
const SEE = 255;
const decode = (rows: string[]): Art => {
    const w = rows[0].length, h = rows.length, px = new Uint8Array(w * h);
    rows.forEach((row, y) => { for (let x = 0; x < w; x++) px[y * w + x] = row[x] === "." ? SEE : parseInt(row[x], 16); });
    return { w, h, px };
};
/** A quarter turn clockwise. */
const turn = (a: Art): Art => {
    const px = new Uint8Array(a.px.length);
    for (let y = 0; y < a.h; y++) for (let x = 0; x < a.w; x++) px[x * a.h + y] = a.px[(a.h - 1 - y) * a.w + x];
    return { w: a.h, h: a.w, px };
};
/** A sprite and its three quarter turns clockwise. */
const turns4 = (a: Art) => [a, turn(a), turn(turn(a)), turn(turn(turn(a)))];
const turned = (frames: string[][]) => FRAME_ORDER.map((i) => turns4(decode(frames[i])));
// The walker is the "beetle" of the rules, the floater the "shield".
const ENEMY_ART = { beetle: turned(WALKER), shield: turned([FLOATER, FLOATER, FLOATER]) };
const SHADOW_ART = SHADOWS.map(decode);
/** Each turret by facing (quarter turns clockwise from up): its facing-up and facing-right
 *  drawings, and each turned a half for down and left (a pad is 45x47 either way). */
const turretFacings = (t: { up: string[]; side: string[] }) => {
    const up = decode(t.up), side = decode(t.side);
    return [up, side, turn(turn(up)), turn(turn(side))];
};
const TURRET_SPRITES = { sniper: turretFacings(TURRET_ART.sniper), cannon: turretFacings(TURRET_ART.cannon) };
const BOSS_ART = decode(BOSS);
const POST_ART = { laser: turns4(decode(POSTS.laser)), stasis: turns4(decode(POSTS.stasis)) };
/** Per road cell: quarter turns clockwise from up, and its place along the lane. */
const CELL_POSE = new Map<number, { turns: number; step: number }>();

/** Everything about the current map that the display works out once: each road
 *  cell's pose, the cursor's order, and where "next wave" sits. (The road and its walls
 *  are the renderer's, src/render/map.ts.) */
function layoutMap() {
    NEXT = SLOTS.length;
    ORDER = standingOrder();
    CELL_POSE.clear();
    for (const cells of LANES)
        cells.forEach((cell, i) => {
            const [a, b] = i + 1 < cells.length ? [cell, cells[i + 1]] : [cells[i - 1], cell];
            const dr = b[0] - a[0], dc = b[1] - a[1];
            CELL_POSE.set(key(cell), { turns: dr < 0 ? 0 : dc > 0 ? 1 : dr > 0 ? 2 : 3, step: i });
        });
}
/** The marks over a free tower slot, the same on every map, small, at MARK (the
 *  brightest image level): a tripline post is a ring, a turret pad a ring with sights.
 *  '#' is MARK, '-' dark, and a dark pixel goes all round, so a mark shows on whatever
 *  piece the slot stands on. While building, every slot also has corner brackets. */
const MARK = 14;
const MARKS: Record<"post" | "pad", string[]> = {
    post: [".####.", "#----#", "#----#", "#----#", "#----#", ".####."],
    pad: [
        ".....#.....",
        ".....#.....",
        "....###....",
        "...#---#...",
        "..#-----#..",
        "###-----###",
        "..#-----#..",
        "...#---#...",
        "....###....",
        ".....#.....",
        ".....#.....",
    ],
};

/** A tower's dark halo: how much of the map is kept 1, 2, 3, 4 px from its silhouette. */
const HALO = 4, HALO_KEEP = [0, 0.25, 0.5, 0.75];

/** Drawing on a screen-size image of levels. */
function painter(px: Uint8Array) {
    /** The pixels set while `outlined` draws, or null. */
    let drawn: Set<number> | null = null;
    /** Every tower pixel drawn so far: a neighbour's halo never darkens a tower. */
    const towers = new Set<number>();
    const set = (x: number, y: number, v: number) => {
        x = Math.round(x); y = Math.round(y);
        if (x >= 0 && x < W && y >= 0 && y < H) { px[y * W + x] = v; drawn?.add(y * W + x); }
    };
    /** Draw, then darken what lies round it: black next to the silhouette, fading out
     *  over HALO px (asked for after 0.6.1: a 1 px line didn't lift towers off busy map
     *  pieces), so a tower stands out on whatever it is placed on. */
    const outlined = (draw: () => void) => {
        drawn = new Set();
        draw();
        const inside = drawn;
        drawn = null;
        for (const i of inside) towers.add(i);
        const near = new Map<number, number>();   // pixel round it -> its distance to the silhouette
        for (const i of inside) {
            const x = i % W, y = (i - x) / W;
            for (let dy = -HALO; dy <= HALO; dy++) for (let dx = -HALO; dx <= HALO; dx++) {
                const xx = x + dx, yy = y + dy, j = yy * W + xx, d = Math.hypot(dx, dy);
                if (d <= HALO + 0.5 && xx >= 0 && xx < W && yy >= 0 && yy < H && !towers.has(j) && d < (near.get(j) ?? Infinity)) near.set(j, d);
            }
        }
        for (const [j, d] of near) px[j] = Math.round(px[j] * HALO_KEEP[Math.min(HALO, Math.round(d)) - 1]);
    };
    const rect = (x0: number, y0: number, x1: number, y1: number, v: number) => {
        for (let y = Math.round(y0); y <= y1; y++) for (let x = Math.round(x0); x <= x1; x++) set(x, y, v);
    };
    /** Draw a sprite as it is, see-through where it is. */
    const blit = (a: Art, x0: number, y0: number) => {
        for (let y = 0; y < a.h; y++) for (let x = 0; x < a.w; x++) { const v = a.px[y * a.w + x]; if (v !== SEE) set(x0 + x, y0 + y, v); }
    };
    return { set, rect, blit, outlined };
}

/** What of the map image only changes with the map, drawn once per map by the renderer
 *  (src/render/map.ts) from the map's layout: floor, pieces, walls, the road; dark behind
 *  the HUD box. */
let base: { id: string; px: Uint8Array } | null = null;
/** The message box's frame level; whether the map last drawn has the box. */
const MSG_FRAME = 6;
let boxDrawn = false;
async function readyBase() {
    if (base?.id === MAP.id) return;
    const px = drawMap(MAP.id, LAYOUTS[MAP.id] ?? EMPTY);
    for (let y = 0; y < BOX_H; y++) px.fill(0, y * W + BOX_X, (y + 1) * W);
    base = { id: MAP.id, px };
}

/** The map image as display levels: the map's base (readyBase first) with the towers,
 *  free-slot marks, enemy sprites and the boss over it. Without `enemies`, the road is
 *  bare (the phone's view). */
function mapLevels(enemies = true): Uint8Array {
    const px = base!.px.slice();
    const { set, rect, blit, outlined } = painter(px);

    /** One of MARKS centred on (cx, cy). */
    const stamp = (mask: string[], cx: number, cy: number) => {
        const x0 = Math.round(cx) - (mask[0].length >> 1), y0 = Math.round(cy) - (mask.length >> 1);
        mask.forEach((row, y) => [...row].forEach((ch, x) => { if (ch !== ".") rect(x0 + x - 1, y0 + y - 1, x0 + x + 1, y0 + y + 1, 0); }));
        mask.forEach((row, y) => [...row].forEach((ch, x) => { if (ch !== ".") set(x0 + x, y0 + y, ch === "#" ? MARK : 0); }));
    };
    /** Corner brackets just outside the box x0..x1, y0..y1: arms `arm` px long, 2 thick,
     *  at MARK with a dark pixel all round. */
    const brackets = (x0: number, y0: number, x1: number, y1: number, arm: number) => {
        const bars: number[][] = [];
        for (const [x, dx] of [[x0 - 2, 1], [x1 + 2, -1]]) for (const [y, dy] of [[y0 - 2, 1], [y1 + 2, -1]]) {
            bars.push([x, y, x + dx * (arm - 1), y + dy], [x, y, x + dx, y + dy * (arm - 1)]);
        }
        const box = (b: number[]) => [Math.min(b[0], b[2]), Math.min(b[1], b[3]), Math.max(b[0], b[2]), Math.max(b[1], b[3])];
        for (const b of bars) { const [a, c, d, e] = box(b); rect(a - 1, c - 1, d + 1, e + 1, 0); }
        for (const b of bars) { const [a, c, d, e] = box(b); rect(a, c, d, e, MARK); }
    };

    // Triplines: two posts beside the road, each over its cell's piece. Free, a ring on
    // each. Built, a thin line joins them across the road (it shows in the gaps; the
    // idle text layer carries it over the covers) and each post is its sprite (POSTS),
    // 24x24, turned so its emitter faces the road.
    SLOTS.forEach((sl, i) => {
        if (sl.cls !== "trip") return;
        const b = g.built.get(i);
        // Posts sit on the thin glyphs' ink: │ at x 9-10, ─ at y 14.
        const posts = sl.cells.map(([r, c]): [number, number] => [X[c] + 9, r * CH + 14]);
        if (!b) { if (building()) for (const [x, y] of posts) stamp(MARKS.post, x + 1, y); return; }
        if (sl.vertical) rect(posts[0][0], posts[0][1], posts[0][0] + 1, posts[1][1], 10);
        else rect(posts[0][0], posts[0][1], posts[1][0], posts[0][1], 10);
        // The first post is above (or left of) the road, the second below (or right).
        sl.cells.forEach(([r, c], k) => outlined(() => blit(POST_ART[b.kind as "laser" | "stasis"][(sl.vertical ? [2, 0] : [1, 3])[k]], X[c] - 2, r * CH + 2)));
    });

    // Enemy sprites in every road cell, by which lane holds which kind here, in what
    // the cell's █ cover hides (x 0-19, y 4-23). A floater's shadow never turns.
    if (enemies) for (const rc of ROAD_CELLS) {
        const kind = kindOfCell(g, rc);
        const pose = CELL_POSE.get(key(rc.cell))!;
        const frame = pose.step % FRAME_ORDER.length;
        const [r, c] = rc.cell;
        if (kind === "shield") blit(SHADOW_ART[FRAME_ORDER[frame]], X[c], r * CH + 4);
        blit(ENEMY_ART[kind][frame][pose.turns], X[c], r * CH + 4);
    }

    // Turrets fill their 2x2 pad with their sprite for the stretch they fire down. Its
    // barrels were drawn on the lanes (tools/piece_sketches.py, `tower`) at the pad's own
    // size, so it is drawn as it is, over the pad's piece. A free pad is a ring with
    // sights on its piece.
    SLOTS.forEach((sl, i) => {
        if (sl.cls !== "turret") return;
        const [r, c] = sl.cells[0];
        const x0 = X[c], x1 = X[c + 1] + 19, y0 = r * CH + 4, y1 = (r + 1) * CH + 24;
        const [fr, fc] = sl.face;
        const b = g.built.get(i);
        if (!b) { if (building()) stamp(MARKS.pad, (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2); return; }
        outlined(() => blit(TURRET_SPRITES[b.kind as "sniper" | "cannon"][fr < 0 ? 0 : fc > 0 ? 1 : fr > 0 ? 2 : 3], x0, y0));
    });

    // While building, brackets round every slot, built or free (gone once a wave is
    // sent: sendWave redraws the map first). Not on the phone's map.
    if (enemies && building()) for (const sl of SLOTS) {
        if (sl.cls === "trip") for (const [r, c] of sl.cells) brackets(X[c], r * CH + 4, X[c] + 19, r * CH + 23, 5);
        else { const [r, c] = sl.cells[0]; brackets(X[c], r * CH + 4, X[c + 1] + 19, (r + 1) * CH + 23, 9); }
    }

    // The message box: dark, with a thin frame, over whatever is there (the road's bots
    // too: nothing walks while it shows). Not on the phone's map.
    const box = enemies && boxShown();
    if (enemies) boxDrawn = box;
    if (box) {
        const { x0, x1, y0, y1 } = msgRect();
        rect(x0, y0, x1, y1, MSG_FRAME);
        rect(x0 + 1, y0 + 1, x1 - 1, y1 - 1, 0);
    }

    // The boss: its arms in their sockets, then its hull over their roots.
    if (MAP.boss) drawBoss(blit, outlined);
    else {
        // Entry and goal: bright ticks on the screen edge beside the first and last squares.
        const A = ROADS[0], first = A[0], last = A[A.length - 1];
        for (let y = first[0] * CH + 2; y < (first[0] + 2) * CH - 2; y += 3) set(0, y, 15);
        for (let y = last[0] * CH + 2; y < (last[0] + 2) * CH - 2; y += 3) { set(W - 1, y, 15); set(W - 2, y, 15); }
    }
    return px;
}

// --- the boss --------------------------------------------------------------------------
// The mother drone's body (art/sprites/sprite-boss-body.png: the hull, four legs to the corners
// and an arm socket on each side), with an arm plugged into each socket but one. The arm
// on the road is in the east socket, facing the road; after every wave the boss turns
// clockwise to its next living arm (rules.ts turnBoss), which waits in the north socket.
// Destroyed arms stay on as stumps.
/** The sockets' middles in the body's picture: east, south, west, north (quarter turns
 *  clockwise from east). The south one is under the hull's side band, so the arm there
 *  hides it. Read off the picked picture. */
const SOCKETS: Pt[] = [[88, 58], [60, 90], [33, 56], [60, 34]];
/** Where the body's picture goes: its east socket level with the road's first straight. */
const bossOrigin = (): Pt => {
    const [[, c0]] = MAP.boss!.cells, A = ROADS[0][0];
    return [X[c0], (A[0] + 1) * CH - SOCKETS[0][1]];
};
/** The middle of the hull on screen (over the north and south sockets, level with the
 *  road's first straight). */
const bossCentre = (): Pt => { const [ox, oy] = bossOrigin(); return [ox + SOCKETS[3][0], oy + SOCKETS[0][1]]; };
/** Where an arm's health bar goes for each socket (quarter turns clockwise from east):
 *  its text row, the x of its three glyphs, and whether it is on the offset layer (half
 *  a row lower). The east and west arms' bars sit just above them (offset, the row above
 *  the road's first), the north arm's above it and the south arm's below it. */
function armBar(socket: number): [number, number[], boolean] {
    const [cx] = bossCentre(), r = ROADS[0][0][0], third = (x: number) => [x, x + 20, x + 40];
    return ([[r - 1, third(cx + 15), true], [r + 3, third(cx - 30), false], [r - 1, third(cx - 75), true], [r - 2, third(cx - 30), false]] as [number, number[], boolean][])[socket];
}
/** The arms (tools/import_sprites.py), pointing east, and each turned to every socket. */
const ARM_ART = Object.fromEntries(Object.entries(ARMS).map(([k, rows]) => [k, turns4(decode(rows))])) as Record<ArmKind | "stump", Art[]>;
/** How far an arm's collar reaches back over its socket's middle. */
const ARM_IN = 3;
/** Where an arm's picture goes in a socket (its shaft on the socket's middle). */
function armAt(socket: number, art: Art): Pt {
    const [ox, oy] = bossOrigin(), [sx, sy] = [ox + SOCKETS[socket][0], oy + SOCKETS[socket][1]], half = ARM_ART.walkers[0].h >> 1;
    return ([[sx - ARM_IN, sy - half], [sx - half, sy - ARM_IN], [sx + ARM_IN - art.w, sy - half], [sx - half, sy + ARM_IN - art.h]] as Pt[])[socket];
}
function drawBoss(blit: (a: Art, x: number, y: number) => void, outlined: (draw: () => void) => void) {
    const [ox, oy] = bossOrigin(), arms = MAP.boss!.arms;
    outlined(() => {
        blit(BOSS_ART, ox, oy);
        arms.forEach((a, k) => {
            const socket = socketOf(g, k), art = ARM_ART[g.arms[k] > 0 ? a.kind : "stump"][socket];
            blit(art, ...armAt(socket, art));
        });
    });
}
/** Where the arm on the road is (the east socket's arm's middle), for its explosion. */
const eastArm = (): Pt => { const art = ARM_ART.walkers[0], [x, y] = armAt(0, art); return [x + art.w / 2, y + art.h / 2]; };
/** An arm blowing up, frame by frame: [x, y, glyph] from its middle (a glyph is
 *  centred on x; y is a row's middle). Frame 1 is held while the new picture is sent. */
const BOOM: [number, number, string][][] = [
    [[0, -13, "※"], [0, 14, "※"]],
    [[-25, -13, "※"], [0, -13, "※"], [25, -13, "※"], [-25, 14, "※"], [0, 14, "※"], [25, 14, "※"], [0, -40, "※"], [0, 41, "※"]],
    [[-25, -40, "╳"], [25, -40, "╳"], [0, -13, "※"], [0, 14, "※"], [-25, 41, "╳"], [25, 41, "╳"]],
    [[-25, -13, "◌"], [25, 14, "◌"]],
];
let boom: { at: Pt; frame: number } | null = null;

const TILES = [[0, 0], [288, 0], [0, 144], [288, 144]];
function tileLevels(levels: Uint8Array, ox: number, oy: number): Uint8Array {
    const t = new Uint8Array(288 * 144);
    for (let y = 0; y < 144; y++) t.set(levels.subarray((oy + y) * W + ox, (oy + y) * W + ox + 288), y * 288);
    return t;
}

// --- bridge ------------------------------------------------------------------------

const MENU_NEXT = 1, MENU_RESTART = 2, MENU_SPEED = 6, MENU_MAP = 7;
initPhone();
const bridge = await waitForEvenAppBridge();
layoutMap();
restart(false); // a game to draw the page with; the campaign's map loads once the bridge is up

// Every bridge call goes through one queue, images and text alike. A call can hang
// (saving a setting did, in the simulator), which would stall everything behind it,
// so the queue moves on after 2s and the call counts as failed ("timeout"). An image
// tile gets longer: a slow send that still lands would otherwise count as failed, be
// sent again, and overlap the call after it.
const BRIDGE_TIMEOUT_MS = 2000, TILE_TIMEOUT_MS = 8000;
let queue: Promise<unknown> = Promise.resolve();
const enqueue = <T>(f: () => Promise<T>, what: string, ms = BRIDGE_TIMEOUT_MS) => (queue = queue.then(() => {
    let timer = 0;
    return Promise.race([
        f().catch((err) => { console.log(`${what} failed`, err); return "failed"; }),
        new Promise<string>((ok) => { timer = setTimeout(() => { console.log(`${what} timed out`); ok("timeout"); }, ms); }),
    ]).finally(() => clearTimeout(timer));
})) as Promise<T | string>;

const sentTiles: (Uint8Array | null)[] = [null, null, null, null];
let sendingMap = false, mapDirty = false;
/** "Next wave" was asked for: it starts once the map (without the build brackets) lands. */
let startWhenDrawn = false;
/** Between waves, with nothing sent yet: slots show their build brackets. */
const building = () => !g.waveActive && !g.over && !startWhenDrawn;
/** Redraw the map and send only the tiles that changed. Between waves only. Called
 *  while a send is under way (another build), it redraws again once that one ends.
 *  A tile that failed is sent again (up to 3 passes), so a wave doesn't start over
 *  the last wave's lanes or the build brackets. */
async function sendMap() {
    if (sendingMap) { mapDirty = true; return; }
    sendingMap = true;
    let failed = false, passes = 0;
    do {
        mapDirty = false; failed = false; passes++;
        await readyBase();
        const levels = mapLevels();
        // The message box's tiles last: it is read while the others change.
        const { x0, x1, y0, y1 } = msgRect(), boxIn = (i: number) => x1 >= TILES[i][0] && x0 < TILES[i][0] + 288 && y1 >= TILES[i][1] && y0 < TILES[i][1] + 144;
        for (const i of [0, 1, 2, 3].sort((a, b) => Number(boxIn(a)) - Number(boxIn(b)))) {
            const t = tileLevels(levels, TILES[i][0], TILES[i][1]);
            const old = sentTiles[i];
            if (old && old.every((v, j) => v === t[j])) continue;
            const r = await enqueue(() => bridge.updateImageRawData({
                containerID: 10 + i, containerName: `tile${i}`, imageData: Array.from(encodeGreyPng(t, 288, 144)),
            } as never), `tile${i}`, TILE_TIMEOUT_MS);
            console.log(`tile${i} ${r}`);
            if (r === "success") sentTiles[i] = t;
            else failed = true;
        }
    } while (mapDirty || (failed && passes < 3));
    showMap(() => mapLevels(false));
    sendingMap = false;
    if (startWhenDrawn) { startWhenDrawn = false; startWave(g); }
    void flush();
}

const sent = new Map<number, string>();
let flushing: Promise<void> | null = null, again = false;
/** Send the layers that changed. Resolves once what is on screen matches the game,
 *  also when called while a send is under way (that send makes another pass). Every
 *  layer of a pass is read first, so a pass never mixes two frames. */
function flush(): Promise<void> {
    if (flushing) { again = true; return flushing; }
    flushing = (async () => {
        do {
            again = false;
            const changed = LAYERS.map((L) => [L, L.content()] as const).filter(([L, c]) => c !== sent.get(L.id));
            for (const [L, content] of changed) {
                sent.set(L.id, content);
                const r = await enqueue(() => bridge.textContainerUpgrade({
                    containerID: L.id, containerName: L.name, contentOffset: 0, contentLength: 0, content,
                } as never), L.name);
                // Refused (false) counts as failed too: send it again next pass. Several in
                // a row and the page is rebuilt (the glasses may have dropped it).
                if (r === "timeout" || r === "failed" || r === false) { sent.delete(L.id); if (++refused >= 6) void repaint("text refused"); }
                else refused = 0;
            }
        } while (again);
    })().finally(() => { flushing = null; });
    return flushing;
}

/** The page as it should look now (every layer's current content). */
const pageNow = () => ({
    containerTotalNum: 4 + LAYERS.length,
    imageObject: TILES.map(([x, y], i) => ({
        xPosition: x, yPosition: y, width: 288, height: 144, containerID: 10 + i, containerName: `tile${i}`, zOrderIndex: 1 + i,
    })),
    textObject: LAYERS.map((L, i) => {
        const content = L.content();
        sent.set(L.id, content);
        return {
            ...(L.name === "box" ? { xPosition: BOX_X, yPosition: 0, width: BOX_W, height: BOX_H, borderWidth: 1, borderColor: 8, borderRadius: 8 }
                : L.name === "msg" ? { xPosition: 0, yPosition: 0, width: W, height: H, borderWidth: 0, borderColor: 0 }
                : { xPosition: 0, yPosition: L.y, width: W, height: H - L.y, borderWidth: 0, borderColor: 0 }),
            paddingLength: 0,
            containerID: L.id, containerName: L.name, content, textColor: L.textColor,
            isEventCapture: L.name === "input" ? 1 : 0, zOrderIndex: L.name === "input" ? 0 : 10 + i,
        };
    }),
    menuObject: {
        menuItems: [
            { itemName: "Start Wave", itemID: MENU_NEXT }, { itemName: "Fast Mode", itemID: MENU_SPEED },
            { itemName: "Choose map", itemID: MENU_MAP }, { itemName: "Restart", itemID: MENU_RESTART },
        ],
    },
});
console.log("create", await bridge.createStartUpPageContainer(pageNow() as never));

/** Text updates refused in a row; a repaint under way; the exit dialog asked for. */
let refused = 0, repainting = false, exitAsked = false;
/** Build the page again and send everything (the map too): when the glasses keep
 *  refusing text updates, or after the exit dialog was cancelled. Not on the
 *  foreground events: the long-press menu sends those too (enter as it opens, exit
 *  once an item is picked, in the simulator). */
async function repaint(why: string) {
    if (repainting) return;
    repainting = true; refused = 0;
    console.log(`repaint: ${why}`);
    const r = await enqueue(() => bridge.rebuildPageContainer(pageNow() as never), "rebuild");
    console.log(`rebuild ${r}`);
    sentTiles.fill(null);
    repainting = false;
    await sendMap();
}

// Stored settings ("" when there is none, or the call failed).
const load = async (k: string) => {
    const v = await enqueue(() => bridge.getLocalStorage(k), `load ${k}`);
    return v === "timeout" || v === "failed" ? "" : v;
};
const save = (k: string, v: string) => void enqueue(() => bridge.setLocalStorage(k, v), `save ${k}`);
if ((await load("g2td.fast")) === "1") speed = FAST_SPEED;
console.log(`settings speed ${speed}`);
// Where the campaign was left, or ?map=N (1-based) to start on a map in the simulator.
{
    const asked = Number(new URLSearchParams(location.search).get("map"));
    const [i, lives] = (await load("g2td.campaign")).split(",").map(Number);
    const kept = await load("g2td.game");
    if (i === RANDOM_INDEX) newRandomMap(Number(await load("g2td.random")) || 1);
    if (asked >= 1) startMap(asked - 1, START_LIVES);
    else if (i >= 0 && i < MAPS.length && lives > 0) { startMap(i, lives); if (!testedW) { resume(kept); persist(); } }
    else startMap(0, START_LIVES);
}
await sendMap();

// --- input -------------------------------------------------------------------------

function move(d: number) {
    g.note = "";
    if (mode === "confirm") { restartYes = (restartYes + d + RESTART.length) % RESTART.length; return; }
    if (mode === "map") { pickMap = (pickMap + d + MAPS.length) % MAPS.length; return; }
    if (g.waveActive || startWhenDrawn) return;
    if (mode === "select") opt = (opt + d + options().length) % options().length;
    else if (mode === "browse") {
        // Down the list is up the swipe: it felt backwards the other way round.
        const list = stops(), at = Math.max(0, list.indexOf(sel));
        sel = list[(at - d + list.length) % list.length];
    }
}

function tap() {
    g.note = "";
    if (mode === "confirm") {
        if (restartYes === 1) { restart(); keepPlace(MAP_INDEX, entryLives); persist(); void sendMap(); }
        else if (restartYes === 2) { startMap(0, START_LIVES); void sendMap(); }
        else mode = beforeConfirm;
        return;
    }
    if (mode === "map") {
        // The random map is a new one every time it is picked; its seed is kept to resume it.
        if (pickMap === RANDOM_INDEX) { const seed = Date.now() & 0x7fffffff; newRandomMap(seed); save("g2td.random", String(seed)); }
        startMap(pickMap, START_LIVES); void sendMap(); return;
    }
    if (mode === "over") {
        if (!g.won) { restart(); persist(); }
        else startMap(...nextMap());
        void sendMap();
        return;
    }
    if (g.waveActive || startWhenDrawn) return;
    if (mode === "browse") {
        if (sel === NEXT) sendWave();
        else { mode = "select"; opt = 0; }
        return;
    }
    const o = options()[opt];
    mode = "browse";
    if (o === "cancel") return;
    if (o === "remove") {
        const why = unbuild(g, sel);
        if (why) { g.note = why; return; }
        persist(); void sendMap(); return;
    }
    const why = buy(g, sel, o as TowerKind);
    if (why) { g.note = why; return; }
    // The slot is built now; the cursor moves on to the next free one along the road,
    // round to the start if those past it are taken, and to Next wave only when none is free.
    const at = ORDER.indexOf(sel);
    sel = [...ORDER.slice(at + 1), ...ORDER.slice(0, at)].find((i) => !g.built.has(i)) ?? NEXT;
    persist();
    void sendMap();
}

/** Start the next wave. The enemies' lanes are in the map, so if it is still on its
 *  way to the glasses (redrawn after the last wave or a build), the wave starts as
 *  soon as it lands. */
function sendWave() {
    if (g.waveActive || g.over || startWhenDrawn) return;
    // Saved as the wave starts: its towers can't be taken back any more.
    g.fresh.clear();
    persist();
    // The map is redrawn without the build brackets, and the wave starts once it lands.
    startWhenDrawn = true;
    void sendMap();
}

bridge.onEvenHubEvent((e: any) => {
    const item = e?.menuItemClickEvent?.itemID;
    if (item === MENU_NEXT) { g.note = ""; mode = "browse"; sendWave(); }
    else if (item === MENU_SPEED) {
        speed = speed === FAST_SPEED ? NORMAL_SPEED : FAST_SPEED;
        save("g2td.fast", speed === FAST_SPEED ? "1" : "0");
        g.note = speed === FAST_SPEED ? "Fast Mode Enabled" : "Fast Mode Disabled";
    }
    else if (item === MENU_MAP) {
        if (mode !== "confirm" && mode !== "map") beforeConfirm = mode;
        mode = "map"; pickMap = MAP_INDEX;
    }
    else if (item === MENU_RESTART) {
        if (mode !== "confirm" && mode !== "map") beforeConfirm = mode;
        mode = "confirm"; restartYes = 0;
    }
    else {
        const ev = e?.textEvent ?? e?.sysEvent ?? e?.listEvent;
        if (!ev) return;
        // CLICK_EVENT is 0, which the host sometimes leaves out entirely.
        const t = ev.eventType === undefined ? OsEventTypeList.CLICK_EVENT : OsEventTypeList.fromJson(ev.eventType);
        // Input again after the exit dialog: it was cancelled. Build the page again, in
        // case the dialog took the glasses' copy of it, and play on. That input only
        // cancels: a stray tap as the dialog comes up must not send a wave.
        if (exitAsked && [OsEventTypeList.CLICK_EVENT, OsEventTypeList.SCROLL_TOP_EVENT, OsEventTypeList.SCROLL_BOTTOM_EVENT, OsEventTypeList.DOUBLE_CLICK_EVENT].includes(t!)) {
            exitAsked = false; void repaint("exit cancelled"); return;
        }
        if (t === OsEventTypeList.CLICK_EVENT) tap();
        else if (t === OsEventTypeList.SCROLL_TOP_EVENT) move(-1);
        else if (t === OsEventTypeList.SCROLL_BOTTOM_EVENT) move(1);
        else if (t === OsEventTypeList.DOUBLE_CLICK_EVENT) {
            // Always the way out, as Even Hub's rules ask: the glasses ask first
            // (shutDownPageContainer(1)), and the game is saved. An open choice (tower
            // picker, restart question, map picker) is dropped too, so cancelling the
            // dialog comes back to the map.
            g.note = "";
            if (mode === "select") mode = "browse";
            else if (mode === "confirm" || mode === "map") mode = beforeConfirm;
            exitAsked = true; persist();
            void enqueue(() => bridge.shutDownPageContainer(1), "exit");
            return;
        }
        else if (t === OsEventTypeList.ABNORMAL_EXIT_EVENT || t === OsEventTypeList.SYSTEM_EXIT_EVENT) {
            // Closed: stop playing too (a wave under way starts again from its start).
            exitAsked = true; persist();
            return;
        }
        else if (t === OsEventTypeList.FOREGROUND_EXIT_EVENT) {
            // Only saved: the long-press menu sends it as an item is picked.
            persist();
            return;
        }
        else return;
    }
    void flush();
});

// The page's own timers fire about once a second while it is hidden (the phone in a
// pocket, and the simulator), whatever the game speed. A worker's timers are not held
// back, so the loop waits on one; plain setTimeout if a worker can't be made.
const wait = (() => {
    try {
        const src = "onmessage = (e) => setTimeout(() => postMessage(e.data), e.data.ms)";
        const worker = new Worker(URL.createObjectURL(new Blob([src], { type: "text/javascript" })));
        const waiting = new Map<number, () => void>();
        let n = 0;
        worker.onmessage = (e) => { waiting.get(e.data.id)?.(); waiting.delete(e.data.id); };
        return (ms: number) => new Promise<void>((ok) => { waiting.set(++n, ok); worker.postMessage({ id: n, ms }); });
    } catch (err) {
        console.log("no worker timer", err);
        return (ms: number) => new Promise<void>((ok) => setTimeout(ok, ms));
    }
})();

/** Bursts over the destroyed arm, frame by frame, the second held until the map with
 *  its stump has landed (only the tiles under the boss change). */
async function explode() {
    boom = { at: eastArm(), frame: 0 };
    for (let f = 0; f < BOOM.length; f++) {
        boom.frame = f;
        await flush();
        if (f === 1) await Promise.all([sendMap(), wait(TICK_MS)]);
        else await wait(TICK_MS);
    }
    boom = null;
}

// A HUD message stays about four seconds, then the status line comes back.
let shownNote = "", noteAt = 0;
async function loop() {
    const t0 = performance.now();
    tick++;
    const playing = g.waveActive;
    // Nothing plays once the way out is asked for (the exit dialog, or the host closing
    // the app): the page can live on hidden, and a wave left running there played out
    // alone, a win moving the campaign on to the next map (seen on the glasses, 0.6.0:
    // closed before wave 5, resumed on the next map).
    if (playing && !exitAsked && mode !== "confirm" && mode !== "map") {
        shown = g.phase;
        const r = stepPhase(g);
        // The arm on the road was destroyed: the game stops while it blows up, and its
        // new picture (a stump) is sent under the bursts.
        if (g.broke) { g.broke = false; await explode(); }
        // Saved as each wave ends. A lost map is retried from its start; a won one
        // carries on with the next map, even if the app closes before the tap.
        if (r.over) { mode = "over"; shown = -1; save("g2td.game", ""); console.log(`GAME OVER wave ${g.wave}`); void sendMap(); }
        if (r.cleared) {
            shown = -1;
            if (g.won) { mode = "over"; keepPlace(...nextMap()); save("g2td.game", ""); console.log("WON"); void sendMap(); }
            else {
                // The cursor stays where it was if that slot is still free, else Next wave.
                if (!stops().includes(sel)) { sel = NEXT; mode = "browse"; }
                persist(); console.log(`WAVE ${g.wave} CLEARED`); void sendMap();
            }
        }
    }
    // Restart or Choose map opened or closed mid-wave: the map with or without the box.
    if (g.waveActive && boxShown() !== boxDrawn && !sendingMap) void sendMap();
    if (g.note !== shownNote) { shownNote = g.note; noteAt = t0; }
    else if (g.note && t0 - noteAt > 4000) g.note = shownNote = "";
    await flush();
    showStats(g);
    // Between waves the cursor blinks at the normal pace whatever the game speed.
    const frame = playing ? TICK_MS / speed : TICK_MS;
    await wait(Math.max(0, frame - (performance.now() - t0)));
    void loop();
}
console.log("TD2 READY");
void loop();
