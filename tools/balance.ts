// Headless balance check for the tower defense. Plays the real rules (src/rules.ts)
// with a few build strategies on every map and reports how far each one gets.
//
//   node tools/balance.ts            # every map
//   node tools/balance.ts 2          # map 2 (1-based) only
//
// A road map is WAVES (5) waves, on the 10-step curve (levelOf). What the numbers are aiming at:
//   - wave 1-3 are safe with what the starting credits buy;
//   - a mixed build clearly beats any single tower type (each type has a job:
//     laser = everything that crosses it, stasis = more time on the next line,
//     sniper = single tough targets from far, cannon = groups up close);
//   - these bots only just win, or lose late, with the best mixes: a person who
//     places towers well did far better than the bots on the glasses (they lasted
//     to wave 23 when the bots fell in the teens);
//   - later maps are harder: the bots fall earlier, map by map (MAP.hp).
// The boss map: the bots' plans, and plans that change with the arm on the road (it
// is announced between waves), with how many waves each arm took.

import { MAPS, MAP, useMap, newGame, startWave, stepPhase, SLOTS, waveOf, hpScale, ENEMIES, armOf, type TowerKind, type ArmKind } from "../src/rules.ts";
import { play, build } from "../src/bot.ts";

const PLANS: Record<string, TowerKind[]> = {
    "laser only": ["laser"],
    "sniper only": ["sniper"],
    "cannon only": ["cannon"],
    "laser + stasis": ["laser", "laser", "stasis"],
    "turrets mixed": ["sniper", "cannon"],
    "mixed": ["laser", "sniper", "stasis", "laser", "cannon"],
    "all four": ["laser", "stasis", "sniper", "cannon"],
};

function roadMap() {
    // The rules are deterministic apart from where the lanes flip, so a few seeds is enough.
    const SEEDS = [1, 2, 3];
    console.log("strategy          won   lost at wave   first leak   slots full at   lives after w1/w3/w5");
    for (const [name, order] of Object.entries(PLANS)) {
        const runs = SEEDS.map((s) => play(order, s));
        const avg = (f: (r: (typeof runs)[0]) => number) => (runs.reduce((a, r) => a + f(r), 0) / runs.length);
        const lost = runs.filter((r) => !r.won);
        const at = (w: number) => avg((r) => r.lives[w - 1] ?? 0).toFixed(0);
        console.log(
            name.padEnd(18),
            `${runs.length - lost.length}/${runs.length}`.padEnd(6),
            (lost.length ? (lost.reduce((a, r) => a + r.reached, 0) / lost.length).toFixed(1) : "-").padEnd(15),
            (avg((r) => r.firstLeak) || 0).toFixed(1).padEnd(12),
            avg((r) => r.full).toFixed(1).padEnd(15),
            `${at(1)}/${at(3)}/${at(5)}`,
        );
    }
}

// The boss map: each plan builds from its order for the arm on the road (announced
// before the wave; the same order for every arm in the bots' plans), cycling through
// it whenever it can afford the next tower.
function bossMap() {
    const same = (o: TowerKind[]) => ({ walkers: o, floaters: o, swarm: o });
    const STRATS: Record<string, Record<ArmKind, TowerKind[]>> = {
        ...Object.fromEntries(Object.entries(PLANS).map(([k, o]) => [k, same(o)])),
        "react": { walkers: ["sniper", "laser"], floaters: ["cannon", "laser"], swarm: ["cannon", "stasis", "laser"] },
        "react, lasers first": { walkers: ["laser", "laser", "sniper"], floaters: ["laser", "cannon"], swarm: ["stasis", "laser", "cannon"] },
    };
    for (const [name, plan] of Object.entries(STRATS)) {
        const g = newGame(1, 6);
        let steps = 0;
        const built = { n: 0 }, fell: number[] = [];
        while (!g.over && steps < 200000) {
            build(g, plan[armOf(g).kind], built);
            startWave(g);
            for (; steps < 200000 && g.waveActive; steps++) for (let p = 0; p < 3; p++) stepPhase(g);
            g.arms.forEach((a, k) => { if (!a && !fell[k]) fell[k] = g.wave; });
        }
        console.log(`${name.padEnd(20)} ${g.won ? "won " : "lost"} with ${String(g.lives).padStart(2)} lives in wave ${String(g.wave).padStart(2)}, ~${(steps * 0.75 / 60).toFixed(1)} min at 1x, arms fell in waves ${fell.join("/")}, arms ${g.arms.join("/")}, towers ${g.built.size}/${SLOTS.length}`);
    }
}

// @ts-expect-error: node's process (the tools have no node types)
const only = Number(process.argv[2]) || 0;
MAPS.forEach((m, i) => {
    if (only && only !== i + 1) return;
    useMap(i);
    console.log(`\n== ${i + 1}. ${m.name}: ${SLOTS.filter((s) => s.cls === "trip").length} tripline slots, ${SLOTS.filter((s) => s.cls === "turret").length} turret pads, health x${MAP.hp ?? 1}`);
    if (MAP.boss) bossMap(); else roadMap();
});

// Context: how much is coming each wave, at health x1.
useMap(0);
const rows = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => {
    const w = waveOf(n);
    const hp = w.reduce((a, k) => a + Math.round(ENEMIES[k].hp * hpScale(n)), 0);
    return `w${n}: ${w.length} enemies, ${w.filter((k) => k === "shield").length} shields, ${hp} hp`;
});
console.log("\n" + rows.join("\n"));
