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

export const extractMetricValue = (content: string): string => {
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
		const cleaned = stripDateTime(normalized);
		const candidates = parseNumberCandidates(cleaned);
		const filtered = filterTimeUnits(candidates);
		return filtered.length === 1 ? filtered[0] : '';
	}

	const metricPattern = /^[-+]?[\d,.]+(?:e[-+]?\d+)?(?:\s*[%a-zA-Z\u00b0/]+)?$/;
	return metricPattern.test(normalized) ? normalized : '';
};

export const extractTimeframe = (content: string): string => {
	if (!content) {
		return '';
	}

	const normalized = content.replace(/\s+/g, ' ').trim().toLowerCase();
	if (!normalized) {
		return '';
	}

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

	return '';
};
