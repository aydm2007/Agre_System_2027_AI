import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OfflineHarvestService } from './OfflineHarvestService';
import { HarvestLogs } from '../api/client';
import * as DexieDB from '../offline/dexie_db';

// Mocks
vi.mock('../api/client', () => ({
    HarvestLogs: {
        create: vi.fn()
    }
}));

vi.mock('../offline/dexie_db', () => ({
    queueHarvest: vi.fn(),
    getPendingHarvests: vi.fn(),
    db: {
        harvest_queue: {
            delete: vi.fn()
        }
    }
}));

describe('OfflineHarvestService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should use online API when online', async () => {
        // Mock Online
        const originalOnLine = navigator.onLine;
        Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });

        HarvestLogs.create.mockResolvedValue({ data: { id: 100 } });

        const result = await OfflineHarvestService.recordHarvest({ items: [] });

        expect(HarvestLogs.create).toHaveBeenCalled();
        expect(result.mode).toBe('online');

        // Restore
        Object.defineProperty(navigator, 'onLine', { value: originalOnLine, configurable: true });
    });

    it('should fallback to offline when offline', async () => {
        // Mock Offline
        const originalOnLine = navigator.onLine;
        Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });

        DexieDB.queueHarvest.mockResolvedValue(123);

        const result = await OfflineHarvestService.recordHarvest({ items: [] });

        expect(HarvestLogs.create).not.toHaveBeenCalled();
        expect(DexieDB.queueHarvest).toHaveBeenCalled();
        expect(result.mode).toBe('offline');
        expect(result.id).toBe(123);

        // Restore
        Object.defineProperty(navigator, 'onLine', { value: originalOnLine, configurable: true });
    });

    it('should fallback to offline when API fails with network error', async () => {
        // Mock Online but API Error
        const originalOnLine = navigator.onLine;
        Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });

        const networkError = new Error('Network Error');
        networkError.code = 'ERR_NETWORK';
        HarvestLogs.create.mockRejectedValue(networkError);

        DexieDB.queueHarvest.mockResolvedValue(124);

        const result = await OfflineHarvestService.recordHarvest({ items: [] });

        expect(HarvestLogs.create).toHaveBeenCalled();
        expect(DexieDB.queueHarvest).toHaveBeenCalled(); // Fallback triggered
        expect(result.mode).toBe('offline');

        // Restore
        Object.defineProperty(navigator, 'onLine', { value: originalOnLine, configurable: true });
    });

    it('should sync pending harvests', async () => {
        const originalOnLine = navigator.onLine;
        Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });

        // Mock pending data
        DexieDB.getPendingHarvests.mockResolvedValue([
            { id: 1, product: 'A', qty: 10, status: 'pending' },
            { id: 2, product: 'B', qty: 20, status: 'pending' }
        ]);

        HarvestLogs.create.mockResolvedValue({}); // Success

        const report = await OfflineHarvestService.syncPendingHarvests();

        expect(HarvestLogs.create).toHaveBeenCalledTimes(2);
        expect(DexieDB.db.harvest_queue.delete).toHaveBeenCalledTimes(2);
        expect(report.synced).toBe(2);

        Object.defineProperty(navigator, 'onLine', { value: originalOnLine, configurable: true });
    });
});
