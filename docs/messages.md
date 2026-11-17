# Message line: every message

<!-- From src/main.ts (message(), g.note) and src/rules.ts (wave and build notes). Width is the glasses
     font's (@evenrealities/pretext) for the widest example of each message. Widest first. -->

Room for a one-row box free of tower slots: Hydroponics 270 px (its best), Cargo Bay 295, the other maps 345 or more.
The message line today is 280 px wide.

| px | When | Message | Widest example | Edit notes |
| ---: | --- | --- | --- | --- |
| 299 | Tower picker, too dear | `↕ <Tower> <glyph> $<cost> · need $<n> more` | `↕ Cannon ● $90 · need $90 more` | `↕ Cannon ● $90 · ╳ $90` |
| 264 | Cursor on Start Wave (road maps) | `tap: send wave <n> of <N>` + ` · swarm!` on swarm waves | `tap: send wave 4 of 5 · swarm!` | `Start wave 4/5 · SWARM!` |
| 249 | Picker on a new tower | `↕ remove <Tower> +$<cost> · tap` | `↕ remove Cannon +$90 · tap` | `↕ ╳ Cannon · +$90` |
| 249 | Random map start | `random map · endless waves` | `random map · endless waves` | `Random · ∞ waves` |
| 246 | Cursor on a tower built this phase | `<Tower>, new · tap to remove` | `Cannon, new · tap to remove` | `Cannon, removable` |
| 238 | Choose map (menu) | `Map ↕ <i> <Map> · tap` | `Map ↕ 3 Regolith Mine · tap` | `Map ↕ 3 Regolith Mine` |
| 237 | Wave sent, map still drawing | `wave <n> is coming` + `: a swarm!` | `wave 4 is coming: a swarm!` | `Wave 4 incoming: SWARM!` |
| 236 | Boss beaten | `the Boss Bot is destroyed!`, then `BASE SAVED! · tap to replay` | `BASE SAVED! · tap to replay` | `Boss Bot destroyed!`, then `BASE SAVED! · replay` |
| 233 | Cursor on Start Wave (boss) | `tap: send wave <n> · <walkers\|drones\|swarm>` | `tap: send wave 12 · walkers` | `Start wave 12 · Walkers` (also `· Drones`, `· SWARM`) |
| 231 | Boss map start | `Airlock · <walkers\|drones\|a swarm> incoming!` | `Airlock · a swarm incoming!` | `Airlock · swarm incoming!` |
| 229 | Cursor on Start Wave (random map) | `tap: send wave <n>` + ` · swarm!` | `tap: send wave 12 · swarm!` | `Start wave 12 · SWARM!` |
| 229 | Map cleared | `<Map> cleared! · tap` | `Regolith Mine cleared! · tap` | `Map cleared! · tap` |
| 228 | Map start | `map <i> of <N> · <Map>` | `map 3 of 5 · Regolith Mine` | `Map 3 · Regolith Mine` |
| 228 | Restart (menu) | `Restart? ↕ <NO\|THIS MAP\|ALL MAPS> · tap` | `Restart? ↕ ALL MAPS · tap` | `Restart? ↕ ALL MAPS` |
| 214 | Lost | `GAME OVER · tap to retry` | `GAME OVER · Tap to retry` | `GAME OVER · Tap to retry` (as in your example) |
| 211 | Wave cleared (boss) | `<walkers\|drones\|a swarm> incoming! +$<n>` | `a swarm incoming! +$80` | `SWARM incoming! +$80` (also `Walkers incoming! +$80`, `Drones incoming! +$80`) |
| 206 | Cursor on a free slot | `tripline slot · tap to build` / `turret slot · tap to build` | `tripline slot · tap to build` | `Tripline · tap to build` |
| 203 | Resumed | `<Map> · resumed` | `Regolith Mine · resumed` | `Regolith Mine · resumed` (unchanged) |
| 195 | Tower picker, affordable | `↕ <Tower> <glyph> $<cost> · tap` | `↕ Cannon ● $90 · tap` | `↕ Cannon ● $90 · tap` (unchanged) |
| 191 | Remove refused | `built in an earlier wave` / `build between waves` | `built in an earlier wave` | `Built in an earlier wave` / `Build between waves` |
| 182 | Build refused | `need $<n> more` / `slot taken` / `wrong slot` / `build between waves` | `build between waves` | `Need $90 more` / `Slot taken` / `Wrong slot` / `Build between waves` |
| 182 | Wave cleared (road maps) | `wave <n> cleared +$<bonus>` | `wave 4 cleared +$62` | `Wave 4 cleared +$62` |
| 169 | Last wave of a road map | `all <N> waves cleared!` | `all 5 waves cleared!` | `All 5 waves cleared!` |
| 169 | Fast Mode (menu, also mid-wave) | `Fast Mode Enabled` / `Fast Mode Disabled` | `Fast Mode Disabled` | `Fast Mode Disabled` (unchanged) |
| 119 | Picker cancel | `↕ cancel · tap` | `↕ cancel · tap` | `↕ Cancel · tap` |

