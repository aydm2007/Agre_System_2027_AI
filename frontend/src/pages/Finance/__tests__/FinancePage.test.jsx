import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

const useSettingsMock = vi.fn()

vi.mock('../../../contexts/SettingsContext', () => ({
  useSettings: () => useSettingsMock(),
}))

vi.mock('../LedgerList', () => ({
  default: ({ endpoint }) => <div data-testid="ledger-root" data-endpoint={endpoint} />,
}))

vi.mock('../FiscalYearList', () => ({ default: () => <div /> }))
vi.mock('../FiscalPeriodList', () => ({ default: () => <div /> }))
vi.mock('../ActualExpenseList', () => ({ default: () => <div /> }))
vi.mock('../TreasuryDashboard', () => ({ default: () => <div /> }))
vi.mock('../CashBoxList', () => ({ default: () => <div /> }))
vi.mock('../TreasuryTransactions', () => ({ default: () => <div /> }))
vi.mock('../ReceiptsDepositDashboard', () => ({ default: () => <div /> }))
vi.mock('../SupplierSettlementDashboard', () => ({ default: () => <div /> }))
vi.mock('../WorkflowExport', () => ({ default: () => <div /> }))
vi.mock('../AdvancedReportsScreen', () => ({ default: () => <div /> }))
vi.mock('../MakerCheckerDashboard', () => ({ default: () => <div /> }))
vi.mock('../VarianceAnalysis', () => ({ default: () => <div /> }))
vi.mock('../PayrollSettlement', () => ({ default: () => <div /> }))
vi.mock('../PettyCashDashboard', () => ({ default: () => <div /> }))
vi.mock('../../../components/ModeGuard.jsx', () => ({
  default: ({ children }) => children ?? <div />,
}))

import FinancePage from '../index.jsx'

describe('FinancePage', () => {
  it('uses the shadow-ledger surface in SIMPLE mode', () => {
    useSettingsMock.mockReturnValue({
      isPettyCashEnabled: true,
      isStrictMode: false,
    })

    render(
      <MemoryRouter initialEntries={['/']}>
        <FinancePage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('ledger-root').getAttribute('data-endpoint')).toBe(
      '/shadow-ledger/',
    )
  })

  it('uses the governed ledger endpoint in STRICT mode', () => {
    useSettingsMock.mockReturnValue({
      isPettyCashEnabled: true,
      isStrictMode: true,
    })

    render(
      <MemoryRouter initialEntries={['/']}>
        <FinancePage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('ledger-root').getAttribute('data-endpoint')).toBe(
      '/finance/ledger/',
    )
  })
})
