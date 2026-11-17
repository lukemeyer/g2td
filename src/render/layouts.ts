/// <reference types="vite/client" />
// Every map's layout (art/maps/<id>/layout.json, written by the map editor), bundled into
// the game. Saving in the editor changes the file, and Vite reloads the game with it.
import type { Layout } from "./map.ts";

const files = import.meta.glob("/art/maps/*/layout.json", { eager: true, import: "default" }) as Record<string, Layout>;
export const LAYOUTS: Record<string, Layout> = Object.fromEntries(Object.entries(files).map(([path, layout]) => [path.split("/")[3], layout]));
