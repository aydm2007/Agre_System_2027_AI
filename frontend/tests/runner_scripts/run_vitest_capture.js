const { execSync } = require('child_process');
const fs = require('fs');
try {
    const out = execSync('npx vitest run --reporter=verbose', { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe'] });
    fs.writeFileSync('vitest_complete.txt', out);
} catch (e) {
    fs.writeFileSync('vitest_complete.txt', e.stdout + '\n\n' + e.stderr);
}
