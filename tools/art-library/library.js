// The art library page (index.html has the notes).
import { MAPS, CH, W, H, useMap } from "/src/rules.ts";
import { PACK, drawFloor, drawPieces, drawWalls, drawMap, artOf, artFor, piecesFor, xOf, EMPTY } from "/src/render/map.ts";

const $ = (id) => document.getElementById(id);
const yOf = (r) => r * CH + 4;
const REDO_REASONS = ["low detail", "wrong perspective", "style", "wrong scale", "seams"];
let reviews = {};
try { reviews = await fetch(`/art/reviews.json?t=${Date.now()}`).then((r) => (r.ok ? r.json() : {})); } catch { /* none yet */ }

/** The shared set, each group a page of its own (the inventory of the graphics remake),
 *  drawn on SHARED_FLOOR's floor. A map's page has the rest: its own pieces, floors, walls
 *  and road. */
const SHARED = {
    furniture: { name: "Shared furniture", ids: ["chair", "office-chair", "stool", "bench", "desk", "side-table", "table-4", "table-6", "couch", "bunk", "locker", "cabinet", "shelf", "vending", "water-cooler", "plant", "bin", "workstation", "console"] },
    industrial: { name: "Shared industrial", ids: ["cargo-case", "case-stack", "barrel", "gas-cylinder", "tank", "tool-chest", "cable-reel", "generator", "work-light", "fire-point", "bot-wreck", "pipe", "cable-tray", "conveyor"] },
    decals: { name: "Shared decals", ids: ["hatch", "grate", "drain", "floor-arrow", "hazard", "mat", "scorch"] },
};
const SHARED_FLOOR = "hab-ring";
const isShared = (id) => Object.values(SHARED).some((g) => g.ids.includes(id));
/** Per-browser conveniences (open cards, scroll across a reload); fine to lose. */
const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* private window */ } },
};
const opened = new Set(store.get("artlib.open", []));

const shared = document.createElement("optgroup"); shared.label = "Shared";
for (const [g, { name }] of Object.entries(SHARED)) shared.append(new Option(name, `shared:${g}`));
const maps = document.createElement("optgroup"); maps.label = "Maps";
for (const m of MAPS) maps.append(new Option(m.name, m.id));
$("map").append(shared, maps);
const want = new URLSearchParams(location.search).get("map");
if (want) $("map").value = want;
if (!$("map").value) $("map").value = "shared:furniture";
for (const id of ["map", "find", "reviewed", "picks", "hidden", "zoom", "glasses"]) $(id).addEventListener("input", () => render());
$("collapse").onclick = () => { opened.clear(); store.set("artlib.open", []); for (const c of cards.values()) c.refresh(); };
$("expand").onclick = () => { for (const k of cards.keys()) opened.add(k); store.set("artlib.open", [...opened]); for (const c of cards.values()) c.refresh(); };

/** A level as the glasses show it: black at 0, big steps up to 6, small after (the test
 *  card's readings), in the glasses' green. Or plain, level x 17. */
