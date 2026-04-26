
import { useCallback } from 'react'
import { useToast } from '../components/ToastProvider'

export function useErrorHandler() {
    const addToast = useToast()

    const handleError = useCallback((error, defaultMessage = 'حدث خطأ غير متوقع') => {
        console.error('API Error:', error)

        let message = defaultMessage

        if (error.response) {
            const { data, status } = error.response

            // 1. Django ValidationError (Array or String)
            if (status === 400 && data) {
                if (Array.isArray(data)) {
                    message = data[0]
                } else if (typeof data === 'string') {
                    message = data
                } else if (typeof data === 'object') {
                    // Extract first value from dict like {"field": ["Error"]}
                    const firstKey = Object.keys(data)[0]
                    if (firstKey) {
                        const firstVal = data[firstKey]
                        message = Array.isArray(firstVal) ? firstVal[0] : firstVal
                    }
                }
            }

            // 2. Permission Denied
            if (status === 403) {
                message = data?.detail || 'لا تملك صلاحية للقيام بهذا الإجراء'
            }
        }

        addToast({
            title: 'خطأ في النظام',
            message: message,
            type: 'error',
            duration: 5000
        })

        return message
    }, [addToast])

    return { handleError }
}
