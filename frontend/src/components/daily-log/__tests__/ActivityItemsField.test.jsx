import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'

const itemsList = vi.fn()

vi.mock('../../../api/client', () => ({
  MaterialCatalog: { list: vi.fn() },
  Items: { list: (...args) => itemsList(...args) },
}))

vi.mock('../../../utils/errorUtils.js', () => ({
  extractApiError: (_err, fallback) => fallback,
}))

import { ActivityItemsField } from '../ActivityItemsField.jsx'

function StatefulField() {
  const [items, setItems] = useState([{ item_id: '', qty: '', uom: '', batch_number: '' }])
  return <ActivityItemsField items={items} onChange={setItems} farmId="4" />
}

describe('ActivityItemsField', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads generic farm items when crop is not selected and fills the canonical unit', async () => {
    itemsList.mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 1,
            name: 'سماد يوريا',
            unit: { symbol: 'كغ' },
          },
        ],
      },
    })

    render(<StatefulField />)

    await waitFor(() =>
      expect(itemsList).toHaveBeenCalledWith({ limit: 500, exclude_group: 'Produce,Fuel' }),
    )

    const select = await screen.findByRole('combobox')
    fireEvent.change(select, { target: { value: '1' } })

    await waitFor(() => expect(screen.getByDisplayValue('كغ')).toBeTruthy())
  })

  it('keeps unit display read-only after selecting a tracked item', async () => {
    itemsList.mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 2,
            name: 'مبيد يحتاج دفعة',
            requires_batch_tracking: true,
            unit: { symbol: 'لتر' },
          },
        ],
      },
    })

    render(<StatefulField />)

    const select = await screen.findByRole('combobox')
    fireEvent.change(select, { target: { value: '2' } })

    const unitField = await screen.findByDisplayValue('لتر')
    expect(unitField.getAttribute('readonly')).not.toBeNull()
  })
})