function rgb(v) {
    let g;
    if (!$("glasses").checked) g = v * 17;
    else g = v <= 0 ? 0 : Math.round(255 * Math.pow(v / 15, 0.55));
    const rb = Math.floor(g * 22 / 100);
    return [rb, g, rb];
}
/** Part of a 576x288 level buffer on a canvas, `z` px a pixel. */
function canvasOf(px, x0, y0, w, h, z) {
    const c = document.createElement("canvas"); c.width = w * z; c.height = h * z;
    const x = c.getContext("2d"), img = x.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let xx = 0; xx < w; xx++) {
        const v = px[(y0 + y) * W + x0 + xx], [r, g, b] = rgb(v), i = (y * w + xx) * 4;
        img.data[i] = r; img.data[i + 1] = g; img.data[i + 2] = b; img.data[i + 3] = 255;
    }
    const o = new OffscreenCanvas(w, h); o.getContext("2d").putImageData(img, 0, 0);
    x.imageSmoothingEnabled = false; x.drawImage(o, 0, 0, w * z, h * z);
    return c;
}
/** One picture alone on dark, `z` px a pixel. */
function picCanvas(pic, z) {
    const a = artOf(pic), c = document.createElement("canvas"); c.width = a.w * z; c.height = a.h * z;
    const x = c.getContext("2d"); x.fillStyle = "#050a05"; x.fillRect(0, 0, c.width, c.height);
    for (let y = 0; y < a.h; y++) for (let xx = 0; xx < a.w; xx++) {
        const v = a.px[y * a.w + xx]; if (v === 255) continue;
        const [r, g, b] = rgb(v); x.fillStyle = `rgb(${r},${g},${b})`; x.fillRect(xx * z, y * z, z, z);
    }
    return c;
}
/** A scene on the map's floor, cropped to the cells r0..r1, c0..c1 (a gap's margin round). */
function scene(mapId, pieces, [r0, c0, r1, c1], walls = []) {
    const px = new Uint8Array(W * H);
    drawFloor(px, mapId, EMPTY);
    drawPieces(px, pieces);
    if (walls.length) drawWalls(px, mapId, walls);
    const x0 = xOf(c0) - 3, y0 = yOf(r0) - 4, x1 = xOf(c1) + 22, y1 = yOf(r1) + 23;
    return { px, box: [x0, y0, x1 - x0 + 1, y1 - y0 + 1] };
}

/** Each kind of join shown the ways it can meet itself; `cells` lists what joins, for the seam score. */
function demo(id, def) {
    const P = (r, c, q = 0, v = 0) => [r, c, id, v, q];
    if (def.joins === "row") {
        const ps = [P(1, 1), P(1, 3), P(1, 4), P(1, 6), P(1, 7), P(1, 8), P(1, 10), P(1, 11), P(1, 12), P(1, 13), P(1, 14),
            P(3, 1, 1), P(4, 1, 1), P(5, 1, 1), P(3, 3, 3), P(4, 3, 3), P(5, 3, 3), P(3, 5, 2), P(3, 6, 2), P(3, 7, 2)];
        return { pieces: ps, crop: [1, 1, 5, 14], text: "1, 2, 3 and 5 in a row; turned columns; a row turned round" };
    }
    if (def.joins === "grid") {
        const ps = [P(1, 1), P(1, 3), P(1, 4), P(1, 5), P(3, 1), P(3, 2), P(4, 1), P(4, 2)];
        for (let r = 3; r <= 5; r++) for (let c = 4; c <= 6; c++) ps.push(P(r, c));
        return { pieces: ps, crop: [1, 1, 5, 6], text: "1x1, 3x1, 2x2, 3x3" };
    }
    if (def.joins === "path") {
        const cells = [[1, 1], [1, 3], [1, 4], [1, 5], [3, 1], [3, 2], [4, 2], [5, 2], [3, 4], [3, 5], [3, 6], [4, 5], [3, 9], [4, 8], [4, 9], [4, 10], [5, 9]];
        return { pieces: cells.map(([r, c]) => P(r, c)), crop: [1, 1, 5, 10], text: "a dot, a straight, a bend, a tee, a cross" };
    }
    // a single piece: every variant, four ways round
    const [w, h] = def.size, span = Math.max(w, h) + 1, n = Object.values(def.parts)[0].length, ps = [];
    for (let v = 0; v < n; v++) for (let q = 0; q < 4; q++) ps.push(P(1 + v * span, 1 + q * span, q, v));
    return { pieces: ps, crop: [1, 1, n * span - 1, 4 * span - 1], text: "each variant turned 0°, 90°, 180°, 270°" };
}
/** How far the levels jump across the edges where joined cells meet their links: the mean
 *  and largest step (in levels) between the pixels either side of each edge. Lower joins smoother. */
function seams(px, pieces) {
    const at = new Set(pieces.map((p) => `${p[0]},${p[1]}`)), steps = [];
    const edge = (xa, ya, xb, yb) => steps.push(Math.abs(px[ya * W + xa] - px[yb * W + xb]));
    for (const [r, c] of pieces) {
        if (at.has(`${r},${c + 1}`)) for (let y = yOf(r); y < yOf(r) + 20; y++) { const x = xOf(c); edge(x + 19, y, x + 20, y); edge(x + 24, y, x + 25, y); }
        if (at.has(`${r + 1},${c}`)) for (let x = xOf(c); x < xOf(c) + 20; x++) { const y = yOf(r); edge(x, y + 19, x, y + 20); edge(x, y + 26, x, y + 27); }
    }
    if (!steps.length) return null;
    return { mean: steps.reduce((a, b) => a + b, 0) / steps.length, max: Math.max(...steps) };
}

