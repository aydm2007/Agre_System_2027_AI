import { useState, useEffect } from 'react'

/**
 * useDarkMode Hook - System-Wide Dark Mode Engine
 *
 * Features:
 * - Persists preference to localStorage
 * - Respects system preference on first load
 * - RTL and Accessibility ready
 */
export function useDarkMode() {
  const [isDark, setIsDark] = useState(() => {
    // Check localStorage first
    const stored = localStorage.getItem('darkMode')
    if (stored !== null) {
      return stored === 'true'
    }
    // Fall back to system preference
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    const root = document.documentElement

    if (isDark) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }

    localStorage.setItem('darkMode', isDark.toString())
  }, [isDark])

  const toggle = () => setIsDark((prev) => !prev)

  return { isDark, toggle, setIsDark }
}

export default useDarkMode
