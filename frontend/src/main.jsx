import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './app.jsx'
import ErrorBoundary from './components/ErrorBoundary'
import './styles.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { applyArabicEnterpriseShell } from './bootstrap/appShell'

// [AGRI-GUARDIAN] Prevent dev/test chunk drift from stale service workers.
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  if (import.meta.env.PROD) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .catch((err) => console.warn('[PWA] Service Worker registration failed:', err))
    })
  } else {
    navigator.serviceWorker
      .getRegistrations()
      .then((regs) => Promise.all(regs.map((reg) => reg.unregister())))
      .catch((err) => console.warn('[PWA] Failed to unregister service workers in dev:', err))
  }
}

i18n.use(initReactI18next).init({
  lng: 'ar',
  fallbackLng: 'ar',
  interpolation: { escapeValue: false },
  resources: { ar: { translation: {} } },
})

const queryClient = new QueryClient()
applyArabicEnterpriseShell()

createRoot(document.getElementById('root')).render(
  <QueryClientProvider client={queryClient}>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </BrowserRouter>
  </QueryClientProvider>,
)
