/**
 * [AGRI-GUARDIAN] Storybook Stories — ErrorBoundary + OfflineStatusBanner
 */
import ErrorBoundary from '../components/ErrorBoundary.jsx'

// ──────────────────────────────────────────────────────────────────────────────
// ErrorBoundary
// ──────────────────────────────────────────────────────────────────────────────
export default {
  title: 'Core/ErrorBoundary',
  component: ErrorBoundary,
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component: 'حاجز الأخطاء — يلتقط أخطاء React ويعرض واجهة بديلة بدلاً من الانهيار الكامل.',
      },
    },
  },
  tags: ['autodocs'],
}

const ErrorComponent = () => {
  throw new Error('خطأ اختباري — Storybook')
}

export const WithError = {
  render: () => (
    <ErrorBoundary>
      <ErrorComponent />
    </ErrorBoundary>
  ),
}

export const WithoutError = {
  render: () => (
    <ErrorBoundary>
      <div className="p-4 text-emerald-600 font-semibold">
        ✅ لا يوجد خطأ — المكون يعمل بشكل طبيعي
      </div>
    </ErrorBoundary>
  ),
}
