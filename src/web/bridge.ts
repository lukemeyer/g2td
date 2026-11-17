/** A stand-in for the Even Hub SDK, for playtesting in a plain browser (play.html,
 *  `npm run play`; vite.play.config.ts points the game's SDK import here). The game's
 *  code is unchanged: this draws the page it sends on a 576x288 canvas and turns
 *  buttons and keys into the glasses' events.
 *
 *  Text is placed glyph by glyph at the glasses' own advances (`@evenrealities/pretext`),
 *  so the █ covers hide the enemies baked into the map image as they do on the glasses;
 *  the glyphs themselves are the browser's, stretched to those advances. */
import { OsEventTypeList } from "@evenrealities/even_hub_sdk";
import { getTextWidth } from "@evenrealities/pretext";

export { OsEventTypeList };

const W = 576, H = 288, LINE = 27;

type Box = { x: number; y: number; w: number; h: number; z: number };
type Text = Box & { content: string; color: number; border: number; borderColor: number; radius: number };
type Image = Box & { bitmap: ImageBitmap | null };

const texts = new Map<number, Text>();
const images = new Map<number, Image>();
let listener: ((e: unknown) => void) | null = null;
let exitAsked = false;

// --- the screen and controls ---------------------------------------------------------

const style = document.createElement("style");
style.textContent = `
  #glasses { display: block; width: 100%; max-width: 1152px; margin: 0 auto; aspect-ratio: 2; image-rendering: pixelated; background: #000; border-radius: 0; }
  #controls { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; padding: 12px 16px; max-width: 1152px; margin: 0 auto; }
  #controls button, #controls select { font: 600 15px system-ui, sans-serif; padding: 12px 18px; border-radius: 8px; border: 1px solid #2a2f35; background: #181b1f; color: #e6e8ea; touch-action: manipulation; }
  #controls button:active { background: #2a2f35; }
  #controls .keys { width: 100%; text-align: center; color: #9aa1a8; font: 13px system-ui, sans-serif; }`;
document.head.append(style);

const canvas = document.createElement("canvas");
canvas.id = "glasses";
canvas.width = W; canvas.height = H;
const ctx = canvas.getContext("2d")!;
const controls = document.createElement("div");
controls.id = "controls";
document.body.prepend(canvas, controls);

const send = (eventType: OsEventTypeList) => {
    exitAsked = false; draw();
    listener?.({ textEvent: { eventType } });
};
const button = (label: string, f: () => void) => {
    const b = document.createElement("button");
    b.textContent = label;
    b.addEventListener("click", f);
    controls.append(b);
};
button("▲ Up", () => send(OsEventTypeList.SCROLL_TOP_EVENT));
button("▼ Down", () => send(OsEventTypeList.SCROLL_BOTTOM_EVENT));
button("Tap", () => send(OsEventTypeList.CLICK_EVENT));
button("Double tap", () => send(OsEventTypeList.DOUBLE_CLICK_EVENT));
const menu = document.createElement("select");
menu.addEventListener("change", () => {
    const itemID = Number(menu.value);
    menu.selectedIndex = 0;
    listener?.({ menuItemClickEvent: { itemID } });
});
controls.append(menu);
const keys = document.createElement("div");
keys.className = "keys";
keys.textContent = "Keys: ↑ ↓ swipe · Enter or Space tap · Esc or Backspace double tap · M menu";
controls.append(keys);

addEventListener("keydown", (e) => {
    if (e.target instanceof HTMLSelectElement) return;
    const t = { ArrowUp: OsEventTypeList.SCROLL_TOP_EVENT, ArrowDown: OsEventTypeList.SCROLL_BOTTOM_EVENT, Enter: OsEventTypeList.CLICK_EVENT,
        " ": OsEventTypeList.CLICK_EVENT, Escape: OsEventTypeList.DOUBLE_CLICK_EVENT, Backspace: OsEventTypeList.DOUBLE_CLICK_EVENT }[e.key];
    if (t !== undefined) { e.preventDefault(); send(t); }
    else if (e.key === "m") { menu.focus(); menu.showPicker?.(); }
});

function setMenu(items: { itemName: string; itemID: number }[] = []) {
    menu.replaceChildren(new Option("Long-press menu…", ""), ...items.map((m) => new Option(m.itemName, String(m.itemID))));
}

// --- drawing -------------------------------------------------------------------------

/** Text colours 0-4 are image levels 3 apart (read on the glasses with the test card). */
const textGrey = (c: number) => Math.min(15, 3 + 3 * c) * 17;
const glyphFont = `20px Menlo, "DejaVu Sans Mono", monospace`;

/** Each glyph's advance on the glasses, kerning with the next one included. */
function advances(line: string): [string, number][] {
    const cs = Array.from(line);
    return cs.map((c, i) => [c, i + 1 < cs.length ? getTextWidth(c + cs[i + 1]) - getTextWidth(cs[i + 1]) : getTextWidth(c)]);
}

