export function resolveDisplayName(entity, fallback = 'غير معرّف') {
  if (!entity || typeof entity !== 'object') return fallback

  const firstName = String(entity.first_name || '').trim()
  const lastName = String(entity.last_name || '').trim()
  const combinedName = [firstName, lastName].filter(Boolean).join(' ').trim()

  const candidates = [
    entity.full_name_ar,
    entity.display_name_ar,
    entity.name_arabic,
    entity.name_ar,
    entity.full_name,
    entity.display_name,
    combinedName,
    entity.name,
    entity.user_full_name,
    entity.user_name,
    entity.supervisor_name,
    entity.username,
    entity.slug,
    entity.code,
  ]

  const match = candidates.find((value) => typeof value === 'string' && value.trim())
  return match ? match.trim() : fallback
}

export function resolveSecondaryIdentity(entity) {
  if (!entity || typeof entity !== 'object') return ''
  const candidates = [entity.email]
  const match = candidates.find((value) => typeof value === 'string' && value.trim())
  return match ? match.trim() : ''
}

export function resolvePermissionDisplayName(permission, fallback = 'صلاحية غير معرّفة') {
  if (!permission || typeof permission !== 'object') return fallback
  const candidates = [permission.name_arabic, permission.display_name_ar, permission.name]
  const match = candidates.find((value) => typeof value === 'string' && value.trim())
  return match ? match.trim() : fallback
}
