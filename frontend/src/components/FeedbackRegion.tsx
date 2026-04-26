export default function FeedbackRegion({ error, message }) {
  if (error || message) {
    return (
      <div className="space-y-2" aria-live="polite" role="status">
        {error && <div className="bg-red-100 text-red-700 p-3 rounded">{error}</div>}
        {message && <div className="bg-green-100 text-green-700 p-3 rounded">{message}</div>}
      </div>
    )
  }

  return <div className="min-h-[2.75rem]" aria-live="polite" role="status" />
}
