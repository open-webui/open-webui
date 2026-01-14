const stripCodeBlockWrapper = (text: string): string => {
	const match = text.match(/^\s*```(?:\w+)?\s*([\s\S]*?)\s*```\s*$/);
	return match ? match[1] : text;
};

const parseJsonMetric = (text: string): string => {
	if (!text.startsWith('{') || !text.endsWith('}')) {
		return '';
	}
	try {
		const parsed = JSON.parse(text);
		if (!parsed || typeof parsed !== 'object') {
			return '';
		}
		const keys = ['value', 'metric', 'result', 'answer', 'txt_answer'];
		for (const key of keys) {
			if (parsed[key] !== undefined && parsed[key] !== null) {
				return String(parsed[key]).trim();
			}
		}
	} catch (error) {
		return '';
	}
	return '';
};

const parseNumberCandidates = (text: string): string[] => {
	const matches = [
		...text.matchAll(/[-+]?\d[\d,]*(?:\.\d+)?(?:e[-+]?\d+)?(?:\s*[a-zA-Z%/\u00b0]+)?/g)
	];
	return matches.map((match) => match[0].trim()).filter((value) => value.length > 0);
};

const stripDateTime = (text: string): string => {
	return text
		.replace(
			/\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b/g,
			' '
		)
		.replace(/\b\d{4}-\d{2}-\d{2}\b/g, ' ')
		.replace(/\b\d{1,2}\/\d{1,2}\/\d{2,4}\b/g, ' ')
		.replace(/\b\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\b/g, ' ')
		.replace(
			/\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{2,4})?\b/gi,
			' '
		)
		.replace(
			/\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}\b/gi,
			' '
		);
};

const getLocaleKey = (locale?: string): string => {
	if (!locale) {
		return 'en';
	}
	return locale.split('-')[0]?.toLowerCase() || 'en';
};

const stripTimeframePhrases = (text: string, locale?: string): string => {
	const normalized = text.toLowerCase();
	const localeKey = getLocaleKey(locale);
	if (localeKey === 'es') {
		return normalized
			.replace(
				/\b(?:en\s+)?(?:las|los)?\s*(?:últimas|ultimas|últimos|ultimos|pasadas|anteriores)\s+\d+\s*(segundos?|seg|s|minutos?|mins?|m|horas?|h|días?|dias|d|semanas?|sem|s|mes(?:es)?|mo|años?|anos?|a)\b/g,
				' '
			)
			.replace(
				/\b(?:en\s+)?(?:el|la)?\s*(?:último|ultimo|última|ultima|pasado|pasada)\s+(semana|mes|año|ano|trimestre)\b/g,
				' '
			)
			.replace(
				/\bhace\s+\d+\s*(segundos?|seg|s|minutos?|mins?|m|horas?|h|días?|dias|d|semanas?|sem|s|mes(?:es)?|mo|años?|anos?|a)\b/g,
				' '
			)
			.replace(/\b(hoy|ayer)\b/g, ' ');
	}

	return normalized
		.replace(
			/\b(?:in\s+the\s+)?(past|last|previous)\s+\d+\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|wks?|wk|w|months?|mons?|mo|years?|yrs?|yr|y)\b/g,
			' '
		)
		.replace(
			/\b(this|last|past)\s+(week|month|year|quarter)\b/g,
			' '
		)
		.replace(/\b\d+\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|wks?|wk|w|months?|mons?|mo|years?|yrs?|yr|y)\s+ago\b/g, ' ')
		.replace(/\b(today|yesterday)\b/g, ' ');
};

const filterTimeUnits = (candidates: string[]): string[] => {
	const timeUnits = new Set([
		's',
		'sec',
		'secs',
		'second',
		'seconds',
		'm',
		'min',
		'mins',
		'minute',
		'minutes',
		'h',
		'hr',
		'hrs',
		'hour',
		'hours',
		'd',
		'day',
		'days',
		'w',
		'wk',
		'wks',
		'week',
		'weeks',
		'mo',
		'mon',
		'mons',
		'month',
		'months',
		'y',
		'yr',
		'yrs',
		'year',
		'years'
	]);

	return candidates.filter((candidate) => {
		const unitMatch = candidate.match(/[a-zA-Z%/\u00b0]+$/);
		if (!unitMatch) {
			return true;
		}
		const unit = unitMatch[0].toLowerCase();
		return !timeUnits.has(unit);
	});
};

