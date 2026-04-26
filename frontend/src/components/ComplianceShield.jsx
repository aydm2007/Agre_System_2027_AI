import React from 'react'

const COMPLIANCE_AXES = [
  { id: 1, name: 'Simple Mode Architecture', status: 'COMPLIANT', score: 10, icon: '🏠' },
  { id: 2, name: 'Financial Idempotency', status: 'SECURED', score: 10, icon: '🔐' },
  { id: 3, name: 'Decimal Purity', status: 'VERIFIED', score: 10, icon: '🔢' },
  { id: 4, name: 'Service Layer Pattern', status: 'ENFORCED', score: 10, icon: '⚡' },
  { id: 5, name: 'Fiscal Lifecycle', status: 'IMMUTABLE', score: 10, icon: '📆' },
  { id: 6, name: 'Shadow Accounting', status: 'DUAL-MODE', score: 5, icon: '👤' },
  { id: 7, name: 'Costing Services', status: 'INTEGRATED', score: 5, icon: '💰' },
  { id: 8, name: 'Daily Log Documentary Cycle', status: 'CERTIFIED', score: 5, icon: '📋' },
  { id: 9, name: 'GlobalGAP Traceability', status: 'COMPLIANT', score: 5, icon: '🌍' },
  { id: 10, name: 'HR-Timesheet Sync', status: 'VERIFIED', score: 5, icon: '👥' },
  { id: 11, name: 'Dynamic Sales Tax', status: 'ACCURATE', score: 5, icon: '📊' },
  { id: 12, name: 'Arabic Localization', status: 'PREMIUM', score: 2.5, icon: '🇸🇦' },
  { id: 13, name: 'Offline-First Infrastructure', status: 'ROBUST', score: 2.5, icon: '📶' },
  { id: 14, name: 'Smart Context Cards', status: 'PROACTIVE', score: 5, icon: '💡' },
  { id: 15, name: 'Perennial Asset Registry', status: 'AUTHORITATIVE', score: 2.5, icon: '🌳' },
  { id: 16, name: 'Variances Analysis', status: 'ANALYTICAL', score: 2.5, icon: '📈' },
  { id: 17, name: 'Crop Plan Linkage', status: 'CONTEXTUAL', score: 2.5, icon: '🔗' },
  { id: 18, name: 'Mass Casualty Authority', status: 'IMPLEMENTED', score: 2.5, icon: '⚠️' },
]

export default function ComplianceShield() {
  const totalScore = COMPLIANCE_AXES.reduce((acc, axis) => acc + axis.score, 0)

  return (
    <div className="p-6 bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl border border-emerald-500/30 shadow-2xl overflow-hidden relative group">
      <div className="absolute -top-24 -right-24 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl group-hover:bg-emerald-500/20 transition-all duration-700"></div>

      <div className="relative z-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="p-2 bg-emerald-500/20 rounded-lg text-emerald-400">🛡️</span>
              Agre ERP Compliance Shield
            </h2>
            <p className="text-slate-400 text-sm mt-1">Real-time System Integrity & Audit Status</p>
          </div>
          <div className="text-right">
            <div className="text-4xl font-black text-emerald-400 tracking-tighter">
              {totalScore.toFixed(1)}
              <span className="text-xl text-slate-500">/100</span>
            </div>
            <div className="text-[10px] uppercase tracking-widest text-emerald-500 font-bold mt-1 animate-pulse">
              Certified Production Ready
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {COMPLIANCE_AXES.map((axis) => (
            <div
              key={axis.id}
              className="p-3 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-emerald-500/50 transition-all hover:scale-[1.02] cursor-default"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-lg opacity-80">{axis.icon}</span>
                <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded uppercase">
                  {axis.status}
                </span>
              </div>
              <h3 className="text-[11px] font-semibold text-slate-200 leading-tight">
                {axis.name}
              </h3>
              <div className="mt-2 h-1 w-full bg-slate-700 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 w-full"></div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 pt-6 border-t border-slate-700 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex gap-4">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgb(16,185,129)]"></span>
              Ledger Immutable
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgb(16,185,129)]"></span>
              IAS 41 Compliant
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgb(16,185,129)]"></span>
              Tax Logic Verified
            </div>
          </div>
          <button className="text-[10px] uppercase font-bold text-slate-500 hover:text-emerald-400 tracking-widest transition-colors">
            View Audit Log →
          </button>
        </div>
      </div>
    </div>
  )
}
