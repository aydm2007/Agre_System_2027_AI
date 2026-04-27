/* eslint-env node */
import { defineConfig, devices } from '@playwright/test'
import path from 'path'
import fs from 'fs'

/**
 * Playwright Configuration — Best Practices Edition
 * @see https://playwright.dev/docs/test-configuration
 *
 * Architecture:
 *   1. 'setup' project authenticates ONCE and saves storageState.
 *   2. 'chromium' project depends on 'setup' → all tests run pre-authenticated.
 *   3. Windows stability: workers=1 as per AGENTS.md §Frontend Contract.
 */
const externalBaseUrl = process.env.E2E_BASE_URL
const hasExternalBaseUrl = Boolean(
  externalBaseUrl &&
  !externalBaseUrl.includes('localhost') &&
  !externalBaseUrl.includes('127.0.0.1'),
)
const apiBase = process.env.E2E_API_BASE || 'http://127.0.0.1:8000'
const apiServerRoot = apiBase.replace(/\/api\/?$/, '')
const frontendBaseUrl = externalBaseUrl || process.env.VITE_API_BASE || 'http://127.0.0.1:5173'
const hasExternalApiBase = Boolean(
  apiServerRoot &&
  !apiServerRoot.includes('localhost') &&
  !apiServerRoot.includes('127.0.0.1'),
)
const frontendServerUrl = new URL(frontendBaseUrl)
const frontendServerOrigin = frontendServerUrl.origin
const frontendServerHost = frontendServerUrl.hostname
const frontendServerPort =
  Number(frontendServerUrl.port || (frontendServerUrl.protocol === 'https:' ? '443' : '80'))
const backendServerUrl = new URL(apiServerRoot)
const backendServerOrigin = backendServerUrl.origin
const backendServerHost = backendServerUrl.hostname
const backendServerPort =
  Number(backendServerUrl.port || (backendServerUrl.protocol === 'https:' ? '443' : '80'))
const reuseExistingBackendServer =
  !process.env.CI && process.env.PLAYWRIGHT_REUSE_EXISTING_BACKEND !== '0'
const reuseExistingFrontendServer =
  !process.env.CI && process.env.PLAYWRIGHT_REUSE_EXISTING_FRONTEND !== '0'
const repoRoot = path.resolve(import.meta.dirname, '..')
const backendPython = process.env.PLAYWRIGHT_BACKEND_PYTHON || process.env.PYTHON || 'python'
const windowsDbEnvScript = path.join(repoRoot, 'scripts', 'windows', 'Resolve-BackendDbEnv.ps1')
const backendStartupCommand =
  process.platform === 'win32'
    ? `powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '${windowsDbEnvScript}'; ${backendPython} backend/manage.py migrate --noinput; ${backendPython} backend/manage.py runserver ${backendServerHost}:${backendServerPort} --noreload }"`
    : `${backendPython} backend/manage.py migrate --noinput && ${backendPython} backend/manage.py runserver ${backendServerHost}:${backendServerPort} --noreload`

const ARTIFACT_ROOT = process.env.PLAYWRIGHT_ARTIFACT_ROOT
  ? path.resolve(process.env.PLAYWRIGHT_ARTIFACT_ROOT)
  : path.join(import.meta.dirname, '.pw-results')
const VITE_CACHE_ROOT = process.env.PLAYWRIGHT_VITE_CACHE_DIR
  ? path.resolve(process.env.PLAYWRIGHT_VITE_CACHE_DIR)
  : path.join(import.meta.dirname, '.vite-playwright-cache')
const WEB_SERVER_TIMEOUT_MS = 300 * 1000

const STORAGE_STATE = path.join(ARTIFACT_ROOT, '.auth', 'user.json')

fs.mkdirSync(ARTIFACT_ROOT, { recursive: true })
fs.mkdirSync(VITE_CACHE_ROOT, { recursive: true })

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: path.join(ARTIFACT_ROOT, 'test-results'),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  /* AGENTS.md: --workers=1 on Windows/local */
  workers: 1,
  reporter: [['html', { outputFolder: path.join(ARTIFACT_ROOT, 'playwright-report'), open: 'never' }]],
  use: {
    baseURL: frontendBaseUrl,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // [ZENITH 11.5] Sovereign Silent Protocol: Headless by default
    headless: process.env.HEADED !== 'true',
    serviceWorkers: 'block',
  },

  projects: [
    /* --- Auth Setup Project (runs first) --- */
    {
      name: 'setup',
      testMatch: /auth\.setup\.js/,
    },
    /* --- Main Test Project (depends on setup) --- */
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: STORAGE_STATE,
      },
      dependencies: ['setup'],
      testIgnore: /auth\.setup\.js/,
    },
  ],

  webServer: hasExternalBaseUrl
    ? undefined
    : [
        ...(!hasExternalApiBase
          ? [
              {
                command: backendStartupCommand,
                cwd: repoRoot,
                env: {
                  ...process.env,
                  DJANGO_DEBUG: process.env.DJANGO_DEBUG || 'True',
                  DJANGO_SECURE_SSL_REDIRECT: 'False',
                  DJANGO_ALLOWED_HOSTS:
                    process.env.DJANGO_ALLOWED_HOSTS ||
                    `localhost,127.0.0.1,0.0.0.0,${backendServerHost},${frontendServerHost}`,
                },
                url: `${backendServerOrigin}/api/health/`,
                reuseExistingServer: reuseExistingBackendServer,
                timeout: WEB_SERVER_TIMEOUT_MS,
              },
            ]
          : []),
        {
          command: `npm run dev -- --host ${frontendServerHost} --port ${frontendServerPort}`,
          cwd: import.meta.dirname,
          env: {
            ...process.env,
            PLAYWRIGHT_VITE_CACHE_DIR: VITE_CACHE_ROOT,
            VITE_API_BASE: '/api',
            VITE_PROXY_TARGET: apiServerRoot,
            VITE_DISABLE_PWA: '1',
          },
          url: frontendServerOrigin,
          reuseExistingServer: reuseExistingFrontendServer,
          timeout: WEB_SERVER_TIMEOUT_MS,
        },
      ],
})
