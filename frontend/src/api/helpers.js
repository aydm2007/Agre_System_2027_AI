import { v4 as uuidv4 } from 'uuid'

export const trimTrailingSlashes = (value) => {
  if (typeof value !== 'string') {
    return ''
  }
  let clean = value
  while (clean.endsWith('/')) {
    clean = clean.slice(0, -1)
  }
  return clean
}

export const dataUrlToFile = (dataUrl, filename, fileType) => {
  try {
    const parts = dataUrl.split(',')
    const base64 = parts[1] || ''
    const binary = atob(base64)
    const buffer = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i += 1) {
      buffer[i] = binary.charCodeAt(i)
    }
    const blob = new Blob([buffer], { type: fileType || 'application/octet-stream' })
    return new File([blob], filename, { type: fileType || 'application/octet-stream' })
  } catch (error) {
    console.error('Failed to convert data URL to file', error)
    return null
  }
}

export const resolveApiBase = () => {
  const envValue =
    typeof import.meta.env.VITE_API_BASE === 'string'
      ? trimTrailingSlashes(import.meta.env.VITE_API_BASE.trim())
      : ''
  if (envValue) {
    return envValue
  }
  return '/api'
}

export const resolveApiRoots = () => {
  const configuredBase = resolveApiBase()

  if (!configuredBase) {
    return { authBase: '/api', apiV1Base: '/api/v1' }
  }

  if (configuredBase.endsWith('/api/v1')) {
    return {
      authBase: configuredBase.slice(0, -3),
      apiV1Base: configuredBase,
    }
  }

  if (configuredBase.endsWith('/api')) {
    return {
      authBase: configuredBase,
      apiV1Base: `${configuredBase}/v1`,
    }
  }

  return {
    authBase: `${configuredBase}/api`,
    apiV1Base: `${configuredBase}/api/v1`,
  }
}

export const nowIso = () => new Date().toISOString()

export const generateOfflineId = () => {
  if (typeof crypto !== 'undefined' && crypto?.randomUUID) {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

export const createClientSideId = () => uuidv4()
