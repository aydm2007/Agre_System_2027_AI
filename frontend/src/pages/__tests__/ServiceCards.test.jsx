import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const farmsList = vi.fn()
const serviceCardsList = vi.fn()
const toast = vi.fn()

vi.mock('../../api/client', () => ({
  Farms: { list: (...args) => farmsList(...args) },
  ServiceCards: { list: (...args) => serviceCardsList(...args) },
}))

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'auditor' } }),
}))

vi.mock('../../components/ToastProvider', () => ({
  useToast: () => Object.assign(toast, { error: vi.fn() }),
}))

vi.mock('../../stories/Header', () => ({
  Header: () => <div data-testid="header" />,
}))

import ServiceCards from '../ServiceCards'

describe('ServiceCards page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders integrated smart-card sections from canonical payload', async () => {
    farmsList.mockResolvedValueOnce({
      data: { results: [{ id: 7, name: 'Farm Seven' }] },
    })
    serviceCardsList.mockResolvedValueOnce({
      data: [
        {
          crop: { id: 1, name: 'Tomato' },
          metrics: {
            total: 6,
            machinery: 2,
            well: 1,
            area: 1,
            tree_count: 0,
            asset_types: ['tractor'],
            asset_tasks_missing_type: 0,
          },
          cost_display_mode: 'full_amounts',
          smart_card_stack: [
            {
              card_key: 'execution',
              title: 'التنفيذ',
              order: 0,
              mode_visibility: 'simple_preview',
              status: 'ready',
              metrics: {
                task_name: 'Inspection',
                planned_count: 2,
                executed_count: 1,
                budget_total: '300.0000',
                actual_total: '250.0000',
              },
              flags: [],
              data_source: 'task_contract_snapshot',
              policy: {
                read_only: true,
                shadow_accounting: true,
              },
              source_refs: ['activity'],
            },
            {
              card_key: 'materials',
              title: 'المواد',
              order: 1,
              mode_visibility: 'simple_preview',
              status: 'attention',
              metrics: {
                planned_qty: '10.0000',
                actual_qty: '8.0000',
                qty_variance: '-2.0000',
                planned_cost: '120.0000',
                actual_cost: '90.0000',
                cost_variance: '-30.0000',
              },
              flags: [],
              data_source: 'activity_items',
              source_refs: ['activity.items', 'crop_plan.recipe'],
            },
            {
              card_key: 'control',
              title: 'الرقابة',
              order: 2,
              mode_visibility: 'simple_preview',
              status: 'critical',
              metrics: {
                total_logs: 3,
                rejected_logs: 0,
                critical_logs: 1,
              },
              flags: ['critical_control'],
              data_source: 'daily_log',
              source_refs: ['daily_log'],
            },
            {
              card_key: 'variance',
              title: 'الانحراف',
              order: 3,
              mode_visibility: 'simple_preview',
              status: 'attention',
              metrics: {
                total_alerts: 2,
                open_alerts: 1,
                total_variance: '50.0000',
              },
              flags: ['open_variance'],
              data_source: 'variance_alert',
              source_refs: ['variance_alert'],
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
                credit_total: '250.0000',
              },
              flags: [],
              data_source: 'financial_ledger',
              source_refs: ['financial_ledger'],
            },
          ],
          stage_groups: [{ stage: 'Preparation', count: 2, services: [{ id: 1, name: 'Soil tillage' }] }],
        },
      ],
    })

    render(<ServiceCards />)

    await waitFor(() => expect(serviceCardsList).toHaveBeenCalledWith({ farm_id: '7' }))
    expect(await screen.findByText('Tomato')).toBeTruthy()
    expect(screen.getByText('الرقابة والانحرافات والقيود')).toBeTruthy()
    expect(screen.getAllByText('انحرافات مفتوحة').length).toBeGreaterThan(0)
    expect(screen.getAllByText('قيود دفترية').length).toBeGreaterThan(0)
    expect(screen.getByText(/الانحرافات: 2 إجماليًا/)).toBeTruthy()
    expect(screen.getByText(/القيود: مدين 250.0000/)).toBeTruthy()
    expect(screen.getByTestId('service-cards-stack-count-1').textContent).toContain('5')
    expect(screen.getByText('معاينة Smart Card Stack')).toBeTruthy()
    expect(screen.getByTestId('service-cards-stack-1-card-title-execution')).toBeTruthy()
    expect(screen.getByTestId('service-cards-stack-1-card-title-materials')).toBeTruthy()
    expect(
      screen.getByTestId('service-cards-stack-1-card-policy-execution-shadow_accounting').textContent,
    ).toContain('القيد الظلي محفوظ')
    expect(
      screen.getByTestId('service-cards-stack-1-card-metric-materials-planned_cost').textContent,
    ).toContain('120.0000')
  })

})
