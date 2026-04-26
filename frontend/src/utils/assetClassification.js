const normalizeText = (value) =>
  String(value || '')
    .trim()
    .toLowerCase()

const assetText = (asset) =>
  [
    asset?.category,
    asset?.type,
    asset?.asset_type,
    asset?.category_display,
    asset?.type_display,
    asset?.name,
  ]
    .map(normalizeText)
    .filter(Boolean)
    .join(' ')

export const getAssetFarmId = (asset) =>
  asset?.farm_id ?? asset?.farm?.id ?? asset?.farm ?? asset?.farmId ?? null

export const isWellLikeAsset = (asset) => {
  const text = assetText(asset)
  if (!text) return false
  return (
    text.includes('well') ||
    text.includes('irrig') ||
    text.includes('pump') ||
    text.includes('bore') ||
    text.includes('بئر') ||
    text.includes('آبار') ||
    text.includes('مضخ') ||
    text.includes('ري')
  )
}

export const isExcludedNonMachineAsset = (asset) => {
  const text = assetText(asset)
  if (!text) return false
  return (
    isWellLikeAsset(asset) ||
    text.includes('solar') ||
    text.includes('building') ||
    text.includes('facility') ||
    text.includes('مبنى') ||
    text.includes('منش') ||
    text.includes('شمسي')
  )
}

export const isMachineLikeAsset = (asset) => {
  const text = assetText(asset)
  if (!text) return false
  if (isExcludedNonMachineAsset(asset)) {
    return false
  }
  return (
    text.includes('machine') ||
    text.includes('machinery') ||
    text.includes('tractor') ||
    text.includes('equipment') ||
    text.includes('vehicle') ||
    text.includes('generator') ||
    text.includes('sprayer') ||
    text.includes('جرار') ||
    text.includes('آلة') ||
    text.includes('معدات') ||
    text.includes('معدة') ||
    text.includes('مركبة') ||
    text.includes('مولد') ||
    text.includes('رش')
  )
}

export const isOperationalMachineAsset = (asset) => {
  if (!asset) return false
  if (isMachineLikeAsset(asset)) return true
  return !isExcludedNonMachineAsset(asset)
}
