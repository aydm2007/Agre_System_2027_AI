import { useQuery } from '@tanstack/react-query';
import { db, updateCatalog } from '../offline/dexie_db';
import { Customers, Items, Locations } from '../api/client'; // Assuming client exports these
import useNetworkStatus from '../offline/useNetworkStatus';

export function useOfflineData(farmId, type) { // type: 'customers' | 'items' | 'locations'
    const isOnline = useNetworkStatus();

    return useQuery({
        queryKey: [type, farmId],
        queryFn: async () => {
            if (isOnline) {
                try {
                    // 1. Fetch from API
                    let data = [];
                    if (type === 'customers') {
                        const res = await Customers.list({ farm_id: farmId, page_size: 1000 });
                        data = res.data.results || res.data || [];
                    } else if (type === 'items') {
                        const res = await Items.list({ farm: farmId, page_size: 5000 }); // Lite API in future
                        data = res.data.results || res.data || [];
                    } else if (type === 'locations') {
                        const res = await Locations.list({ farm: farmId });
                        data = res.data.results || res.data || [];
                    }

                    // 2. Update Local DB (Non-blocking)
                    if (data.length > 0) {
                        // Add farm_id to each record if missing
                        const enriched = data.map(d => ({ ...d, farm_id: farmId }));
                        updateCatalog(type, enriched).catch(console.error);
                    }
                    return data;
                } catch (err) {
                    console.warn(`Online fetch failed for ${type}, falling back to DB`, err);
                    // Fallthrough to DB
                }
            }

            // 3. Offline Mode (or Fallback)
            return await db[type].where('farm_id').equals(farmId).toArray();
        },
        staleTime: 1000 * 60 * 5, // 5 minutes freshness
        refetchOnMount: true,
        refetchOnWindowFocus: false,
    });
}
