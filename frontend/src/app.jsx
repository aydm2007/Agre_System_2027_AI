import { Suspense, lazy, useMemo } from 'react'
import { Routes, Route, Navigate, Outlet, useNavigate } from 'react-router-dom'
import { Activity } from 'lucide-react'
import Nav from './components/Nav.jsx'
import PrivateRoute from './components/PrivateRoute.jsx'
import { AuthProvider, useAuth } from './auth/AuthContext.js'
import { FarmProvider } from './api/farmContext.jsx'
import { OpsRuntimeProvider } from './contexts/OpsRuntimeContext.jsx'
import { SettingsProvider } from './contexts/SettingsContext.jsx'
import { useSettings } from './contexts/SettingsContext.jsx'
import { OfflineQueueProvider } from './offline/OfflineQueueProvider.jsx'
import OfflineStatusBanner from './components/OfflineStatusBanner.jsx'
import { ToastProvider, useToast } from './components/ToastProvider'
import { ThemeProvider } from './contexts/ThemeContext.jsx'
import { useGlobalHotkeys } from './hooks/useGlobalHotkeys'
import ModeGuard from './components/ModeGuard.jsx'
import LiveNotificationToast from './components/LiveNotificationToast.jsx'

const loadingFallback = (
  <div className="p-4 space-y-3 animate-pulse" role="status" aria-label="جارٍ التحميل">
    <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded-xl w-48" />
    <div className="h-64 bg-gray-100 dark:bg-slate-800 rounded-2xl" />
    <span className="sr-only">جارٍ تحميل الصفحة...</span>
  </div>
)

const Login = lazy(() => import('./pages/Login.jsx'))
const Dashboard = lazy(() => import('./pages/Dashboard.jsx'))
const Farms = lazy(() => import('./pages/Farms.jsx'))
const FarmDetails = lazy(() => import('./pages/FarmDetails.jsx'))
const Crops = lazy(() => import('./pages/Crops.jsx'))
const CropCardsPage = lazy(() => import('./pages/CropCards.jsx'))
const ServiceProvidersList = lazy(() => import('./pages/ServiceCards.jsx'))
const ManageCatalogPage = lazy(() => import('./pages/ManageCatalog.jsx'))
const TemplateManagerPage = lazy(() => import('./pages/TemplateManager.jsx'))
const CropPlansPage = lazy(() => import('./pages/CropPlans.jsx'))
const CropPlanDetailPage = lazy(() => import('./pages/CropPlanDetail.jsx'))
const CropTasks = lazy(() => import('./pages/CropTasks.jsx'))
const DailyLog = lazy(() => import('./pages/DailyLog.jsx'))
const DailyLogHarvestLaunch = lazy(() => import('./pages/DailyLogHarvestLaunch.jsx'))
const DailyLogHistory = lazy(() => import('./pages/DailyLogHistory.jsx'))
const SimpleOperationsHub = lazy(() => import('./pages/SimpleOperationsHub.jsx'))
const Audit = lazy(() => import('./pages/Audit.jsx'))
const Reports = lazy(() => import('./pages/Reports/index.jsx'))
const AdvancedReports = lazy(() => import('./pages/Reports/AdvancedReports.jsx'))
const CustodyWorkspace = lazy(() => import('./pages/CustodyWorkspace.jsx'))
const TreeCensus = lazy(() => import('./pages/TreeCensus.jsx'))
const TreeInventory = lazy(() => import('./pages/TreeInventory.jsx'))
const LocationWellsPage = lazy(() => import('./pages/LocationWellsPage.jsx'))
const Settings = lazy(() => import('./pages/Settings.jsx'))
const NotFound = lazy(() => import('./pages/NotFound.jsx'))
const ResourceAnalyticsPage = lazy(() => import('./pages/ResourceAnalytics.jsx'))
const StockManagementPage = lazy(() => import('./pages/StockManagement.jsx'))
const MaterialsCatalogPage = lazy(() => import('./pages/MaterialsCatalog.jsx'))
const HarvestProductsPage = lazy(() => import('./pages/HarvestProducts/index.jsx'))
const CommercialDashboard = lazy(() => import('./pages/CommercialDashboard.jsx'))
const ContractOperationsDashboard = lazy(() => import('./pages/ContractOperationsDashboard.jsx'))
const FixedAssetsDashboard = lazy(() => import('./pages/FixedAssetsDashboard.jsx'))
const AssetsRegistry = lazy(() => import('./pages/AssetsRegistry.jsx'))
const AssetForm = lazy(() => import('./pages/AssetForm.jsx'))
const FuelReconciliationDashboard = lazy(() => import('./pages/FuelReconciliationDashboard.jsx'))
const ReceiptsDepositDashboard = lazy(
  () => import('./pages/Finance/ReceiptsDepositDashboard.jsx'),
)
const PettyCashDashboard = lazy(() => import('./pages/Finance/PettyCashDashboard.jsx'))
const SupplierSettlementDashboard = lazy(
  () => import('./pages/Finance/SupplierSettlementDashboard.jsx'),
)
const Sales = lazy(() => import('./pages/Sales.jsx'))
const PurchaseOrders = lazy(() => import('./pages/PurchaseOrders.jsx'))
const PurchaseOrderForm = lazy(() => import('./pages/PurchaseOrderForm.jsx'))
const Finance = lazy(() => import('./pages/Finance/index.jsx'))
const Employees = lazy(() => import('./pages/Employees/index.jsx'))
const ApprovalInbox = lazy(() => import('./pages/ApprovalInbox.jsx'))
const ProcurementApprovals = lazy(() => import('./pages/ProcurementApprovals.jsx'))
const VarianceAlerts = lazy(() => import('./pages/VarianceAlerts.jsx'))
const TreeVarianceAlerts = lazy(() => import('./pages/TreeVarianceAlerts.jsx'))
const PredictiveVariance = lazy(() => import('./pages/PredictiveVariance.jsx'))
const QRScanner = lazy(() => import('./pages/QRScanner.jsx'))
const SolarFleetMonitor = lazy(() => import('./pages/SolarFleetMonitor.jsx'))
const TimesheetPage = lazy(() => import('./pages/HR/TimesheetPage.jsx'))
const WorkerProductivity = lazy(() => import('./pages/HR/WorkerProductivity.jsx'))
const EmployeeAdvancesPage = lazy(() => import('./pages/HR/EmployeeAdvancesPage.jsx'))
const AuditLogExplorer = lazy(() => import('./pages/AuditLogExplorer.jsx'))

