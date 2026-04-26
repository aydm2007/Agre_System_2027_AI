import { useEffect, useMemo, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useSettings } from '../contexts/SettingsContext'
import { ROLES } from '../auth/roles'
import {
  canAccessContractRoutes,
  canAccessFixedAssetRoutes,
  canAccessFuelReconciliationRoutes,
  canAccessTreasuryRoutes,
} from '../auth/modeAccess'
import ar from '../i18n/ar'
import ThemeToggle from './ui/ThemeToggle'

// Phase 12: Legacy DarkModeToggle removed, now using ThemeToggle component

const STRINGS = ar.nav

/**
 * [AGRI-GUARDIAN Axis 6 / AGENTS.md L30]
 * Financial interfaces bypass strict_erp_mode for these roles:
 *   - مدير النظام  (isSuperuser)
 *   - المدير المالي لقطاع المزارع  (hasFarmRole)
 */
const isFinancialRole = ({ isSuperuser, hasFarmRole }) =>
  isSuperuser ||
  (hasFarmRole &&
    (hasFarmRole(ROLES.SECTOR_FINANCE_MANAGER) ||
      hasFarmRole(ROLES.CHIEF_ACCOUNTANT) ||
      hasFarmRole(ROLES.FARM_ACCOUNTANT) ||
      hasFarmRole(ROLES.CASHIER) ||
      hasFarmRole(ROLES.FINANCIAL_AUDITOR)))

const isSalesRole = ({ isSuperuser, hasFarmRole }) =>
  isSuperuser || (hasFarmRole && hasFarmRole(ROLES.SALES_MANAGER))

const isInventoryRole = ({ isSuperuser, hasFarmRole }) =>
  isSuperuser ||
  (hasFarmRole && (hasFarmRole(ROLES.STOREKEEPER) || hasFarmRole(ROLES.PURCHASING_OFFICER)))

