import PlanningImportCenter from './planning/PlanningImportCenter'
import { useToast } from './ToastProvider'

export default function CropPlanStructureImportModal({ planId, plan = {}, onClose, onSuccess }) {
  const toast = useToast()
  const farmId = typeof plan?.farm === 'object' ? plan.farm?.id : plan?.farm

  return (
    <PlanningImportCenter
      farmId={farmId}
      cropPlanId={planId}
      templateCode="planning_crop_plan_structure"
      title="استيراد الهيكل التشغيلي للخطة"
      description="استيراد صفوف الخطة التشغيلية والأنشطة المخططة من قالب Excel عربي RTL عبر المنصة الموحدة."
      onClose={onClose}
      onApplied={onSuccess}
      addToast={toast}
    />
  )
}
