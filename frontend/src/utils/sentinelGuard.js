/**
 * 🛡️ [SENTINEL-COHORT] SOVEREIGN MONITORING SWARM
 * Zenith 11.5 OMEGA-Z Operational Integrity Layer.
 */

export const SentinelGuard = {
    /**
     * Analyzes an activity payload for financial and operational deviations.
     */
    analyzeActivity(payload, _context = {}) {
        const anomalies = [];
        const { machine_hours, fuel_consumed, water_volume, activity_tree_count } = payload;

        // 1. Efficiency Check: Fuel vs Hours (Typical max 25L/hour for heavy machinery)
        if (machine_hours > 0 && fuel_consumed > 0) {
            const ratio = fuel_consumed / machine_hours;
            if (ratio > 35) {
                anomalies.push({
                    type: 'FINANCIAL_LEAK',
                    severity: 'HIGH',
                    message: `انحراف كبير في استهلاك الوقود (${ratio.toFixed(1)} لتر/ساعة). قد يكون هناك تسرب أو سوء استخدام.`
                });
            }
        }

        // 2. Irrigation Check: Water volume per tree (Typical max 150L/tree/day for mature trees)
        if (water_volume > 0 && activity_tree_count > 0) {
            const waterPerTree = (water_volume * 1000) / activity_tree_count;
            if (waterPerTree > 250) {
                anomalies.push({
                    type: 'RESOURCE_WASTE',
                    severity: 'MEDIUM',
                    message: `كمية المياه مرتفعة جداً مقارنة بعدد الأشجار (${waterPerTree.toFixed(0)} لتر/شجرة).`
                });
            }
        }

        // 3. Operational Logic: Solar vs Diesel
        if (payload.is_solar_powered && payload.diesel_qty > 0) {
            anomalies.push({
                type: 'LOGIC_CONFLICT',
                severity: 'CRITICAL',
                message: 'تضارب منطقي: تم اختيار طاقة شمسية مع إدخال كمية ديزل.'
            });
        }

        return {
            hasAnomalies: anomalies.length > 0,
            anomalies,
            timestamp: new Date().toISOString()
        };
    }
};

export default SentinelGuard;
