import { useEffect, useRef } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useSettings } from '../contexts/SettingsContext'
import {
    canAccessFinanceHubRoutes,
    canRegisterStrictRoutes,
    canRegisterFinancialRoutes,
    canAccessTreasuryRoutes,
    canAccessContractRoutes,
    canAccessFixedAssetRoutes,
    canAccessFuelReconciliationRoutes,
    canAccessStockManagementRoutes,
} from '../auth/modeAccess'
import { api } from '../api/client'
import { logRuntimeError } from '../utils/runtimeLogger'

const POLICY_MAP = {
    canAccessFinanceHubRoutes,
    canRegisterStrictRoutes,
    canRegisterFinancialRoutes,
    canAccessTreasuryRoutes,
    canAccessContractRoutes,
    canAccessFixedAssetRoutes,
    canAccessFuelReconciliationRoutes,
    canAccessStockManagementRoutes,
}

export default function ModeGuard({
    requiredMode = 'STRICT',
    policyCheck = null,
    redirectTo = '/dashboard',
    fallback = null,
}) {
    const location = useLocation()
    const { isAdmin, isSuperuser, hasFarmRole } = useAuth()
    const { isStrictMode, contractMode, treasuryVisibility, fixedAssetMode, settings } = useSettings()

    const breachLogged = useRef(false)

    const policyOptions = {
        strictErpMode: isStrictMode,
        showFinanceInSimple: settings?.show_finance_in_simple,
        showStockInSimple: settings?.show_stock_in_simple,
        showEmployeesInSimple: settings?.show_employees_in_simple,
        isAdmin,
        isSuperuser,
        hasFarmRole,
        contractMode,
        treasuryVisibility,
        fixedAssetMode,
    }

    let isAllowed = false

    if (policyCheck && POLICY_MAP[policyCheck]) {
        isAllowed = POLICY_MAP[policyCheck](policyOptions)
    } else if (requiredMode === 'STRICT') {
        isAllowed = Boolean(policyOptions.strictErpMode)
    } else {
        isAllowed = true
    }

    useEffect(() => {
        if (!isAllowed && !breachLogged.current) {
            breachLogged.current = true
            api
                .post('/audit/breach/', {
                    target_url: location.pathname,
                    required_mode: requiredMode,
                    policy_check: policyCheck,
                    current_mode: policyOptions.strictErpMode ? 'STRICT' : 'SIMPLE',
                    timestamp: new Date().toISOString(),
                })
                .catch((err) => {
                    logRuntimeError('MODE_GUARD_BREACH_LOG_FAILED', err, {
                        path: location.pathname,
                        requiredMode,
                        policyCheck,
                    })
                })
        }
    }, [isAllowed, location.pathname, policyCheck, policyOptions.strictErpMode, requiredMode])

    useEffect(() => {
        breachLogged.current = false
    }, [location.pathname])

    if (isAllowed) {
        return <Outlet />
    }

    if (fallback) {
        return fallback
    }

    return <Navigate to={redirectTo} replace />
}
