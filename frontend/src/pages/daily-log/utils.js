
import { get as idbGet, set as idbSet } from 'idb-keyval'
import { SERVICE_SCOPE_OPTIONS } from './constants'

export const SERVICE_SCOPE_LABEL_MAP = SERVICE_SCOPE_OPTIONS.reduce((acc, option) => {
    acc[option.value] = option.label
    return acc
}, {})

export const DEFAULT_SERVICE_SCOPE = SERVICE_SCOPE_OPTIONS[0].value
export const PRODUCT_CACHE_PREFIX = 'daily-log-products::'
export const PRODUCT_CACHE_TTL_MS = 1000 * 60 * 60 * 24 // 24h
export const TREE_LOSS_CACHE_KEY = 'daily-log::tree-loss-reasons'
export const TREE_SNAPSHOT_CACHE_PREFIX = 'daily-log::tree-snapshot'
export const LOCATION_SUMMARY_CACHE_PREFIX = 'daily-log::location-summary'
export const TREE_DATA_CACHE_TTL_MS = 1000 * 60 * 60 * 24 // 24h
export const LOCATION_SUMMARY_TTL_MS = 1000 * 60 * 60 * 12 // 12h

const fallbackMemoryCache = new Map()
let indexedDbSupported = null
let localStorageSupported = null
let loggedIndexedDbWarning = false

export const hasIndexedDb = () => {
    if (indexedDbSupported !== null) {
        return indexedDbSupported
    }
    try {
        indexedDbSupported = typeof indexedDB !== 'undefined'
    } catch (error) {
        indexedDbSupported = false
    }
    return indexedDbSupported
}

export const hasLocalStorage = () => {
    if (localStorageSupported !== null) {
        return localStorageSupported
    }
    try {
        if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
            localStorageSupported = false
            return false
        }
        const testKey = '__daily-log-cache-test__'
        window.localStorage.setItem(testKey, '1')
        window.localStorage.removeItem(testKey)
        localStorageSupported = true
        return true
    } catch (error) {
        localStorageSupported = false
        return false
    }
}

export const logIndexedDbFallback = () => {
    if (loggedIndexedDbWarning || typeof window === 'undefined') {
        return
    }
    loggedIndexedDbWarning = true
    console.warn('IndexedDB غير متاح، سيتم استخدام مخزن بديل للحفاظ على البيانات مؤقتاً.')
}

export const readFallbackCache = (key, ttlMs) => {
    if (hasLocalStorage()) {
        try {
            const raw = window.localStorage.getItem(key)
            if (!raw) {
                return null
            }
            const payload = JSON.parse(raw)
            if (ttlMs && typeof payload?.storedAt === 'number' && Date.now() - payload.storedAt > ttlMs) {
                window.localStorage.removeItem(key)
                return null
            }
            return payload
        } catch (error) {
            console.warn('Failed to read fallback cache entry', { key, error })
        }
    }
    const payload = fallbackMemoryCache.get(key)
    if (!payload) {
        return null
    }
    if (ttlMs && typeof payload.storedAt === 'number' && Date.now() - payload.storedAt > ttlMs) {
        fallbackMemoryCache.delete(key)
        return null
    }
    return payload
}

export const writeFallbackCache = (key, payload) => {
    if (hasLocalStorage()) {
        try {
            window.localStorage.setItem(key, JSON.stringify(payload))
            return
        } catch (error) {
            console.warn('Failed to persist fallback cache entry', { key, error })
        }
    }
    fallbackMemoryCache.set(key, payload)
}

export const buildProductCacheKey = (farmId, cropId) => {
    const safeFarm = farmId ? String(farmId) : 'any'
    const safeCrop = cropId ? String(cropId) : 'any'
    return `${PRODUCT_CACHE_PREFIX}farm:${safeFarm}::crop:${safeCrop}`
}

export const buildTreeSnapshotCacheKey = (locationId, varietyId) =>
    `${TREE_SNAPSHOT_CACHE_PREFIX}::loc:${locationId || 'unknown'}::var:${varietyId || 'unknown'}`

export const buildLocationSummaryCacheKey = (locationId, date, cropId) =>
    `${LOCATION_SUMMARY_CACHE_PREFIX}::loc:${locationId || 'unknown'}::date:${date || 'any'}::crop:${cropId || 'any'}`

export const readCacheEntry = async (key, ttlMs) => {
    if (!hasIndexedDb()) {
        logIndexedDbFallback()
        return readFallbackCache(key, ttlMs)
    }
    try {
        const payload = await idbGet(key)
        if (!payload || typeof payload !== 'object') {
            return null
        }
        if (ttlMs && typeof payload.storedAt === 'number' && Date.now() - payload.storedAt > ttlMs) {
            return null
        }
        return payload
    } catch (error) {
        console.warn('Failed to read cached entry', { key, error })
        return null
    }
}

export const writeCacheEntry = async (key, data) => {
    if (!hasIndexedDb()) {
        logIndexedDbFallback()
        writeFallbackCache(key, { storedAt: Date.now(), data })
        return
    }
    try {
        await idbSet(key, { storedAt: Date.now(), data })
    } catch (error) {
        console.warn('Failed to persist cached entry', { key, error })
    }
}

export const readCachedProducts = (key) => {
    if (typeof window === 'undefined' || !window.sessionStorage) {
        return null
    }
    try {
        const raw = window.sessionStorage.getItem(key)
        if (!raw) {
            return null
        }
        const parsed = JSON.parse(raw)
        if (!parsed || !Array.isArray(parsed.data)) {
            return null
        }
        if (
            typeof parsed.storedAt === 'number' &&
            Date.now() - parsed.storedAt > PRODUCT_CACHE_TTL_MS
        ) {
            window.sessionStorage.removeItem(key)
            return null
        }
        return parsed.data
    } catch (error) {
        console.warn('Failed to read cached crop products', error)
        return null
    }
}

