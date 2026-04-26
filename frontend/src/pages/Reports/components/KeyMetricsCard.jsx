import React from 'react'
import { TEXT, formatNumber } from '../constants'

const MetricCard = ({ label, value, unit }) => (
    <div className="bg-white dark:bg-slate-800 p-4 rounded-lg shadow">
        <div className="text-sm text-gray-500 dark:text-slate-400">{label}</div>
        <div className="text-2xl font-semibold text-gray-900 dark:text-white">
            {value} <span className="text-sm text-gray-500 dark:text-slate-400">{unit}</span>
        </div>
    </div>
)

const KeyMetricsCard = ({ summary }) => {
    return (
        <div className="grid md:grid-cols-6 gap-3">
            <MetricCard
                label={TEXT.summary.totalHours}
                value={formatNumber(summary?.metrics?.total_hours)}
                unit={TEXT.summary.unitHours}
            />
            <MetricCard
                label={TEXT.summary.machineHours}
                value={formatNumber(summary?.metrics?.machine_hours)}
                unit={TEXT.summary.unitHours}
            />
            <MetricCard
                label={TEXT.summary.materialsQty}
                value={formatNumber(summary?.metrics?.materials_total_qty)}
                unit={TEXT.summary.unitQty}
            />
            <MetricCard
                label={TEXT.summary.harvestQty}
                value={formatNumber(summary?.metrics?.harvest_total_qty)}
                unit={TEXT.summary.unitQty}
            />
            <MetricCard
                label={TEXT.summary.distinctLocations}
                value={Number(summary?.metrics?.distinct_locations ?? 0)}
                unit=""
            />
            <MetricCard
                label={TEXT.summary.distinctWells}
                value={Number(summary?.metrics?.distinct_wells ?? 0)}
                unit=""
            />
        </div>
    )
}

export default KeyMetricsCard
