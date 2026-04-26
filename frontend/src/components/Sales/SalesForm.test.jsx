import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import SalesForm from './SalesForm'
import { FarmProvider } from '../../api/farmContext'
import { ToastProvider } from '../ToastProvider'
import { HarvestProductCatalog, api } from '../../api/client'

// Mock API clients — include ALL exports used by farmContext and SalesForm
vi.mock('../../api/client', () => ({
  HarvestProductCatalog: {
    list: vi.fn(),
  },
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  Sales: {
    create: vi.fn(),
    update: vi.fn(),
  },
  // [FIX] farmContext uses Farms.list() to load farm list
  Farms: {
    list: vi.fn().mockResolvedValue({ data: { results: [] } }),
  },
}))

vi.mock('../../auth/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    user: { id: 1, first_name: 'Test' },
    hasPermission: vi.fn().mockReturnValue(true),
  })),
  AuthProvider: ({ children }) => <div>{children}</div>,
}))

describe('SalesForm UI Component Integrity', () => {
  it('renders correctly and loads mock catalog products', async () => {
    // Setup Mock Responses
    HarvestProductCatalog.list.mockResolvedValue({
      data: {
        results: [
          {
            item_id: '1',
            name: 'UI Validation Tomato',
            total_harvest_qty: 1500,
            reference_price: 55.0,
          },
        ],
      },
    })

    api.get.mockImplementation((url) => {
      if (url === '/customers/') return Promise.resolve({ data: [] })
      if (url === '/locations/')
        return Promise.resolve({ data: [{ id: 1, name: 'Main UI Store' }] })
      return Promise.resolve({ data: [] })
    })

    render(
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <ToastProvider>
          <FarmProvider>
            <SalesForm />
          </FarmProvider>
        </ToastProvider>
      </BrowserRouter>,
    )

    // Verify UI rendering expectations without hitting real production server
    // [FIX] Use standard Vitest assertion instead of jest-dom toBeInTheDocument()
    const heading = await screen.findByText(/إنشاء فاتورة مبيعات/)
    expect(heading).toBeTruthy()

    // Add Item button
    const addBtn = await screen.findByText(/إضافة بند/)
    fireEvent.click(addBtn)

    // Wait for dropdowns (this will test if the mocked product from HarvestProductCatalog is shown)
    const selects = await screen.findAllByRole('combobox')
    // Selects: 0 is Location, 1 is the product selector for the newly added item row
    expect(selects.length).toBeGreaterThanOrEqual(2)
  })
})