export const writeCachedProducts = (key, data) => {
    if (typeof window === 'undefined' || !window.sessionStorage || !Array.isArray(data)) {
        return
    }
    try {
        window.sessionStorage.setItem(key, JSON.stringify({ storedAt: Date.now(), data }))
    } catch (error) {
        console.warn('Failed to cache crop products', error)
    }
}

export const normalizeTeamLabel = (value) => {
    if (typeof value !== 'string') {
        return ''
    }
    let text = value.replace(/\r\n/g, '\n').trim()
    if (!text) {
        return ''
    }
    text = text.replace(/\s{2,}/g, ' ')
    if (typeof text.normalize === 'function') {
        try {
            text = text.normalize('NFKC')
        } catch (error) {
            // ignore normalization issues in unsupported environments
        }
    }
    return text
}

export const teamKey = (value) => {
    const normalized = normalizeTeamLabel(value)
    if (!normalized) {
        return ''
    }
    if (typeof normalized.toLocaleLowerCase === 'function') {
        return normalized.toLocaleLowerCase('ar')
    }
    return normalized.toLowerCase()
}

export const normaliseTeamEntries = (items, { dedupe = true } = {}) => {
    const list = []
    const seen = dedupe ? new Set() : null

    items.forEach((entry) => {
        const normalized = normalizeTeamLabel(entry)
        if (!normalized) {
            return
        }
        if (!dedupe) {
            list.push(normalized)
            return
        }
        const key = teamKey(normalized)
        if (!key || seen.has(key)) {
            return
        }
        seen.add(key)
        list.push(normalized)
    })

    return list
}

export const mergeUniqueTeamEntries = (base = [], additions = []) => {
    const result = []
    const seen = new Set()
    const push = (entry) => {
        const normalized = normalizeTeamLabel(entry)
        if (!normalized) {
            return
        }
        const key = teamKey(normalized)
        if (!key || seen.has(key)) {
            return
        }
        seen.add(key)
        result.push(normalized)
    }
    base.forEach(push)
    additions.forEach(push)
    return result
}

export const normalizeNumericInput = (value) => {
    if (typeof value !== 'string') {
        return value
    }
    const easternArabicDigits = {
        '\u0660': '0',
        '\u0661': '1',
        '\u0662': '2',
        '\u0663': '3',
        '\u0664': '4',
        '\u0665': '5',
        '\u0666': '6',
        '\u0667': '7',
        '\u0668': '8',
        '\u0669': '9',
        '\u06f0': '0',
        '\u06f1': '1',
        '\u06f2': '2',
        '\u06f3': '3',
        '\u06f4': '4',
        '\u06f5': '5',
        '\u06f6': '6',
        '\u06f7': '7',
        '\u06f8': '8',
        '\u06f9': '9',
    }
    let normalized = ''
    for (const char of value.trim()) {
        if (easternArabicDigits[char] !== undefined) {
            normalized += easternArabicDigits[char]
            continue
        }
        if (char === '\u066b' || char === '\u060c' || char === ',') {
            normalized += '.'
            continue
        }
        normalized += char
    }
    return normalized
}

export const numberOrNull = (value) => {
    if (value === undefined || value === null || value === '') {
        return null
    }
    const normalized = typeof value === 'string' ? normalizeNumericInput(value) : value
    const numericValue = Number(normalized)
    return Number.isFinite(numericValue) ? numericValue : null
}

const TEAM_SPLIT_REGEX = /[\n\r,;|\u061B\u060C]+/u

export const shouldPreserveFreeform = (rawValue, tokens) => {
    if (!rawValue || tokens.length <= 1) {
        return false
    }
    if (!rawValue.includes('\n')) {
        return false
    }
    const lines = rawValue
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
    if (!lines.length) {
        return false
    }
    const hasBullet = lines.some((line) => /^[-*•▪\u2022]/.test(line))
    const hasSentenceEnding = lines.some((line) => /[.!?\u061F]$/.test(line))
    const hasLongLine = lines.some((line) => line.length >= 48)
    return hasBullet || (hasSentenceEnding && hasLongLine)
}

export const parseTeamEntries = (value, options = {}) => {
    const { dedupe = true, preserveFreeform = true } = options
    if (Array.isArray(value)) {
        return normaliseTeamEntries(value, { dedupe })
    }
    if (typeof value !== 'string') {
        return []
    }
    const normalisedValue = value.replace(/\r\n/g, '\n')
    let parsed = normaliseTeamEntries(normalisedValue.split(TEAM_SPLIT_REGEX), { dedupe })
    if (preserveFreeform) {
        const fallback = normalizeTeamLabel(normalisedValue)
        if (fallback && shouldPreserveFreeform(fallback, parsed)) {
            parsed = [fallback]
        }
    }
    if (parsed.length) {
        return parsed
    }
    const fallback = normalizeTeamLabel(value)
    return fallback ? [fallback] : []
}

export const teamEntriesToString = (value) => {
    const entries = Array.isArray(value)
        ? normaliseTeamEntries(value, { dedupe: true })
        : parseTeamEntries(value, { dedupe: true })
    return entries.join('\n')
}

export const summariseTeamEntries = (value, limit = 120) => {
    const entries = parseTeamEntries(value, { dedupe: true })
    if (!entries.length) {
        return ''
    }
    const summary = entries.join(', ')
    return summary.length > limit ? summary.slice(0, limit) : summary
}

export const formatTeamDisplay = (value) => {
    const entries = parseTeamEntries(value, { dedupe: true })
    return entries.length ? entries.join('، ') : '-'
}
