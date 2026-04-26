/* eslint-env node */
const fs = require('fs')
const filePath = 'c:\\tools\\workspace\\saradud2027\\frontend\\src\\pages\\DailyLog.jsx'

try {
  const data = fs.readFileSync(filePath, 'utf8')
  let lines = data.split('\n')

  // Delete Range 2 first (682-697) to preserve indices for Range 1
  // 682-697 are 1-based line numbers.
  // 0-based index start: 681
  // Count: 697 - 682 + 1 = 16
  lines.splice(681, 16)
  // [AG-CLEANUP] console.log('Removed range 682-697');

  // Delete Range 1 (446-659)
  // 0-based index start: 445
  // Count: 659 - 446 + 1 = 214
  lines.splice(445, 214)
  // [AG-CLEANUP] console.log('Removed range 446-659');

  const newData = lines.join('\n')
  fs.writeFileSync(filePath, newData, 'utf8')
  // [AG-CLEANUP] console.log('Successfully removed TEXT constants.');
} catch (err) {
  console.error('Error:', err)
  process.exit(1)
}
