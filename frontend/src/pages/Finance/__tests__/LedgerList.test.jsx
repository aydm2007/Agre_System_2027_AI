import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockApiGet = vi.fn()
const mockUseFinancialFilters = vi.fn()
const mockToastError = vi.fn()

vi.mock('../../../api/client', () => ({
  api: {
    get: (...args) => mockApiGet(...args),
  },
  Seasons: {
    list: vi.fn(),
  },
}))

vi.mock('../../../api/farmContext.jsx', () => ({
  useFarmContext: () => ({
    selectedFarmId: '4',
    farms: [{ id: 4, name: 'Finance Farm' }],
  }),
}))

vi.mock('../../../hooks/useFinancialFilters', () => ({
  default: (...args) => mockUseFinancialFilters(...args),
}))

vi.mock('react-hot-toast', () => ({
  toast: {
    error: (...args) => mockToastError(...args),
  },
}))

vi.mock('../../../components/filters/FinancialFilterBar', () => ({
  default: () => <div data-testid="financial-filter-bar" />,
}))

import LedgerList from '../LedgerList'

describe('LedgerList', () => {
  beforeEach(() => {
    mockApiGet.mockReset()
    mockUseFinancialFilters.mockReset()
    mockToastError.mockReset()

    mockUseFinancialFilters.mockReturnValue({
      filters: { farm: '4', location: '15', costCenter: '9', crop_plan: '137', activity: '501' },
      options: {},
      loading: {},
      setFilter: vi.fn(),
      resetFilters: vi.fn(),
      filterParams: {
        farm: '4',
        location: '15',
        costCenter: '9',
        crop_plan: '137',
        activity: '501',
      },
    })
  })

  it('loads summary first and then paginated rows with the active filter scope', async () => {
    mockApiGet
      .mockResolvedValueOnce({
        data: {
          totals: { debit: '120', credit: '20', balance: '100', entry_count: 1 },
          by_account: [],
        },
      })
      .mockResolvedValueOnce({
        data: {
          count: 1,
          next: null,
          previous: null,
          results: [
            {
              id: 1,
              created_at: '2026-04-01T10:00:00Z',
              account_code: '1300-INV-ASSET',
              account_code_name: 'أصول المخزون',
              description: 'قيد يومي',
              localized_description: 'قيد يومي',
              debit: '120.0000',
              credit: '0.0000',
              currency: 'YER',
            },
          ],
        },
      })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <LedgerList />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockApiGet).toHaveBeenNthCalledWith(
        1,
        '/finance/ledger/summary/',
        expect.objectContaining({
          params: expect.objectContaining({
            farm: '4',
            location: '15',
            crop_plan: '137',
            activity: '501',
            ordering: '-created_at',
            created_at__gte: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
            created_at__lte: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
          }),
        }),
      )
      expect(mockApiGet).toHaveBeenNthCalledWith(
        2,
        '/finance/ledger/',
        expect.objectContaining({
          params: expect.objectContaining({
            farm: '4',
            location: '15',
            crop_plan: '137',
            activity: '501',
            ordering: '-created_at',
            page: 1,
            page_size: 50,
          }),
        }),
      )
    })

    expect(await screen.findByText('القيود اليومية')).toBeTruthy()
    expect(screen.getByTestId('financial-filter-bar')).toBeTruthy()
  })

  it('keeps filters visible and shows an integration banner when shadow-ledger is missing on the backend', async () => {
    mockApiGet.mockRejectedValueOnce({
      response: { status: 404 },
    })

    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <LedgerList endpoint="/shadow-ledger/" />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('financial-filter-bar')).toBeTruthy()

    await waitFor(() => {
      expect(
        screen.getByText(/backend المنشور لا يحتوي endpoint المطلوب بعد/i),
      ).toBeTruthy()
    })

    expect(mockApiGet).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('حدث خطأ أثناء تحميل البيانات')).toBeNull()
  })
})
