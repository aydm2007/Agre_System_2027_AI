import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const DEFAULT_TIMEOUT = 4000

export default function useFeedback (timeout = DEFAULT_TIMEOUT) {
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const timersRef = useRef({ message: null, error: null })

  const clearTimer = useCallback((type) => {
    const timerId = timersRef.current[type]
    if (timerId) {
      clearTimeout(timerId)
      timersRef.current[type] = null
    }
  }, [])

  const scheduleClear = useCallback((type, setter) => {
    clearTimer(type)
    timersRef.current[type] = setTimeout(() => {
      setter('')
      timersRef.current[type] = null
    }, timeout)
  }, [clearTimer, timeout])

  const showMessage = useCallback((text) => {
    if (!text) {
      clearTimer('message')
      setMessage('')
      return
    }
    setMessage(text)
    scheduleClear('message', setMessage)
  }, [clearTimer, scheduleClear])

  const showError = useCallback((text) => {
    if (!text) {
      clearTimer('error')
      setError('')
      return
    }
    setError(text)
    scheduleClear('error', setError)
  }, [clearTimer, scheduleClear])

  useEffect(() => () => {
    Object.values(timersRef.current).forEach((timer) => {
      if (timer) clearTimeout(timer)
    })
  }, [])

  return useMemo(() => ({ message, error, showMessage, showError }), [message, error, showMessage, showError])
}