function drawText(t: Text) {
    ctx.save();
    ctx.beginPath(); ctx.rect(t.x, t.y, t.w, t.h); ctx.clip();
    if (t.border) {
        ctx.strokeStyle = `rgb(${t.borderColor * 17},${t.borderColor * 17},${t.borderColor * 17})`;
        ctx.lineWidth = t.border;
        ctx.beginPath(); ctx.roundRect(t.x + 0.5, t.y + 0.5, t.w - 1, t.h - 1, t.radius); ctx.stroke();
    }
    const g = textGrey(t.color);
    ctx.fillStyle = `rgb(${g},${g},${g})`;
    ctx.font = glyphFont;
    ctx.textBaseline = "middle";
    t.content.split("\n").forEach((line, row) => {
        let x = t.x + t.border;
        const y = t.y + t.border + row * LINE;
        for (const [c, a] of advances(line)) {
            if (c === "█") ctx.fillRect(x, y + 3, a, 21);
            else if (c === "▒") for (let py = 3; py < 24; py++) for (let px = (py & 1); px < a; px += 2) ctx.fillRect(x + px, y + py, 1, 1);
            else if (c !== " ") {
                const m = ctx.measureText(c).width || a;
                ctx.save(); ctx.translate(x, y + LINE / 2); ctx.scale(a / m, 1); ctx.fillText(c, 0, 0); ctx.restore();
            }
            x += a;
        }
    });
    ctx.restore();
}

let queued = false;
function draw() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
        queued = false;
        ctx.globalCompositeOperation = "source-over";
        ctx.fillStyle = "#000"; ctx.fillRect(0, 0, W, H);
        const all: (["i", Image] | ["t", Text])[] = [...[...images.values()].map((i) => ["i", i] as ["i", Image]), ...[...texts.values()].map((t) => ["t", t] as ["t", Text])];
        all.sort((a, b) => a[1].z - b[1].z);
        for (const [k, o] of all) {
            if (k === "i") { if (o.bitmap) ctx.drawImage(o.bitmap, o.x, o.y, o.w, o.h); }
            else drawText(o);
        }
        if (exitAsked) {
            ctx.fillStyle = "rgba(0,0,0,0.75)"; ctx.fillRect(0, 0, W, H);
            ctx.fillStyle = "#fff"; ctx.font = "bold 22px system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
            ctx.fillText("Exit asked: the glasses show their exit dialog here.", W / 2, H / 2 - 16);
            ctx.font = "18px system-ui, sans-serif";
            ctx.fillText("Any input cancels it. Reload to relaunch.", W / 2, H / 2 + 16);
            ctx.textAlign = "start";
        }
        // The glasses' green.
        ctx.globalCompositeOperation = "multiply";
        ctx.fillStyle = "#5f5"; ctx.fillRect(0, 0, W, H);
    });
}

// --- the bridge ----------------------------------------------------------------------

function setPage(page: any) {
    texts.clear(); images.clear();
    for (const o of page.imageObject ?? []) images.set(o.containerID, { x: o.xPosition, y: o.yPosition, w: o.width, h: o.height, z: o.zOrderIndex ?? 0, bitmap: null });
    for (const o of page.textObject ?? []) texts.set(o.containerID, {
        x: o.xPosition, y: o.yPosition, w: o.width, h: o.height, z: o.zOrderIndex ?? 0, content: o.content ?? "", color: o.textColor ?? 4,
        border: o.borderWidth ?? 0, borderColor: o.borderColor ?? 0, radius: o.borderRadius ?? 0,
    });
    setMenu(page.menuObject?.menuItems);
    draw();
}

const bridge = {
    async createStartUpPageContainer(page: unknown) { setPage(page); return 0; },
    async rebuildPageContainer(page: unknown) { setPage(page); return true; },
    async updateImageRawData(d: { containerID: number; imageData: number[] }) {
        const im = images.get(d.containerID);
        if (!im) return "imageException";
        im.bitmap = await createImageBitmap(new Blob([new Uint8Array(d.imageData)], { type: "image/png" }));
        draw();
        return "success";
    },
    async textContainerUpgrade(d: { containerID: number; content: string }) {
        const t = texts.get(d.containerID);
        if (!t) return false;
        t.content = d.content;
        draw();
        return true;
    },
    async getLocalStorage(k: string) { try { return localStorage.getItem(k) ?? ""; } catch { return ""; } },
    async setLocalStorage(k: string, v: string) { try { localStorage.setItem(k, v); return true; } catch { return false; } },
    async shutDownPageContainer() { exitAsked = true; draw(); return true; },
    onEvenHubEvent(f: (e: unknown) => void) { listener = f; return () => { listener = null; }; },
};

export const waitForEvenAppBridge = async () => bridge;
