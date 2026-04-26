/* eslint-disable */
const fs = require('fs')
const path = require('path')

const navPath = path.join(__dirname, 'src', 'components', 'Nav.jsx')
let nav = fs.readFileSync(navPath, 'utf8')

// Replace all isFinanceLeader with isFinancialRole
nav = nav.replace(/isFinanceLeader/g, 'isFinancialRole')

// Fix 'isSalesRole' unused warning
nav = nav.replace(
  /(key:\s*'sales'[\s\S]*?)visible:\s*\(ctx\)\s*=>\s*isFinancialRole\(ctx\)\s*\|\|\s*ctx\.isAdmin/g,
  '$1visible: (ctx) => isSalesRole(ctx) || isFinancialRole(ctx) || ctx.isAdmin',
)

// Fix 'isInventoryRole' unused warning in stockManagement and materialsCatalog
nav = nav.replace(
  /(key:\s*'stock-management'[\s\S]*?)visible:\s*\(\{\s*isAdmin,\s*isSuperuser,\s*strictErpMode\s*\}\)\s*=>([\s\S]*?)(?=,)/g,
  '$1visible: ({ isAdmin, isSuperuser, strictErpMode, hasFarmRole }) =>$2 || isInventoryRole({ isSuperuser, hasFarmRole })',
)

nav = nav.replace(
  /(key:\s*'materials-catalog'[\s\S]*?)visible:\s*\(\{\s*isAdmin,\s*isSuperuser,\s*strictErpMode\s*\}\)\s*=>([\s\S]*?)(?=,)/g,
  '$1visible: ({ isAdmin, isSuperuser, strictErpMode, hasFarmRole }) =>$2 || isInventoryRole({ isSuperuser, hasFarmRole })',
)

fs.writeFileSync(navPath, nav, 'utf8')

const modePath = path.join(__dirname, 'src', 'auth', 'modeAccess.js')
let mode = fs.readFileSync(modePath, 'utf8')
mode = mode.replace(
  /export function canRegisterFinancialRoutes\(\{ strictErpMode, isAdmin, isSuperuser, hasFarmRole \}\) \{/g,
  'export function canRegisterFinancialRoutes({ _strictErpMode, isAdmin, isSuperuser, hasFarmRole }) {',
)
fs.writeFileSync(modePath, mode, 'utf8')

console.log('Patch applied successfully.')
