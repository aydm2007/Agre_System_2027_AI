import { useState, useRef, useEffect } from 'react'

/**
 * TagInput Component
 * allows entering multiple items as chips/tags
 * Supports autocomplete suggestion from a provided list
 */
export const TagInput = ({
  value = [],
  onChange,
  suggestions = [],
  placeholder = 'أضف عضو فريق...',
  error,
}) => {
  const [inputValue, setInputValue] = useState('')
  const [filteredSuggestions, setFilteredSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef(null)

  // Filter suggestions based on input
  useEffect(() => {
    if (!inputValue.trim()) {
      setFilteredSuggestions([])
      return
    }

    const existing = new Set(value)
    const matches = suggestions.filter(
      (s) => s.toLowerCase().includes(inputValue.toLowerCase()) && !existing.has(s),
    )
    setFilteredSuggestions(matches)
  }, [inputValue, suggestions, value])

  const addTag = (tag) => {
    const trimmed = tag.trim()
    if (trimmed && !value.includes(trimmed)) {
      onChange([...value, trimmed])
    }
    setInputValue('')
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const removeTag = (tagToRemove) => {
    onChange(value.filter((tag) => tag !== tagToRemove))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTag(inputValue)
    } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
      removeTag(value[value.length - 1])
    }
  }

  return (
    <div className="relative">
      <div
        className={`
                    flex flex-wrap items-center gap-2 p-2 rounded-lg border bg-white dark:bg-slate-700 transition-all
                    ${error ? 'border-red-500 bg-red-50 dark:bg-red-900/30' : 'border-gray-300 dark:border-slate-600 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary'}
                `}
        onClick={() => inputRef.current?.focus()}
      >
        {/* Render Chips */}
        {value.map((tag, index) => (
          <span
            key={index}
            className="inline-flex items-center gap-1 bg-primary/10 dark:bg-primary/20 text-primary px-2 py-1 rounded-md text-sm font-medium animate-in fade-in zoom-in duration-200"
          >
            {tag}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                removeTag(tag)
              }}
              className="text-primary/60 hover:text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-full w-4 h-4 flex items-center justify-center transition-colors"
            >
              &times;
            </button>
          </span>
        ))}

        {/* Input Field */}
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => {
            setInputValue(e.target.value)
            setShowSuggestions(true)
          }}
          onKeyDown={handleKeyDown}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          onFocus={() => setShowSuggestions(true)}
          placeholder={value.length === 0 ? placeholder : ''}
          className="flex-1 bg-transparent border-none outline-none min-w-[120px] text-sm py-1 dark:text-white dark:placeholder-slate-400"
        />
      </div>

      {/* Error Message */}
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}

      {/* Autocomplete Dropdown */}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-slate-800 border border-gray-100 dark:border-slate-600 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
          {filteredSuggestions.map((suggestion, index) => (
            <button
              key={index}
              type="button"
              className="w-full text-end px-4 py-2 hover:bg-gray-50 dark:hover:bg-slate-700 text-sm text-gray-700 dark:text-slate-200 transition-colors"
              onClick={() => addTag(suggestion)}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
