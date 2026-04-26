const { spawnSync } = require('child_process');
const fs = require('fs');
const result = spawnSync('npx.cmd', ['vitest', 'run', '--reporter=verbose'], { encoding: 'utf-8' });
fs.writeFileSync('final_vitest.txt', (result.stdout || '') + '\n\n' + (result.stderr || '') + '\n\n' + (result.error ? result.error.message : ''));
