import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => {
  const configDir = path.dirname(fileURLToPath(import.meta.url))
  const env = loadEnv(mode, configDir, '')
  const disablePwa =
    process.env.VITE_DISABLE_PWA === '1' ||
    env.VITE_DISABLE_PWA === '1' ||
    process.env.PLAYWRIGHT === '1'
  const configuredApiBase = env.VITE_API_BASE || ''
  const proxyTarget =
    env.VITE_PROXY_TARGET ||
    env.VITE_API_PROXY_TARGET ||
    (configuredApiBase.startsWith('http') ? configuredApiBase : 'http://127.0.0.1:8000')
  const defaultOutDir = env.VITE_BUILD_OUT_DIR || 'dist'
  const outDir = resolveWritableOutDir(configDir, defaultOutDir)
  const cacheDir = resolveWritableRuntimeDir(
    configDir,
    process.env.PLAYWRIGHT_VITE_CACHE_DIR ||
      process.env.VITE_CACHE_DIR ||
      env.PLAYWRIGHT_VITE_CACHE_DIR ||
      env.VITE_CACHE_DIR ||
      'node_modules/.vite',
    '.vite-local',
    'cacheDir',
  )

  return {
    cacheDir,
    resolve: {
      dedupe: ['react', 'react-dom', 'react-router-dom'],
    },
    plugins: [
      react(),
      ...(!disablePwa
        ? [VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
        manifest: {
          name: 'Saradud Agri-Guardian',
          short_name: 'Saradud',
          description: 'AgriAsset 2025: Offline-First Farm Management',
          theme_color: '#ffffff',
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png',
            },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
          runtimeCaching: [
            {
              urlPattern: /^\/api\/v1\/lookups\/.*/i,
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'api-lookups-cache',
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 7, // 7 days
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
          ],
        },
      })]
        : []),
    ],
    server: {
      host: true, // يعني 0.0.0.0
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
        '/media': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      outDir,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return undefined
            }
            if (/[\\/]node_modules[\\/](chart\.js|react-chartjs-2)[\\/]/.test(id)) {
              return 'vendor-chartjs'
            }
            if (/[\\/]node_modules[\\/]recharts[\\/]/.test(id)) {
              return 'vendor-recharts'
            }
            if (/[\\/]node_modules[\\/]xlsx[\\/]/.test(id)) {
              return 'vendor-xlsx'
            }
            if (/[\\/]node_modules[\\/]html5-qrcode[\\/]/.test(id)) {
              return 'vendor-qr'
            }
            if (/[\\/]node_modules[\\/](lucide-react|framer-motion|@headlessui)[\\/]/.test(id)) {
              return 'vendor-ui'
            }
            if (/[\\/]node_modules[\\/](date-fns|moment)[\\/]/.test(id)) {
              return 'vendor-date'
            }
            if (/[\\/]node_modules[\\/](axios|dexie|idb-keyval|uuid|jwt-decode)[\\/]/.test(id)) {
              return 'vendor-data'
            }
            return undefined
          },
        },
      },
    },
    preview: {
      port: 4173,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
        '/media': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './vitest.setup.js',
      css: true,
      coverage: {
        reporter: ['text', 'json', 'html'],
      },
    },
  }
})

function resolveWritableOutDir(configDir, preferredOutDir) {
  const preferredAbs = path.resolve(configDir, preferredOutDir)
  const swPath = path.join(preferredAbs, 'sw.js')
  const probePath = path.join(preferredAbs, '.vite_write_probe.tmp')

  try {
    if (!fs.existsSync(preferredAbs)) {
      return preferredOutDir
    }

    // Real write probe for Windows ACL edge cases.
    fs.writeFileSync(probePath, 'ok', { encoding: 'utf8' })
    fs.unlinkSync(probePath)

    if (fs.existsSync(swPath)) {
      const fd = fs.openSync(swPath, 'r+')
      fs.closeSync(fd)
    }
    return preferredOutDir
  } catch {
    const fallback = '.dist-local'
    console.warn(
      `[vite-config] '${preferredOutDir}' is not writable on this machine. Falling back to '${fallback}'.`,
    )
    return fallback
  }
}

function resolveWritableRuntimeDir(configDir, preferredDir, fallbackDir, label) {
  const preferredAbs = path.resolve(configDir, preferredDir)
  const probePath = path.join(preferredAbs, '.vite_write_probe.tmp')

  try {
    fs.mkdirSync(preferredAbs, { recursive: true })
    fs.writeFileSync(probePath, 'ok', { encoding: 'utf8' })
    fs.unlinkSync(probePath)
    return preferredAbs
  } catch {
    const fallbackAbs = path.resolve(configDir, fallbackDir)
    fs.mkdirSync(fallbackAbs, { recursive: true })
    console.warn(
      `[vite-config] '${preferredDir}' is not writable for ${label}. Falling back to '${fallbackDir}'.`,
    )
    return fallbackAbs
  }
}
