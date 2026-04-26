import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import { useFarmContext } from '../api/farmContext.jsx'
import { useAuth } from '../auth/AuthContext'
import { canAccessFinanceHubRoutes } from '../auth/modeAccess'
import { useSettings } from '../contexts/SettingsContext.jsx'
import { useOpsRuntime } from '../contexts/OpsRuntimeContext.jsx'
import { useOfflineQueue } from '../offline/OfflineQueueProvider.jsx'

const formatDateTime = (value) => {
  if (!value) return 'لم تتم مزامنة بعد'
  try {
    return new Date(value).toLocaleString('ar-EG', { hour12: false })
  } catch {
    return String(value)
  }
}

const resolveSyncStateLabel = (offlineSignals) => {
  const failedTotal =
    Number(offlineSignals.failedRequests || 0) +
    Number(offlineSignals.failedHarvests || 0) +
    Number(offlineSignals.failedDailyLogs || 0) +
    Number(offlineSignals.failedCustody || 0)
  const queuedTotal =
    Number(offlineSignals.queuedRequests || 0) +
    Number(offlineSignals.queuedHarvests || 0) +
    Number(offlineSignals.queuedDailyLogs || 0) +
    Number(offlineSignals.queuedCustody || 0)

  if (failedTotal > 0) {
    return {
      label: 'يوجد تعارض',
      tone: 'rose',
      helper: `${failedTotal} عناصر تحتاج معالجة أو إعادة محاولة.`,
    }
  }
  if (queuedTotal > 0) {
    return {
      label: 'بانتظار الإرسال',
      tone: 'amber',
      helper: `${queuedTotal} عناصر محفوظة محليًا وستُرسل عند اكتمال المزامنة.`,
    }
  }
  return {
    label: 'جاهز للمزامنة',
    tone: 'emerald',
    helper: 'لا توجد عناصر معلّقة في الطوابير التشغيلية.',
  }
}

const toneClasses = {
  emerald:
    'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200',
  amber:
    'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200',
  rose:
    'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200',
  sky: 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200',
}

function HubCard({
  title,
  description,
  statusLabel,
  helper,
  primaryValue,
  secondaryValue,
  to,
  ctaLabel,
  state,
  testId,
}) {
  return (
    <article
      data-testid={testId}
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800"
    >
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">{title}</h2>
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{description}</p>
          </div>
          <span
            className={`rounded-full border px-3 py-1 text-xs font-semibold ${toneClasses.sky}`}
          >
            {statusLabel}
          </span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-900/40">
            <div className="text-xs text-slate-500 dark:text-slate-400">الحالة التشغيلية</div>
            <div className="mt-1 font-semibold text-slate-900 dark:text-white">{primaryValue}</div>
          </div>
          <div className="rounded-xl bg-slate-50 px-3 py-2 dark:bg-slate-900/40">
            <div className="text-xs text-slate-500 dark:text-slate-400">آخر مزامنة</div>
            <div className="mt-1 font-semibold text-slate-900 dark:text-white">
              {secondaryValue}
            </div>
          </div>
        </div>
        <p className="text-xs leading-6 text-slate-500 dark:text-slate-400">{helper}</p>
        <div className="pt-1">
          <Link
            to={to}
            state={state}
            data-testid={`${testId}-cta`}
            className="inline-flex items-center rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary/90"
          >
            {ctaLabel}
          </Link>
        </div>
      </div>
    </article>
  )
}

