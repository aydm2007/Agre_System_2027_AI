import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

// --- Mock setup ---
const useAuthMock = vi.fn()
const useSettingsMock = vi.fn()
const apiPost = vi.fn()

vi.mock('../../auth/AuthContext', () => ({
    useAuth: () => useAuthMock(),
}))

vi.mock('../../contexts/SettingsContext', () => ({
    useSettings: () => useSettingsMock(),
}))

vi.mock('../../api/client', () => ({
    api: { post: (...args) => apiPost(...args) },
}))

vi.mock('../../utils/runtimeLogger', () => ({
    logRuntimeError: vi.fn(),
}))

import ModeGuard from '../ModeGuard'

// --- Test helpers ---
function renderWithGuard({ route, requiredMode, policyCheck } = {}) {
    return render(
        <MemoryRouter initialEntries={[route || '/protected']}>
            <Routes>
                <Route
                    element={
                        <ModeGuard
                            requiredMode={requiredMode || 'STRICT'}
                            policyCheck={policyCheck || null}
                        />
                    }
                >
                    <Route path="/protected" element={<div data-testid="protected-content">محمي</div>} />
                </Route>
                <Route path="/dashboard" element={<div data-testid="dashboard">لوحة التحكم</div>} />
            </Routes>
        </MemoryRouter>,
    )
}

function mockStrictMode() {
    useAuthMock.mockReturnValue({
        strictErpMode: true,
        isAdmin: true,
        isSuperuser: false,
        hasFarmRole: vi.fn(() => false),
    })
    useSettingsMock.mockReturnValue({
        isStrictMode: true,
        contractMode: 'operational_only',
        treasuryVisibility: 'visible',
        fixedAssetMode: 'full',
    })
}

function mockSimpleMode() {
    useAuthMock.mockReturnValue({
        strictErpMode: false,
        isAdmin: false,
        isSuperuser: false,
        hasFarmRole: vi.fn(() => false),
    })
    useSettingsMock.mockReturnValue({
        isStrictMode: false,
        contractMode: 'operational_only',
        treasuryVisibility: 'hidden',
        fixedAssetMode: 'tracking_only',
    })
}

// --- Tests ---
describe('ModeGuard [PRD V21 §7 / AGENTS.md Rules 12, 14, 25]', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        apiPost.mockResolvedValue({ data: {} })
    })

    it('renders protected content in STRICT mode', () => {
        mockStrictMode()
        renderWithGuard({ route: '/protected' })
        expect(screen.getByTestId('protected-content')).toBeTruthy()
    })

    it('redirects to dashboard in SIMPLE mode when STRICT is required', () => {
        mockSimpleMode()
        renderWithGuard({ route: '/protected' })
        expect(screen.queryByTestId('protected-content')).toBeNull()
        expect(screen.getByTestId('dashboard')).toBeTruthy()
    })

    it('logs breach attempt via AuditLog API when access is denied', async () => {
        mockSimpleMode()
        renderWithGuard({ route: '/protected' })

        await waitFor(() =>
            expect(apiPost).toHaveBeenCalledWith(
                '/audit/breach/',
                expect.objectContaining({
                    target_url: '/protected',
                    required_mode: 'STRICT',
                    current_mode: 'SIMPLE',
                }),
            ),
        )
    })

    it('does NOT log breach when access is granted', async () => {
        mockStrictMode()
        renderWithGuard({ route: '/protected' })

        // Give it a tick to see if it fires
        await new Promise((r) => setTimeout(r, 50))
        expect(apiPost).not.toHaveBeenCalled()
    })

    it('uses policyCheck when provided instead of simple mode check', () => {
        // canRegisterFinancialRoutes requires strictErpMode + (admin OR financial role)
        useAuthMock.mockReturnValue({
            strictErpMode: true,
            isAdmin: false,
            isSuperuser: false,
            hasFarmRole: vi.fn(() => false),
        })
        useSettingsMock.mockReturnValue({
            isStrictMode: true,
            contractMode: 'operational_only',
            treasuryVisibility: 'visible',
            fixedAssetMode: 'full',
        })

        renderWithGuard({ route: '/protected', policyCheck: 'canRegisterFinancialRoutes' })
        // Non-admin, non-financial user should be denied even in STRICT
        expect(screen.queryByTestId('protected-content')).toBeNull()
        expect(screen.getByTestId('dashboard')).toBeTruthy()
    })

    it('allows admin access through canRegisterFinancialRoutes policy in STRICT', () => {
        useAuthMock.mockReturnValue({
            strictErpMode: true,
            isAdmin: true,
            isSuperuser: false,
            hasFarmRole: vi.fn(() => false),
        })
        useSettingsMock.mockReturnValue({
            isStrictMode: true,
            contractMode: 'operational_only',
            treasuryVisibility: 'visible',
            fixedAssetMode: 'full',
        })

        renderWithGuard({ route: '/protected', policyCheck: 'canRegisterFinancialRoutes' })
        expect(screen.getByTestId('protected-content')).toBeTruthy()
    })

    it('blocks fuel reconciliation in SIMPLE mode via policy check', () => {
        mockSimpleMode()
        renderWithGuard({ route: '/protected', policyCheck: 'canAccessFuelReconciliationRoutes' })
        expect(screen.queryByTestId('protected-content')).toBeNull()
        expect(screen.getByTestId('dashboard')).toBeTruthy()
    })
})
