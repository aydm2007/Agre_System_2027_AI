import { useState, useEffect } from 'react';
import { db } from '../offline/dexie_db';

export function useSmartDefaults() {
    const [defaults, setDefaults] = useState({
        location: '',
        lastCustomer: ''
    });

    useEffect(() => {
        const load = async () => {
            const loc = await db.userData.get('last_location');
            const cust = await db.userData.get('last_customer');
            setDefaults({
                location: loc?.value || '',
                lastCustomer: cust?.value || ''
            });
        };
        load();
    }, []);

    const setSmartDefault = async (key, value) => {
        await db.userData.put({ key: `last_${key}`, value });
    };

    return { defaults, setSmartDefault };
}
