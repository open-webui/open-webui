import dayjs from 'dayjs';
import i18n from '$lib/i18n';

// Import all locales
import 'dayjs/locale/af';
import 'dayjs/locale/am';
import 'dayjs/locale/ar';
import 'dayjs/locale/az';
import 'dayjs/locale/be';
import 'dayjs/locale/bg';
import 'dayjs/locale/bi';
import 'dayjs/locale/bm';
import 'dayjs/locale/bn';
import 'dayjs/locale/bo';
import 'dayjs/locale/br';
import 'dayjs/locale/bs';
import 'dayjs/locale/ca';
import 'dayjs/locale/cs';
import 'dayjs/locale/cv';
import 'dayjs/locale/cy';
import 'dayjs/locale/da';
import 'dayjs/locale/de';
import 'dayjs/locale/dv';
import 'dayjs/locale/el';
import 'dayjs/locale/en';
import 'dayjs/locale/eo';
import 'dayjs/locale/es';
import 'dayjs/locale/eu';
import 'dayjs/locale/fa';
import 'dayjs/locale/fi';
import 'dayjs/locale/fo';
import 'dayjs/locale/fr';
import 'dayjs/locale/fy';
import 'dayjs/locale/ga';
import 'dayjs/locale/gd';
import 'dayjs/locale/gl';
import 'dayjs/locale/gu';
import 'dayjs/locale/he';
import 'dayjs/locale/hi';
import 'dayjs/locale/hr';
import 'dayjs/locale/ht';
import 'dayjs/locale/hu';
import 'dayjs/locale/id';
import 'dayjs/locale/is';
import 'dayjs/locale/it';
import 'dayjs/locale/ja';
import 'dayjs/locale/jv';
import 'dayjs/locale/ka';
import 'dayjs/locale/kk';
import 'dayjs/locale/km';
import 'dayjs/locale/kn';
import 'dayjs/locale/ko';
import 'dayjs/locale/ku';
import 'dayjs/locale/ky';
import 'dayjs/locale/lb';
import 'dayjs/locale/lo';
import 'dayjs/locale/lt';
import 'dayjs/locale/lv';
import 'dayjs/locale/me';
import 'dayjs/locale/mi';
import 'dayjs/locale/mk';
import 'dayjs/locale/ml';
import 'dayjs/locale/mn';
import 'dayjs/locale/mr';
import 'dayjs/locale/ms';
import 'dayjs/locale/mt';
import 'dayjs/locale/my';
import 'dayjs/locale/nb';
import 'dayjs/locale/ne';
import 'dayjs/locale/nl';
import 'dayjs/locale/nn';
import 'dayjs/locale/pl';
import 'dayjs/locale/pt';
import 'dayjs/locale/ro';
import 'dayjs/locale/ru';
import 'dayjs/locale/rw';
import 'dayjs/locale/sd';
import 'dayjs/locale/se';
import 'dayjs/locale/si';
import 'dayjs/locale/sk';
import 'dayjs/locale/sl';
import 'dayjs/locale/sq';
import 'dayjs/locale/sr';
import 'dayjs/locale/ss';
import 'dayjs/locale/sv';
import 'dayjs/locale/sw';
import 'dayjs/locale/ta';
import 'dayjs/locale/te';
import 'dayjs/locale/tet';
import 'dayjs/locale/tg';
import 'dayjs/locale/th';
import 'dayjs/locale/tk';
import 'dayjs/locale/tlh';
import 'dayjs/locale/tr';
import 'dayjs/locale/tzl';
import 'dayjs/locale/tzm';
import 'dayjs/locale/uk';
import 'dayjs/locale/ur';
import 'dayjs/locale/uz';
import 'dayjs/locale/vi';
import 'dayjs/locale/yo';
import 'dayjs/locale/zh';
import 'dayjs/locale/zh-tw';
import 'dayjs/locale/et';

// Add plugins that components need
import relativeTime from 'dayjs/plugin/relativeTime';
import isToday from 'dayjs/plugin/isToday';
import isYesterday from 'dayjs/plugin/isYesterday';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import duration from 'dayjs/plugin/duration';
import calendar from 'dayjs/plugin/calendar';

dayjs.extend(relativeTime);
dayjs.extend(isToday);
dayjs.extend(isYesterday);
dayjs.extend(localizedFormat);
dayjs.extend(duration);
dayjs.extend(calendar);

// Global locale loader
function loadDayjsLocale(locales) {
    if (!locales || !Array.isArray(locales)) {
        return;
    }

    for (const locale of locales) {
        try {
            dayjs.locale(locale);
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

export default dayjs;
