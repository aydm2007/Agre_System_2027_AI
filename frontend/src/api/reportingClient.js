export const createReportingClients = ({ api }) => {
  const Reports = {
    dailySummary: (params = {}) => api.get('/reports/', { params }),
  }

  const AsyncReports = {
    request: (payload) => api.post('/advanced-report/requests/', payload),
    status: (id) => api.get(`/advanced-report/requests/${id}/`),
    download: async (resultUrl, filename) => {
      const downloadUrl = `${window.location.origin}${resultUrl}`
      const response = await fetch(downloadUrl, { credentials: 'include' })
      if (!response.ok) {
        throw new Error('فشل تحميل الملف')
      }
      const blob = await response.blob()
      const objectUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(objectUrl)
    },
  }

  return { Reports, AsyncReports }
}
