import { useEffect } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import { api } from '../api/client'
import { logRuntimeError } from '../utils/runtimeLogger'

export default function StrictRouteGuard() {
  const location = useLocation()

  useEffect(() => {
    // [AGRI-GUARDIAN Axis 12] Log the breach attempt implicitly
    api
      .post('/audit/breach/', {
        target_url: location.pathname,
        timestamp: new Date().toISOString(),
      })
      .catch((err) => {
        logRuntimeError('STRICT_ROUTE_BREACH_LOG_FAILED', err, { path: location.pathname })
        toast.error('تعذر تسجيل محاولة الوصول غير المصرح.')
      })
  }, [location.pathname])

  // Bounce unauthorized user back to dashboard silently
  return <Navigate to="/dashboard" replace />
}
