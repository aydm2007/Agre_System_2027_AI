export function applyArabicEnterpriseShell() {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.lang = 'ar'
  root.dir = 'rtl'
  root.dataset.locale = 'ar-YE'
  root.dataset.timezone = 'Asia/Aden'
  root.classList.add('rtl')
}