// --- reviews ---------------------------------------------------------------------------
const said = (r) => !!(r?.redo?.length || r?.note);
const shown = (k) => { const w = $("reviewed").value, r = reviews[k]; return w === "all" || (w === "fav" && r?.favorite) || (w === "redo" && said(r)) || (w === "none" && !r); };
/** A picture with its review buttons: ★ favorite, and redo (reasons ticked, a note). */
function reviewed(k, label, canvas) {
    const box = document.createElement("div"); box.className = "v";
    box.innerHTML = `<div class="label">${label}</div>`; box.append(canvas);
    const draw = () => {
        box.querySelector(".review")?.remove(); box.querySelector(".said")?.remove();
        const r = reviews[k] ?? {};
        box.classList.toggle("fav", !!r.favorite); box.classList.toggle("redoing", said(r));
        const bar = document.createElement("div"); bar.className = "review";
        const star = document.createElement("button"); star.className = "star" + (r.favorite ? " on" : ""); star.textContent = r.favorite ? "★ favorite" : "☆ favorite";
        star.onclick = () => save(k, { ...r, favorite: !r.favorite }, draw);
        const redo = document.createElement("button"); redo.className = "redo" + (said(r) ? " on" : ""); redo.textContent = "redo…";
        redo.onclick = () => { const f = box.querySelector(".redo-form"); f ? f.remove() : box.append(redoForm(k, r, draw)); };
        bar.append(star, redo); box.append(bar);
        if (said(r)) box.insertAdjacentHTML("beforeend", `<div class="said">redo: ${[...(r.redo ?? []), r.note].filter(Boolean).join(" · ").replace(/</g, "&lt;")}</div>`);
    };
    draw();
    return box;
}
function redoForm(k, r, done) {
    const f = document.createElement("div"); f.className = "redo-form";
    for (const reason of REDO_REASONS) f.insertAdjacentHTML("beforeend", `<label><input type="checkbox" value="${reason}"${r.redo?.includes(reason) ? " checked" : ""}> ${reason}</label>`);
    const note = document.createElement("textarea"); note.placeholder = "what to change"; note.value = r.note ?? ""; f.append(note);
    const buttons = document.createElement("div"); buttons.className = "buttons";
    const ok = document.createElement("button"); ok.textContent = "save";
    ok.onclick = () => { f.remove(); save(k, { ...r, redo: [...f.querySelectorAll("input:checked")].map((c) => c.value), note: note.value.trim() }, done); };
    const clear = document.createElement("button"); clear.textContent = "clear redo";
    clear.onclick = () => { f.remove(); save(k, { ...r, redo: [], note: "" }, done); };
    buttons.append(ok, clear); f.append(buttons);
    return f;
}
async function save(k, r, done) {
    $("status").textContent = "saving…";
    try {
        const res = await fetch("/__library/review", { method: "POST", body: JSON.stringify({ key: k, favorite: !!r.favorite, redo: r.redo ?? [], note: r.note ?? "", hidden: !!r.hidden }) }).then((x) => x.json());
        if (!res.ok) throw new Error(res.error);
        if (res.review) reviews[k] = res.review; else delete reviews[k];
        $("status").textContent = "saved";
    } catch (e) { $("status").textContent = "save failed: " + e.message; }
    done();
}

// --- the page --------------------------------------------------------------------------
function section(title, note) {
    const h = document.createElement("h2"); h.textContent = title; $("main").append(h);
    if (note) $("main").insertAdjacentHTML("beforeend", `<p class="note">${note}</p>`);
}
/** Every card on the page by key: its element and a refresh that redraws its head and, when
 *  it's open, its body (built off the page, then swapped in, so the page doesn't jump). */
