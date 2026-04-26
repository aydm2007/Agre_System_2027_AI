import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { describe, it, expect, vi } from 'vitest'
import ApprovalButton from '../src/components/ApprovalButton'
import * as AuthContext from '../src/auth/AuthContext'

// Mock useAuth
const useAuthSpy = vi.spyOn(AuthContext, 'useAuth')

describe('ApprovalButton Checks', () => {
  it('should be disabled for the creator (Four-Eyes Principle)', () => {
    // Mock current user = 1
    useAuthSpy.mockReturnValue({ user: { id: 1 } })

    render(<ApprovalButton creatorId={1} logId={100} onApprove={() => {}} />)

    const button = screen.getByRole('button')
    // Check if disabled and has lock icon text
    expect(button).toBeDisabled()
    expect(button).toHaveTextContent('اعتماد السجل 🔒')
  })

  it('should be enabled for supervisor (different user)', () => {
    // Mock current user = 2
    useAuthSpy.mockReturnValue({ user: { id: 2 } })

    const approveMock = vi.fn()
    render(<ApprovalButton creatorId={1} logId={100} onApprove={approveMock} />)

    const button = screen.getByRole('button')
    expect(button).not.toBeDisabled()
    expect(button).toHaveTextContent('اعتماد السجل ✅')

    fireEvent.click(button)
    expect(approveMock).toHaveBeenCalledTimes(1)
  })
})
