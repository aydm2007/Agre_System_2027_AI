let authContextRef = null

export function getAuthContext() {
  return authContextRef
}

export function setAuthContext(value) {
  authContextRef = value
}
