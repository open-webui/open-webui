import type { i18n as I18n } from 'i18next';

export const formatSchedule = (rrule: string, i18n: I18n): string => {
	const match = rrule.match(/DTSTART[^:]*:(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/i);
	if (/COUNT=1(?!\d)/.test(rrule)) {
		if (match) {
			const d = new Date(`${match[1]}-${match[2]}-${match[3]}T${match[4]}:${match[5]}`);
			return `${i18n.t('Once')} · ${d.toLocaleDateString(i18n.language, {
				month: 'short',
				day: 'numeric'
			})} ${d.toLocaleTimeString(i18n.language, { hour: 'numeric', minute: '2-digit' })}`;
		}
		return i18n.t('Once');
	}

	const parts: Record<string, string> = {};
	rrule
		.split(/\s+/)
		.filter((line) => !line.toUpperCase().startsWith('DTSTART'))
		.join('')
		.replace('RRULE:', '')
		.split(';')
		.forEach((part) => {
			const [key, value] = part.split('=');
			if (key && value) parts[key] = value;
		});

	const freq = parts.FREQ || '';
	const hour = parseInt(parts.BYHOUR || match?.[4] || '0');
	const minute = (parts.BYMINUTE || match?.[5] || '0').padStart(2, '0');
	const interval = parseInt(parts.INTERVAL || '1');
	const time = new Date(2000, 0, 1, hour, Number(minute)).toLocaleTimeString(i18n.language, {
		hour: 'numeric',
		minute: '2-digit'
	});

	if (freq === 'MINUTELY')
		return interval === 1
			? i18n.t('Every minute')
			: i18n.t('Every {{count}} minutes', { count: interval });
	if (freq === 'HOURLY')
		return interval === 1 ? i18n.t('Hourly') : i18n.t('Every {{count}} hours', { count: interval });
	if (freq === 'DAILY') return `${i18n.t('Daily at')} ${time}`;
	if (freq === 'WEEKLY')
		return parts.BYDAY
			? `${parts.BYDAY.split(',')
					.map((day) => i18n.t(day[0] + day.slice(1).toLowerCase(), { context: 'day_of_week' }))
					.join(', ')} ${i18n.t('at')} ${time}`
			: `${i18n.t('Weekly at')} ${time}`;
	if (freq === 'MONTHLY')
		return `${i18n.t('Monthly')} ${parts.BYMONTHDAY ?? '1'} ${i18n.t('at')} ${time}`;

	return rrule;
};
