import { useState, useMemo, useRef, useEffect } from 'react'
import { FixedSizeList as List } from 'react-window'
import { Search } from 'lucide-react'

export default function VirtualizedSelect({
  options,
  value,
  onChange,
  placeholder = 'Select...',
  autoFocus: _autoFocus = false,
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const wrapperRef = useRef(null)

  // Filter options
  const filteredOptions = useMemo(() => {
    if (!search) return options
    const lower = search.toLowerCase()
    return options.filter((o) => o.label.toLowerCase().includes(lower))
  }, [options, search])

  // Handle outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (val) => {
    onChange(val)
    setIsOpen(false)
    setSearch('') // Optional: clear search on select
  }

  const selectedLabel = options.find((o) => String(o.value) === String(value))?.label || ''

  // Row Renderer
  const Row = ({ index, style }) => {
    const option = filteredOptions[index]
    return (
      <div
        style={style}
        className="px-3 py-2 hover:bg-green-50 dark:hover:bg-slate-700 cursor-pointer flex items-center text-sm border-b border-gray-50 dark:border-slate-700 dark:text-slate-200"
        onClick={() => handleSelect(option.value)}
      >
        {option.label}
      </div>
    )
  }

  return (
    <div className="relative w-full" ref={wrapperRef}>
      {/* Display / Trigger */}
      <div
        className="w-full p-2 border dark:border-slate-600 rounded bg-white dark:bg-slate-700 flex items-center justify-between cursor-pointer focus:ring-2 focus:ring-green-500"
        onClick={() => setIsOpen(!isOpen)}
        tabIndex={0}
      >
        <span
          className={`truncate ${!selectedLabel ? 'text-gray-400 dark:text-slate-500' : 'text-gray-800 dark:text-white'}`}
        >
          {selectedLabel || placeholder}
        </span>
        <span className="text-gray-400 dark:text-slate-500 text-xs">▼</span>
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 w-full bg-white dark:bg-slate-800 shadow-xl rounded-b-lg border dark:border-slate-600 z-50 mt-1 max-h-[300px] flex flex-col">
          {/* Search Bar */}
          <div className="p-2 border-b dark:border-slate-700 bg-gray-50 dark:bg-slate-700 flex items-center gap-2">
            <Search size={14} className="text-gray-400 dark:text-slate-400" />
            <input
              className="bg-transparent outline-none w-full text-sm dark:text-white dark:placeholder-slate-400"
              placeholder="Type to search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              autoFocus={true}
            />
          </div>

          {/* Virtualized List */}
          <div className="flex-1">
            {filteredOptions.length > 0 ? (
              <List
                height={Math.min(filteredOptions.length * 35, 250)}
                itemCount={filteredOptions.length}
                itemSize={35}
                width="100%"
              >
                {Row}
              </List>
            ) : (
              <div className="p-3 text-center text-gray-400 dark:text-slate-500 text-sm">
                No results
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