const cards = new Map();
function card(key, title, info, badge, body) {
    const el = document.createElement("div"); el.className = "item";
    const head = document.createElement("div"); head.className = "head";
    head.innerHTML = `<span class="tw"></span><b>${title}</b><span class="badge"></span><span>${info}</span>`;
    const inner = document.createElement("div");
    el.append(head, inner);
    let drawing = 0;
    const refresh = async () => {
        const open = opened.has(key), b = badge?.();
        el.classList.toggle("open", open);
        head.querySelector(".tw").textContent = open ? "▾" : "▸";
        const bs = head.querySelector(".badge"); bs.className = "badge " + (b?.cls ?? ""); bs.textContent = b?.text ?? "";
        const mine = ++drawing;
        if (!open) { inner.replaceChildren(); return; }
        const off = document.createElement("div"); await body(off);
        if (mine === drawing) inner.replaceChildren(...off.childNodes);
    };
    head.onclick = () => { opened.has(key) ? opened.delete(key) : opened.add(key); store.set("artlib.open", [...opened]); refresh(); };
    cards.set(key, { el, refresh });
    $("main").append(el);
    return refresh();
}
/** Every picture of a thing, reviewable, as "<thing>|<part>|<index>". */
function pictures(el, thing, parts, z) {
    const row = document.createElement("div"); row.className = "row";
    let any = false;
    for (const [part, pics] of Object.entries(parts)) pics.forEach((pic, i) => {
        const k = `${thing}|${part}|${i}`;
        if (!shown(k)) return;
        any = true;
        row.append(reviewed(k, `${part}${pics.length > 1 ? " " + (i + 1) : ""} · ${pic[0].length}x${pic.length}`, picCanvas(pic, z)));
    });
    if (any) el.append(row);
    return any;
}
const picKeys = (thing, parts) => Object.entries(parts).flatMap(([part, pics]) => pics.map((_, i) => `${thing}|${part}|${i}`));

// --- candidates (tools/piece_gen.py) -----------------------------------------------------
let work = {};
const pics = new Map();
/** A candidate's PNG (grey = level x 17, alpha) as levels, 255 see-through. */
function levelsOf(url) {
    if (!pics.has(url)) pics.set(url, new Promise((ok) => {
        const im = new Image();
        im.onload = () => {
            const c = new OffscreenCanvas(im.width, im.height), x = c.getContext("2d");
            x.drawImage(im, 0, 0);
            const d = x.getImageData(0, 0, im.width, im.height).data, px = new Uint8Array(im.width * im.height);
            for (let i = 0; i < px.length; i++) px[i] = d[i * 4 + 3] < 128 ? 255 : Math.round(d[i * 4] / 17);
            ok({ w: im.width, h: im.height, px });
        };
        im.onerror = () => ok(null);
        im.src = url + "?t=" + Date.now();
    }));
    return pics.get(url);
}
/** A candidate on the map's floor, drawn by the renderer like a pack piece: its parts
 *  loaded as a temporary piece and shown in the same demo (every turn, rows, grids, a
 *  little path network), with the seam score for pieces that join. */
async function candidateScene(mapId, id, piece, cand, z) {
    const rows = (a) => Array.from({ length: a.h }, (_, y) => Array.from(a.px.slice(y * a.w, (y + 1) * a.w), (v) => (v === 255 ? "." : v.toString(16))).join(""));
    const parts = {};
    for (const [name, file] of Object.entries(cand.parts)) parts[name] = [rows(await levelsOf(`/art/work/${id}/${file}`))];
    const tmp = "__candidate";
    const def = { size: piece.size, joins: piece.joins, ...(piece.decal ? { decal: true } : {}), parts };
    PACK.pieces[tmp] = def;
    try {
        const d = demo(tmp, def), { px, box } = scene(mapId, d.pieces, d.crop);
        const s = def.joins === "none" ? null : seams(px, d.pieces);
        return { canvas: canvasOf(px, ...box, z), note: s ? `seams ${s.mean.toFixed(2)} / ${s.max}` : "" };
    } finally { delete PACK.pieces[tmp]; }
}
/** The candidates still to show: hidden ones only with "hidden" ticked, and only those the
 *  review filter lets through. */
