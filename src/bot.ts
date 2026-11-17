// The balance bots (tools/balance.ts), shared with the random map's checks
// (src/random_map.ts): build from a plan whenever credits allow, play a wave, repeat.
import { newGame, startWave, stepPhase, buy, SLOTS, TOWERS, KINDS_OF, type TowerKind, type Game } from "./rules.ts";

/**
 * Build from `order` (cycled) while credits allow. A laser goes on the free
 * tripline slot furthest along the road; stasis on the free one closest before a
 * built laser (its slow lasts about 1.5 cells, so only a laser right after it gains),
 * else nearest the start; a turret goes on the free pad with the most road in reach.
 */
/** Higher is better: just before a built laser, else as early as possible. */
function stasisScore(g: Game, i: number) {
    const after = [...g.built].filter(([j, b]) => b.kind === "laser" && SLOTS[j].t > SLOTS[i].t).map(([j]) => SLOTS[j].t - SLOTS[i].t);
    return after.length ? -Math.min(...after) : -1e6 - SLOTS[i].t;
}

export function build(g: Game, order: TowerKind[], built: { n: number }) {
    for (let skipped = 0; skipped < order.length;) {
        const kind = order[built.n % order.length];
        const free = SLOTS.map((_, i) => i).filter((i) => !g.built.has(i) && KINDS_OF[SLOTS[i].cls].includes(kind));
        if (!free.length) { built.n++; skipped++; continue; } // that class is full
        if (g.credits < TOWERS[kind].cost) return;
        const score = (i: number) =>
            kind === "laser" ? SLOTS[i].t : kind === "stasis" ? stasisScore(g, i) : SLOTS[i].depth.filter((d) => d <= TOWERS[kind].range).length;
        const slot = free.reduce((a, b) => (score(b) > score(a) ? b : a));
        if (buy(g, slot, kind)) return;
        built.n++;
        skipped = 0;
    }
}

export function play(order: TowerKind[], seed: number, upTo = Infinity) {
    const g = newGame(seed);
    const built = { n: 0 };
    const lives: number[] = [];
    let firstLeak = 0, full = 0;
    while (!g.over && g.wave < upTo) {
        build(g, order, built);
        if (!full && g.built.size === SLOTS.length) full = g.wave + 1;
        startWave(g);
        for (let t = 0; t < 30000 && g.waveActive; t++) {
            const r = stepPhase(g);
            if (r.leaked && !firstLeak) firstLeak = g.wave;
        }
        lives.push(g.lives);
    }
    return { won: g.won, reached: g.wave, firstLeak, full, lives, left: g.lives };
}

