import React from 'react'
import { enterpriseArabicConfig } from '../../config/enterpriseArabicConfig'

export default function ArabicExecutiveKpiCards() {
  return (
    <section dir="rtl" lang="ar" className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {enterpriseArabicConfig.executiveKpis.map((label) => (
        <article key={label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="text-sm text-slate-500">مؤشر تنفيذي</div>
          <div className="mt-2 text-lg font-semibold text-slate-900">{label}</div>
          <div className="mt-1 text-xs text-slate-500">جاهز للربط مع لوحات V6 التنفيذية والتحليلية</div>
        </article>
      ))}
    </section>
  )
}