const candKeys = (id) => Object.keys(work[id]?.candidates ?? {}).map((name) => [name, `work:${id}|${name}`]).filter(([, k]) => $("hidden").checked || !reviews[k]?.hidden);
async function candidateRow(el, mapId, id, z) {
    const { piece, candidates: cands } = work[id];
    const row = document.createElement("div"); row.className = "row";
    for (const [name, k] of candKeys(id)) {
        if (!shown(k)) continue;
        const cand = cands[name], box = document.createElement("div");
        if (cand.raw) { const im = document.createElement("img"); im.src = `/art/work/${id}/${cand.raw}`; im.style.cssText = "width:120px;display:block;margin-bottom:4px;border-radius:2px"; box.append(im); }
        if (cand.parts) {
            const { canvas, note } = await candidateScene(mapId, id, piece, cand, z);
            box.append(canvas);
            const how = cand.method === "drawn" ? "drawn" : `${cand.method}${cand.sure ? ", sure " + cand.sure : ""}`;
            box.insertAdjacentHTML("beforeend", `<div class="nums">${how}${note ? " · " + note : ""}</div>`);
            const inUse = PACK.pieces[id]?.from?.includes(name);
            const use = document.createElement("button"); use.textContent = inUse ? "✓ in the pack" : "use";
            use.style.cssText = inUse ? "background:var(--accent);color:#0b1a10;border-color:var(--accent)" : "border-color:var(--accent);color:var(--accent)";
            use.onclick = async () => {
                use.disabled = true; $("status").textContent = "updating the pack…";
                const r = await fetch("/__library/use", { method: "POST", body: JSON.stringify({ piece: id, cand: name, use: !inUse }) }).then((x) => x.json()).catch((e) => ({ error: e.message }));
                $("status").textContent = r.ok ? "pack updated" : "failed: " + r.error;
                if (!r.ok) use.disabled = false;      // on success the new pack arrives by HMR and redraws the card
            };
            use.style.marginTop = "4px"; box.append(use);
        } else box.insertAdjacentHTML("beforeend", `<div class="nums">didn't convert: ${cand.method ?? "?"}</div>`);
        const hidden = !!reviews[k]?.hidden;
        const hide = document.createElement("button"); hide.className = "hide"; hide.textContent = hidden ? "unhide" : "hide";
        hide.title = hidden ? "Show this candidate again" : "Stop showing this candidate (tick \"hidden\" to see it again)";
        hide.onclick = () => save(k, { ...(reviews[k] ?? {}), hidden: !hidden }, () => cards.get(`piece:${id}`)?.refresh());
        box.append(hide);
        const v = reviewed(k, cand.label, box); v.classList.toggle("hidden", hidden);
        row.append(v);
    }
    if (row.children.length) el.append(row);
    else el.insertAdjacentHTML("beforeend", `<p class="note">No candidates to show${$("hidden").checked ? "" : " (some may be hidden)"}.</p>`);
}

/** One object's card: what the pack has of it, drawn in its demo, then its candidates. */
function pieceCard(id, mapId, z) {
    const def = () => PACK.pieces[id], w = work[id]?.piece;
    const d0 = def() ?? w, joins = d0.joins === "none" ? "single" : d0.joins + " joins";
    const info = `${d0.size.join("x")} · ${joins}${d0.decal ? " · decal" : ""}${w ? " · " + w.what : ""}`;
    const badge = () => {
        const p = def();
        if (!p) return w ? { cls: "none", text: "no pick" } : null;
        return { cls: "picked", text: "✓ " + (p.from?.length ? p.from.join(", ") : "in the pack") };
    };
    return card(`piece:${id}`, id, info, badge, async (el) => {
        const p = def();
        if (p) {
            el.insertAdjacentHTML("beforeend", `<h3>in the pack</h3>`);
            const d = demo(id, p), { px, box } = scene(mapId, d.pieces, d.crop);
            const wrap = document.createElement("div"); wrap.className = "demo";
            wrap.append(canvasOf(px, ...box, z));
            const s = p.joins === "none" ? null : seams(px, d.pieces);
            wrap.insertAdjacentHTML("beforeend", `<div class="nums">${d.text}${s ? ` · seams ${s.mean.toFixed(2)} / ${s.max}` : ""}</div>`);
            el.append(wrap);
            pictures(el, id, p.parts, z + 1);
        }
        if (work[id]) {
            el.insertAdjacentHTML("beforeend", `<h3>candidates</h3>`);
            await candidateRow(el, mapId, id, z + 1);
        }
    });
}
/** Whether an object passes the header's filters: found, picked or not, and with some
 *  picture the review filter lets through. */