// ─── YECO Total Completion: Advanced GRP Modules ─────────────────────
const POSPage = lazy(() => import('./pages/POS/index.jsx'))
const POSTerminal = lazy(() => import('./pages/POS/index.jsx'))
const RFQManager = lazy(() => import('./pages/Procurement/index.jsx'))
const WarehouseManagement = lazy(() => import('./pages/Inventory/WarehouseManagement.jsx'))
const DynamicReportBuilder = lazy(() => import('./pages/Reports/index.jsx'))
const MaintenanceDashboard = lazy(() => import('./pages/Maintenance/index.jsx'))
const MaintenanceTasks = lazy(() => import('./pages/Maintenance/Tasks.jsx'))

function AppLayout() {
  const navigate = useNavigate()
  const toast = useToast()

  // [Protocol XVI] Persona Polish: Global Hotkeys
  useGlobalHotkeys({
    onHelp: () => toast.info('F1: المساعدة | F2: سجل جديد | Esc: رجوع'),
    onAction: () => navigate('/daily-log'),
    onCancel: () => {
      /* Handle global cancel/back if needed */
    },
  })

  return (
    <div className="container mx-auto p-4 space-y-4 elastic-entry">
      <header className="space-y-3 rounded-2xl border border-gray-200/80 bg-white/85 p-3 shadow-sm backdrop-blur sovereign-shimmer dark:border-slate-700/80 dark:bg-slate-900/75">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <img 
              src="/assets/logo_ye.png" 
              alt="YECO Logo" 
              className="w-12 h-12 object-contain drop-shadow-md"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
            <div>
              <h1 className="text-xl md:text-2xl font-bold text-text-primary">
                منصة إدارة الزراعة والمزارع (Agri-Guardian)
              </h1>
              <p className="text-[10px] text-gray-500 font-bold dark:text-gray-400">
                المؤسسة الاقتصادية اليمنية - قطاع الانتاج الزراعي والحيواني
              </p>
            </div>
          </div>
          <button 
            onClick={() => navigate('/daily-log')}
            className="btn-premium text-xs"
          >
            <Activity size={16} /> السجل اليومي السريع
          </button>
        </div>
        <Nav />
      </header>
      <OfflineStatusBanner />
      <LiveNotificationToast />
      <main className="min-h-[60vh]">
        <Suspense fallback={loadingFallback}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}

function AppRoutes() {
  const {
    isAdmin,
    is_superuser,
    canViewModel,
    isFarmRoleRestricted,
    userFarmIds,
  } = useAuth()
  const { isStrictMode, isPettyCashEnabled } = useSettings()

  const canAccessSettings = useMemo(
    () =>
      isAdmin ||
      is_superuser ||
      (!isFarmRoleRestricted && (canViewModel('user') || canViewModel('group'))),
    [canViewModel, isAdmin, isFarmRoleRestricted, is_superuser],
  )
  const hasOperationalFarmScope = useMemo(
    () => Array.isArray(userFarmIds) && userFarmIds.length > 0,
    [userFarmIds],
  )
  const canAccessCoreAgronomy = useMemo(
    () =>
      isAdmin ||
      is_superuser ||
      canViewModel('crop') ||
      (!isFarmRoleRestricted && hasOperationalFarmScope),
    [canViewModel, hasOperationalFarmScope, isAdmin, isFarmRoleRestricted, is_superuser],
  )
  const materialsCatalogRoutesEnabled = canAccessCoreAgronomy
  const canAccessFarmDirectory = useMemo(
    () =>
      isAdmin ||
      is_superuser ||
      canViewModel('farm') ||
      (!isFarmRoleRestricted && hasOperationalFarmScope),
    [canViewModel, hasOperationalFarmScope, isAdmin, isFarmRoleRestricted, is_superuser],
  )
  const defaultOperationalHome = isStrictMode ? <Dashboard /> : <SimpleOperationsHub />

  return (
    <Suspense fallback={loadingFallback}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<PrivateRoute />}>
          <Route path="/" element={<AppLayout />}>
            <Route index element={defaultOperationalHome} />
            <Route path="dashboard" element={defaultOperationalHome} />
            <Route path="simple-hub" element={<SimpleOperationsHub />} />

            {canAccessFarmDirectory && (
              <>
                <Route path="farms" element={<Farms />} />
                <Route path="farms/:id" element={<FarmDetails />} />
              </>
            )}

            {canAccessCoreAgronomy && (
              <>
                <Route path="crops" element={<Crops />} />
                <Route path="crop-cards" element={<CropCardsPage />} />
                <Route path="service-providers" element={<ServiceProvidersList />} />
                <Route path="crop-plans" element={<CropPlansPage />} />
                <Route path="crop-plans/:id" element={<CropPlanDetailPage />} />
                <Route path="catalog" element={<ManageCatalogPage />} />
                <Route path="template-manager" element={<TemplateManagerPage />} />
                <Route path="crops/:id/tasks" element={<CropTasks />} />
              </>
            )}

            {/* Financial routes — STRICT for ordinary users; SIMPLE stays technical/control-oriented */}
            <Route
              path="finance/supplier-settlements"
              element={<SupplierSettlementDashboard />}
            />
            <Route path="finance/receipts-deposits" element={<ReceiptsDepositDashboard />} />
            <Route
              path="finance/petty-cash"
              element={isPettyCashEnabled ? <PettyCashDashboard /> : <Navigate to="/dashboard" replace />}
            />
            <Route path="fuel-reconciliation" element={<FuelReconciliationDashboard />} />
            <Route element={<ModeGuard policyCheck="canRegisterFinancialRoutes" />}>
              <Route path="commercial" element={<CommercialDashboard />} />
              <Route path="harvest-products" element={<HarvestProductsPage />} />
              <Route path="sales/*" element={<Sales />} />
              <Route path="purchases" element={<PurchaseOrders />} />
              <Route path="purchases/new" element={<PurchaseOrderForm />} />
              <Route path="purchases/:id" element={<PurchaseOrderForm />} />
              <Route path="employees/*" element={<Employees />} />
              <Route path="hr/timesheets" element={<TimesheetPage />} />
              <Route path="hr/worker-kpi" element={<WorkerProductivity />} />
              <Route path="hr/advances" element={<EmployeeAdvancesPage />} />
            </Route>
            <Route element={<ModeGuard policyCheck="canAccessFinanceHubRoutes" />}>
              <Route path="finance/*" element={<Finance />} />
            </Route>

            <Route element={<ModeGuard policyCheck="canAccessContractRoutes" />}>
              <Route path="sharecropping" element={<ContractOperationsDashboard />} />
            </Route>

            <Route element={<ModeGuard policyCheck="canAccessFixedAssetRoutes" />}>
              <Route path="fixed-assets" element={<FixedAssetsDashboard />} />
              <Route path="assets" element={<AssetsRegistry />} />
              <Route path="assets/new" element={<AssetForm />} />
              <Route path="assets/:id" element={<AssetForm />} />
            </Route>

            {/* Non-financial strict routes — still require strictErpMode */}
            <Route element={<ModeGuard policyCheck="canRegisterStrictRoutes" />}>
              <Route path="resource-analytics" element={<ResourceAnalyticsPage />} />
            </Route>
            
            <Route element={<ModeGuard policyCheck="canAccessStockManagementRoutes" />}>
              <Route path="stock-management" element={<StockManagementPage />} />
            </Route>

            {/* Materials Catalog is broadly accessible for operations */}
            {materialsCatalogRoutesEnabled ? (
              <Route path="materials-catalog" element={<MaterialsCatalogPage />} />
            ) : (
              <Route path="materials-catalog" element={<ModeGuard requiredMode="STRICT" />} />
            )}

            <Route path="daily-log" element={<DailyLog />} />
            <Route path="daily-log/harvest" element={<DailyLogHarvestLaunch />} />
            <Route path="daily-log-history" element={<DailyLogHistory />} />
            <Route path="inventory/custody" element={<CustodyWorkspace />} />
            <Route path="approvals" element={<ApprovalInbox />} />
            <Route path="procurement-approvals" element={<ProcurementApprovals />} />
            <Route path="variance-alerts" element={<VarianceAlerts />} />
            <Route path="tree-variance-alerts" element={<TreeVarianceAlerts />} />
            <Route path="predictive-variance" element={<PredictiveVariance />} />

            {(canViewModel('auditlog') || isAdmin || is_superuser) && (
              <>
                <Route path="audit" element={<Audit />} />
                <Route path="audit-explorer" element={<AuditLogExplorer />} />
              </>
            )}

            <Route path="reports" element={<Reports />} />
            <Route path="reports/advanced" element={<AdvancedReports />} />
            <Route path="tree-census" element={<TreeCensus />} />
            <Route path="tree-inventory" element={<TreeInventory />} />

            {canAccessFarmDirectory && (
              <Route path="location-wells" element={<LocationWellsPage />} />
            )}

            <Route element={<ModeGuard policyCheck="canRegisterStrictRoutes" />}>
              <Route path="solar-monitor" element={<SolarFleetMonitor />} />
              <Route path="qr-scanner" element={<QRScanner />} />
              
              {/* YECO Advanced GRP: Strict Mode Entries */}
              <Route path="procurement/rfq" element={<RFQManager />} />
              <Route path="inventory/warehouse" element={<WarehouseManagement />} />
              <Route path="reports/builder" element={<DynamicReportBuilder />} />
            </Route>

            <Route element={<ModeGuard policyCheck="canRegisterFinancialRoutes" />}>
              <Route path="pos" element={<POSPage />} />
              <Route path="pos/terminal" element={<POSTerminal />} />
            </Route>

            <Route element={<ModeGuard policyCheck="canRegisterStrictRoutes" />}>
              <Route path="maintenance" element={<MaintenanceDashboard />} />
              <Route path="maintenance/tasks" element={<MaintenanceTasks />} />
            </Route>

            <Route
              path="settings"
              element={canAccessSettings ? <Settings /> : <Navigate to="/dashboard" replace />}
            />

            <Route path="*" element={<NotFound />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <FarmProvider>
            <SettingsProvider>
              <OfflineQueueProvider>
                <OpsRuntimeProvider>
                  <AppRoutes />
                </OpsRuntimeProvider>
              </OfflineQueueProvider>
            </SettingsProvider>
          </FarmProvider>
        </ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
