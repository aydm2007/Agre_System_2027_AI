/* eslint-env node */
const fs = require('fs')
try {
  const content = fs.readFileSync('src/components/ToastProvider.jsx', 'utf8')
  fs.writeFileSync('output.json', JSON.stringify({ content }))
} catch (e) {
  fs.writeFileSync('output.json', JSON.stringify({ error: e.toString() }))
}