function passes(id, picked, keys) {
    const find = $("find").value.trim().toLowerCase(), want = $("picks").value;
    if (find && !id.includes(find)) return false;
    if ((want === "none" && picked) || (want === "picked" && !picked)) return false;
    return $("reviewed").value === "all" || keys.some(shown);
}
function pieceKeys(id) {
    const p = PACK.pieces[id];
    return [...(p ? picKeys(id, p.parts) : []), ...candKeys(id).map(([, k]) => k)];
}

// --- floors and walls (tools/kit_gen.py) ------------------------------------------------
let kits = {};
const KIND_PACK = { floor: "floors", wall: "walls", road: "roads" };
const KIND_FIELD = { floor: "floor", wall: "walls", road: "road" };
function floorScene(mapId, fid, z) {
    const px = new Uint8Array(W * H), rows = ["", ...Array(4).fill(".aaaaaaaa")];
    drawFloor(px, mapId, { version: 2, floor: { legend: { a: fid }, rows }, pieces: [], walls: [] });
    return canvasOf(px, xOf(1), yOf(1), 25 * 8, 27 * 4, z);
}
function wallScene(mapId, z) {
    const walls = [[1, 1, "s"], [1, 2, "s"], [1, 3, "s"], [1, 3, "e"], [2, 3, "e"], [3, 1, "e"], [3, 1, "s"]];
    const { px, box } = scene(mapId, [], [1, 1, 3, 4], walls);
    return canvasOf(px, ...box, z);
}
function roadScene(mapId, z) {
    useMap(MAPS.findIndex((m) => m.id === mapId));      // the road comes from the current map's rules
    return canvasOf(drawMap(mapId, EMPTY), 0, 0, W, H, Math.max(1, z - 1));
}
/** A kit candidate drawn as if the map used it: loaded into the pack under a temporary
 *  name, the map pointed at it, drawn, and both put back. */