export const extractMetricValue = (content: string, locale?: string): string => {
	if (!content) {
		return '';
	}

	let text = stripCodeBlockWrapper(content).trim();
	if (!text) {
		return '';
	}

	const jsonMetric = parseJsonMetric(text);
	if (jsonMetric) {
		text = jsonMetric;
	} else {
		text =
			text
				.split('\n')
				.map((line) => line.trim())
				.find((line) => line.length > 0) || '';
		text = text.replace(/^["'`*_~]+|["'`*_~]+$/g, '');
	}

	if (!text) {
		return '';
	}

	const normalized = text.replace(/\s+/g, ' ').trim();
	const wordCount = normalized.split(' ').length;
	if (wordCount > 3) {
		const cleaned = stripDateTime(stripTimeframePhrases(normalized, locale));
		const candidates = parseNumberCandidates(cleaned);
		const filtered = filterTimeUnits(candidates);
		return filtered.length === 1 ? filtered[0] : '';
	}

	const metricPattern = /^[-+]?[\d,.]+(?:e[-+]?\d+)?(?:\s*[%a-zA-Z\u00b0/]+)?$/;
	return metricPattern.test(normalized) ? normalized : '';
};

export const extractTimeframe = (content: string, locale?: string): string => {
	if (!content) {
		return '';
	}

	const normalized = content.replace(/\s+/g, ' ').trim().toLowerCase();
	if (!normalized) {
		return '';
	}

	const localeKey = getLocaleKey(locale);
	if (localeKey === 'es') {
		if (/\bhoy\b/.test(normalized)) {
			return 'Hoy';
		}
		if (/\bayer\b/.test(normalized)) {
			return 'Ayer';
		}

		const simplePeriod = normalized.match(
			/\b(este|esta|último|ultimo|última|ultima|pasado|pasada)\s+(semana|mes|año|ano|trimestre)\b/
		);
		if (simplePeriod) {
			const descriptor = simplePeriod[1];
			const period = simplePeriod[2] === 'ano' ? 'año' : simplePeriod[2];
			return `${descriptor.charAt(0).toUpperCase()}${descriptor.slice(1)} ${period}`;
		}

		const relativeMatch = normalized.match(
			/\b(?:en\s+)?(?:las|los)?\s*(últimas|ultimas|últimos|ultimos|pasadas|anteriores)\s+(\d+)\s*(segundos?|seg|s|minutos?|mins?|m|horas?|h|días?|dias|d|semanas?|sem|s|mes(?:es)?|mo|años?|anos?|a)\b/
		);
		if (relativeMatch) {
			const amount = parseInt(relativeMatch[2], 10);
			const unitRaw = relativeMatch[3];
			const unitMap: Record<string, { singular: string; plural: string; gender: 'm' | 'f' }> =
				{
					s: { singular: 'segundo', plural: 'segundos', gender: 'm' },
					seg: { singular: 'segundo', plural: 'segundos', gender: 'm' },
					segundo: { singular: 'segundo', plural: 'segundos', gender: 'm' },
					segundos: { singular: 'segundo', plural: 'segundos', gender: 'm' },
					m: { singular: 'minuto', plural: 'minutos', gender: 'm' },
					min: { singular: 'minuto', plural: 'minutos', gender: 'm' },
					mins: { singular: 'minuto', plural: 'minutos', gender: 'm' },
					minuto: { singular: 'minuto', plural: 'minutos', gender: 'm' },
					minutos: { singular: 'minuto', plural: 'minutos', gender: 'm' },
					h: { singular: 'hora', plural: 'horas', gender: 'f' },
					hora: { singular: 'hora', plural: 'horas', gender: 'f' },
					horas: { singular: 'hora', plural: 'horas', gender: 'f' },
					d: { singular: 'día', plural: 'días', gender: 'm' },
					dia: { singular: 'día', plural: 'días', gender: 'm' },
					dias: { singular: 'día', plural: 'días', gender: 'm' },
					día: { singular: 'día', plural: 'días', gender: 'm' },
					días: { singular: 'día', plural: 'días', gender: 'm' },
					sem: { singular: 'semana', plural: 'semanas', gender: 'f' },
					semana: { singular: 'semana', plural: 'semanas', gender: 'f' },
					semanas: { singular: 'semana', plural: 'semanas', gender: 'f' },
					mo: { singular: 'mes', plural: 'meses', gender: 'm' },
					mes: { singular: 'mes', plural: 'meses', gender: 'm' },
					meses: { singular: 'mes', plural: 'meses', gender: 'm' },
					a: { singular: 'año', plural: 'años', gender: 'm' },
					ano: { singular: 'año', plural: 'años', gender: 'm' },
					anos: { singular: 'año', plural: 'años', gender: 'm' },
					año: { singular: 'año', plural: 'años', gender: 'm' },
					años: { singular: 'año', plural: 'años', gender: 'm' }
				};

			const unitInfo = unitMap[unitRaw] || { singular: unitRaw, plural: unitRaw, gender: 'm' };
			const unit = amount === 1 ? unitInfo.singular : unitInfo.plural;
			const prefix = unitInfo.gender === 'f' ? 'Últimas' : 'Últimos';
			return `${prefix} ${amount} ${unit}`;
		}

		const agoMatch = normalized.match(
			/\bhace\s+(\d+)\s*(segundos?|seg|s|minutos?|mins?|m|horas?|h|días?|dias|d|semanas?|sem|s|mes(?:es)?|mo|años?|anos?|a)\b/
		);
		if (agoMatch) {
			const amount = parseInt(agoMatch[1], 10);
			const unitRaw = agoMatch[2];
			const unitMap: Record<string, { singular: string; plural: string }> = {
				s: { singular: 'segundo', plural: 'segundos' },
				seg: { singular: 'segundo', plural: 'segundos' },
				segundo: { singular: 'segundo', plural: 'segundos' },
				segundos: { singular: 'segundo', plural: 'segundos' },
				m: { singular: 'minuto', plural: 'minutos' },
				min: { singular: 'minuto', plural: 'minutos' },
				mins: { singular: 'minuto', plural: 'minutos' },
				minuto: { singular: 'minuto', plural: 'minutos' },
				minutos: { singular: 'minuto', plural: 'minutos' },
				h: { singular: 'hora', plural: 'horas' },
				hora: { singular: 'hora', plural: 'horas' },
				horas: { singular: 'hora', plural: 'horas' },
				d: { singular: 'día', plural: 'días' },
				dia: { singular: 'día', plural: 'días' },
				dias: { singular: 'día', plural: 'días' },
				día: { singular: 'día', plural: 'días' },
				días: { singular: 'día', plural: 'días' },
				sem: { singular: 'semana', plural: 'semanas' },
				semana: { singular: 'semana', plural: 'semanas' },
				semanas: { singular: 'semana', plural: 'semanas' },
				mo: { singular: 'mes', plural: 'meses' },
				mes: { singular: 'mes', plural: 'meses' },
				meses: { singular: 'mes', plural: 'meses' },
				a: { singular: 'año', plural: 'años' },
				ano: { singular: 'año', plural: 'años' },
				anos: { singular: 'año', plural: 'años' },
				año: { singular: 'año', plural: 'años' },
				años: { singular: 'año', plural: 'años' }
			};
			const unitInfo = unitMap[unitRaw] || { singular: unitRaw, plural: unitRaw };
			const unit = amount === 1 ? unitInfo.singular : unitInfo.plural;
			return `Hace ${amount} ${unit}`;
		}
	} else {
		if (/\btoday\b/.test(normalized)) {
			return 'Today';
		}
		if (/\byesterday\b/.test(normalized)) {
			return 'Yesterday';
		}

		const simplePeriod = normalized.match(/\b(this|last|past)\s+(week|month|year|quarter)\b/);
		if (simplePeriod) {
			const descriptor = simplePeriod[1];
			const period = simplePeriod[2];
			return `${descriptor.charAt(0).toUpperCase()}${descriptor.slice(1)} ${period}`;
		}

		const relativeMatch = normalized.match(
			/\b(?:in\s+the\s+)?(past|last|previous)\s+(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|wks?|wk|w|months?|mons?|mo|years?|yrs?|yr|y)\b/
		);
		if (relativeMatch) {
			const amount = parseInt(relativeMatch[2], 10);
			const unitRaw = relativeMatch[3];
			const unitMap: Record<string, string> = {
				s: 'sec',
				sec: 'sec',
				secs: 'secs',
				second: 'second',
				seconds: 'seconds',
				m: 'min',
				min: 'min',
				mins: 'mins',
				minute: 'minute',
				minutes: 'minutes',
				h: 'hr',
				hr: 'hr',
				hrs: 'hrs',
				hour: 'hour',
				hours: 'hours',
				d: 'day',
				day: 'day',
				days: 'days',
				w: 'week',
				wk: 'week',
				wks: 'weeks',
				week: 'week',
				weeks: 'weeks',
				mo: 'month',
				mon: 'month',
				mons: 'months',
				month: 'month',
				months: 'months',
				y: 'year',
				yr: 'year',
				yrs: 'years',
				year: 'year',
				years: 'years'
			};

			let unit = unitMap[unitRaw] || unitRaw;
			if (amount === 1) {
				if (unit === 'secs') unit = 'sec';
				if (unit === 'mins') unit = 'min';
				if (unit === 'hrs') unit = 'hr';
				if (unit === 'days') unit = 'day';
				if (unit === 'weeks') unit = 'week';
				if (unit === 'months') unit = 'month';
				if (unit === 'years') unit = 'year';
			}

			return `Past ${amount} ${unit}`;
		}

		const agoMatch = normalized.match(
			/\b(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|wks?|wk|w|months?|mons?|mo|years?|yrs?|yr|y)\s+ago\b/
		);
		if (agoMatch) {
			const amount = parseInt(agoMatch[1], 10);
			const unitRaw = agoMatch[2];
			const unitMap: Record<string, string> = {
				s: 'sec',
				sec: 'sec',
				secs: 'secs',
				second: 'second',
				seconds: 'seconds',
				m: 'min',
				min: 'min',
				mins: 'mins',
				minute: 'minute',
				minutes: 'minutes',
				h: 'hr',
				hr: 'hr',
				hrs: 'hrs',
				hour: 'hour',
				hours: 'hours',
				d: 'day',
				day: 'day',
				days: 'days',
				w: 'week',
				wk: 'week',
				wks: 'weeks',
				week: 'week',
				weeks: 'weeks',
				mo: 'month',
				mon: 'month',
				mons: 'months',
				month: 'month',
				months: 'months',
				y: 'year',
				yr: 'year',
				yrs: 'years',
				year: 'year',
				years: 'years'
			};

			let unit = unitMap[unitRaw] || unitRaw;
			if (amount === 1) {
				if (unit === 'secs') unit = 'sec';
				if (unit === 'mins') unit = 'min';
				if (unit === 'hrs') unit = 'hr';
				if (unit === 'days') unit = 'day';
				if (unit === 'weeks') unit = 'week';
				if (unit === 'months') unit = 'month';
				if (unit === 'years') unit = 'year';
			}

			return `${amount} ${unit} ago`;
		}
	}

	return '';
};

const normalizeTitleWord = (word: string): string => {
	return word.charAt(0).toUpperCase() + word.slice(1);
};

export const extractMetricTitle = (content: string, locale?: string): string => {
	if (!content) {
		return '';
	}

	let text = stripCodeBlockWrapper(content).trim();
	if (!text) {
		return '';
	}

	const jsonMetric = parseJsonMetric(text);
	if (jsonMetric) {
		text = jsonMetric;
	} else {
		text =
			text
				.split('\n')
				.map((line) => line.trim())
				.find((line) => line.length > 0) || '';
		text = text.replace(/^["'`*_~]+|["'`*_~]+$/g, '');
	}

	if (!text) {
		return '';
	}

	let normalized = text.replace(/\s+/g, ' ').trim().toLowerCase();
	normalized = stripTimeframePhrases(normalized, locale);
	normalized = stripDateTime(normalized);
	normalized = normalized.replace(/\b[-+]?\d[\d,]*(?:\.\d+)?(?:e[-+]?\d+)?\b/g, ' ');
	normalized = normalized.replace(/[^\w\s-]/g, ' ').replace(/\s+/g, ' ').trim();

	if (!normalized) {
		return '';
	}

	const localeKey = getLocaleKey(locale);
	const baseStopwords = [
		'the',
		'a',
		'an',
		'and',
		'or',
		'of',
		'for',
		'in',
		'on',
		'at',
		'to',
		'with',
		'by',
		'from',
		'is',
		'are',
		'was',
		'were',
		'be',
		'been',
		'being',
		'total',
		'number',
		'count',
		'amount',
		'value',
		'detected',
		'past',
		'last',
		'previous',
		'infeed',
		'system'
	];
	const spanishStopwords = [
		'el',
		'la',
		'los',
		'las',
		'un',
		'una',
		'y',
		'o',
		'de',
		'del',
		'para',
		'en',
		'sobre',
		'con',
		'por',
		'desde',
		'es',
		'son',
		'fue',
		'fueron',
		'ser',
		'siendo',
		'total',
		'número',
		'numero',
		'cuenta',
		'cantidad',
		'valor',
		'detectado',
		'últimas',
		'ultimas',
		'últimos',
		'ultimos',
		'pasadas',
		'anteriores',
		'sistema'
	];

	const stopwords = new Set(
		localeKey === 'es' ? baseStopwords.concat(spanishStopwords) : baseStopwords
	);

	const words = normalized
		.split(' ')
		.filter((word) => word.length > 1 && !stopwords.has(word));

	if (!words.length) {
		return '';
	}

	const titleWords = words.slice(0, 3).map((word) => normalizeTitleWord(word));
	return titleWords.join(' ');
};
