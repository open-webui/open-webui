const HIJRI_FORMATTERS: Record<string, Intl.DateTimeFormat> = {};

function hijriFormatter(locale: string, options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
	const key = `${locale}|${JSON.stringify(options)}`;
	if (!HIJRI_FORMATTERS[key]) {
		try {
			HIJRI_FORMATTERS[key] = new Intl.DateTimeFormat(`${locale}-u-ca-islamic-umalqura`, options);
		} catch {
			HIJRI_FORMATTERS[key] = new Intl.DateTimeFormat(`en-US-u-ca-islamic-umalqura`, options);
		}
	}
	return HIJRI_FORMATTERS[key];
}

/** Full Hijri (Umm al-Qura) date string for a Gregorian date, e.g. "١٢ محرم ١٤٤٦". */
export function formatHijri(date: Date, locale = 'ar-SA'): string {
	try {
		return hijriFormatter(locale, { day: 'numeric', month: 'short', year: 'numeric' }).format(date);
	} catch {
		return '';
	}
}

/** Compact Hijri label for calendar cells, e.g. "١٢ محرم". */
export function formatHijriShort(date: Date, locale = 'ar-SA'): string {
	try {
		return hijriFormatter(locale, { day: 'numeric', month: 'short' }).format(date);
	} catch {
		return '';
	}
}

/** True when the active locale is an Arabic-script locale that commonly uses the Hijri calendar. */
export function isHijriPreferredLocale(locale: string | undefined): boolean {
	if (!locale) return false;
	const base = locale.split('-')[0];
	return ['ar', 'fa', 'ur', 'ps', 'ku', 'ug'].includes(base);
}