async function kitScene(mapId, id, name, z) {
    const { kit, candidates } = kits[id], cand = candidates[name];
    const rows = (a) => Array.from({ length: a.h }, (_, y) => Array.from(a.px.slice(y * a.w, (y + 1) * a.w), (v) => (v === 255 ? "." : v.toString(16))).join(""));
    const part = {};
    for (const [p, file] of Object.entries(cand.parts)) part[p] = rows(await levelsOf(`/art/work/kits/${id}/${file}`));
    const tmp = "__kit", bank = PACK[KIND_PACK[kit.kind]], field = KIND_FIELD[kit.kind];
    bank[tmp] = kit.kind === "floor"
        ? { tile: Object.keys(part).sort((a, b) => a.slice(4) - b.slice(4)).map((p) => part[p]), ...(kit.panel[0] * kit.panel[1] > 1 ? { panel: kit.panel } : {}) }
        : kit.kind === "road" ? { width: 7, ...part } : part;
    const was = PACK.maps[mapId];
    PACK.maps[mapId] = { ...was, [field]: tmp };
    try { return kit.kind === "floor" ? floorScene(mapId, tmp, z) : kit.kind === "wall" ? wallScene(mapId, z) : roadScene(mapId, z); }
    finally { PACK.maps[mapId] = was; delete bank[tmp]; }
}
const kitKeys = (id) => Object.keys(kits[id]?.candidates ?? {}).map((name) => `kit:${id}|${name}`).filter((k) => $("hidden").checked || !reviews[k]?.hidden);
/** A kit's card: its candidates, each drawn on the map, with use. */
function kitCard(id, mapId, z) {
    const { kit } = kits[id];
    const inPack = () => PACK[KIND_PACK[kit.kind]]?.[id];
    const used = () => artFor(mapId)[KIND_FIELD[kit.kind]] === id;
    const badge = () => inPack() ? { cls: "picked", text: `✓ ${inPack().from ?? "in the pack"}${used() ? "" : " (not in use)"}` } : { cls: "none", text: "no pick" };
    return card(`kit:${id}`, id, `${kit.kind} kit · ${kit.what}`, badge, async (el) => {
        el.insertAdjacentHTML("beforeend", `<h3>candidates</h3>`);
        const row = document.createElement("div"); row.className = "row";
        for (const name of Object.keys(kits[id].candidates)) {
            const k = `kit:${id}|${name}`;
            if (!kitKeys(id).includes(k) || !shown(k)) continue;
            const cand = kits[id].candidates[name], box = document.createElement("div");
            if (cand.raw) { const im = document.createElement("img"); im.src = `/art/work/kits/${id}/${cand.raw}`; im.style.cssText = "width:160px;display:block;margin-bottom:4px;border-radius:2px"; box.append(im); }
            box.append(await kitScene(mapId, id, name, kit.kind === "road" ? z : z + 1));
            const inUse = inPack()?.from === name && used();
            const use = document.createElement("button"); use.textContent = inUse ? "✓ in use" : "use";
            use.style.cssText = (inUse ? "background:var(--accent);color:#0b1a10;" : "color:var(--accent);") + "border-color:var(--accent);margin-top:4px";
            use.disabled = inUse;
            use.onclick = async () => {
                use.disabled = true; $("status").textContent = "updating the pack…";
                const r = await fetch("/__library/use-kit", { method: "POST", body: JSON.stringify({ kit: id, cand: name }) }).then((x) => x.json()).catch((e) => ({ error: e.message }));
                $("status").textContent = r.ok ? "pack updated" : "failed: " + r.error;
                if (!r.ok) use.disabled = false;
            };
            box.append(use);
            const hidden = !!reviews[k]?.hidden;
            const hide = document.createElement("button"); hide.className = "hide"; hide.textContent = hidden ? "unhide" : "hide";
            hide.onclick = () => save(k, { ...(reviews[k] ?? {}), hidden: !hidden }, () => cards.get(`kit:${id}`)?.refresh());
            box.append(hide);
            const v = reviewed(k, cand.label, box); v.classList.toggle("hidden", hidden);
            row.append(v);
        }
        if (row.children.length) el.append(row);
        else el.insertAdjacentHTML("beforeend", `<p class="note">No candidates to show.</p>`);
    });
}

