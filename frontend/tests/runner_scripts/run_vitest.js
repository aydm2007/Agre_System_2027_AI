const { execSync } = require('child_process');
const fs = require('fs');
try {
    execSync('npx vitest run --reporter=json > vitest_dump.json', { stdio: 'inherit' });
} catch (e) {
    console.log('vitest failed, but output dumped.');
}
