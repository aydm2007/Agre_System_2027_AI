/**
 * [AGRI-GUARDIAN] Storybook Stories — CollapsibleCard Component
 */
import CollapsibleCard from '../components/CollapsibleCard.jsx'

export default {
  title: 'Core/CollapsibleCard',
  component: CollapsibleCard,
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component: 'بطاقة قابلة للطي — تُستخدم في Dashboard وصفحات التقارير لتنظيم البيانات.',
      },
    },
  },
  tags: ['autodocs'],
}

export const Expanded = {
  args: {
    title: 'ملخص الإنتاج اليومي',
    defaultOpen: true,
    children: 'إجمالي العمال: 45 | الأنشطة المنجزة: 12 | التكلفة: 125,000 ريال',
  },
}

export const Collapsed = {
  args: {
    title: 'التحليل المالي',
    defaultOpen: false,
    children: 'الإيرادات: 500,000 ريال | المصروفات: 350,000 ريال | صافي الربح: 150,000 ريال',
  },
}

export const WithBadge = {
  args: {
    title: 'تنبيهات الانحراف',
    badge: 3,
    defaultOpen: true,
    children: '⚠️ 3 انحرافات جديدة تحتاج مراجعة',
  },
}
