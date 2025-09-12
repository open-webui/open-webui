import { writable } from 'svelte/store';
import dayjs from '$lib/dayjs';
import i18n from '$lib/i18n';

export const dayjsLocale = writable('en');

// Global locale loader
async function loadDayjsLocale(locales) {
    if (!locales || !Array.isArray(locales)) {
        return;
    }

    for (const locale of locales) {
        try {
            dayjs.locale(locale);
            dayjsLocale.set(locale);
            break;
        } catch (error) {
            console.error(`Could not load dayjs locale '${locale}':`, error);
        }
    }
}

// Subscribe to i18n language changes
i18n.subscribe(($i18n) => {
    if ($i18n?.languages) {
        loadDayjsLocale($i18n.languages);
    }
});
// Export dayjs as default so components can import it
export default dayjs;
