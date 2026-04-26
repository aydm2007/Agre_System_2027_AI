import ar from '../../i18n/ar'

const TEXT = ar.farms

export default function FarmFilters({ query, setQuery, onRefresh, onClear }) {
  return (
    <div className="flex flex-col gap-2 md:flex-row md:items-center">
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={TEXT.searchPlaceholder}
        className="flex-1 border border-gray-300 dark:border-slate-600 rounded-lg p-2 text-sm bg-white dark:bg-slate-700 dark:text-white focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
      />
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onRefresh}
          className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary-dark transition shadow-sm hover:shadow"
        >
          {TEXT.searchButton}
        </button>
        <button
          type="button"
          onClick={onClear}
          className="px-4 py-2 bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 text-sm font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition shadow-sm"
        >
          {TEXT.clearButton}
        </button>
      </div>
    </div>
  )
}
