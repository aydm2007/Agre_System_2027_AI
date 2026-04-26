import { useEffect } from 'react';

export const useGlobalHotkeys = (handlers) => {
    useEffect(() => {
        const handleKeyDown = (e) => {
            // Debug key
            // console.log(e.key);

            if (e.key === 'F1') {
                e.preventDefault();
                handlers.onHelp?.();
            } else if (e.key === 'F2') {
                e.preventDefault();
                handlers.onAction?.();
            } else if (e.key === 'Escape') {
                // Let default behavior happen often, but custom handler if needed
                handlers.onCancel?.();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [handlers]);
};
