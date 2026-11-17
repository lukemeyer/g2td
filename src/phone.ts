// The phone screen: a Guide (the game, the controls, each enemy and tower, the maps;
// its words are the user's own, docs/guide.md) and Stats (the map as built, and this game wave by wave). The glasses
// game runs in this same page; this only fills in the DOM beside it.
//
// Everything on the Guide comes from rules.ts, so it stays right when the numbers are
// tuned. The art is the high-res generated pictures (public/guide/, written by
// tools/import_sprites.py).

import {
    ENEMIES, TOWERS, WAVES, SWARM_EVERY, START_CREDITS, START_LIVES, LASER_DAMAGE, SNIPER_DAMAGE, CANNON_DAMAGE, SLOW_FACTOR, SLOW_STEPS,
    MAPS, MAP, MAP_INDEX, MAP_BONUS_LIVES, ARM_NAMES, type Game, type TowerKind,
} from "./rules.ts";

const KINDS: TowerKind[] = ["laser", "stasis", "sniper", "cannon"];
const DAMAGE: Record<TowerKind, number> = { laser: LASER_DAMAGE, stasis: 0, sniper: SNIPER_DAMAGE, cannon: CANNON_DAMAGE };
const ART: Record<TowerKind | "walker" | "floater", string> = {
    walker: "guide/walker.png", floater: "guide/floater.png",
    laser: "guide/laser.png", stasis: "guide/stasis.png", sniper: "guide/sniper.png", cannon: "guide/cannon.png",
};
const WHAT: Record<TowerKind, string> = {
    laser: "A tripline across the path that hits everything in both lanes. Has a cooldown every other step, so fast enemies may slip by.",
    stasis: "A tripline that slows enemies crossing it, in both lanes, so the next towers get more time on them. No damage, but passes through shields.",
    sniper: "Snipers can fire down long stretches of the path, hitting one enemy at a time with a powerful shot.",
    cannon: "Cannons fire a short-range explosive that hits all enemies around the target.",
};

const el = (tag: string, attrs: Record<string, string> = {}, ...kids: (Node | string)[]) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    e.append(...kids);
    return e;
};
const table = (head: string[], rows: (string | number)[][], foot?: (string | number)[]) =>
    el("table", {},
        el("thead", {}, el("tr", {}, ...head.map((h) => el("th", {}, h)))),
        el("tbody", {}, ...rows.map((r) => el("tr", {}, ...r.map((v) => el("td", {}, String(v)))))),
        ...(foot ? [el("tfoot", {}, el("tr", {}, ...foot.map((v) => el("td", {}, String(v)))))] : []));

function card(img: string, title: string, facts: string[], text: string) {
    return el("div", { class: "card" },
        el("img", { src: img, alt: title }),
        el("div", {}, el("h3", {}, title), el("div", { class: "facts" }, ...facts.map((f) => el("span", {}, f))), el("p", {}, text)));
}

function guide() {
    const w = ENEMIES.beetle, f = ENEMIES.shield, campaign = MAPS.filter((m) => !m.random), road = campaign.filter((m) => !m.boss);
    return el("section", { id: "guide" },
        el("p", { class: "lead" }, `${isFinite(WAVES) ? `Hold the base for ${WAVES} waves.` : "Hold the base as long as you can: the waves never end."} You start with $${START_CREDITS} and ${START_LIVES} lives; build between waves, ` +
            "and anything you build can be taken back for a full refund until the next wave starts."),
        el("h2", {}, "Gameplay"),
        el("p", {}, `Fight off the bot invasion through ${road.length} levels, then confront the boss at the airlock.`),
        el("ul", {},
            ...[`Each level is ${road[0].waves} waves, with more and stronger enemies`,
                "Earn money for towers by defeating enemies and clearing waves",
                `Recover ${MAP_BONUS_LIVES} lives by clearing a level`,
                "Progress is auto-saved",
                "Choose any campaign level, or a randomized map from the menu"].map((t) => el("li", {}, t))),
        el("h2", {}, "Controls"),
        el("p", {}, "Swipe to select tower locations along the path, tap to place. Long press to open the menu."),
        el("h2", {}, "Enemies"),
        card(ART.walker, "Walker", [`Health: ${w.hp}`, `Bonus: +$${w.reward}`, `Damage: −${w.harm}♥`],
            `Fast, numerous, Walkers try to overwhelm your defenses by sheer number. On the ${ordinal(SWARM_EVERY)} wave they will swarm.`),
        card(ART.floater, "Drone", [`Health: ${f.hp}`, `Bonus: +$${f.reward}`, `Damage: −${f.harm}♥`],
            "Slow and strong, the Drone has a shield that can take one hit from any tower. Drones always appear on the 2nd wave."),
        el("h2", {}, "Towers"),
        ...KINDS.map((k) => {
            const t = TOWERS[k];
            const damage = k === "stasis" ? `0 - Slows enemies to 1/${Math.round(1 / SLOW_FACTOR)} speed for ${SLOW_STEPS} steps`
                : k === "cannon" ? `${DAMAGE[k]} + Splash Damage` : String(DAMAGE[k]);
            // A tripline's range is the road's two lanes.
            const facts = [`Cost: $${t.cost}`, `Damage: ${damage}`, `Fire Rate: ${2 / t.cooldown}x`, `Range: ${t.range || 2}`];
            return card(ART[k], t.name, facts, WHAT[k]);
        }),
        el("h2", {}, "The maps"),
        el("ol", {}, ...campaign.map((m) => el("li", {}, m.boss ? `${m.name} (Boss Battle)` : m.name))));
}

