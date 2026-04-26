// دالة لتوليد كود للموقع
export function generateLocationCode(type, farmId) {
  const prefixMap = {
    'Field': 'Fi',
    'Protected': 'Pr',
    'Orchard': 'Or',
    'Grain': 'Gr',
    'Service': 'Se'
  }

  const prefix = prefixMap[type] || 'Lo'
  return `${prefix}-${farmId}-${Math.floor(Math.random() * 100)}`
}
