import PlanningImportCenter from './planning/PlanningImportCenter'
import { useToast } from './ToastProvider'

export default function MasterPlanImportModal({ farmId, onClose, onSuccess }) {
  const toast = useToast()

  return (
    <PlanningImportCenter
      farmId={farmId}
      templateCode="planning_master_schedule"
      title="استيراد الخطة الرئيسية"
      description="استيراد الجدولة الرئيسية والخطط الموسمية من قالب Excel عربي RTL عبر المنصة الحاكمة."
      onClose={onClose}
      onApplied={onSuccess}
      addToast={toast}
    />
  )
}
