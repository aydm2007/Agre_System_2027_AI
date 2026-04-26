const fs = require('fs');
const path = require('path');

const ROOT = 'C:\\tools\\workspace\\AgriAsset_v445\\frontend';

const CATEGORIES = {
    'scripts/ci_helpers': [
        'analyze_results.py', 'fix_nav.py', 'read_toast.py', 'to_json.py',
        'patch_lint.js', 'evaluate_reopen.js'
    ],
    'tests/runner_scripts': [
        'run_test.js', 'run_vitest.js', 'run_vitest_capture.js',
        'test_read.js', 'test_rejected_ui.js', 'test_ui_e2e.js'
    ],
    'logs_and_temp': [
        'auth_error.log', 'farmContext-vitest.log', 'test_output.log',
        'test-results.json', 'package-lock.copy'
    ],
    'scripts/openapi_cache': [
        'openapi.json'
    ]
};

function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function processMoves() {
    console.log("=== BEGIN FRONTEND RUKUN REFACTOR ===");
    for (const [folder, files] of Object.entries(CATEGORIES)) {
        const fullDir = path.join(ROOT, folder);
        ensureDir(fullDir);
        
        let movedCount = 0;
        files.forEach(file => {
            const src = path.join(ROOT, file);
            const dest = path.join(fullDir, file);
            if (fs.existsSync(src)) {
                fs.renameSync(src, dest);
                movedCount++;
            }
        });
        console.log(`Moved ${movedCount} files to /${folder}`);
    }
    console.log("=== COMPLETED ===");
}

processMoves();
