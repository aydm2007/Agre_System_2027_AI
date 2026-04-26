import { render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const serviceCardsList = vi.fn()
const useSettingsMock = vi.fn()
const useFarmContextMock = vi.fn()

vi.mock('../../../api/client', () => ({
  ServiceCards: { list: (...args) => serviceCardsList(...args) },
}))

vi.mock('../../../contexts/SettingsContext', () => ({
  useSettings: () => useSettingsMock(),
}))

vi.mock('../../../api/farmContext', () => ({
  useFarmContext: () => useFarmContextMock(),
}))

vi.mock('../../../utils/errorUtils', () => ({
  extractApiError: (_err, fallback) => fallback,
}))

import { DailyLogSmartCard } from '../DailyLogSmartCard'

const buildCard = (overrides = {}) => ({
  crop: { id: 11, name: 'Tomato' },
  smart_card_stack: [
    {
      card_key: 'execution',
      title: 'التنفيذ',
      order: 0,
      mode_visibility: 'simple_preview',
      status: 'attention',
      metrics: {
        task_id: 8,
        task_name: 'Inspection',
        stage: 'Control',
        planned_count: 1,
        executed_count: 1,
        schedule_status: 'due_today',
        open_variances: 2,
        plan_id: 77,
        plan_name: 'Tomato Plan',
        plan_status: 'active',
        planned_tasks: 4,
        completed_tasks: 3,
        plan_progress_pct: 75,
        budget_total: '500.0000',
        actual_total: '250.0000',
        variance_total: '-250.0000',
        variance_pct: -50,
        matched_locations: 1,
        planned_locations: 2,
      },
      flags: ['budget_overrun'],
      data_source: 'task_contract_snapshot',
      policy: {
        read_only: true,
        shadow_accounting: true,
        cost_display_mode: 'summarized_amounts',
      },
      source_refs: ['activity', 'daily_log', 'crop_plan'],
    },
    {
      card_key: 'materials',
      title: 'المواد',
      order: 1,
      mode_visibility: 'simple_preview',
      status: 'attention',
      metrics: {
        planned_qty: '10.0000',
        actual_qty: '6.0000',
        qty_variance: '-4.0000',
        planned_cost: '100.0000',
        actual_cost: '72.0000',
        cost_variance: '-28.0000',
      },
      flags: [],
      data_source: 'activity_items',
      policy: {
        cost_visibility: 'summarized_amounts',
        full_cost_allowed: false,
      },
      source_refs: ['activity.items', 'crop_plan.recipe'],
    },
    {
      card_key: 'variance',
      title: 'الانحراف',
      order: 2,
      mode_visibility: 'simple_preview',
      status: 'attention',
      metrics: {
        total_alerts: 2,
        open_alerts: 2,
        total_variance: '25.0000',
        latest_alert_at: '2026-03-13T10:00:00Z',
      },
      flags: ['open_variance'],
      data_source: 'variance_alert',
      source_refs: ['variance_alert'],
    },
    {
      card_key: 'control',
      title: 'الرقابة',
      order: 3,
      mode_visibility: 'simple_preview',
      status: 'critical',
      metrics: {
        total_logs: 3,
        critical_logs: 1,
        rejected_logs: 0,
      },
      flags: ['critical_control'],
      data_source: 'daily_log',
      source_refs: ['daily_log'],
    },
    {
      card_key: 'financial_trace',
      title: 'الأثر المالي',
      order: 4,
      mode_visibility: 'simple_preview',
      status: 'ready',
      metrics: {
        entries_count: 4,
        debit_total: '250.0000',
        credit_total: '100.0000',
      },
      flags: [],
      data_source: 'financial_ledger',
      source_refs: ['financial_ledger'],
    },
  ],
  ...overrides,
})

describe('DailyLogSmartCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useFarmContextMock.mockReturnValue({
      selectedFarmId: '1',
    })
    useSettingsMock.mockReturnValue({
      costVisibility: 'summarized_amounts',
      showDailyLogSmartCard: true,
    })
  })

  it('renders the smart card stack in contract order for the current daily log context', async () => {
    serviceCardsList.mockResolvedValueOnce({
      data: [buildCard({ cost_display_mode: 'full_amounts' })],
    })

    render(
      <DailyLogSmartCard
        form={{
          farm: '1',
          crop: '11',
          task: '8',
          date: '2026-03-13',
          locations: ['4'],
        }}
        linkedCropPlan={{ id: 77 }}
      />,
    )

    expect(screen.getByTestId('daily-log-smart-card-loading')).toBeTruthy()

    await waitFor(() =>
      expect(serviceCardsList).toHaveBeenCalledWith({
        farm_id: '1',
        crop_id: '11',
        task_id: '8',
        crop_plan_id: 77,
        date: '2026-03-13',
        location_ids: '4',
      }),
    )

    expect(await screen.findByTestId('daily-log-smart-card')).toBeTruthy()
    expect(screen.getByTestId('daily-log-smart-card-title').textContent).toContain('Tomato')
    expect(screen.getByTestId('daily-log-smart-card-title').textContent).toContain('Inspection')
    expect(screen.getByTestId('daily-log-smart-card-plan-name').textContent).toContain('Tomato Plan')

    const stack = screen.getByTestId('daily-log-smart-card-stack')
    const cards = within(stack).getAllByRole('article')
    expect(cards).toHaveLength(5)
    expect(within(cards[0]).getByText('التنفيذ')).toBeTruthy()
    expect(within(cards[1]).getByText('المواد')).toBeTruthy()
    expect(within(cards[2]).getByText('الانحراف')).toBeTruthy()
    expect(
      screen.getByTestId('daily-log-smart-card-stack-card-metric-materials-planned_cost').textContent,
    ).toContain('100.0000')
    expect(
      screen.getByTestId('daily-log-smart-card-stack-card-policy-execution-shadow_accounting').textContent,
    ).toContain('القيد الظلي محفوظ')
    expect(screen.getByTestId('daily-log-smart-card-stack-card-flag-variance-open_variance')).toBeTruthy()
  })

  it('renders ratios-only smart card metrics without exposing cost line items', async () => {
    serviceCardsList.mockResolvedValueOnce({
      data: [
        buildCard({
          cost_display_mode: 'ratios_only',
          smart_card_stack: [
            {
              card_key: 'execution',
              title: 'التنفيذ',
              order: 0,
              mode_visibility: 'simple_preview',
              status: 'ready',
              metrics: {
                task_name: 'Inspection',
                schedule_status: 'due_today',
                plan_name: 'Tomato Plan',
                plan_status: 'active',
                planned_tasks: 4,
                completed_tasks: 3,
                plan_progress_pct: 75,
                budget_total: '500.0000',
                actual_total: '250.0000',
              },
              flags: [],
              data_source: 'task_contract_snapshot',
              source_refs: ['activity'],
            },
            {
              card_key: 'materials',
              title: 'المواد',
              order: 1,
              mode_visibility: 'simple_preview',
              status: 'ready',
              metrics: {
                planned_qty: '10.0000',
                actual_qty: '6.0000',
                qty_variance: '-4.0000',
                cost_ratio_pct: 72,
              },
              flags: [],
              data_source: 'activity_items',
              source_refs: ['activity.items'],
            },
          ],
        }),
      ],
    })

    render(
      <DailyLogSmartCard
        form={{
          farm: '1',
          crop: '11',
          task: '8',
          date: '2026-03-13',
          locations: ['4'],
        }}
        linkedCropPlan={{ id: 77 }}
      />,
    )

    expect(await screen.findByTestId('daily-log-smart-card')).toBeTruthy()
    expect(screen.getByTestId('daily-log-smart-card-stat-cost').textContent).toContain('50%')
    expect(screen.getByTestId('daily-log-smart-card-plan-budget-policy').textContent).toContain('50%')
    expect(screen.getByTestId('daily-log-smart-card-task-budget-policy')).toBeTruthy()
    expect(
      screen.getByTestId('daily-log-smart-card-stack-card-metric-materials-cost_ratio_pct').textContent,
    ).toContain('72%')
    expect(
      screen.queryByTestId('daily-log-smart-card-stack-card-metric-materials-planned_cost'),
    ).toBeNull()
  })



  it('stays hidden until farm and crop are selected', () => {
    const { container } = render(
      <DailyLogSmartCard
        form={{ farm: '', crop: '', task: '', date: '2026-03-13', locations: [] }}
        linkedCropPlan={null}
      />,
    )

    expect(container.firstChild).toBeNull()
  })

  it('stays hidden when farm policy disables the smart card', () => {
    useSettingsMock.mockReturnValue({
      costVisibility: 'summarized_amounts',
      showDailyLogSmartCard: false,
    })

    const { container } = render(
      <DailyLogSmartCard
        form={{ farm: '1', crop: '11', task: '8', date: '2026-03-13', locations: ['4'] }}
        linkedCropPlan={{ id: 77 }}
      />,
    )

    expect(container.firstChild).toBeNull()
    expect(serviceCardsList).not.toHaveBeenCalled()
  })

  it('renders against the form farm policy when it differs from the selected page farm', async () => {
    useFarmContextMock.mockReturnValue({
      selectedFarmId: '30',
    })
    useSettingsMock.mockReturnValue({
      costVisibility: 'summarized_amounts',
      showDailyLogSmartCard: false,
    })
    serviceCardsList.mockResolvedValueOnce({
      data: [
        buildCard({
          policy_snapshot: {
            show_daily_log_smart_card: true,
          },
        }),
      ],
    })

    render(
      <DailyLogSmartCard
        form={{ farm: '28', crop: '11', task: '8', date: '2026-03-13', locations: ['4'] }}
        linkedCropPlan={{ id: 77 }}
      />,
    )

    expect(await screen.findByTestId('daily-log-smart-card')).toBeTruthy()
    expect(serviceCardsList).toHaveBeenCalledWith({
      farm_id: '28',
      crop_id: '11',
      task_id: '8',
      crop_plan_id: 77,
      date: '2026-03-13',
      location_ids: '4',
    })
  })
})
