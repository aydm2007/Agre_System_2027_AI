/**
 * [AGRI-GUARDIAN] Storybook Stories — Modal Component
 */
import Modal from '../components/Modal.jsx'

export default {
  title: 'Core/Modal',
  component: Modal,
  parameters: {
    layout: 'centered',
    docs: {
      description: { component: 'مكون النافذة المنبثقة — يُستخدم في كل عمليات الإدخال والتأكيد.' },
    },
  },
  tags: ['autodocs'],
}

export const Open = {
  args: {
    isOpen: true,
    onClose: () => console.log('Modal closed'),
    title: 'تأكيد العملية',
    children: 'هل أنت متأكد من تنفيذ هذا الإجراء؟',
  },
}

export const WithLongContent = {
  args: {
    isOpen: true,
    onClose: () => console.log('Modal closed'),
    title: 'تفاصيل القيد المالي',
    children:
      'قيد رقم: 12345\nالمبلغ: 50,000 ريال\nالتاريخ: 2026-03-06\nالوصف: مصاريف تشغيلية — أسمدة ومبيدات\nمركز التكلفة: مزرعة سردود — الموقع 3\nحالة الاعتماد: معلّق',
  },
}

export const Closed = {
  args: {
    isOpen: false,
    onClose: () => {},
    title: 'عنوان',
    children: 'محتوى',
  },
}
