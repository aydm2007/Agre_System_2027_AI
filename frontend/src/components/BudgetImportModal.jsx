import PlanningImportCenter from './planning/PlanningImportCenter'
import { useToast } from './ToastProvider'

export default function BudgetImportModal({ planId, plan = {}, onClose, onSuccess }) {
  const toast = useToast()
  const farmId = typeof plan?.farm === 'object' ? plan.farm?.id : plan?.farm

  return (
    <PlanningImportCenter
      farmId={farmId}
      cropPlanId={planId}
      templateCode="planning_crop_plan_budget"
      title="استيراد ميزانية الخطة"
      description="استيراد بنود الميزانية المرتبطة بالخطة الزراعية عبر قالب Excel حاكم. هذا المسار يخضع لسياسة STRICT فقط."
      onClose={onClose}
      onApplied={onSuccess}
      addToast={toast}
    />
  )
}
