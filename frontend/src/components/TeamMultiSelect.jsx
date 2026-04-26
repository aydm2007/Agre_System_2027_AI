import { useEffect, useMemo, useRef, useState } from 'react'
import PropTypes from 'prop-types'

const normalizeLabel = (value) => {
  if (typeof value !== 'string') {
    return ''
  }
  let label = value.replace(/\r\n/g, '\n').trim()
  if (!label) {
    return ''
  }
  label = label.replace(/\s{2,}/g, ' ')
  if (typeof label.normalize === 'function') {
    try {
      label = label.normalize('NFKC')
    } catch (error) {
      // ignore normalization issues in unsupported runtimes
    }
  }
  return label
}

const labelKey = (value) => {
  const label = normalizeLabel(value)
  if (!label) {
    return ''
  }
  if (typeof label.toLocaleLowerCase === 'function') {
    return label.toLocaleLowerCase('ar')
  }
  return label.toLowerCase()
}

const mergeUnique = (items) => {
  const result = []
  const seen = new Set()
  items.forEach((item) => {
    const label = normalizeLabel(item)
    if (!label) {
      return
    }
    const key = labelKey(label)
    if (!key || seen.has(key)) {
      return
    }
    seen.add(key)
    result.push(label)
  })
  return result
}

export default function TeamMultiSelect({
  value = [],
  onChange,
  suggestions = [],
  onInputChange,
  placeholder = '',
  disabled = false,
  loading = false,
  maxSuggestions = 8,
}) {
  const selected = useMemo(() => (Array.isArray(value) ? mergeUnique(value) : []), [value])
  const [inputValue, setInputValue] = useState('')
  const [open, setOpen] = useState(false)
  const containerRef = useRef(null)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const listboxId = useMemo(
    () => `team-multi-select-${Math.random().toString(36).slice(2, 10)}`,
    [],
  )

  const selectedKeys = useMemo(() => new Set(selected.map(labelKey)), [selected])

  const filteredSuggestions = useMemo(() => {
    const base = Array.isArray(suggestions) ? suggestions : []
    const queryKey = labelKey(inputValue)
    const seen = new Set()
    const list = []

    base.forEach((candidate) => {
      const label = normalizeLabel(candidate)
      if (!label) {
        return
      }
      const key = labelKey(label)
      if (!key || seen.has(key) || selectedKeys.has(key)) {
        return
      }
      if (queryKey && !key.includes(queryKey)) {
        return
      }
      seen.add(key)
      list.push(label)
    })

    return list.slice(0, maxSuggestions)
  }, [suggestions, inputValue, selectedKeys, maxSuggestions])

  const activeOptionId =
    highlightedIndex >= 0 && filteredSuggestions[highlightedIndex]
      ? `${listboxId}-option-${highlightedIndex}`
      : undefined

  useEffect(() => {
    if (!open || typeof document === 'undefined') {
      return () => {}
    }
    const handleClickAway = (event) => {
      if (!containerRef.current || containerRef.current.contains(event.target)) {
        return
      }
      setOpen(false)
    }
    document.addEventListener('mousedown', handleClickAway)
    return () => {
      document.removeEventListener('mousedown', handleClickAway)
    }
  }, [open])

  useEffect(() => {
    if (!selected.length) {
      setInputValue('')
    }
  }, [selected.length])

  useEffect(() => {
    if (!open) {
      setHighlightedIndex(-1)
      return
    }
    if (!filteredSuggestions.length) {
      setHighlightedIndex(-1)
      return
    }
    setHighlightedIndex((prev) => (prev >= 0 && prev < filteredSuggestions.length ? prev : 0))
  }, [open, filteredSuggestions])

  const emitInputChange = (next) => {
    if (typeof onInputChange === 'function') {
      onInputChange(next)
    }
  }

  const handleInputChange = (event) => {
    const next = event.target.value
    setInputValue(next)
    emitInputChange(next)
    if (!disabled) {
      setOpen(true)
    }
  }

  const handleAdd = (label) => {
    const normalized = normalizeLabel(label)
    if (!normalized) {
      setInputValue('')
      emitInputChange('')
      return
    }
    const key = labelKey(normalized)
    if (!key) {
      return
    }
    const exists = selectedKeys.has(key)
    if (exists) {
      setInputValue('')
      emitInputChange('')
      setOpen(false)
      return
    }
    const next = [...selected, normalized]
    onChange(next)
    setInputValue('')
    emitInputChange('')
    setOpen(true)
    setHighlightedIndex(-1)
  }

  const handleRemove = (index) => {
    if (disabled) {
      return
    }
    const next = selected.filter((_, idx) => idx !== index)
    onChange(next)
  }

  const handleKeyDown = (event) => {
    if (disabled) {
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (!open) {
        setOpen(true)
      }
      setHighlightedIndex((prev) => {
        if (!filteredSuggestions.length) {
          return -1
        }
        const next = prev + 1
        return next >= filteredSuggestions.length ? 0 : next
      })
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (!open) {
        setOpen(true)
      }
      setHighlightedIndex((prev) => {
        if (!filteredSuggestions.length) {
          return -1
        }
        if (prev <= 0) {
          return filteredSuggestions.length - 1
        }
        return prev - 1
      })
    } else if (event.key === 'Enter') {
      if (highlightedIndex >= 0 && filteredSuggestions[highlightedIndex]) {
        event.preventDefault()
        handleAdd(filteredSuggestions[highlightedIndex])
        return
      }
      event.preventDefault()
      handleAdd(inputValue)
    } else if (event.key === ',') {
      event.preventDefault()
      handleAdd(inputValue)
    } else if (event.key === 'Backspace' && !inputValue) {
      if (selected.length) {
        event.preventDefault()
        onChange(selected.slice(0, -1))
      }
    } else if (event.key === 'Escape') {
      event.preventDefault()
      setOpen(false)
      setHighlightedIndex(-1)
    }
  }

  const handleFocus = () => {
    if (!disabled) {
      setOpen(true)
    }
  }

  const handleBlur = () => {
    setTimeout(() => {
      if (!containerRef.current || typeof document === 'undefined') {
        return
      }
      const active = document.activeElement
      if (!active || !containerRef.current.contains(active)) {
        setOpen(false)
      }
    }, 100)
  }

  const showDropdown = open && (filteredSuggestions.length > 0 || loading)

  return (
    <div
      className="relative"
      ref={containerRef}
      role="combobox"
      aria-haspopup="listbox"
      aria-expanded={showDropdown}
      aria-owns={showDropdown ? listboxId : undefined}
    >
      <div
        className={`flex flex-wrap items-center gap-2 border rounded px-2 py-1 min-h-[2.5rem] bg-white dark:bg-slate-700 ${
          disabled
            ? 'bg-gray-100 dark:bg-slate-600 text-gray-500 dark:text-slate-400 border-gray-200 dark:border-slate-600'
            : 'border-gray-300 dark:border-slate-600 focus-within:border-sky-400 focus-within:ring-2 focus-within:ring-sky-200 dark:focus-within:ring-sky-800'
        }`}
      >
        {selected.map((label, index) => (
          <span
            key={`${labelKey(label)}-${index}`}
            className="flex items-center gap-1 rounded-full bg-sky-100 dark:bg-sky-900/50 px-2 py-0.5 text-xs text-sky-800 dark:text-sky-200 whitespace-pre-line"
          >
            {label}
            {!disabled && (
              <button
                type="button"
                className="text-sky-600 dark:text-sky-400 hover:text-sky-900 dark:hover:text-sky-200"
                onClick={() => handleRemove(index)}
                aria-label={`إزالة ${label}`}
              >
                ×
              </button>
            )}
          </span>
        ))}
        <input
          type="text"
          className="flex-1 min-w-[6rem] border-none bg-transparent py-1 text-sm focus:outline-none focus:ring-0 disabled:cursor-not-allowed dark:text-white dark:placeholder-slate-400"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={selected.length ? '' : placeholder}
          disabled={disabled}
          autoComplete="off"
          aria-autocomplete="list"
          aria-controls={showDropdown ? listboxId : undefined}
          aria-expanded={showDropdown}
          aria-activedescendant={activeOptionId}
        />
      </div>
      {showDropdown && (
        <ul
          className="absolute z-20 mt-1 max-h-48 w-full overflow-auto rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm shadow-lg"
          role="listbox"
          id={listboxId}
          aria-busy={loading}
        >
          {loading ? (
            <li className="px-3 py-2 text-gray-500 dark:text-slate-400">جاري التحميل...</li>
          ) : filteredSuggestions.length ? (
            filteredSuggestions.map((option, index) => {
              const optionId = `${listboxId}-option-${index}`
              const isActive = index === highlightedIndex
              return (
                <li
                  key={labelKey(option)}
                  id={optionId}
                  role="option"
                  aria-selected={isActive}
                  className={`cursor-pointer px-3 py-2 hover:bg-sky-50 dark:hover:bg-slate-700 dark:text-slate-200 ${isActive ? 'bg-sky-100 dark:bg-slate-600' : ''}`}
                  onMouseDown={(event) => {
                    event.preventDefault()
                    handleAdd(option)
                  }}
                  onMouseEnter={() => {
                    setHighlightedIndex(index)
                  }}
                >
                  {option}
                </li>
              )
            })
          ) : (
            <li className="px-3 py-2 text-gray-500 dark:text-slate-400">لا توجد اقتراحات</li>
          )}
        </ul>
      )}
    </div>
  )
}

TeamMultiSelect.propTypes = {
  value: PropTypes.arrayOf(PropTypes.string),
  onChange: PropTypes.func.isRequired,
  suggestions: PropTypes.arrayOf(PropTypes.string),
  onInputChange: PropTypes.func,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  maxSuggestions: PropTypes.number,
}
