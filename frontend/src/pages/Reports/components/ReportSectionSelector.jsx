import React from 'react'

import { REPORT_SECTION_STATUS_LABELS, REPORT_SECTIONS, TEXT } from '../constants'

const LOAD_CLASS_LABELS = {
  fast: 'سريع',
  heavy: 'ثقيل',
}

export default function ReportSectionSelector({
  filters,
  selectedSections,
  sectionStatusMap,
  hasStaleSections,
  onToggleSection,
}) {
  return (
    <section className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow space-y-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white">{TEXT.sections.title}</h2>
        {hasStaleSections ? (
          <span className="inline-flex w-fit rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-500/10 dark:text-amber-200">
            {TEXT.sections.staleHint}
          </span>
        ) : null}
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {REPORT_SECTIONS.map((section) => {
          const selected = selectedSections.includes(section.key)
          const status = sectionStatusMap[section.key] || 'idle'
          const requirementsMet = section.requires.every((requirement) => Boolean(filters?.[requirement]))
          const disabled = section.key === 'summary' || !requirementsMet

          return (
            <label
              key={section.key}
              className={`rounded-2xl border p-4 transition ${
                selected
                  ? 'border-emerald-300 bg-emerald-50 dark:border-emerald-500/40 dark:bg-emerald-500/10'
                  : 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/40'
              } ${disabled && section.key !== 'summary' ? 'opacity-70' : ''}`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  checked={selected}
                  disabled={disabled}
                  onChange={() => onToggleSection(section.key)}
                />
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                      {section.label}
                    </span>
                    <span className="rounded-full bg-white/80 px-2 py-1 text-[11px] font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-300">
                      {LOAD_CLASS_LABELS[section.loadClass]}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
                      {REPORT_SECTION_STATUS_LABELS[status] || status}
                    </span>
                  </div>
                  <p className="text-xs leading-5 text-slate-500 dark:text-slate-400">{section.description}</p>
                  {!requirementsMet && section.key !== 'summary' ? (
                    <p className="text-xs font-medium text-amber-700 dark:text-amber-200">
                      {TEXT.sections.missingRequirements}
                    </p>
                  ) : null}
                </div>
              </div>
            </label>
          )
        })}
      </div>
    </section>
  )
}
