/**
 * 🧠 [TOPIC-CACHE-MANAGER] SOVEREIGN MEMORY LAYER
 * Zenith 11.5 OMEGA-Z Pattern Recognition for Precision Agriculture.
 */

const CACHE_KEY = 'SOVEREIGN_TOPIC_CACHE';
const MAX_ENTRIES = 100;

export const TopicCacheManager = {
    /**
     * Records an activity pattern into the local neural cache.
     */
    learnFromActivity(payload) {
        try {
            const { farm, crop, task, locations, fuel_consumed, water_volume } = payload;
            if (!farm || !task) return;

            const cache = this._getCache();
            const patternKey = `${farm}_${crop || 'ALL'}_${task}_${(locations || []).join(',')}`;
            
            cache[patternKey] = {
                fuel: fuel_consumed || 0,
                water: water_volume || 0,
                lastSeen: new Date().toISOString()
            };

            // Maintain cache size
            const keys = Object.keys(cache);
            if (keys.length > MAX_ENTRIES) {
                delete cache[keys[0]];
            }

            localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
        } catch (e) {
            console.warn('[TopicCache] Learning failed:', e);
        }
    },

    /**
     * Predicts likely values for the current context.
     */
    predict(farm, crop, task, locations) {
        try {
            const cache = this._getCache();
            const patternKey = `${farm}_${crop || 'ALL'}_${task}_${(locations || []).join(',')}`;
            return cache[patternKey] || null;
        } catch (e) {
            return null;
        }
    },

    _getCache() {
        try {
            return JSON.parse(localStorage.getItem(CACHE_KEY)) || {};
        } catch (e) {
            return {};
        }
    }
};

export default TopicCacheManager;
