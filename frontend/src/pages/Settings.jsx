import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Farms } from '../api/client'
import FeedbackRegion from '../components/FeedbackRegion'
import OfflineQueuePanel from '../components/offline/OfflineQueuePanel.jsx'
import useApiRequest from '../hooks/useApiRequest'
import useFeedback from '../hooks/useFeedback'
import ar from '../i18n/ar'
import GroupManagement from './GroupManagement'
import UserManagement from './UserManagement'
import ApprovalRulesTab from './settings/ApprovalRulesTab'
import CostCentersTab from './settings/CostCentersTab'
import CropRecipesTab from './settings/CropRecipesTab'
import GovernanceTab from './settings/GovernanceTab'
import FarmSettingsTab from './settings/FarmSettingsTab'
import MembershipsTab from './settings/MembershipsTab'
import RoleTemplateMatrix from './settings/RoleTemplateMatrix'
import SharecroppingContractsTab from './settings/SharecroppingContractsTab'
import SupervisorsTab from './settings/SupervisorsTab'
import TeamBuilderTab from './settings/TeamBuilderTab'

const TEXT = ar.settings

const TABS = [
  { key: 'memberships', label: TEXT.membershipTab },
  { key: 'teamBuilder', label: 'باني الفريق (التفويض)' },
  { key: 'supervisors', label: TEXT.supervisorsTab },
  { key: 'users', label: TEXT.usersTab },
  { key: 'groups', label: 'مجموعات الصلاحيات' },
  { key: 'templates', label: 'قوالب الصلاحيات والربط' },
  { key: 'governance', label: 'الحوكمة والسياسات' },
  { key: 'farmSettings', label: 'إعدادات المزرعة' },
  { key: 'costCenters', label: 'مراكز التكلفة' },
  { key: 'approvalRules', label: 'قواعد الاعتمادات' },
  { key: 'cropRecipes', label: 'البصمة الزراعية' },
  { key: 'sharecropping', label: 'عقود الشراكة' },
  { key: 'offline', label: 'مزامنة دون اتصال' },
]

function normalizeFarmsPayload(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

export default function Settings() {
  const location = useLocation()
  const allowedTabs = useMemo(() => new Set(TABS.map((tab) => tab.key)), [])
  const [activeTab, setActiveTab] = useState(() => {
    const queryTab = new URLSearchParams(location.search).get('tab')
    return queryTab && allowedTabs.has(queryTab) ? queryTab : 'memberships'
  })
  const [farms, setFarms] = useState([])
  const [selectedFarmId, setSelectedFarmId] = useState('')
  const { execute: runFarmsRequest, loading: loadingFarms } = useApiRequest()

  const {
    message: globalMessage,
    error: globalError,
    showMessage: showGlobalMessage,
    showError: showGlobalError,
  } = useFeedback()

  const selectedFarm = useMemo(
    () => farms.find((farm) => String(farm.id) === String(selectedFarmId)) || null,
    [farms, selectedFarmId],
  )

  const hasFarms = farms.length > 0

  const loadFarms = useCallback(async () => {
    try {
      const data = await runFarmsRequest(async () => {
        const response = await Farms.list()
        return response.data
      })
      const nextFarms = normalizeFarmsPayload(data)
      setFarms(nextFarms)
      if (nextFarms.length > 0) {
        setSelectedFarmId((prev) => (prev ? prev : String(nextFarms[0].id)))
        showGlobalMessage('')
      } else {
        setSelectedFarmId('')
        showGlobalMessage(TEXT.noFarms)
      }
    } catch (err) {
      console.error('Failed to load farms', err)
      showGlobalError(TEXT.membersError)
      setFarms([])
      setSelectedFarmId('')
    }
  }, [runFarmsRequest, showGlobalError, showGlobalMessage])

  useEffect(() => {
    loadFarms()
  }, [loadFarms])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const queryTab = params.get('tab')
    if (queryTab && allowedTabs.has(queryTab)) {
      setActiveTab(queryTab)
    }
  }, [allowedTabs, location.search])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const queryFarm = params.get('farm')
    if (!queryFarm || !farms.length) return
    if (farms.some((farm) => String(farm.id) === String(queryFarm))) {
      setSelectedFarmId(String(queryFarm))
    }
  }, [farms, location.search])

  const handleSelectFarm = useCallback((value) => {
    setSelectedFarmId(value)
  }, [])

  return (
    <div data-testid="settings-page" className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{TEXT.pageTitle}</h1>
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-3">
          <label
            className="text-sm font-medium text-gray-700 dark:text-slate-300"
            htmlFor="settings-farm-select"
          >
            {TEXT.selectFarmLabel}
          </label>
          <select
            id="settings-farm-select"
            value={selectedFarmId}
            onChange={(event) => handleSelectFarm(event.target.value)}
            className="min-w-[10rem] rounded border bg-white p-2 text-sm dark:border-slate-600 dark:bg-slate-700 dark:text-white"
            disabled={!hasFarms}
          >
            {hasFarms ? (
              farms.map((farm) => (
                <option key={farm.id} value={farm.id}>
                  {farm.name}
                </option>
              ))
            ) : (
              <option value="">{loadingFarms ? TEXT.loading : TEXT.noFarms}</option>
            )}
          </select>
          <button
            type="button"
            onClick={loadFarms}
            className="rounded border border-gray-200 bg-white px-3 py-2 text-sm shadow-sm hover:bg-gray-50 dark:border-slate-600 dark:bg-slate-700 dark:text-white dark:hover:bg-slate-600"
          >
            {TEXT.refreshButton}
          </button>
        </div>
      </div>

      <FeedbackRegion error={globalError} message={globalMessage} />

      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            data-testid={`settings-tab-${tab.key}`}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${activeTab === tab.key ? 'bg-primary text-white shadow' : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'memberships' && (
        <MembershipsTab
          hasFarms={hasFarms}
          selectedFarmId={selectedFarmId}
          selectedFarmName={selectedFarm?.name}
        />
      )}

      {activeTab === 'teamBuilder' && (
        <TeamBuilderTab selectedFarmId={selectedFarmId} selectedFarmName={selectedFarm?.name} />
      )}
      {activeTab === 'supervisors' && <SupervisorsTab selectedFarmId={selectedFarmId} />}
      {activeTab === 'users' && <UserManagement key="users" />}
      {activeTab === 'groups' && <GroupManagement key="groups" />}
      {activeTab === 'templates' && <RoleTemplateMatrix key="templates" />}
      {activeTab === 'governance' && (
        <GovernanceTab selectedFarmId={selectedFarmId} hasFarms={hasFarms} />
      )}
      {activeTab === 'farmSettings' && (
        <FarmSettingsTab selectedFarmId={selectedFarmId} hasFarms={hasFarms} />
      )}
      {activeTab === 'costCenters' && (
        <CostCentersTab selectedFarmId={selectedFarmId} hasFarms={hasFarms} />
      )}
      {activeTab === 'approvalRules' && (
        <ApprovalRulesTab selectedFarmId={selectedFarmId} hasFarms={hasFarms} />
      )}
      {activeTab === 'cropRecipes' && (
        <CropRecipesTab selectedFarmId={selectedFarmId} hasFarms={hasFarms} />
      )}
      {activeTab === 'sharecropping' && (
        <SharecroppingContractsTab selectedFarmId={selectedFarmId} hasFarms={hasFarms} />
      )}
      {activeTab === 'offline' && <OfflineQueuePanel />}
    </div>
  )
}
