import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

import { DailyLogResources } from '../DailyLogResources'

const previewMock = vi.fn()

vi.mock('../../ui/EmployeeSelect', () => ({
  EmployeeSelect: () => <div data-testid="team-input">employee-select-mock</div>,
}))

vi.mock('../../../api/client', () => ({
  default: {
    post: vi.fn(),
  },
  LaborEstimates: {
    preview: (...args) => previewMock(...args),
  },
}))

describe('DailyLogResources', () => {
  beforeEach(() => {
    previewMock.mockReset()
  })

  const baseProps = {
    form: {
      farm: 1,
      labor_entry_mode: 'CASUAL_BATCH',
      casual_workers_count: '10',
      casual_batch_label: 'دفعة عمال',
      surrah_count: '1.5',
      team: [],
    },
    updateField: vi.fn(),
    lookups: {},
    errors: {},
  }

  it('renders updated period label and helper text', () => {
    render(<DailyLogResources {...baseProps} />)
    expect(screen.getByText('عدد فترات العمل (وردية)')).toBeTruthy()
    expect(screen.getByText(/الفترة الواحدة = 8 ساعات/)).toBeTruthy()
  })

  it('shows labor estimate panel for casual mode', async () => {
    previewMock.mockResolvedValue({
      data: {
        equivalent_hours_per_worker: '12.0000',
        equivalent_hours_total: '120.0000',
        estimated_labor_cost: '27000.0000',
        currency: 'YER',
      },
    })

    render(<DailyLogResources {...baseProps} />)

    await waitFor(() => expect(previewMock).toHaveBeenCalled(), { timeout: 2500 })
    expect(await screen.findByTestId('labor-estimate-panel')).toBeTruthy()
    expect(screen.getByTestId('equivalent-hours-per-worker').textContent).toContain('12.00')
    expect(screen.getByTestId('equivalent-hours-total').textContent).toContain('120.00')
    expect(screen.getByTestId('estimated-labor-cost').textContent).toContain('27,000.00')
  })

  it('renders a contract-driven placeholder when labor card is disabled', () => {
    render(<DailyLogResources {...baseProps} taskContext={{ enabledCards: { labor: false } }} />)

    expect(screen.getByText('هذه المهمة لا تتطلب بطاقة عمالة مستقلة')).toBeTruthy()
  })

  it('renders only allowed labor modes from task policy', () => {
    render(
      <DailyLogResources
        {...baseProps}
        form={{ ...baseProps.form, labor_entry_mode: 'CASUAL_BATCH' }}
        taskContext={{
          enabledCards: { labor: true },
          laborPolicy: {
            registeredAllowed: false,
            casualBatchAllowed: true,
            surrahRequired: true,
          },
        }}
      />,
    )

    const select = screen.getByTestId('labor-entry-mode-select')
    expect(select.querySelector('option[value="REGISTERED"]')).toBeNull()
    expect(select.querySelector('option[value="CASUAL_BATCH"]')).toBeTruthy()
  })
})
