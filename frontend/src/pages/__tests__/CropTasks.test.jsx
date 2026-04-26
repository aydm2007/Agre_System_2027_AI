import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const tasksList = vi.fn()
const addTask = vi.fn()
const updateTask = vi.fn()
const deleteTask = vi.fn()
const navigate = vi.fn()
const toast = vi.fn()

vi.mock('../../api/client', () => ({
  Crops: {
    tasks: (...args) => tasksList(...args),
    addTask: (...args) => addTask(...args),
    updateTask: (...args) => updateTask(...args),
    deleteTask: (...args) => deleteTask(...args),
  },
}))

vi.mock('../../components/ToastProvider', () => ({
  useToast: () => toast,
}))

vi.mock('react-router-dom', () => ({
  useParams: () => ({ id: '5' }),
  useNavigate: () => navigate,
}))

import CropTasks from '../CropTasks'

describe('CropTasks smart multi-card form', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    tasksList.mockResolvedValue({ data: { results: [] } })
    addTask.mockResolvedValue({ data: { id: 99 } })
    updateTask.mockResolvedValue({ data: { id: 1 } })
    deleteTask.mockResolvedValue({})
    window.confirm = vi.fn(() => true)
  })

  it('creates a mango task with explicit smart-card contract', async () => {
    render(<CropTasks />)

    fireEvent.click(await screen.findByText(/\+ إضافة مهمة جديدة/))
    fireEvent.change(screen.getByLabelText('المرحلة'), { target: { value: 'الخدمة' } })
    fireEvent.change(screen.getByLabelText('اسم المهمة'), { target: { value: 'تسميد مانجو' } })
    fireEvent.change(screen.getByTestId('crop-task-preset'), { target: { value: 'MANGO' } })
    fireEvent.click(screen.getByTestId('crop-task-card-machinery'))
    fireEvent.click(screen.getByTestId('crop-task-submit'))

    await waitFor(() => expect(addTask).toHaveBeenCalled())
    const [, payload] = addTask.mock.calls[0]
    expect(payload.name).toBe('تسميد مانجو')
    expect(payload.archetype).toBe('PERENNIAL_SERVICE')
    expect(payload.task_contract.smart_cards.materials.enabled).toBe(true)
    expect(payload.task_contract.smart_cards.labor.enabled).toBe(true)
    expect(payload.task_contract.smart_cards.perennial.enabled).toBe(true)
    expect(payload.task_contract.smart_cards.machinery.enabled).toBe(true)
    expect(payload.requires_tree_count).toBe(true)
    expect(payload.is_perennial_procedure).toBe(true)
  })

  it('keeps mandatory cards locked and updates preview on preset change', async () => {
    render(<CropTasks />)

    fireEvent.click(await screen.findByText(/\+ إضافة مهمة جديدة/))
    expect(screen.getByTestId('crop-task-card-execution').disabled).toBe(true)
    expect(screen.getByTestId('crop-task-card-control').disabled).toBe(true)
    expect(screen.getByTestId('crop-task-card-variance').disabled).toBe(true)

    fireEvent.change(screen.getByTestId('crop-task-preset'), { target: { value: 'BANANA' } })

    expect(screen.getByTestId('crop-task-preview-simple-well')).toBeTruthy()
    expect(screen.getByTestId('crop-task-preview-simple-perennial')).toBeTruthy()
    expect(screen.getByTestId('crop-task-preview-strict-financial_trace')).toBeTruthy()
    expect(screen.getByTestId('crop-task-derived-flags').textContent).toContain('عداد أشجار')
  })

  it('hydrates edit mode from effective task contract', async () => {
    tasksList.mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 1,
            stage: 'الري',
            name: 'ري موز',
            archetype: 'IRRIGATION',
            requires_area: true,
            is_asset_task: false,
            asset_type: '',
            requires_well: true,
            requires_machinery: false,
            requires_tree_count: true,
            is_perennial_procedure: true,
            effective_task_contract: {
              smart_cards: {
                execution: { enabled: true },
                materials: { enabled: true },
                labor: { enabled: true },
                well: { enabled: true },
                perennial: { enabled: true },
                control: { enabled: true },
                variance: { enabled: true },
                financial_trace: { enabled: true },
              },
            },
          },
        ],
      },
    })

    render(<CropTasks />)

    fireEvent.click(await screen.findByTestId('crop-task-edit-1'))

    expect(screen.getByDisplayValue('ري موز')).toBeTruthy()
    expect(screen.getByTestId('crop-task-card-well').checked).toBe(true)
    expect(screen.getByTestId('crop-task-card-materials').checked).toBe(true)
    expect(screen.getByTestId('crop-task-card-perennial').checked).toBe(true)
    expect(screen.getByTestId('crop-task-preview-simple-well')).toBeTruthy()
  })
})
