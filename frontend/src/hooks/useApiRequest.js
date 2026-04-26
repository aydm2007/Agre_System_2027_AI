import { useCallback, useState } from 'react'

export default function useApiRequest() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const execute = useCallback(async (requestFn) => {
    setLoading(true)
    setError(null)
    try {
      const result = await requestFn()
      return result
    } catch (err) {
      setError(err)
      // Round 17: Kamikaze Hook Fix - Do not crash the app by default
      // throw err 
      return { error: err }
    } finally {
      setLoading(false)
    }
  }, [])

  return { execute, loading, error }
}
