/* eslint-env node */
const fs = require('fs')
const filePath = 'c:\\tools\\workspace\\saradud2027\\frontend\\src\\pages\\DailyLog.jsx'

try {
  const data = fs.readFileSync(filePath, 'utf8')
  let lines = data.split('\n')
  const initialLength = lines.length

  // Block 1: const TEXT = { ... }
  // Find Start
  let start1 = -1
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() === 'const TEXT = {') {
      start1 = i
      break
    }
  }

  // Find End of Block 1 (before CollapsibleCard)
  let end1 = -1
  if (start1 !== -1) {
    for (let i = start1; i < lines.length; i++) {
      if (lines[i].includes('function CollapsibleCard')) {
        // The closing brace is likely a few lines before this
        // Scan back for `}`
        for (let j = i - 1; j > start1; j--) {
          if (lines[j].trim() === '}') {
            end1 = j
            break
          }
        }
        break
      }
    }
  }

  if (start1 !== -1 && end1 !== -1) {
    // [AG-CLEANUP] console.log(`Removing TEXT block lines ${start1 + 1} to ${end1 + 1}`);
    // Set lines to null/empty string to preserve indices for next search?
    // Or just splice now?
    // Better to mark for deletion and filter later to avoid index shifting.
    for (let i = start1; i <= end1; i++) {
      lines[i] = null
    }
  } else {
    console.error('Could not find TEXT block boundaries.')
  }

  // Block 2: TEXT.tree... assignments
  // Find Start
  let start2 = -1
  for (let i = 0; i < lines.length; i++) {
    if (lines[i] && lines[i].includes('TEXT.tree.serviceExistingTotal =')) {
      start2 = i
      break
    }
  }

  // Find End (last assignment)
  let end2 = -1
  if (start2 !== -1) {
    for (let i = start2; i < lines.length; i++) {
      if (lines[i] && lines[i].includes('TEXT.tree.serviceLocationUpdated =')) {
        end2 = i
        break // Assuming this is the last one based on view
      }
    }
  }

  if (start2 !== -1 && end2 !== -1) {
    // [AG-CLEANUP] console.log(`Removing TEXT.tree assignments lines ${start2 + 1} to ${end2 + 1}`);
    for (let i = start2; i <= end2; i++) {
      lines[i] = null
    }
  } else {
    console.error('Could not find TEXT.tree assignments block.')
  }

  // Filter out null lines
  const newLines = lines.filter((line) => line !== null)

  if (newLines.length < initialLength) {
    fs.writeFileSync(filePath, newLines.join('\n'), 'utf8')
    // [AG-CLEANUP] console.log('Successfully removed TEXT constants.');
  } else {
    // [AG-CLEANUP] console.log('No changes made.');
  }
} catch (err) {
  console.error('Error:', err)
  process.exit(1)
}
