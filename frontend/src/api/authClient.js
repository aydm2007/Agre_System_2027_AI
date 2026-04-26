const rethrowLogged = async (request, label) => {
  try {
    return await request()
  } catch (error) {
    console.error(`${label}:`, error.response?.data || error.message)
    throw error
  }
}

export const createAuthClient = ({ api, authApi, getAccessTokenValue, getRefreshTokenValue, setAccessTokenValue, setRefreshTokenValue, clearAccessTokenValue, clearRefreshTokenValue }) => ({
  login: async (username, password) => rethrowLogged(() => authApi.post('/auth/token/', { username, password }), 'Login error'),
  refresh: async (refreshToken) => {
    const token = refreshToken ?? getRefreshTokenValue()
    if (!token) {
      throw new Error('Missing refresh token')
    }
    return authApi.post('/auth/refresh/', { refresh: token })
  },
  setTokens: (accessToken, refreshToken) => {
    setAccessTokenValue(accessToken || null)
    if (refreshToken !== undefined) {
      setRefreshTokenValue(refreshToken || null)
    }
  },
  getToken: () => getAccessTokenValue(),
  getRefreshToken: () => getRefreshTokenValue(),
  logout: () => {
    clearAccessTokenValue()
    clearRefreshTokenValue()
  },
  getCurrentUser: async () => rethrowLogged(() => api.get('/auth/users/me/'), 'Error fetching current user'),
  getUserPermissions: async (userId) => rethrowLogged(() => api.get(`/auth/users/${userId}/permissions/`), 'Error fetching user permissions'),
  getUserGroups: async (userId) => rethrowLogged(() => api.get(`/auth/users/${userId}/groups/`), 'Error fetching user groups'),
  getUsers: async (params = {}) => rethrowLogged(() => api.get('/auth/users/', { params }), 'Error fetching users'),
  getUser: async (userId) => rethrowLogged(() => api.get(`/auth/users/${userId}/`), 'Error fetching user'),
  createUser: async (userData) => rethrowLogged(() => api.post('/auth/users/', userData), 'Error creating user'),
  updateUser: async (userId, userData) => rethrowLogged(() => api.patch(`/auth/users/${userId}/`, userData), 'Error updating user'),
  deleteUser: async (userId) => rethrowLogged(() => api.delete(`/auth/users/${userId}/`), 'Error deleting user'),
  assignPermission: async (userId, permissionId, confirmed = false) => {
    const payload = { permission_id: permissionId }
    if (confirmed) payload.confirmed = true
    return rethrowLogged(() => api.post(`/auth/users/${userId}/permissions/`, payload), 'Error assigning permission')
  },
  removePermission: async (userId, permissionId) => rethrowLogged(() => api.delete(`/auth/users/${userId}/permissions/${permissionId}/`), 'Error removing permission'),
  getGroups: async (params = {}) => rethrowLogged(() => api.get('/auth/groups/', { params }), 'Error fetching groups'),
  getGroup: async (groupId) => rethrowLogged(() => api.get(`/auth/groups/${groupId}/`), 'Error fetching group'),
  createGroup: async (groupData) => rethrowLogged(() => api.post('/auth/groups/', groupData), 'Error creating group'),
  updateGroup: async (groupId, groupData) => rethrowLogged(() => api.patch(`/auth/groups/${groupId}/`, groupData), 'Error updating group'),
  deleteGroup: async (groupId) => rethrowLogged(() => api.delete(`/auth/groups/${groupId}/`), 'Error deleting group'),
  assignGroupPermission: async (groupId, permissionId) => rethrowLogged(() => api.post(`/auth/groups/${groupId}/permissions/`, { permission_id: permissionId }), 'Error assigning group permission'),
  removeGroupPermission: async (groupId, permissionId) => rethrowLogged(() => api.delete(`/auth/groups/${groupId}/permissions/${permissionId}/`), 'Error removing group permission'),
  addUserToGroup: async (userId, groupId, confirmed = false) => {
    const payload = { group_id: groupId }
    if (confirmed) payload.confirmed = true
    return rethrowLogged(() => api.post(`/auth/users/${userId}/groups/`, payload), 'Error adding user to group')
  },
  removeUserFromGroup: async (userId, groupId) => rethrowLogged(() => api.delete(`/auth/users/${userId}/groups/${groupId}/`), 'Error removing user from group'),
  getPermissions: async (params = {}) => rethrowLogged(() => api.get('/auth/permissions/', { params }), 'Error fetching permissions'),
  getPermission: async (permissionId) => rethrowLogged(() => api.get(`/auth/permissions/${permissionId}/`), 'Error fetching permission'),
})
