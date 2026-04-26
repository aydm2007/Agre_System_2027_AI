import { getAuthContext } from '../auth/contextBridge'

export const createApprovalClients = ({ api, safeRequest }) => {
  const resolveFarmScopedParams = async (params = {}) => {
    const authContext = getAuthContext()
    const userFarmIds = authContext ? authContext.userFarmIds : []
    return !params.farm_id && userFarmIds.length > 0
      ? { ...params, farm_id: userFarmIds.join(',') }
      : params
  }

  const ApprovalRules = {
    list: async (params = {}) => api.get('/finance/approval-rules/', { params: await resolveFarmScopedParams(params) }),
    create: (payload) => safeRequest('post', '/finance/approval-rules/', payload),
    update: (id, payload) => safeRequest('patch', `/finance/approval-rules/${id}/`, payload),
    delete: (id) => safeRequest('delete', `/finance/approval-rules/${id}/`),
  }

  const ApprovalRequests = {
    list: async (params = {}) => api.get('/finance/approval-requests/', { params: await resolveFarmScopedParams(params) }),
    retrieve: (id) => api.get(`/finance/approval-requests/${id}/`),
    myQueue: async (params = {}) => api.get('/finance/approval-requests/my-queue/', { params: await resolveFarmScopedParams(params) }),
    queueSummary: async () => api.get('/finance/approval-requests/queue-summary/'),
    maintenanceSummary: async () => api.get('/finance/approval-requests/maintenance-summary/'),
    runtimeGovernance: async () => api.get('/finance/approval-requests/runtime-governance/'),
    runtimeGovernanceDetail: async (params = {}) => api.get('/finance/approval-requests/runtime-governance/detail/', { params: await resolveFarmScopedParams(params) }),
    roleWorkbench: async (params = {}) => api.get('/finance/approval-requests/role-workbench/', { params: await resolveFarmScopedParams(params) }),
    roleWorkbenchSummary: async () => api.get('/finance/approval-requests/role-workbench-summary/'),
    attentionFeed: async (params = {}) => api.get('/finance/approval-requests/attention-feed/', { params: await resolveFarmScopedParams(params) }),
    sectorDashboard: async () => api.get('/finance/approval-requests/sector-dashboard/'),
    policyImpact: async () => api.get('/finance/approval-requests/policy-impact/'),
    farmGovernance: async (params = {}) => api.get('/finance/approval-requests/farm-governance/', { params: await resolveFarmScopedParams(params) }),
    farmOps: async (params = {}) => api.get('/finance/approval-requests/farm-ops/', { params: await resolveFarmScopedParams(params) }),
    requestTrace: async (params = {}) => api.get('/finance/approval-requests/request-trace/', { params: await resolveFarmScopedParams(params) }),
    dryRunMaintenance: (payload = {}) => safeRequest('post', '/finance/approval-requests/runtime-governance/dry-run-maintenance/', payload),
    timeline: (id) => api.get(`/finance/approval-requests/${id}/timeline/`),
    approve: (id, payload) => safeRequest('post', `/finance/approval-requests/${id}/approve/`, payload),
    overrideStage: (id, payload) => safeRequest('post', `/finance/approval-requests/${id}/override-stage/`, payload),
    reopen: (id, payload) => safeRequest('post', `/finance/approval-requests/${id}/reopen/`, payload),
    reject: (id, payload) => safeRequest('post', `/finance/approval-requests/${id}/reject/`, payload),
  }

  return { ApprovalRules, ApprovalRequests }
}
