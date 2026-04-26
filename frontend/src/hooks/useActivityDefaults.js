
import { useState, useEffect } from 'react'
import { Activities } from '../api/client'

// Debounce helper to prevent spamming queries while user is selecting
function useDebounce(value, delay) {
    const [debouncedValue, setDebouncedValue] = useState(value)

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value)
        }, delay)

        return () => {
            clearTimeout(handler)
        }
    }, [value, delay])

    return debouncedValue
}

export function useActivityDefaults(taskId, locationId) {
    const [defaults, setDefaults] = useState(null)
    const [loading, setLoading] = useState(false)

    // Create a composite key to denounce
    // We only fetch if BOTH exist
    const queryKey = taskId && locationId ? `${taskId}-${locationId}` : null
    const debouncedQueryKey = useDebounce(queryKey, 500)

    useEffect(() => {
        if (!debouncedQueryKey) {
            setDefaults(null)
            return
        }

        // Split back to params (safe because we formed it)
        // Actually better to use the raw values caught in effect closure if they match
        // checking if current values match debounced trigger

        let active = true
        setLoading(true)

        Activities.defaults({ task: taskId, location: locationId })
            .then((res) => {
                if (active) {
                    // Check if response has meaningful data
                    if (Object.keys(res.data).length > 0) {
                        setDefaults(res.data)
                    } else {
                        setDefaults(null)
                    }
                }
            })
            .catch((err) => {
                console.warn('Failed to fetch activity defaults', err)
            })
            .finally(() => {
                if (active) setLoading(false)
            })

        return () => {
            active = false
        }
    }, [debouncedQueryKey, taskId, locationId])

    return { defaults, loading }
}