const baseNavItems = {
  simpleHub: {
    key: 'simple-hub',
    to: '/simple-hub',
    label: 'مركز العمليات',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M4 7h7v5H4zM13 4h7v8h-7zM4 14h7v6H4zM13 14h7v6h-7z" />
      </svg>
    ),
    visible: ({ strictErpMode }) => !strictErpMode,
  },
  dashboard: {
    key: 'dashboard',
    to: '/dashboard',
    label: STRINGS.dashboard,
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M3 13h4V3H3v10zm7 8h4V3h-4v18zm7-5h4V3h-4v13z" />
      </svg>
    ),
    visible: ({ strictErpMode }) => Boolean(strictErpMode),
  },
  approvals: {
    key: 'approvals',
    to: '/approvals',
    label: 'صندوق الاعتمادات (Inbox)',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
        <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
      </svg>
    ),
    visible: (ctx) => Boolean(ctx.strictErpMode),
  },
  varianceAlerts: {
    key: 'variance-alerts',
    to: '/variance-alerts',
    label: 'انحرافات التكاليف (Variance)',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
      </svg>
    ),
    // [AGRI-GUARDIAN FIX] User requested Deviations visible in BOTH modes 100%
    visible: () => true,
  },
  qrScanner: {
    key: 'qr-scanner',
    to: '/qr-scanner',
    label: 'الماسح الميداني (QR)',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0113.5 9.375v-4.5z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M6.75 6.75h.75v.75h-.75v-.75zM6.75 16.5h.75v.75h-.75v-.75zM16.5 6.75h.75v.75h-.75v-.75zM13.5 13.5h.75v.75h-.75v-.75zM13.5 19.5h.75v.75h-.75v-.75zM19.5 13.5h.75v.75h-.75v-.75zM19.5 19.5h.75v.75h-.75v-.75zM16.5 16.5h.75v.75h-.75v-.75z"
        />
      </svg>
    ),
    visible: ({ isAdmin, isSuperuser, strictErpMode }) =>
      Boolean(strictErpMode) && (isAdmin || isSuperuser),
  },
  predictiveVariance: {
    key: 'predictive-variance',
    to: '/predictive-variance',
    label: 'الانحرافات التنبؤية (Predictive)',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
        />
      </svg>
    ),
    // [AGRI-GUARDIAN FIX] User requested Deviations visible in BOTH modes 100%
    visible: () => true,
  },
  commercialDashboard: {
    key: 'commercial-dashboard',
    to: '/commercial',
    label: 'الرؤية التجارية Premium',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
    // Financial: visible to finance leadership ONLY in strict mode
    visible: (ctx) => ctx.strictErpMode && (isFinancialRole(ctx) || ctx.isAdmin),
  },
  sharecropping: {
    key: 'sharecropping',
    to: '/sharecropping',
    label: 'سندات الشراكة',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"
        />
      </svg>
    ),
    visible: (ctx) => ctx.contractRoutesEnabled,
  },
  reports: {
    key: 'reports',
    to: '/reports',
    label: STRINGS.reports,
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M4 4h16v16H4z" />
        <path d="M8 12h8M8 8h4M8 16h6" strokeLinecap="round" />
      </svg>
    ),
    visible: () => true,
  },
  reportBuilder: {
    key: 'report-builder',
    to: '/reports/builder',
    label: 'منشئ التقارير (BI)',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 20v-6M6 20V10M18 20V4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: (ctx) => ctx.strictErpMode && (ctx.isAdmin || isFinancialRole(ctx)),
  },
  dailyLog: {
    key: 'daily-log',
    to: '/daily-log',
    label: STRINGS.dailyLog,
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M4 5h16M4 12h16M4 19h16" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: () => true,
  },
  harvestEntry: {
    key: 'daily-log-harvest',
    to: '/daily-log/harvest',
    label: 'إدخال الحصاد',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M5 14c3-5 11-5 14 0" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M7 18c2-3 8-3 10 0" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="12" cy="8" r="3" />
      </svg>
    ),
    visible: () => true,
  },
  dailyLogHistory: {
    key: 'daily-log-history',
    to: '/daily-log-history',
    label: 'سجل الإنجاز',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <rect x="9" y="3" width="6" height="4" rx="1" />
        <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: () => true,
  },
  preventiveMaintenance: {
    key: 'preventive-maintenance',
    to: '/maintenance',
    label: 'الصيانة الوقائية',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
      </svg>
    ),
    visible: () => true,
  },
  audit: {
    key: 'audit',
    to: '/audit',
    label: STRINGS.audit,
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M12 3l8 4-8 4-8-4 8-4z" />
        <path d="M4 11l8 4 8-4" />
        <path d="M4 15l8 4 8-4" />
      </svg>
    ),
    visible: ({ canViewModel, isAdmin, isSuperuser, strictErpMode }) =>
      Boolean(strictErpMode) && (isAdmin || isSuperuser || canViewModel('auditlog')),
  },
  crops: {
    key: 'crops',
    to: '/crops',
    label: STRINGS.crops,
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M12 3c-1.5 2.5-1.5 4.5 0 6 1.5-1.5 1.5-3.5 0-6z" strokeLinecap="round" />
        <path d="M6 11c2.5 1.5 4.5 1.5 6 0-1.5-1.5-3.5-1.5-6 0z" strokeLinecap="round" />
        <path d="M18 11c-2.5 1.5-4.5 1.5-6 0 1.5-1.5 3.5-1.5 6 0z" strokeLinecap="round" />
        <path d="M12 9v12" strokeLinecap="round" />
      </svg>
    ),
    visible: ({ canViewModel, isAdmin, isSuperuser }) =>
      isAdmin || isSuperuser || canViewModel('crop'),
  },
  cropCards: {
    key: 'crop-cards',
    to: '/crop-cards',
    label: STRINGS.cropCards || 'بطاقات المحاصيل',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <rect x="3" y="4" width="8" height="14" rx="2" />
        <rect x="13" y="6" width="8" height="12" rx="2" />
        <path d="M6 8h2M16 10h2" strokeLinecap="round" />
      </svg>
    ),
    visible: ({ canViewModel, isAdmin, isSuperuser }) =>
      isAdmin || isSuperuser || canViewModel('crop'),
  },
  serviceCards: {
    key: 'service-cards',
    to: '/service-providers',
    label: 'المقاولين (Contractors)',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <rect x="3" y="4" width="8" height="14" rx="2" />
        <rect x="13" y="6" width="8" height="12" rx="2" />
        <path d="M7 8h2M17 10h2" strokeLinecap="round" />
      </svg>
    ),
    visible: ({ canViewModel, isAdmin, isSuperuser }) =>
      isAdmin || isSuperuser || canViewModel('crop'),
  },
  cropPlans: {
    key: 'crop-plans',
    to: '/crop-plans',
    label: STRINGS.cropPlans || 'خطط المحاصيل',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M4 7h16M4 12h10M4 17h8" strokeLinecap="round" />
        <rect x="4" y="4" width="16" height="16" rx="2" />
      </svg>
    ),
    visible: ({ canViewModel, isAdmin, isSuperuser }) =>
      isAdmin || isSuperuser || canViewModel('crop'),
  },
  catalog: {
    key: 'catalog',
    to: '/catalog',
    label: STRINGS.catalog || 'إدارة السجل الزراعي',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
        <path d="M9 7h6M9 12h6M9 17h3" strokeLinecap="round" />
      </svg>
    ),
    visible: ({ canAddModel, isAdmin, isSuperuser }) =>
      isAdmin || isSuperuser || canAddModel('crop') || canAddModel('task'),
  },
  harvestProducts: {
    key: 'harvest-products',
    to: '/harvest-products',
    label: STRINGS.harvestProducts || 'منتجات الحصاد',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M4 13c3-5 13-5 16 0" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M6 17c2-3 10-3 12 0" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="12" cy="7" r="3" />
      </svg>
    ),
    // Financial: visible to finance leadership even in simple mode
    visible: (ctx) =>
      ctx.strictErpMode &&
      (isFinancialRole(ctx) || ctx.isAdmin || ctx.canViewModel?.('cropproduct')),
  },
  farms: {
    key: 'farms',
    to: '/farms',
    label: STRINGS.farms,
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M3 21v-8l9-5 9 5v8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M9 21v-5h6v5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: ({ canViewModel, isAdmin, isSuperuser }) =>
      isAdmin || isSuperuser || canViewModel('farm'),
  },
  locationWells: {
    key: 'location-wells',
    to: '/location-wells',
    label: 'ربط المواقع بالآبار',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
      </svg>
    ),
    visible: ({ canViewModel, isAdmin, isSuperuser }) =>
      isAdmin || isSuperuser || canViewModel('farm'),
  },
  solarFleetMonitor: {
    key: 'solar-monitor',
    to: '/solar-monitor',
    label: 'رقابة الأصول الشمسية',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
        />
      </svg>
    ),
    visible: ({ isAdmin, isSuperuser, strictErpMode }) =>
      Boolean(strictErpMode) && (isAdmin || isSuperuser),
  },
  fixedAssets: {
    key: 'fixed-assets',
    label: 'الأصول الثابتة',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <rect x="4" y="5" width="16" height="14" rx="2" />
        <path d="M8 9h8M8 13h5" strokeLinecap="round" />
      </svg>
    ),
    children: [
      { to: '/fixed-assets', label: 'لوحة القيادة والمؤشرات' },
      { to: '/assets', label: 'سجل الأصول المدخلة' },
    ],
    visible: (ctx) => Boolean(ctx.strictErpMode) && ctx.fixedAssetRoutesEnabled,
  },
  fuelReconciliation: {
    key: 'fuel-reconciliation',
    to: '/fuel-reconciliation',
    label: 'مطابقة الوقود',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M9 3h6v5H9z" />
        <path d="M10 8h4v12a3 3 0 0 1-4 0V8z" />
        <path d="M14 10h2.5a1.5 1.5 0 0 1 1.5 1.5V16" strokeLinecap="round" />
      </svg>
    ),
    visible: (ctx) => ctx.fuelReconciliationRoutesEnabled,
  },
  materialsCatalog: {
    key: 'materials-catalog',
    to: '/materials-catalog',
    label: STRINGS.materialsCatalog || 'مواد التشغيل',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M4 6h16M4 12h12M4 18h8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: (ctx) =>
      ctx.isAdmin ||
      ctx.isSuperuser ||
      ctx.canViewModel?.('crop') ||
      (!ctx.isFarmRoleRestricted && Array.isArray(ctx.userFarmIds) && ctx.userFarmIds.length > 0),
  },
  custody: {
    key: 'custody',
    to: '/inventory/custody',
    label: 'عهدة المشرف',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M5 8h14v11H5z" />
        <path d="M9 8V6a3 3 0 0 1 6 0v2" strokeLinecap="round" />
        <path d="M9 13h6" strokeLinecap="round" />
      </svg>
    ),
    visible: (ctx) =>
      ctx.isAdmin ||
      ctx.isSuperuser ||
      isInventoryRole(ctx) ||
      (!ctx.isFarmRoleRestricted && Array.isArray(ctx.userFarmIds) && ctx.userFarmIds.length > 0),
  },
  stockManagement: {
    key: 'stock-management',
    to: '/stock-management',
    label: STRINGS.stockManagement || 'إدارة المخزون',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M4 9l8-5 8 5v9l-8 5-8-5z" />
        <path d="M12 4v16" />
      </svg>
    ),
    visible: (ctx) =>
      (Boolean(ctx.strictErpMode) || ctx.showStockInSimple) && (ctx.isAdmin || ctx.isSuperuser || isInventoryRole(ctx)),
  },
  warehouseBins: {
    key: 'warehouse-bins',
    to: '/inventory/warehouse',
    label: 'إدارة المواقع (Bins)',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line x1="12" y1="22.08" x2="12" y2="12" />
      </svg>
    ),
    visible: (ctx) => ctx.strictErpMode && (ctx.isAdmin || isInventoryRole(ctx)),
  },
  resourceAnalytics: {
    key: 'resource-analytics',
    to: '/resource-analytics',
    label: STRINGS.resourceAnalytics || 'تحليلات الموارد',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M4 14h10v6H4z" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M8 10V4h12v6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: (ctx) =>
      Boolean(ctx.strictErpMode) && (ctx.isAdmin || ctx.isSuperuser || isInventoryRole(ctx)),
  },
  treeCensus: {
    key: 'tree-census',
    to: '/tree-census',
    label: 'جرد الأشجار التفصيلي',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          d="M12 3c2.5 0 4.5 2 4.5 4.5a4.5 4.5 0 0 1-1.8 3.6H18l-4 4h2l-4 5-4-5h2l-4-4h3.3a4.5 4.5 0 0 1-1.8-3.6C7.5 5 9.5 3 12 3z"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
    visible: () => true,
  },
  treeVarianceAlerts: {
    key: 'tree-variance-alerts',
    to: '/tree-variance-alerts',
    label: 'تنبيهات الفاقد الشجري',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
    ),
    // [AGRI-GUARDIAN FIX] User requested Deviations visible in BOTH modes 100%
    visible: () => true,
  },
  settings: {
    key: 'settings',
    to: '/settings',
    label: STRINGS.settings,
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6z" />
        <path d="M3 21a9 9 0 0 1 18 0" />
      </svg>
    ),
    visible: ({ canViewModel, isAdmin, isSuperuser, isFarmRoleRestricted }) =>
      isAdmin ||
      isSuperuser ||
      (!isFarmRoleRestricted && (canViewModel('user') || canViewModel('group'))),
  },
  sales: {
    key: 'sales',
    to: '/sales',
    label: 'فواتير المبيعات',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
    // Unified Visibility: Everyone allowed by role, but ONLY in Strict Mode
    visible: (ctx) => ctx.strictErpMode && (isSalesRole(ctx) || isFinancialRole(ctx) || ctx.isAdmin),
  },
  posTerminal: {
    key: 'pos-terminal',
    to: '/pos/terminal',
    label: 'نقطة البيع (POS)',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="2" y="4" width="20" height="16" rx="2" />
        <path d="M7 15h10M7 11h10" strokeLinecap="round" />
        <path d="M2 9h20" />
      </svg>
    ),
    visible: (ctx) => ctx.strictErpMode && (isSalesRole(ctx) || isFinancialRole(ctx) || ctx.isAdmin),
  },
  purchases: {
    key: 'purchases',
    to: '/purchases',
    label: 'طلبات الشراء',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path
          d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <circle cx="9" cy="21" r="1" />
        <circle cx="20" cy="21" r="1" />
      </svg>
    ),
    visible: (ctx) => ctx.strictErpMode && (isInventoryRole(ctx) || isFinancialRole(ctx) || ctx.isAdmin),
  },
  rfqManager: {
    key: 'rfq-manager',
    to: '/procurement/rfq',
    label: 'إدارة المناقصات (RFQ)',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
        <rect x="8" y="2" width="8" height="4" rx="1" />
        <path d="M9 14h6M9 18h6M9 10h6" strokeLinecap="round" />
      </svg>
    ),
    visible: (ctx) => ctx.strictErpMode && (ctx.isAdmin || isInventoryRole(ctx)),
  },
  finance: {
    key: 'finance',
    to: '/finance',
    label: 'المالية والدفتر',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M2 3h6v18H2zM16 3h6v18h-6z" strokeLinecap="round" strokeLinejoin="round" />
        <path
          d="M8 6h8v3H8zM8 12h8v3H8zM8 18h8v3H8z"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
    // Unified Visibility: Everyone allowed by role, but ONLY in Strict Mode or if enabled in Simple mode
    visible: (ctx) => (ctx.strictErpMode || ctx.showFinanceInSimple) && (isFinancialRole(ctx) || ctx.isAdmin),
  },
  financialReports: {
    key: 'financial-reports',
    to: '/finance/reports',
    label: 'تقارير الأرباح والميزانية',
    icon: (
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M21.21 15.89A10 10 0 1 1 8 2.83" />
        <path d="M22 12A10 10 0 0 0 12 2v10z" />
      </svg>
    ),
    visible: (ctx) => (ctx.strictErpMode || ctx.showFinanceInSimple) && (isFinancialRole(ctx) || ctx.isAdmin),
  },
  makerChecker: {
    key: 'maker-checker',
    to: '/finance/approvals',
    label: 'الاعتماد المالي',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" strokeLinecap="round" strokeLinejoin="round" />
        <polyline points="22 4 12 14.01 9 11.01" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: (ctx) => ctx.treasuryRoutesEnabled,
  },
  varianceAnalysisBI: {
    key: 'variance-analysis-bi',
    to: '/finance/variance-analysis',
    label: 'تحليل الانحراف',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <line x1="18" y1="20" x2="18" y2="10" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="12" y1="20" x2="12" y2="4" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="6" y1="20" x2="6" y2="14" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: (ctx) => ctx.treasuryRoutesEnabled && ctx.isPettyCashEnabled,
  },
  payrollSettlement: {
    key: 'payroll-settlement',
    to: '/finance/payroll-settlement',
    label: 'تصفية الرواتب',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <rect x="2" y="6" width="20" height="12" rx="2" />
        <circle cx="12" cy="12" r="2" />
        <path d="M6 12h.01M18 12h.01" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    visible: (ctx) => ctx.strictErpMode && (isFinancialRole(ctx) || ctx.isAdmin),
  },
  treasury: {
    key: 'treasury',
    to: '/finance/treasury',
    label: 'الخزينة',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M7 8h10M7 12h10M7 16h6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    // Financial: visible to finance leadership even in simple mode
    visible: (ctx) => ctx.strictErpMode && (isFinancialRole(ctx) || ctx.isAdmin),
  },
  pettyCash: {
    key: 'petty-cash',
    to: '/finance/petty-cash',
    label: 'العهد النقدية',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
      </svg>
    ),
    visible: (ctx) => ctx.strictErpMode && (isFinancialRole(ctx) || ctx.isAdmin),
  },
  employees: {
    key: 'employees',
    to: '/employees',
    label: 'الموظفين والرواتب',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <circle cx="12" cy="7" r="4" />
        <path d="M5.5 21a6.5 6.5 0 0 1 13 0" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    // Financial: visible to finance leadership even in simple mode if toggle enabled
    visible: (ctx) => (ctx.strictErpMode || ctx.showEmployeesInSimple) && (isFinancialRole(ctx) || ctx.isAdmin),
  },
  advancedReports: {
    key: 'advanced-reports',
    to: '/finance/advanced-reports',
    label: 'التقارير المالية المتقدمة',
    icon: (
      <svg
        className="h-4 w-4"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="16" y1="13" x2="8" y2="13" strokeLinecap="round" strokeLinejoin="round" />
        <line x1="16" y1="17" x2="8" y2="17" strokeLinecap="round" strokeLinejoin="round" />
        <polyline points="10 9 9 9 8 9" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
    // Financial: visible to finance leadership even in simple mode
    visible: (ctx) => ctx.strictErpMode && (isFinancialRole(ctx) || ctx.isAdmin),
  },
}

