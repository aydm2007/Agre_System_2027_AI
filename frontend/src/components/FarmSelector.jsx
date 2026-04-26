import { Fragment } from 'react'
import { Listbox, Transition } from '@headlessui/react'
import { Check, ChevronDown } from 'lucide-react'
import { useFarmContext } from '../api/farmContext'

export default function FarmSelector() {
  const { farms, selectedFarmId, selectFarm, loading } = useFarmContext()

  const selectedFarm = farms.find((f) => String(f.id) === String(selectedFarmId)) || null

  if (loading) {
    return <div className="w-48 h-10 bg-gray-100 dark:bg-slate-800 rounded-lg animate-pulse" />
  }

  if (farms.length === 0) {
    return <div className="text-sm text-red-500 font-medium px-2">لا توجد مزارع مصرح بها</div>
  }

  return (
    <div className="relative z-20 w-full md:w-72">
      <Listbox value={selectedFarm} onChange={(farm) => selectFarm(farm.id)}>
        <div className="relative">
          <Listbox.Button
            data-testid="farm-selector-button"
            className="relative w-full cursor-default rounded-xl border border-emerald-100/70 bg-gradient-to-b from-white to-emerald-50/35 py-2.5 pr-4 pl-10 text-end shadow-sm transition focus:outline-none focus:ring-2 focus:ring-emerald-500/60 dark:border-slate-600 dark:from-slate-800 dark:to-slate-900 sm:text-sm"
          >
            <span className="block truncate text-gray-900 dark:text-gray-100 font-bold">
              {selectedFarm ? selectedFarm.name : 'اختر مزرعة...'}
            </span>
            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-emerald-600/80 dark:text-emerald-300/70">
              <ChevronDown className="h-5 w-5 text-gray-400" aria-hidden="true" />
            </span>
          </Listbox.Button>
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className="absolute z-30 mt-2 max-h-60 w-full overflow-auto rounded-xl border border-emerald-100/70 bg-white/98 py-1 text-base shadow-lg ring-1 ring-black/5 focus:outline-none dark:border-slate-700 dark:bg-slate-900 sm:text-sm text-end">
              {farms.map((farm, farmIdx) => (
                <Listbox.Option
                  key={farmIdx}
                  data-testid={`farm-option-${farm.id}`}
                  className={({ active }) =>
                    `relative cursor-default select-none py-2 pr-4 pl-10 ${
                      active
                        ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400'
                        : 'text-gray-900 dark:text-gray-100'
                    }`
                  }
                  value={farm}
                >
                  {({ selected }) => (
                    <>
                      <span className={`block truncate ${selected ? 'font-bold' : 'font-normal'}`}>
                        {farm.name}
                      </span>
                      {selected ? (
                        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-emerald-600">
                          <Check className="h-5 w-5" aria-hidden="true" />
                        </span>
                      ) : null}
                    </>
                  )}
                </Listbox.Option>
              ))}
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
    </div>
  )
}
