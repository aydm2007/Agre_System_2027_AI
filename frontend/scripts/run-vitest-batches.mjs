import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const vitestEntrypoint = path.join(frontendDir, 'node_modules', 'vitest', 'vitest.mjs')

const batches = [
  {
    name: 'Core mode and utility tests',
    files: [
      'tests/offlineQueue.test.js',
      'tests/NavVisibility.test.js',
      'tests/ApprovalButton.test.jsx',
      'src/auth/__tests__/modeAccess.test.js',
      'src/auth/__tests__/modeAccessExtended.test.js',
      'src/utils/__tests__/decimal.test.js',
      'src/hooks/__tests__/useFinancialFilters.test.js',
      'src/hooks/__tests__/useDailyLogForm.test.js',
      'src/hooks/__tests__/dailyLog.integration.test.js',
      'src/services/OfflineHarvestService.test.js',
      'src/services/ChaosNetworkSimulator.test.js',
    ],
  },
  {
    name: 'Daily execution and agronomy tests',
    files: [
      'tests/treeInventory-ui.test.jsx',
      'src/components/daily-log/__tests__/DailyLogSmartCard.test.jsx',
      'src/components/daily-log/__tests__/DailyLogResources.test.jsx',
      'src/components/daily-log/__tests__/ActivityItemsField.test.jsx',
      'src/pages/__tests__/DailyLogHistory.test.jsx',
      'src/pages/__tests__/ServiceCards.test.jsx',
    ],
  },
  {
    name: 'Governed finance dashboards',
    files: [
      'src/pages/Finance/__tests__/PettyCashDashboard.test.jsx',
      'src/pages/Finance/__tests__/SupplierSettlementDashboard.test.jsx',
      'src/pages/Finance/__tests__/ReceiptsDepositDashboard.test.jsx',
      'src/pages/Finance/__tests__/LedgerList.test.jsx',
      'src/pages/Finance/__tests__/AdvancedReportsScreen.test.jsx',
      'src/pages/Finance/__tests__/reportParams.test.js',
      'src/pages/Reports/__tests__/reportParams.test.js',
    ],
  },
  {
    name: 'Mode-aware operational dashboards',
    files: [
      'src/pages/__tests__/ContractOperationsDashboard.test.jsx',
      'src/pages/__tests__/FixedAssetsDashboard.test.jsx',
      'src/pages/__tests__/FuelReconciliationDashboard.test.jsx',
      'src/pages/__tests__/CommercialDashboard.test.jsx',
      'src/components/Sales/SalesForm.test.jsx',
    ],
  },
]

const nodeArgsPrefix = mergeNodeArgs(process.execArgv, ['--max-old-space-size=6144'])

for (const batch of batches) {
  console.log(`\n==> ${batch.name}`)
  for (const file of batch.files) {
    console.log(`--> ${file}`)
    const result = spawnSync(
      process.execPath,
      [...nodeArgsPrefix, vitestEntrypoint, '--run', file],
      {
        cwd: frontendDir,
        env: process.env,
        stdio: 'inherit',
      },
    )

    if (result.error) {
      console.error(`[FAIL] ${file}: ${result.error.message}`)
      process.exit(1)
    }
    if (result.status !== 0) {
      process.exit(result.status ?? 1)
    }
  }
}

console.log('\n[SUCCESS] All Vitest CI batches passed.')

function mergeNodeArgs(currentArgs, requiredArgs) {
  const merged = [...currentArgs]
  for (const arg of requiredArgs) {
    if (!merged.includes(arg)) {
      merged.push(arg)
    }
  }
  return merged
}
