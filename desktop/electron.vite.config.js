import { resolve } from 'path'
import { copyFileSync } from 'fs'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'

/**
 * Post-build plugin that copies sidecarRuntime.js to out/main/.
 * electron-vite's externalizeDepsPlugin treats CJS require() of relative
 * modules as external, so sidecarRuntime.js must live alongside index.js.
 */
function copySidecarRuntimePlugin() {
  return {
    name: 'copy-sidecar-runtime',
    closeBundle() {
      const src = resolve(__dirname, 'electron/sidecarRuntime.js')
      const dest = resolve(__dirname, 'out/main/sidecarRuntime.js')
      copyFileSync(src, dest)
    }
  }
}

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin(), copySidecarRuntimePlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'electron/main.js')
        }
      }
    }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'electron/preload.js')
        }
      }
    }
  },
  renderer: {
    root: '.',
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'index.html')
        }
      }
    },
    plugins: [react()]
  }
})