export default function SimpleOperationsHub() {
  const { farms, selectedFarmId, selectFarm } = useFarmContext()
  const {
    modeLabel,
    isStrictMode,
    showDailyLogSmartCard,
    remoteSite,
    weeklyRemoteReviewRequired,
  } = useSettings()
  const auth = useAuth()
  const offlineQueue = useOfflineQueue()
  const { topAlerts, summary, localOfflineSignals } = useOpsRuntime()

  const effectiveOfflineSignals = localOfflineSignals || offlineQueue
  const syncState = useMemo(
    () => resolveSyncStateLabel(effectiveOfflineSignals),
    [effectiveOfflineSignals],
  )
  const activeAlerts = Array.isArray(topAlerts) ? topAlerts : []
  const financialPostureVisible = canAccessFinanceHubRoutes({
    isAdmin: auth.isAdmin,
    isSuperuser: auth.isSuperuser,
    hasFarmRole: auth.hasFarmRole,
  })

  const queueSummary = useMemo(
    () =>
      Number(effectiveOfflineSignals.queuedDailyLogs || 0) +
      Number(effectiveOfflineSignals.queuedHarvests || 0) +
      Number(effectiveOfflineSignals.queuedCustody || 0),
    [effectiveOfflineSignals],
  )

  const lastSyncLabel = formatDateTime(effectiveOfflineSignals.lastSync || offlineQueue.lastSync)

  const cards = [
    {
      key: 'daily-log',
      title: 'السجل اليومي',
      description:
        'ابدأ التنفيذ اليومي من هنا. هذا هو مسار الإدخال الفني canonical في الوضع البسيط.',
      statusLabel: 'تنفيذ',
      primaryValue: queueSummary > 0 ? `${queueSummary} عناصر مرتبطة بالتنفيذ` : 'جاهز للإدخال',
      secondaryValue: lastSyncLabel,
      helper: showDailyLogSmartCard
        ? 'البطاقات الذكية مفعّلة، والانحرافات والرقابة تُحتسب من نفس سلسلة الحقيقة.'
        : 'الإدخال الفني متاح حتى عند إخفاء سياق البطاقة الذكية وفق سياسة المزرعة.',
      to: '/daily-log',
      ctaLabel: 'فتح السجل اليومي',
    },
    {
      key: 'harvest',
      title: 'إدخال الحصاد',
      description:
        'إذا كان النشاط حصادًا فاستخدم هذا المسار السريع، وهو يوجّهك إلى نفس السجل اليومي دون إنشاء محرك ثانٍ.',
      statusLabel: 'حصاد',
      primaryValue:
        Number(effectiveOfflineSignals.queuedHarvests || 0) > 0
          ? `${effectiveOfflineSignals.queuedHarvests} حصاد بانتظار الإرسال`
          : 'لا توجد حصادات معلّقة',
      secondaryValue: lastSyncLabel,
      helper: 'يظل إدخال الحصاد جزءًا من دورة التنفيذ اليومية، وليس جزءًا من شاشة التقارير.',
      to: '/daily-log/harvest',
      ctaLabel: 'فتح إدخال الحصاد',
    },
    {
      key: 'custody',
      title: 'عهدة المشرف',
      description:
        'راجع الرصيد المقبول والعهد الواردة وحالة الإرجاع قبل صرف المواد داخل السجل اليومي.',
      statusLabel: 'عهدة',
      primaryValue:
        Number(effectiveOfflineSignals.queuedCustody || 0) > 0
          ? `${effectiveOfflineSignals.queuedCustody} عناصر عهدة بانتظار الإرسال`
          : 'الرصيد المقبول هو المصدر الفني المعتمد',
      secondaryValue: lastSyncLabel,
      helper:
        'في SIMPLE لا تظهر authoring مخزنية موسعة؛ فقط الرصيد المقبول، والقبول، والرفض، والإرجاع، وحالة الطابور.',
      to: '/inventory/custody',
      ctaLabel: 'فتح عهدة المشرف',
    },
    {
      key: 'variance',
      title: 'الانحرافات والتنبيهات',
      description:
        'تابع التنبيهات التشغيلية وما يحتاج تدخّلًا قبل أن يتحول إلى عبء رقابي أو يتطلب مسارًا صارمًا.',
      statusLabel: activeAlerts.length > 0 ? 'رقابة' : 'لا توجد تنبيهات حرجة',
      primaryValue:
        activeAlerts.length > 0 ? `${activeAlerts.length} تنبيهات تشغيلية مفتوحة` : 'الوضع مستقر',
      secondaryValue: lastSyncLabel,
      helper:
        activeAlerts[0]?.title ||
        'تظهر هنا أهم الإشارات التشغيلية والرقابية من نفس الحقيقة التشغيلية دون فتح authoring مالي.',
      to: '/variance-alerts',
      ctaLabel: 'فتح الانحرافات',
    },
    {
      key: 'reports',
      title: 'التقارير',
      description:
        'التقارير في SIMPLE سطح متابعة للتنفيذ نفسه: ما نُفذ، ما حُصد، ما صُرف من العهدة، وما يحتاج تدخلًا.',
      statusLabel: 'قراءة وتحليل',
      primaryValue:
        Number(summary?.open_alerts || 0) > 0
          ? `${summary.open_alerts} إشارات مفتوحة في الملخص التشغيلي`
          : 'ملخص تنفيذي جاهز',
      secondaryValue: lastSyncLabel,
      helper:
        'شاشة التقارير للقراءة والتوليد فقط. يمكنك فتح presets ثابتة دون أن تتحول إلى شاشة إدخال.',
      to: '/reports',
      state: { simplePreset: 'daily_execution' },
      ctaLabel: 'فتح التقارير',
    },
    {
      key: 'financial-posture',
      title: 'الوضع المالي التوافقي',
      description:
        'اعرض الظل المالي والالتزامات الجاهزة للمراجعة دون فتح شجرة authoring مالية صريحة داخل SIMPLE.',
      statusLabel: 'وضع مالي توافقي',
      primaryValue:
        Number(summary?.exceptions_count || 0) > 0
          ? `${summary.exceptions_count} استثناءات تحتاج متابعة`
          : 'لا توجد استثناءات ظاهرة',
      secondaryValue: lastSyncLabel,
      helper:
        'هذا السطح يعرض posture فقط: ظل دفتر، payable posture، وحالة الاستثناءات، دون posting أو ledger authoring.',
      to: financialPostureVisible ? '/finance' : '/reports',
      state: financialPostureVisible ? undefined : { simplePreset: 'financial_posture' },
      ctaLabel: financialPostureVisible ? 'فتح الوضع المالي' : 'فتح التقرير التوافقي',
    },
  ]

  return (
    <div
      dir="rtl"
      data-testid="simple-operations-hub"
      className="space-y-6 p-4 min-h-screen bg-gray-50 dark:bg-slate-900"
    >
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div>
              <h1
                data-testid="simple-hub-title"
                className="text-2xl font-bold text-slate-900 dark:text-white"
              >
                مركز العمليات للمود البسيط
              </h1>
              <p className="mt-2 text-sm leading-7 text-slate-600 dark:text-slate-300">
                هذا المركز يجمع التنفيذ، والحصاد، والعهدة، والرقابة، والتقارير، والوضع المالي
                التوافقي في رحلة واحدة متماسكة. لا يفتح هذا السطح أي authoring مالي جديد، بل
                يعرض نفس الحقيقة التشغيلية بترتيب أوضح للمستخدم.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span
                data-testid="simple-hub-mode-badge"
                className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200"
              >
                الوضع الحالي: {modeLabel}
              </span>
              <span
                data-testid="simple-hub-sync-badge"
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${toneClasses[syncState.tone]}`}
              >
                {syncState.label}
              </span>
              {!isStrictMode && activeAlerts.length > 0 ? (
                <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
                  يتطلب مسارًا صارمًا عند تجاوز العتبات أو ظهور استثناءات حرجة
                </span>
              ) : null}
              {remoteSite ? (
                <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200">
                  موقع جغرافي بعيد
                </span>
              ) : null}
              {weeklyRemoteReviewRequired ? (
                <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
                  التنفيذ اليومي مستمر، لكن بعض مسارات STRICT المالية قد تُحجب حتى تسجيل المراجعة الأسبوعية
                </span>
              ) : null}
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="text-slate-600 dark:text-slate-300">المزرعة</span>
              <select
                data-testid="simple-hub-farm-select"
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                value={selectedFarmId || ''}
                onChange={(event) => selectFarm(event.target.value)}
              >
                {farms.map((farm) => (
                  <option key={farm.id} value={farm.id}>
                    {farm.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/40">
              <div className="text-xs text-slate-500 dark:text-slate-400">آخر مزامنة تشغيلية</div>
              <div className="mt-1 font-semibold text-slate-900 dark:text-white">
                {lastSyncLabel}
              </div>
              <div className="mt-2 text-xs leading-6 text-slate-500 dark:text-slate-400">
                {syncState.helper}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        data-testid="simple-hub-cards"
        className="grid gap-4 xl:grid-cols-2"
      >
        {cards.map((card) => (
          <HubCard
            key={card.key}
            testId={`simple-hub-card-${card.key}`}
            title={card.title}
            description={card.description}
            statusLabel={card.statusLabel}
            primaryValue={card.primaryValue}
            secondaryValue={card.secondaryValue}
            helper={card.helper}
            to={card.to}
            state={card.state}
            ctaLabel={card.ctaLabel}
          />
        ))}
      </section>
    </div>
  )
}
