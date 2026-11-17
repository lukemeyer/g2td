// The random map: a new road, slots and surroundings from a seed, with endless waves.
// The last entry of MAPS (after the campaign); picking it in "Choose map" makes a new one.
//
// Safeguards, so every random map plays fair:
//   - the road runs left to right, its vertical stretches at least 3 columns apart and
//     its rows at least 3 apart (or a one-row step), so no two stretches touch;
//   - the road is 22-44 cells of path, and the rules' automatic slots give 4-8 turret
//     pads and 6-12 triplines (otherwise another road is drawn);
//   - there is room for the message box: a row of MSG_COLS cells clear of slots, the HUD
//     and the margins' limits (rules' messageBox finds it);
//   - enemy health (`hp`) is tuned with the balance bots (src/bot.ts) so their mixed
//     build lasts about TARGET waves and every bot plan clears the first SAFE waves.
//     There is no last wave: waves keep climbing the curve one step each.
import { MAPS, MAP_INDEX, useMap, SLOTS, SQUARES, MSG_BOX, MSG_COLS, inHudBox, COLS, ROWS, key, type MapDef, type Cell, type TowerKind } from "./rules.ts";
import { play } from "./bot.ts";
import { PACK } from "./pack.ts";
import { LAYOUTS } from "./render/layouts.ts";
import { footprint, type Layout, type Placed } from "./render/map.ts";

/** The campaign's maps, before the random one. */
export const CAMPAIGN_LEN = MAPS.length;
export const RANDOM_INDEX = MAPS.length;
const ROAD_MAPS = MAPS.filter((m) => !m.boss);

const TARGET = 14, SAFE = 6;
const PLANS: TowerKind[][] = [["laser", "sniper", "stasis", "laser", "cannon"], ["sniper", "cannon"], ["laser", "laser", "stasis"]];

const rngOf = (seed: number) => () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);

/** A left-to-right road of anchors (top-left of each turn's 2x2 square). */
function road(rnd: () => number): Cell[] {
    const int = (n: number) => Math.floor(rnd() * n);
    let r = 1 + int(7), c = 0;
    const A: Cell[] = [[r, 0]];
    for (;;) {
        const left = 19 - c;
        let run = 3 + int(6);
        if (run >= left || left - run < 3) run = left;
        c += run;
        A.push([r, c]);
        if (c === 19) return A;
        let r2: number;
        do r2 = 1 + int(7); while (!(Math.abs(r2 - r) >= 3 || (Math.abs(r2 - r) === 1 && rnd() < 0.3)));
        r = r2;
        A.push([r, c]);
    }
}

/** Free cells around the road filled with the source map's own pieces, at random. */
function furnish(rnd: () => number, source: string): Layout {
    const src = LAYOUTS[source];
    const taken = new Set<number>([...SLOTS.flatMap((s) => s.cells.map(key))]);
    const road = new Set(SQUARES.flatMap(([r, c]) => [key([r, c]), key([r + 1, c]), key([r, c + 1]), key([r + 1, c + 1])]));
    const free = (cell: Cell) => cell[0] >= 0 && cell[0] < ROWS && cell[1] >= 0 && cell[1] < COLS && !taken.has(key(cell)) && !road.has(key(cell)) && !inHudBox(cell);
    const kinds = (src?.pieces ?? []).filter((p) => PACK.pieces[p[2]]);
    const pieces: Placed[] = [];
    const cells = Array.from({ length: ROWS * COLS }, (_, i): Cell => [Math.floor(i / COLS), i % COLS]).sort(() => rnd() - 0.5);
    for (const [r, c] of cells) {
        if (!kinds.length || rnd() > 0.6 || !free([r, c])) continue;
        const [, , id, variant, turns] = kinds[Math.floor(rnd() * kinds.length)];
        const fp = footprint(PACK.pieces[id], r, c, turns) as Cell[];
        if (!fp.every(free)) continue;
        fp.forEach((cell) => taken.add(key(cell)));
        pieces.push([r, c, id, variant, turns]);
    }
    return { version: 2, floor: src?.floor, pieces, walls: [] };
}

/** Make the random map from `seed` and put it at RANDOM_INDEX (the map current after is
 *  whatever was current before). */
export function newRandomMap(seed: number) {
    const rnd = rngOf(seed || 1);
    const was = MAP_INDEX;
    for (let tries = 0; ; tries++) {
        const source = ROAD_MAPS[Math.floor(rnd() * ROAD_MAPS.length)];
        const def: MapDef = {
            id: `random-${seed}`, name: "Random", random: true, theme: source.theme, waves: Infinity, credits: 200, hp: 1, pace: 1,
            anchors: road(rnd),
        };
        MAPS[RANDOM_INDEX] = def;
        try { useMap(RANDOM_INDEX); } catch { continue; }
        const turrets = SLOTS.filter((s) => s.cls === "turret").length, trips = SLOTS.length - turrets;
        if (SQUARES.length < 22 || SQUARES.length > 44 || turrets < 4 || turrets > 8 || trips < 6 || trips > 12) continue;
        // Room for the whole message box (one row of MSG_COLS cells clear of slots).
        if (MSG_BOX.cols < MSG_COLS) continue;
        // Enemy health: the mixed bot should fall around wave TARGET; every plan clears SAFE.
        const reach = (hp: number) => { def.hp = hp; return (play(PLANS[0], 1, 40).reached + play(PLANS[0], 2, 40).reached) / 2; };
        let lo = 0.3, hi = 3;
        for (let i = 0; i < 7; i++) { const mid = (lo + hi) / 2; if (reach(mid) > TARGET) lo = mid; else hi = mid; }
        def.hp = Math.round(lo * 100) / 100;
        while (def.hp > 0.3 && PLANS.some((p) => play(p, 3, SAFE).left <= 0)) def.hp = Math.round(def.hp * 90) / 100;
        PACK.maps[def.id] = PACK.maps[source.id];
        LAYOUTS[def.id] = furnish(rnd, source.id);
        console.log(`random map ${seed}: ${tries + 1} tries, from ${source.id}, ${SQUARES.length} squares, ${turrets} pads, ${trips} triplines, hp x${def.hp}`);
        break;
    }
    useMap(was);
}

// Something to show in the map list until a random map is asked for.
newRandomMap(1);
