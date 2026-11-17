import { defineConfig, type Plugin, type ViteDevServer } from 'vite'
import { copyFileSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'

/** The dev tools' saves (dev server only, never built). The map editor (tools/map-editor/)
 *  writes a map's art/maps/<id>/layout.json (version 2: floor, pieces, walls), which the
 *  game bundles (src/render/layouts.ts), so Vite reloads it; nothing is rebuilt. The art
 *  library (tools/art-library/) saves the user's reviews, lists the candidates
 *  tools/piece_gen.py made (art/work/<id>/candidates.json) and puts the chosen ones into
 *  the art pack. */
function devTools(): Plugin {
  /** Answer a JSON POST with `job`'s result, or its error. */
  const handle = (server: ViteDevServer, path: string, job: (body: any) => unknown) =>
    server.middlewares.use(path, (req, res) => {
      let body = ''
      req.on('data', (c) => (body += c))
      req.on('end', () => {
        res.setHeader('Content-Type', 'application/json')
        try {
          res.end(JSON.stringify({ ok: true, ...(job(JSON.parse(body)) as object) }))
        } catch (e) {
          res.statusCode = 500
          res.end(JSON.stringify({ ok: false, error: String(e) }))
        }
      })
    })
  /** A layout one line per piece and wall, so diffs read. */
  const list = (xs: unknown[]) => (xs.length ? `[\n${xs.map((p) => `  ${JSON.stringify(p)}`).join(',\n')}\n ]` : '[]')
  return {
    name: 'dev-tools',
    apply: 'serve',
    configureServer(server) {
      handle(server, '/__editor/save', ({ id, layout }) => {
        if (!/^[a-z-]+$/.test(id) || !existsSync(`art/maps/${id}`)) throw new Error('bad map id')
        if (layout?.version !== 2 || !Array.isArray(layout.pieces) || !Array.isArray(layout.walls)) throw new Error('not a version 2 layout')
        const floor = layout.floor ?? { legend: {}, rows: [] }
        const rows = floor.rows.map((r: string) => `   ${JSON.stringify(r)}`).join(',\n')
        writeFileSync(`art/maps/${id}/layout.json`, `{\n "version": 2,\n "floor": {\n  "legend": ${JSON.stringify(floor.legend)},\n${floor.from !== undefined ? `  "from": ${floor.from},\n` : ''}  "rows": [${rows ? `\n${rows}\n  ` : ''}]\n },\n "pieces": ${list(layout.pieces)},\n "walls": ${list(layout.walls)}\n}\n`)
        return {}
      })
      // Every piece's candidates from tools/piece_gen.py, for the library.
      server.middlewares.use('/__library/work', (_req, res) => {
        res.setHeader('Content-Type', 'application/json')
        const all: Record<string, unknown> = {}
        if (existsSync('art/work'))
          for (const id of readdirSync('art/work'))
            if (existsSync(`art/work/${id}/candidates.json`)) all[id] = JSON.parse(readFileSync(`art/work/${id}/candidates.json`, 'utf8'))
        res.end(JSON.stringify(all))
      })
      // Use a candidate as one of a piece's variants in the art pack, or stop using it: its
      // parts are copied to art/pack/<id>/, pack.json lists them (variant i of every part is
      // candidate `from[i]`), and src/pack.ts is rebuilt, which reloads the game's pages (the
      // library takes the new pack in place, by HMR).
      handle(server, '/__library/use', ({ piece, cand, use }) => {
        if (!/^[a-z0-9-]+$/.test(piece) || !/^[\w-]+$/.test(cand)) throw new Error('bad piece or candidate')
        const work = JSON.parse(readFileSync(`art/work/${piece}/candidates.json`, 'utf8'))
        const c = work.candidates[cand]
        if (!c?.parts) throw new Error(`no usable candidate ${cand}`)
        const pack = JSON.parse(readFileSync('art/pack/pack.json', 'utf8'))
        const p = (pack.pieces[piece] ??= { size: work.piece.size, joins: work.piece.joins, ...(work.piece.decal ? { decal: true } : {}), ...(work.piece.map ? { maps: [work.piece.map] } : {}), from: [], parts: {} })
        p.from ??= []
        const i = p.from.indexOf(cand)
        if (use && i < 0) {
          mkdirSync(`art/pack/${piece}`, { recursive: true })
          p.from.push(cand)
          for (const [part, file] of Object.entries(c.parts as Record<string, string>)) {
            copyFileSync(`art/work/${piece}/${file}`, `art/pack/${piece}/${file}`)
            ;(p.parts[part] ??= []).push(`${piece}/${file}`)
          }
        } else if (!use && i >= 0) {
          p.from.splice(i, 1)
          for (const part of Object.keys(p.parts)) {
            const [file] = p.parts[part].splice(i, 1)
            if (file) rmSync(`art/pack/${file}`, { force: true })
          }
          if (!p.from.length) delete pack.pieces[piece]
        } else return {}
        writeFileSync('art/pack/pack.json', JSON.stringify(pack, null, 1) + '\n')
        return { log: execFileSync('.venv/bin/python', ['-I', 'tools/pack_build.py'], { encoding: 'utf8', timeout: 60_000 }) }
      })
      // Every floor, road-wall and placed-wall kit's candidates from tools/kit_gen.py.
      server.middlewares.use('/__library/kits', (_req, res) => {
        res.setHeader('Content-Type', 'application/json')
        const all: Record<string, unknown> = {}
        const dir = 'art/work/kits'
        if (existsSync(dir))
          for (const id of readdirSync(dir))
            if (existsSync(`${dir}/${id}/candidates.json`)) all[id] = JSON.parse(readFileSync(`${dir}/${id}/candidates.json`, 'utf8'))
        res.end(JSON.stringify(all))
      })
      // Use a kit candidate as its map's floor, road wall or placed walls: its pictures are
      // copied to art/pack/<kit>/ (replacing the kit's last pick), pack.json gets the kit and
      // the map takes it (a floor becomes the map's own, the first of its floors), and
      // src/pack.ts is rebuilt.
      handle(server, '/__library/use-kit', ({ kit, cand }) => {
        if (!/^[a-z0-9-]+$/.test(kit) || !/^[\w-]+$/.test(cand)) throw new Error('bad kit or candidate')
        const work = JSON.parse(readFileSync(`art/work/kits/${kit}/candidates.json`, 'utf8'))
        const c = work.candidates[cand], k = work.kit
        if (!c?.parts) throw new Error(`no usable candidate ${cand}`)
        const pack = JSON.parse(readFileSync('art/pack/pack.json', 'utf8'))
        const m = pack.maps[k.map]
        if (!m) throw new Error(`no map ${k.map} in the pack`)
        rmSync(`art/pack/${kit}`, { recursive: true, force: true })
        mkdirSync(`art/pack/${kit}`, { recursive: true })
        const file: Record<string, string> = {}
        for (const [part, f] of Object.entries(c.parts as Record<string, string>)) {
          copyFileSync(`art/work/kits/${kit}/${f}`, `art/pack/${kit}/${f}`)
          file[part] = `${kit}/${f}`
        }
        if (k.kind === 'floor') {
          const tiles = Object.keys(file).sort((a, b) => +a.slice(4) - +b.slice(4)).map((p) => file[p])
          const [pw, ph] = k.panel
          pack.floors[kit] = { from: cand, tile: tiles, ...(pw * ph > 1 ? { panel: [pw, ph] } : {}) }
          m.floor = kit
          m.floors = [kit, ...m.floors.filter((f: string) => f !== kit)]
        } else if (k.kind === 'road') {
          pack.roads[kit] = { from: cand, width: 7, strip: file.strip, corner: file.corner }
          m.road = kit
        } else {
          pack.walls[kit] = { from: cand, h: file.h, v: file.v, node: file.node }
          m.walls = kit
        }
        writeFileSync('art/pack/pack.json', JSON.stringify(pack, null, 1) + '\n')
        return { log: execFileSync('.venv/bin/python', ['-I', 'tools/pack_build.py'], { encoding: 'utf8', timeout: 60_000 }) }
      })
      // The art library's reviews (art/reviews.json, the user's own notes, kept in git): a
      // favorite, or redo with the reasons ticked and a note, per pack picture
      // ("<piece>|<part>|<index>"), and hidden for a candidate the user is done with
      // ("work:<piece>|<candidate>"). An empty review is dropped.
      handle(server, '/__library/review', ({ key, favorite, redo, note, hidden }) => {
        if (typeof key !== 'string' || !key) throw new Error('no picture named')
        const path = 'art/reviews.json'
        const all = existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : {}
        const checks = Array.isArray(redo) ? redo.filter((c: unknown) => typeof c === 'string') : []
        if (!favorite && !checks.length && !note && !hidden) delete all[key]
        else all[key] = { favorite: !!favorite, redo: checks, note: typeof note === 'string' ? note : '', ...(hidden ? { hidden: true } : {}), at: new Date().toISOString() }
        writeFileSync(path, JSON.stringify(all, null, 1) + '\n')
        return { review: all[key] ?? null }
      })
    },
  }
}

export default defineConfig({
  // Relative asset paths, so the build works wherever the package is served from.
  base: './',
  server: { host: true, port: 5173 },
  // main.ts awaits the bridge at the top level.
  build: { target: 'esnext' },
  plugins: [devTools()],
})