/** The page: a shared group or a map. Resolves once every open card has drawn. */
async function render() {
    const page = $("map").value, z = +$("zoom").value;
    history.replaceState(null, "", `?map=${page}`);
    $("main").innerHTML = ""; cards.clear();
    const draws = [];
    let count = 0;
    const pieces = (mapId, ids) => {
        for (const id of ids) {
            if (!passes(id, !!PACK.pieces[id], pieceKeys(id))) continue;
            draws.push(pieceCard(id, mapId, z)); count++;
        }
    };
    if (page.startsWith("shared:")) {
        const g = SHARED[page.slice(7)];
        section(g.name, `Each object's pictures in the pack, drawn by the game's renderer on ${MAPS.find((m) => m.id === SHARED_FLOOR).name}'s floor, then the candidates tools/piece_gen.py made from its house-view sketch (art/work/): the sketch itself, then each seed as klein drew it and converted onto the sketch's levels. Use puts one into the pack as a variant; hide drops one from view. Joining pieces show their seam score (mean / largest level step where a cell meets its link).`);
        pieces(SHARED_FLOOR, g.ids.filter((id) => PACK.pieces[id] || work[id]));
    } else {
        const mapId = page, art = artFor(mapId);
        section("Pieces", `${MAPS.find((m) => m.id === mapId).name}'s own pieces (the shared set has its own pages), on its floor (${art.floor}).`);
        const mapOf = (id) => work[id]?.piece.map ?? PACK.pieces[id]?.maps?.[0];   // a map's own piece, or none named: every map's
        const own = [...new Set([...piecesFor(mapId), ...Object.keys(work)])].filter((id) => !isShared(id) && (!mapOf(id) || mapOf(id) === mapId));
        pieces(mapId, own);
        // floors, walls and road are always in the pack: "picked"
        const kit = (key, title, info, thing, parts, draw) => {
            if (!passes(key, true, picKeys(thing, parts))) return;
            count++;
            draws.push(card(key, title, info, null, async (el) => { el.append(draw()); pictures(el, thing, parts, z + 1); }));
        };
        const kitCands = (kind) => Object.keys(kits).filter((id) => kits[id].kit.map === mapId && kits[id].kit.kind === kind && passes(id, !!PACK[KIND_PACK[kind]][id], kitKeys(id)));
        const kitCards = (kind) => { for (const id of kitCands(kind)) { draws.push(kitCard(id, mapId, z)); count++; } };
        section("Floors", "Tiles 25x27: a cell and the gaps right of and below it, repeated over the map. The first is the map's own; the others can be painted per cell. Then the candidates tools/kit_gen.py made (the sketch, then klein's seeds): use makes one the map's floor.");
        for (const fid of art.floors) {
            const f = PACK.floors[fid];
            if (!f) continue;
            kit(`floor:${fid}`, fid, `${f.tile.length} tile${f.tile.length > 1 ? "s" : ""}${fid === art.floor ? " · the map's floor" : ""}`, `floor:${fid}`, { tile: f.tile }, () => {
                return floorScene(mapId, fid, z);
            });
        }
        kitCards("floor");
        section("Walls", "Placed walls: a strip under a cell, one right of a cell, a post where they meet. Then tools/kit_gen.py's candidates: use makes one the map's wall kit.");
        const wk = PACK.walls[art.walls];
        if (wk) kit(`walls:${art.walls}`, art.walls, "wall kit", `walls:${art.walls}`, { h: [wk.h], v: [wk.v], node: [wk.node] }, () => wallScene(mapId, z));
        kitCards("wall");
        section("Road walls", "The ring round the road, from a strip (x along the road, rows outwards) and a corner. Shown on this map's road. Then tools/kit_gen.py's candidates: use makes one the map's road wall.");
        const road = PACK.roads[art.road];
        if (road) kit(`road:${art.road}`, art.road, `${road.width} px deep`, `road:${art.road}`, { strip: [road.strip], corner: [road.corner] }, () => roadScene(mapId, z));
        kitCards("road");
    }
    $("status").textContent = `${count} objects · ${Object.keys(reviews).length} reviews`;
    await Promise.all(draws);
}

// A new pack (a candidate used or dropped rebuilds src/pack.ts) is taken in place: the
// renderer's PACK object (the one this page draws with, from map.ts) gets the new contents
// and the cards redraw, with no page reload.
// When the game's main.ts is in Vite's module graph it can't take the change, so Vite
// reloads every page; this page declines that reload (a path that isn't this page) and
// fetches the new pack itself. Otherwise the change arrives here by HMR.
function takePack(fresh) {
    if (fresh !== PACK) {
        for (const k of Object.keys(PACK)) delete PACK[k];
        Object.assign(PACK, fresh);
    }
    for (const c of cards.values()) c.refresh();
}
if (import.meta.hot) {
    import.meta.hot.accept("/src/render/map.ts", (m) => { if (m) takePack(m.PACK); });
    import.meta.hot.on("vite:beforeFullReload", (p) => {
        if (!p.triggeredBy?.endsWith("/src/pack.ts")) return;
        p.path = "/__not-this-page.html";
        import(/* @vite-ignore */ `/src/pack.ts?t=${Date.now()}`).then((m) => takePack(m.PACK));
    });
}
// Keep the place across a reload that still happens (a code change, Vite restarting).
addEventListener("pagehide", () => { try { sessionStorage.setItem("artlib.scroll", JSON.stringify([$("map").value, scrollY])); } catch { /* none */ } });
work = await fetch("/__library/work").then((r) => r.json()).catch(() => ({}));
kits = await fetch("/__library/kits").then((r) => r.json()).catch(() => ({}));
await render();
try {
    const [page, y] = JSON.parse(sessionStorage.getItem("artlib.scroll") ?? "[]");
    if (page === $("map").value) scrollTo(0, y);
} catch { /* none */ }
