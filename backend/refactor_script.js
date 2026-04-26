const fs = require('fs');
const path = require('path');

const ROOT = 'C:\\tools\\workspace\\AgriAsset_v445\\backend';

const CATEGORIES = {
    'ops/patches': [
        'fix_farm_membership.py', 'fix_migrations.py', 'fix_tests.py', 'fix_tests_v2.py',
        'fix_variety.py', 'apply_fixes_programmatically.py', 'apply_0085_sql.py', 'temp_cleanup.py', 'remove_bom.py', 'rebuild_view.py'
    ],
    'ops/diagnostics': [
        'check_alhussainiya.py', 'check_auth.py', 'check_items.py', 'check_loc1.py',
        'check_settings_api.py', 'check_stock.py', 'check_variety.py',
        'probe_assets.py', 'probe_db.py', 'probe_wells.py',
        'diag_activity.py', 'diag_admin.py',
        'debug_tree_summary.py', 'debug_varieties.py',
        'inspect_settings.py', 'inspect_sql.py', 'atomic_audit.py', 'system_diagnostics.py',
        'inventory_audit.py', 'report_audit.py', 'sync_audit.py', 'run_audit.py', 'run_audits.py', 'db_check.py',
        'port_scan.py', 'ping_server.py', 'read_error.py', 'read_last_log.py', 'logic_validation.py', 'fetch_500.py'
    ],
    'ops/seeding': [
        'seed_all_defaults.py', 'seed_all_wells.py', 'seed_cycle.py',
        'seed_financial_data.py', 'seed_plans.py', 'seed_real_wells.py',
        'seed_sardud.py', 'seed_tasks.py', 'seed_test_data.py',
        'populate_initial_data.py', 'populate_mahmadieh_farm.py',
        'simulate_sardud_cycle.py', 'simulate_golden_cycle.py', 'simulate_step3.py', 'simulate_step3_file.py', 'e2e_simulation.py', 'e2e_phase3.py', 'e2e_phase4_5.py'
    ],
    'ops/runners': [
        'run_all.py', 'run_all_compliance.py', 'run_all_tests.py',
        'run_axis1.py', 'run_bg.py', 'run_check.py', 'run_checker.py',
        'run_e2e_step3.py', 'run_e2e_step3_safe.py', 'run_local_migrations.py',
        'run_migration.py', 'run_migrations_sub.py', 'run_migs.py',
        'run_pdf_test.py', 'run_seed.py', 'run_test.py'
    ],
    'tests/stray_tests': [
        'test_adv_report.py', 'test_alhusseiniya.py', 'test_api.py',
        'test_api_auth.py', 'test_apps.py', 'test_check.py', 'test_crop_plan_api.py',
        'test_crop_product_creation.py', 'test_django_boot.py', 'test_e2e_cycle.py',
        'test_emp.py', 'test_env.py', 'test_estimate.py', 'test_farm_id.py',
        'test_find.py', 'test_live_api.py', 'test_map.py', 'test_perennials.py',
        'test_perennials_pytest.py', 'test_phase10_compliance.py', 'test_print.py',
        'test_probes.py', 'test_qs.py', 'test_report.py', 'test_run.py',
        'test_runserver.py', 'test_signal.py', 'test_signal2.py',
        'test_ui_locally.py', 'test_variance_api.py', 'test_variety.py', 'sqlite_test.py'
    ]
};

function ensureDir(dir) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function processMoves() {
    console.log("=== BEGIN OMEGA-Z REFACTOR ===");
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