const navSections = [
  {
    key: 'overview',
    title: 'الرئيسية',
    description: 'نظرة عامة وتنبيهات',
    items: [
      'simpleHub',
      'dashboard',
      'qrScanner',
      'approvals',
      'varianceAlerts',
      'predictiveVariance',
      'commercialDashboard',
      'sales',
      'purchases',
      'makerChecker',
      'finance',
      'varianceAnalysisBI',
      'payrollSettlement',
      'treasury',
      'pettyCash',
      'employees',
      'advancedReports',
      'reports',
      'stockManagement',
    ],
  },
  {
    key: 'production',
    title: 'الإنتاج اليومي',
    description: 'إدخال الأنشطة ومراجعة الطابور',
    items: ['dailyLog', 'dailyLogHistory', 'audit'],
  },
  {
    key: 'crops',
    title: 'إدارة المحاصيل',
    description: 'مهام المحاصيل والمنتجات والقوالب',
    items: ['crops', 'cropCards', 'serviceCards', 'cropPlans', 'catalog', 'harvestProducts'],
  },
  {
    key: 'farms',
    title: 'المزارع والموارد',
    description: 'الأصول، الآبار، المخزون والتحليلات',
    items: [
      'farms',
      'locationWells',
      'materialsCatalog',
      'resourceAnalytics',
      'solarFleetMonitor',
      'fixedAssets',
      'fuelReconciliation',
    ],
  },
  {
    key: 'hr',
    title: 'الموارد البشرية',
    description: 'الموظفين والحضور والسلف',
    items: ['employees'],
  },
  {
    key: 'perennial',
    title: 'الأعمال المعمرة',
    description: 'جرد الأشجار وتغطيات الخدمة',
    items: ['treeCensus', 'treeVarianceAlerts'],
  },
  { key: 'settings', title: 'الإعدادات', description: 'الصلاحيات والتكاملات', items: ['settings'] },
]

