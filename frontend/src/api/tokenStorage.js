export const ACCESS_TOKEN_KEY = 'accessToken'
export const REFRESH_TOKEN_KEY = 'refreshToken'

const storage = {
  available() {
    try {
      return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
    } catch (error) {
      console.warn('Failed to detect storage availability:', error)
      return false
    }
  },
  get(key) {
    if (!this.available()) {
      return null
    }
    try {
      return window.localStorage.getItem(key)
    } catch (error) {
      console.warn('Failed to read from storage:', error)
      return null
    }
  },
  set(key, value) {
    if (!this.available()) {
      return
    }
    try {
      if (value === null || value === undefined) {
        window.localStorage.removeItem(key)
      } else {
        window.localStorage.setItem(key, value)
      }
    } catch (error) {
      console.warn('Failed to write to storage:', error)
    }
  },
  remove(key) {
    if (!this.available()) {
      return
    }
    try {
      window.localStorage.removeItem(key)
    } catch (error) {
      console.warn('Failed to remove from storage:', error)
    }
  },
}

export const getAccessTokenValue = () => storage.get(ACCESS_TOKEN_KEY)
export const setAccessTokenValue = (token) => storage.set(ACCESS_TOKEN_KEY, token)
export const clearAccessTokenValue = () => storage.remove(ACCESS_TOKEN_KEY)
export const getRefreshTokenValue = () => storage.get(REFRESH_TOKEN_KEY)
export const setRefreshTokenValue = (token) => storage.set(REFRESH_TOKEN_KEY, token)
export const clearRefreshTokenValue = () => storage.remove(REFRESH_TOKEN_KEY)