const ordinal = (n: number) => `${n}${["th", "st", "nd", "rd"][n % 100 > 10 && n % 100 < 14 ? 0 : n % 10 < 4 ? n % 10 : 0]}`;

let canvas: HTMLCanvasElement, summary: HTMLElement, waves: HTMLElement, towers: HTMLElement;

function stats() {
    canvas = el("canvas", { width: "576", height: "288" }) as HTMLCanvasElement;
    summary = el("p", { class: "lead" });
    waves = el("div", {});
    towers = el("div", {});
    return el("section", { id: "stats", hidden: "" }, el("h2", {}, "The map"), canvas, summary,
        el("h2", {}, "Wave by wave"), waves, el("h2", {}, "By tower"), towers);
}

export function initPhone() {
    const app = document.getElementById("app")!;
    const tabs = ["Guide", "Stats"].map((name, i) => el("button", { class: i ? "" : "on" }, name));
    const pages = [guide(), stats()];
    tabs.forEach((t, i) => t.addEventListener("click", () => {
        tabs.forEach((u, j) => u.classList.toggle("on", i === j));
        pages.forEach((p, j) => (p.hidden = i !== j));
        statsOpen = i === 1;
        if (statsOpen) { drawMap(); if (lastGame) showStats(lastGame); }
    }));
    app.append(el("header", {}, el("h1", {}, "G2TD: Tower Defense"), el("nav", {}, ...tabs)), ...pages);
}

/** The Stats tab is drawn only while it is open (the glasses game runs on this page). */
let statsOpen = false, mapToDraw: (() => Uint8Array) | null = null, lastGame: Game | null = null;
/** Each level's colour, brightened for a phone screen (the glasses' dim levels would be
 *  near black here), as one RGBA word. */
const PHONE_GREY = Uint32Array.from({ length: 16 }, (_, l) => {
    const v = Math.round((l / 15) ** 0.55 * 255);
    return ((255 << 24) | (v << 16) | (v << 8) | v) >>> 0;
});

/** The map as the glasses show it, without enemies (display levels 0-15, 576x288),
 *  drawn now if the Stats tab is open, else when it opens. */
export function showMap(levels: () => Uint8Array) {
    mapToDraw = levels;
    if (statsOpen) drawMap();
}
function drawMap() {
    if (!mapToDraw) return;
    const levels = mapToDraw();
    mapToDraw = null;
    const ctx = canvas.getContext("2d")!, img = ctx.createImageData(576, 288);
    const rgba = new Uint32Array(img.data.buffer);
    for (let i = 0; i < levels.length; i++) rgba[i] = PHONE_GREY[levels[i]];
    ctx.putImageData(img, 0, 0);
}

let lastStats = "";
/** The stats tables, redrawn only when something in them changed and the tab is open.
 *  Only the wave under way changes its history entry. */
export function showStats(g: Game) {
    lastGame = g;
    if (!statsOpen) return;
    const key = JSON.stringify([MAP_INDEX, g.history.length, g.history[g.history.length - 1], g.wave, g.waveActive, g.lives, g.credits,
        g.over, g.won, g.arms, [...g.built.values()].map((b) => b.kind)]);
    if (key === lastStats) return;
    lastStats = key;
    const status = g.won ? "won!" : g.over ? "game over" : g.waveActive ? `wave ${g.wave} under way` : `building before wave ${g.wave + 1}`;
    summary.textContent = `${MAP.random ? "Random map" : `Map ${MAP_INDEX + 1} of ${MAPS.filter((m) => !m.random).length}, ${MAP.name}`}. Wave ${g.wave}${isFinite(WAVES) ? ` of ${WAVES}` : ""}, ${status}. ♥${g.lives}, $${g.credits}.` +
        (MAP.boss ? ` The boss's arms have ${g.arms.map((a, k) => `${a} of ${MAP.boss!.arms[k].hp} (${ARM_NAMES[MAP.boss!.arms[k].kind]})`).join(", ")} hits left.` : "");
    const sum = (f: (h: Game["history"][0]) => number) => g.history.reduce((a, h) => a + f(h), 0);
    waves.replaceChildren(g.history.length
        ? (MAP.boss
            ? table(["Wave", "Laser", "Sniper", "Cannon", "Shields broken", "Arm hits", "Leaked", "Earned"],
                g.history.map((h) => [h.wave, h.kills.laser, h.kills.sniper, h.kills.cannon, h.shields, h.boss, h.leaked, `$${h.earned}`]),
                ["All", sum((h) => h.kills.laser), sum((h) => h.kills.sniper), sum((h) => h.kills.cannon), sum((h) => h.shields), sum((h) => h.boss),
                    sum((h) => h.leaked), `$${sum((h) => h.earned)}`])
            : table(["Wave", "Laser", "Sniper", "Cannon", "Shields broken", "Slowed", "Leaked", "Earned"],
                g.history.map((h) => [h.wave, h.kills.laser, h.kills.sniper, h.kills.cannon, h.shields, h.slowed, h.leaked, `$${h.earned}`]),
                ["All", sum((h) => h.kills.laser), sum((h) => h.kills.sniper), sum((h) => h.kills.cannon), sum((h) => h.shields), sum((h) => h.slowed),
                    sum((h) => h.leaked), `$${sum((h) => h.earned)}`]))
        : el("p", {}, "No waves yet."));
    const built = (k: TowerKind) => [...g.built.values()].filter((b) => b.kind === k).length;
    towers.replaceChildren(table(["Tower", "Built", "Kills", "Damage"],
        KINDS.map((k) => [TOWERS[k].name, built(k), k === "stasis" ? "—" : sum((h) => h.kills[k]), k === "stasis" ? `${sum((h) => h.slowed)} slowed` : sum((h) => h.damage[k])])));
}