const buildLinkClassName = (isActive, extra = '') =>
  [
    'flex h-9 items-center gap-2 rounded-xl px-3 transition-colors whitespace-nowrap text-xs font-semibold md:text-sm rtl:flex-row-reverse',
    extra,
    isActive
      ? 'bg-primary text-white shadow-sm'
      : 'bg-slate-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-primary/10 dark:hover:bg-primary/20',
  ].join(' ')

const buildTabClassName = (isActive) =>
  [
    'h-10 min-w-[132px] rounded-xl px-3 text-xs font-semibold transition-colors md:text-sm',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
    isActive
      ? 'bg-primary text-white shadow-sm'
      : 'bg-white/80 text-slate-600 hover:bg-primary/10 dark:bg-slate-800/70 dark:text-slate-200 dark:hover:bg-primary/20',
  ].join(' ')

export default function Nav() {
  const navigate = useNavigate()
  const auth = useAuth()
  const {
    settings,
    isStrictMode,
    contractMode,
    treasuryVisibility,
    fixedAssetMode,
    isPettyCashEnabled,
  } = useSettings()

  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [expandedSections, setExpandedSections] = useState(() => {
    const stored =
      typeof window !== 'undefined' ? window.localStorage.getItem('nav_sections_state') : null
    return stored ? JSON.parse(stored) : navSections.map((section) => section.key)
  })

  const navContext = useMemo(
    () => ({
      ...auth,
      strictErpMode: isStrictMode,
      treasuryRoutesEnabled: canAccessTreasuryRoutes({
        strictErpMode: isStrictMode,
        treasuryVisibility,
        isAdmin: auth.isAdmin,
        isSuperuser: auth.isSuperuser,
        hasFarmRole: auth.hasFarmRole,
      }),
      contractRoutesEnabled: canAccessContractRoutes({
        contractMode,
        strictErpMode: isStrictMode,
        isAdmin: auth.isAdmin,
        isSuperuser: auth.isSuperuser,
        hasFarmRole: auth.hasFarmRole,
      }),
      fixedAssetRoutesEnabled: canAccessFixedAssetRoutes({
        fixedAssetMode,
        strictErpMode: isStrictMode,
        isAdmin: auth.isAdmin,
        isSuperuser: auth.isSuperuser,
        hasFarmRole: auth.hasFarmRole,
      }),
      fuelReconciliationRoutesEnabled: canAccessFuelReconciliationRoutes({
        strictErpMode: isStrictMode,
        isAdmin: auth.isAdmin,
        isSuperuser: auth.isSuperuser,
        hasFarmRole: auth.hasFarmRole,
      }),
      isPettyCashEnabled,
      showFinanceInSimple: settings?.show_finance_in_simple,
      showStockInSimple: settings?.show_stock_in_simple,
      showEmployeesInSimple: settings?.show_employees_in_simple,
    }),
    [auth, contractMode, fixedAssetMode, isPettyCashEnabled, isStrictMode, treasuryVisibility, settings?.show_finance_in_simple, settings?.show_stock_in_simple, settings?.show_employees_in_simple],
  )

  const visibleSections = useMemo(() => {
    return navSections
      .map((section) => {
        const items = section.items
          .map((key) => baseNavItems[key])
          .filter((item) => item && item.visible(navContext))
        return items.length ? { ...section, items } : null
      })
      .filter(Boolean)
  }, [navContext])

  const [activeSectionKey, setActiveSectionKey] = useState(() => {
    const stored =
      typeof window !== 'undefined' ? window.localStorage.getItem('nav_active_section') : null
    return stored || ''
  })

  useEffect(() => {
    if (!visibleSections.length) {
      return
    }
    const hasActive = visibleSections.some((section) => section.key === activeSectionKey)
    if (!hasActive) {
      setActiveSectionKey(visibleSections[0].key)
    }
  }, [activeSectionKey, visibleSections])

  useEffect(() => {
    if (typeof window !== 'undefined' && activeSectionKey) {
      window.localStorage.setItem('nav_active_section', activeSectionKey)
    }
  }, [activeSectionKey])

  const activeSection = useMemo(
    () => visibleSections.find((section) => section.key === activeSectionKey) || visibleSections[0],
    [activeSectionKey, visibleSections],
  )

  const toggleSection = (key) => {
    setExpandedSections((prev) => {
      const exists = prev.includes(key)
      const next = exists ? prev.filter((item) => item !== key) : [...prev, key]
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('nav_sections_state', JSON.stringify(next))
      }
      return next
    })
  }

  const handleLogout = () => {
    auth.logout()
    setIsMenuOpen(false)
    navigate('/login', { replace: true })
  }

  const renderNavLink = (item, extra = '') => (
    <NavLink
      key={item.key}
      to={item.to}
      className={({ isActive }) => buildLinkClassName(isActive, extra)}
      onClick={() => setIsMenuOpen(false)}
      title={item.label}
      aria-label={item.label}
    >
      <span className="text-primary-600" aria-hidden="true">{item.icon}</span>
      <span className="truncate">{item.label}</span>
    </NavLink>
  )

  return (
    <nav className="relative z-20 rounded-2xl border border-gray-200/90 bg-gradient-to-b from-white to-slate-50/85 p-3 shadow-sm backdrop-blur dark:border-slate-700/90 dark:from-slate-800 dark:to-slate-900/90">
      <div className="flex items-start justify-between gap-3 md:gap-4">
        <button
          type="button"
          className="flex items-center gap-2 rounded-xl border border-primary/30 bg-primary/10 px-3 py-2 text-xs font-semibold text-primary-700 transition-colors hover:bg-primary/20 md:hidden"
          onClick={() => setIsMenuOpen((prev) => !prev)}
          aria-expanded={isMenuOpen}
          aria-controls="primary-navigation"
        >
          <svg
            className="h-5 w-5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>القوائم</span>
        </button>

        <div className="hidden min-w-0 flex-1 flex-col gap-3 md:flex">
          {isStrictMode && (
            <NavLink
              to="/qr-scanner"
              className="flex h-10 w-fit items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-white shadow-md transition-all hover:bg-primary-600 hover:shadow-lg focus:ring-4 focus:ring-primary/30 active:scale-95"
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 013.75 9.375v-4.5zM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 01-1.125-1.125v-4.5zM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0113.5 9.375v-4.5z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6.75 6.75h.75v.75h-.75v-.75zM6.75 16.5h.75v.75h-.75v-.75zM16.5 6.75h.75v.75h-.75v-.75zM13.5 13.5h.75v.75h-.75v-.75zM13.5 19.5h.75v.75h-.75v-.75zM19.5 13.5h.75v.75h-.75v-.75zM19.5 19.5h.75v.75h-.75v-.75zM16.5 16.5h.75v.75h-.75v-.75z"
                />
              </svg>
              <span className="truncate tracking-wide">مسح QR</span>
            </NavLink>
          )}

          <div className="rounded-2xl border border-slate-200/70 bg-white/80 p-2 shadow-sm dark:border-slate-700/80 dark:bg-slate-800/70">
            <div
              className="flex gap-2 overflow-x-auto pb-1"
              role="tablist"
              aria-label="أقسام التنقل الرئيسية"
            >
              {visibleSections.map((section) => {
                const isActive = activeSection?.key === section.key
                return (
                  <button
                    key={section.key}
                    type="button"
                    role="tab"
                    id={`tab-${section.key}`}
                    aria-selected={isActive}
                    aria-controls={`panel-${section.key}`}
                    className={buildTabClassName(isActive)}
                    onClick={() => setActiveSectionKey(section.key)}
                  >
                    {section.title}
                  </button>
                )
              })}
            </div>
          </div>

          {activeSection && (
            <section
              id={`panel-${activeSection.key}`}
              role="tabpanel"
              aria-labelledby={`tab-${activeSection.key}`}
              className="min-h-[220px] max-h-[290px] overflow-y-auto rounded-2xl border border-slate-200/70 bg-white/80 p-3 shadow-sm dark:border-slate-700/80 dark:bg-slate-800/70"
            >
              <div className="mb-2 text-right">
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                  {activeSection.title}
                </p>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  {activeSection.description}
                </p>
              </div>
              <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
                {activeSection.items.map((item) =>
                  renderNavLink(item, 'justify-between flex-row-reverse text-right'),
                )}
              </div>
            </section>
          )}
        </div>

        <div className="flex items-center gap-2 self-start">
          {/* Phase 12: Theme Toggle (Light/Dark/System) */}
          <ThemeToggle />
          <button
            onClick={handleLogout}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 text-red-600 transition-colors hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 md:h-11 md:w-11"
            type="button"
            title={STRINGS.logout}
            aria-label={STRINGS.logout}
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path d="M15 3h4v18h-4" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M10 17l5-5-5-5" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M4 12h11" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span className="sr-only">{STRINGS.logout}</span>
          </button>
        </div>
      </div>

      <div
        id="primary-navigation"
        className={`${isMenuOpen ? 'mt-3 space-y-4' : 'hidden'} md:hidden`}
      >
        {visibleSections.map((section) => (
          <div
            key={section.key}
            className="rounded-2xl border border-slate-200/70 bg-white/90 p-3 shadow-sm dark:border-slate-700 dark:bg-slate-800/90"
          >
            <button
              type="button"
              className="flex w-full items-center justify-between text-start"
              onClick={() => toggleSection(section.key)}
            >
              <div>
                <p className="text-xs font-semibold text-gray-500">{section.title}</p>
                <p className="text-[11px] text-gray-400">{section.description}</p>
              </div>
              <svg
                className={`h-4 w-4 transition-transform ${expandedSections.includes(section.key) ? 'rotate-180' : ''}`}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            {expandedSections.includes(section.key) && (
              <div className="mt-2 space-y-2">
                {section.items.map((item) => renderNavLink(item, 'w-full justify-between'))}
              </div>
            )}
          </div>
        ))}
      </div>
    </nav>
  )
}
