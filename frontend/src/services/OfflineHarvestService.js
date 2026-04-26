import { HarvestLogs } from '../api/client';
import { queueHarvest, getPendingHarvests, db } from '../offline/dexie_db';
import { getQueueOwnerKey } from '../api/offlineQueueStore';

export const OfflineHarvestService = {
    /**
     * Record a harvest. Tries online first, falls back to offline queue.
     * @param {Object} harvestData - The harvest payload
     * @returns {Promise<Object>} - The result (either from API or local DB)
     */
    async recordHarvest(harvestData) {
        if (navigator.onLine) {
            try {
                // Try direct API call
                const response = await HarvestLogs.create(harvestData);
                return { success: true, mode: 'online', data: response.data };
            } catch (error) {
                console.warn("Online harvest failed, falling back to offline", error);
                // If network error (not validation error), fall back
                if (!error.response || error.response.status >= 500 || error.code === 'ERR_NETWORK') {
                    return await this._saveOffline(harvestData);
                }
                throw error; // Re-throw validation errors (400)
            }
        } else {
            return await this._saveOffline(harvestData);
        }
    },

    async _saveOffline(harvestData) {
        try {
            const ownerKey = await getQueueOwnerKey();
            const id = await queueHarvest({ ...harvestData, owner_key: ownerKey });
            return { success: true, mode: 'offline', id };
        } catch (e) {
            console.error("Critical: Failed to save to local DB", e);
            throw new Error("Failed to save harvest locally");
        }
    },

    /**
     * Sync pending harvests to the backend.
     * @returns {Promise<Object>} - Report of success/failure counts
     */
    async syncPendingHarvests() {
        if (!navigator.onLine) return { synced: 0, failed: 0 };

        const ownerKey = await getQueueOwnerKey();
        const pending = await getPendingHarvests(ownerKey);
        if (pending.length === 0) return { synced: 0, failed: 0 };

        let synced = 0;
        let failed = 0;

        for (const item of pending) {
            try {
                // Remove internal Dexie ID before sending
                const { id, status, created_at, ...payload } = item;

                await HarvestLogs.create(payload);

                // Mark as synced (delete from queue)
                await db.harvest_queue.delete(id);
                synced++;
            } catch (error) {
                console.error(`Failed to sync harvest ${item.id}`, error);
                failed++;
                // Optional: Update status to 'failed' in DB if you want to keep history
            }
        }
        return { synced, failed };
    }
};
