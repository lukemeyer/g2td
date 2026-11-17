import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

/** The browser playtest build (play.html): the game as it is, with its Even Hub SDK
 *  import pointed at src/web/bridge.ts, which draws the page on a canvas and gives
 *  buttons for the glasses' input. `npm run play` serves it; `npm run build:play`
 *  writes dist-play/, a static site. */
const shim = fileURLToPath(new URL('./src/web/bridge.ts', import.meta.url))

export default defineConfig({
  base: './',
  server: { host: true, port: 5174, open: '/play.html' },
  build: { target: 'esnext', outDir: 'dist-play', rollupOptions: { input: 'play.html' } },
  plugins: [{
    name: 'web-bridge',
    enforce: 'pre',
    // Everyone but the stand-in itself (which takes the SDK's event enum) gets the stand-in.
    resolveId: (id, importer) => (id === '@evenrealities/even_hub_sdk' && importer !== shim ? shim : null),
  }],
})
