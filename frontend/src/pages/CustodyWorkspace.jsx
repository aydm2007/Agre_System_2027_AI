import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { CustodyTransfers, Farms, Items, Locations, Supervisors } from '../api/client'
import { useFarmContext } from '../api/farmContext.jsx'
import { useAuth } from '../auth/AuthContext'
import { useSettings } from '../contexts/SettingsContext.jsx'
import { useOfflineQueue } from '../offline/OfflineQueueProvider.jsx'
import { resolveDisplayName } from '../utils/displayName'

const STATUS_LABELS = {
  draft: 'مسودة',
  issued_pending_acceptance: 'قيد قبول العهدة',
  accepted: 'مقبولة',
  partially_consumed: 'مستهلكة جزئيًا',
  returned: 'مرجعة',
  reconciled: 'مسوّاة',
  rejected: 'مرفوضة',
  expired_review: 'بانتظار مراجعة',
}

const formatNumber = (value) => {
  const number = Number(value ?? 0)
  if (!Number.isFinite(number)) return '0'
  return number.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  })
}

const formatDateTime = (value) => {
  if (!value) return 'غير معروف'
  try {
    return new Date(value).toLocaleString('ar-EG', { hour12: false })
  } catch {
    return value
  }
}

export default function CustodyWorkspace() {
  const navigate = useNavigate()
  const location = useLocation()
  const { selectedFarmId, selectFarm } = useFarmContext()
  const { isAdmin, isSuperuser, hasFarmRole } = useAuth()
  const { isStrictMode, modeLabel } = useSettings()
  const { queuedCustody, failedCustody, lastSync } = useOfflineQueue()

  const [farms, setFarms] = useState([])
  const [supervisors, setSupervisors] = useState([])
  const [items, setItems] = useState([])
  const [locations, setLocations] = useState([])
  const [_loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [selectedSupervisorId, setSelectedSupervisorId] = useState('')
  const [balances, setBalances] = useState([])
  const [transfers, setTransfers] = useState([])
  const [issueForm, setIssueForm] = useState({
    supervisor_id: '',
    item_id: '',
    from_location_id: '',
    qty: '',
    batch_number: '',
    note: '',
    allow_top_up: false,
  })

  const canIssue = useMemo(
    () => isStrictMode && (isAdmin || isSuperuser || hasFarmRole?.('storekeeper') || hasFarmRole?.('farm_accountant')),
    [hasFarmRole, isAdmin, isStrictMode, isSuperuser],
  )

  const loadWorkspace = useCallback(async () => {
    if (!selectedFarmId) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    try {
      const [farmsRes, supervisorsRes, itemsRes, locationsRes] = await Promise.all([
        Farms.list(),
        Supervisors.list({ farm_id: selectedFarmId }),
        Items.list({ exclude_group: 'Produce' }),
        Locations.list({ farm_id: selectedFarmId }),
      ])
      const nextFarms = farmsRes.data?.results ?? farmsRes.data ?? []
      const nextSupervisors = supervisorsRes.data?.results ?? supervisorsRes.data ?? []
      const nextItems = itemsRes.data?.results ?? itemsRes.data ?? []
      const nextLocations = locationsRes.data?.results ?? locationsRes.data ?? []
      setFarms(Array.isArray(nextFarms) ? nextFarms : [])
      setSupervisors(Array.isArray(nextSupervisors) ? nextSupervisors : [])
      setItems(Array.isArray(nextItems) ? nextItems : [])
      setLocations(Array.isArray(nextLocations) ? nextLocations : [])

      const nextSupervisorId =
        selectedSupervisorId ||
        issueForm.supervisor_id ||
        String(nextSupervisors[0]?.id || '')
      setSelectedSupervisorId(nextSupervisorId)
      setIssueForm((prev) => ({ ...prev, supervisor_id: nextSupervisorId }))
    } catch (err) {
      console.error('Failed to load custody workspace', err)
      setError('تعذر تحميل بيانات عهدة المشرف. تحقق من المزرعة المحددة ثم أعد المحاولة.')
    } finally {
      setLoading(false)
    }
  }, [issueForm.supervisor_id, selectedFarmId, selectedSupervisorId])

  const loadBalances = useCallback(async () => {
    if (!selectedFarmId || !selectedSupervisorId) {
      setBalances([])
      setTransfers([])
      return
    }
    try {
      const { data } = await CustodyTransfers.balance({
        farm_id: selectedFarmId,
        supervisor_id: selectedSupervisorId,
      })
      setBalances(Array.isArray(data?.balances) ? data.balances : [])
      setTransfers(Array.isArray(data?.transfers) ? data.transfers : [])
    } catch (err) {
      console.error('Failed to load custody balance', err)
      setError('تعذر تحميل أرصدة العهدة أو الحركات المرتبطة بها.')
    }
  }, [selectedFarmId, selectedSupervisorId])

  useEffect(() => {
    void loadWorkspace()
  }, [loadWorkspace])

  useEffect(() => {
    void loadBalances()
  }, [loadBalances])

  const warehouseLocations = useMemo(
    () =>
      locations.filter((location) =>
        ['warehouse', 'input', 'store', 'transit'].includes(String(location.type || '').toLowerCase()),
      ),
    [locations],
  )

  const handleIssue = async (event) => {
    event.preventDefault()
    if (!selectedFarmId) return
    setWorking(true)
    setError('')
    setMessage('')
    try {
      await CustodyTransfers.issue({
        farm_id: Number(selectedFarmId),
        supervisor_id: Number(issueForm.supervisor_id),
        item_id: Number(issueForm.item_id),
        from_location_id: Number(issueForm.from_location_id),
        qty: issueForm.qty,
        batch_number: issueForm.batch_number,
        note: issueForm.note,
        allow_top_up: issueForm.allow_top_up,
      })
      setMessage('تم إصدار العهدة بنجاح. يجب على المشرف قبولها قبل استخدامها في الإنجاز اليومي.')
      setIssueForm((prev) => ({
        ...prev,
        item_id: '',
        from_location_id: '',
        qty: '',
        batch_number: '',
        note: '',
        allow_top_up: false,
      }))
      await loadBalances()
    } catch (err) {
      console.error('Failed to issue custody transfer', err)
      setError(
        err?.response?.data?.qty?.[0] ||
          err?.response?.data?.detail ||
          'تعذر إصدار العهدة. تحقق من الرصيد وسياسة التزويد الإضافي.',
      )
    } finally {
      setWorking(false)
    }
  }

  const runTransition = async (transferId, actionName) => {
    setWorking(true)
    setError('')
    setMessage('')
    try {
      if (actionName === 'accept') {
        await CustodyTransfers.accept(transferId, {})
        setMessage('تم قبول العهدة، وأصبحت الآن مصدر الصرف الفني المعتمد للمشرف.')
      } else if (actionName === 'reject') {
        await CustodyTransfers.reject(transferId, {})
        setMessage('تم رفض العهدة وإعادتها إلى مسار المراجعة.')
      } else if (actionName === 'return') {
        await CustodyTransfers.returnTransfer(transferId, {})
        setMessage('تم تسجيل إرجاع من العهدة بنجاح.')
      }
      await loadBalances()
    } catch (err) {
      console.error(`Failed to ${actionName} custody transfer`, err)
      setError('تعذر تنفيذ الإجراء على العهدة. راجع الرصيد والحالة الحالية ثم أعد المحاولة.')
    } finally {
      setWorking(false)
    }
  }

  const summaryCards = [
    {
      label: 'رصيد العهدة المقبول',
      value: balances.length,
      helper: 'أصناف متاحة فعليًا للصرف الفني من العهدة فقط.',
    },
    {
      label: 'عهد قيد القبول أو الإرجاع',
      value: transfers.filter((transfer) =>
        ['issued_pending_acceptance', 'accepted', 'partially_consumed', 'expired_review'].includes(
          transfer.status,
        ),
      ).length,
      helper: 'هذه الحركات تحتاج قبولًا أو تسويةً أو إرجاعًا قبل صرف جديد من نفس الصنف.',
    },
    {
      label: 'طابور العهدة دون اتصال',
      value: queuedCustody,
      helper: failedCustody > 0 ? `فشل ${failedCustody} عناصر ويجب مراجعتها.` : 'لا توجد عناصر فاشلة حاليًا.',
    },
  ]

  return (
    <div
      dir="rtl"
      data-testid="custody-workspace-page"
      className="space-y-6 p-4 min-h-screen bg-gray-50 dark:bg-slate-900"
    >
      <section className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <h1 data-testid="custody-page-title" className="text-2xl font-bold text-gray-900 dark:text-white">مساحة عهدة المشرف</h1>
            <p className="text-sm text-gray-600 dark:text-slate-300">
              هذه الواجهة توحد إصدار العهدة وقبولها وإرجاعها وربطها بالإنجاز اليومي دون فتح محرك مخزون موازٍ.
            </p>
            <div
              data-testid="custody-mode-badge"
              className="inline-flex w-fit rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-200"
            >
              الوضع الحالي: {modeLabel}
            </div>
            {!isStrictMode ? (
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  data-testid="custody-open-daily-log-cta"
                  onClick={() => navigate('/daily-log', { state: { source: 'custody-workspace' } })}
                  className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary/90"
                >
                  استخدم هذه المواد في السجل اليومي
                </button>
                <button
                  type="button"
                  data-testid="custody-open-reports-cta"
                  onClick={() =>
                    navigate('/reports', {
                      state: { source: 'custody-workspace', simplePreset: 'custody_materials' },
                    })
                  }
                  className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  متابعة العهدة في التقارير
                </button>
              </div>
            ) : null}
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="text-gray-600 dark:text-slate-300">المزرعة</span>
              <select
                data-testid="custody-farm-select"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={selectedFarmId || ''}
                onChange={(event) => selectFarm(event.target.value)}
              >
                {(farms || []).map((farm) => (
                  <option key={farm.id} value={farm.id}>
                    {farm.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-gray-600 dark:text-slate-300">المشرف</span>
              <select
                data-testid="custody-supervisor-select"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={selectedSupervisorId}
                onChange={(event) => {
                  setSelectedSupervisorId(event.target.value)
                  setIssueForm((prev) => ({ ...prev, supervisor_id: event.target.value }))
                }}
              >
                {(supervisors || []).map((supervisor) => (
                  <option key={supervisor.id} value={supervisor.id}>
                    {resolveDisplayName(supervisor)}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div
          data-testid="custody-policy-banner"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100"
        >
          في المود البسيط تظهر العهدة كمصدر صرف فني فقط، بينما يظل الإصدار الموسع والتتبع الكامل ظاهرين بوضوح أكبر في المود الصارم. آخر مزامنة لطابور العهدة: {lastSync ? formatDateTime(lastSync) : 'لم تتم مزامنة بعد'}.
        </div>

        {!isStrictMode && location.state?.source === 'daily-log' ? (
          <div
            data-testid="custody-daily-log-context-banner"
            className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200"
          >
            تم فتح العهدة من السجل اليومي. استخدم الرصيد المقبول فقط، ثم ارجع إلى التنفيذ اليومي
            عند جاهزية المواد للصرف الفني.
          </div>
        ) : null}

        {message ? (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200">
            {message}
          </div>
        ) : null}
        {error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-200">
            {error}
          </div>
        ) : null}

        <div className="grid gap-3 md:grid-cols-3">
          {summaryCards.map((card) => (
            <div
              key={card.label}
              data-testid={`custody-summary-card-${summaryCards.indexOf(card)}`}
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900/40"
            >
              <div className="text-sm font-semibold text-slate-700 dark:text-slate-200">{card.label}</div>
              <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{card.value}</div>
              <div className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">{card.helper}</div>
            </div>
          ))}
        </div>
      </section>

      {canIssue ? (
        <section
          data-testid="custody-issue-section"
          className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm space-y-4"
        >
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">إصدار عهدة جديدة</h2>
            <p className="text-sm text-gray-500 dark:text-slate-400">
              يستخدم هذا النموذج نفس service layer الحالية ويصدر حركة إلى موقع `In-Transit` حتى يقبلها المشرف.
            </p>
          </div>
          <form className="grid gap-3 md:grid-cols-2 xl:grid-cols-4" onSubmit={handleIssue}>
            <label className="space-y-1 text-sm">
              <span className="text-gray-600 dark:text-slate-300">الصنف</span>
              <select
                data-testid="custody-item-select"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={issueForm.item_id}
                onChange={(event) => setIssueForm((prev) => ({ ...prev, item_id: event.target.value }))}
                required
              >
                <option value="">اختر الصنف</option>
                {items.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-gray-600 dark:text-slate-300">من المخزن</span>
              <select
                data-testid="custody-location-select"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={issueForm.from_location_id}
                onChange={(event) =>
                  setIssueForm((prev) => ({ ...prev, from_location_id: event.target.value }))
                }
                required
              >
                <option value="">اختر موقع الصرف</option>
                {warehouseLocations.map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-gray-600 dark:text-slate-300">الكمية</span>
              <input
                type="number"
                min="0.001"
                step="0.001"
                data-testid="custody-qty-input"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={issueForm.qty}
                onChange={(event) => setIssueForm((prev) => ({ ...prev, qty: event.target.value }))}
                required
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-gray-600 dark:text-slate-300">رقم الدفعة</span>
              <input
                type="text"
                data-testid="custody-batch-input"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={issueForm.batch_number}
                onChange={(event) =>
                  setIssueForm((prev) => ({ ...prev, batch_number: event.target.value }))
                }
              />
            </label>
            <label className="space-y-1 text-sm md:col-span-2 xl:col-span-3">
              <span className="text-gray-600 dark:text-slate-300">ملاحظة الإصدار</span>
              <input
                type="text"
                data-testid="custody-note-input"
                className="w-full rounded-lg border border-gray-300 dark:border-slate-600 px-3 py-2 bg-white dark:bg-slate-700 dark:text-white"
                value={issueForm.note}
                onChange={(event) => setIssueForm((prev) => ({ ...prev, note: event.target.value }))}
                placeholder="مثال: تسميد مانجو - قطاع المانجو الشرقي"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-200">
              <input
                type="checkbox"
                checked={issueForm.allow_top_up}
                onChange={(event) =>
                  setIssueForm((prev) => ({ ...prev, allow_top_up: event.target.checked }))
                }
              />
              السماح بالتزويد الإضافي المحكوم فقط عند وجود رصيد سابق
            </label>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={working}
                className="w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
              >
                إصدار العهدة
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-2">
        <div
          data-testid="custody-balances-section"
          className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm space-y-4"
        >
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">الرصيد المقبول</h2>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              هذا هو المصدر الفني المعتمد للصرف داخل السجل اليومي.
            </span>
          </div>
          {!balances.length ? (
            <div className="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-600 dark:text-slate-400">
              لا توجد أرصدة عهدة مقبولة حاليًا لهذا المشرف.
            </div>
          ) : (
            <div className="space-y-3">
              {balances.map((balance) => (
                <div key={balance.item_id} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-900/40">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900 dark:text-white">{balance.item_name}</div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        وحدة الصرف الحالية: {balance.uom || 'غير محددة'}
                      </div>
                    </div>
                    <div className="text-lg font-bold text-emerald-700 dark:text-emerald-300">
                      {formatNumber(balance.qty)} {balance.uom || ''}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div
          data-testid="custody-transfers-section"
          className="rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-6 shadow-sm space-y-4"
        >
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">حركات العهدة</h2>
            <span className="text-xs text-slate-500 dark:text-slate-400">قبول / رفض / إرجاع / تتبع</span>
          </div>
          {!transfers.length ? (
            <div className="rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 dark:border-slate-600 dark:text-slate-400">
              لا توجد حركات عهدة مسجلة لهذا المشرف في المزرعة المحددة.
            </div>
          ) : (
            <div className="space-y-3">
              {transfers.map((transfer) => {
                const canAccept = transfer.status === 'issued_pending_acceptance'
                const canReject = transfer.status === 'issued_pending_acceptance'
                const canReturn =
                  transfer.status === 'accepted' || transfer.status === 'partially_consumed'
                return (
                  <div key={transfer.id} className="rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-700">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-1">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {transfer.item_name}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          المصدر: {transfer.source_location_name} • الحالة: {STATUS_LABELS[transfer.status] || transfer.status}
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          صادر: {formatNumber(transfer.issued_qty)} • مقبول: {formatNumber(transfer.accepted_qty)} • مرجع: {formatNumber(transfer.returned_qty)}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
                          onClick={() => runTransition(transfer.id, 'accept')}
                          disabled={!canAccept || working}
                        >
                          قبول العهدة
                        </button>
                        <button
                          type="button"
                          className="rounded-lg border border-amber-300 px-3 py-1 text-xs font-semibold text-amber-700 hover:bg-amber-50 disabled:opacity-50 dark:border-amber-500/40 dark:text-amber-200 dark:hover:bg-amber-500/10"
                          onClick={() => runTransition(transfer.id, 'reject')}
                          disabled={!canReject || working}
                        >
                          رفض
                        </button>
                        <button
                          type="button"
                          className="rounded-lg border border-emerald-300 px-3 py-1 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-50 dark:border-emerald-500/40 dark:text-emerald-200 dark:hover:bg-emerald-500/10"
                          onClick={() => runTransition(transfer.id, 'return')}
                          disabled={!canReturn || working}
                        >
                          إرجاع
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
