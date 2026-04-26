/* eslint-env node */
const fs = require('fs')
const path = require('path')

const filePath = 'c:\\tools\\workspace\\saradud2027\\frontend\\src\\pages\\DailyLog.jsx'

try {
  const data = fs.readFileSync(filePath, 'utf8')
  const lines = data.split('\n')

  let startLineIndex = -1
  const startMarkerPart =
    'className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 space-y-4"'

  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes(startMarkerPart)) {
      startLineIndex = i
      break
    }
  }

  if (startLineIndex === -1) {
    console.error('Could not find start marker.')
    // Debug: print similar lines?
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes('bg-white border border-gray-200')) {
        // [AG-CLEANUP] console.log(`Potential match at ${i + 1}: ${lines[i]}`);
      }
    }
    process.exit(1)
  }

  // [AG-CLEANUP] console.log(`Found start marker at line ${startLineIndex + 1}`);

  let endLineIndex = -1
  const endContextMarker = 'queueDetailsOpen && ('

  for (let i = startLineIndex; i < lines.length; i++) {
    if (lines[i].includes(endContextMarker)) {
      // The closing div should be before this.
      // Scan backwards from i-1
      for (let j = i - 1; j > startLineIndex; j--) {
        if (lines[j].trim() === '</div>') {
          endLineIndex = j
          break
        }
      }
      break
    }
  }

  if (endLineIndex === -1) {
    console.error('Could not find end marker.')
    process.exit(1)
  }

  // [AG-CLEANUP] console.log(`Found end marker at line ${endLineIndex + 1}`);

  // Prepare replacement
  const replacement = `      <ActivityFeed
        daySummary={daySummary}
        loading={summaryLoading}
        error={daySummaryError}
        pendingQueueCount={pendingQueueCount}
        onGoToQueue={goToOfflineQueue}
        highlightedLogIds={highlightedLogIds}
        isEditingActivity={isEditingActivity}
        editingActivityId={editingActivityId}
        submitting={submitting}
        deletingActivityId={deletingActivityId}
        onApproveLog={onApproveLog}
        onEditActivity={startEditingActivity}
        onDeleteActivity={handleDeleteActivity}
        helpers={{
          toDateInputValue,
          formatNumber,
          formatDateTime,
          formatTeamDisplay
        }}
      />`

  lines.splice(startLineIndex, endLineIndex - startLineIndex + 1, replacement)

  const newData = lines.join('\n')
  fs.writeFileSync(filePath, newData, 'utf8')
  // [AG-CLEANUP] console.log('Successfully replaced ActivityFeed block.');
} catch (err) {
  console.error('Error:', err)
  process.exit(1)
}
