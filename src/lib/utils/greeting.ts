type Translate = (key: string, options: { name: string }) => string;

const period = (hour: number) =>
	hour < 5
		? 'lateNight'
		: hour < 7
			? 'superEarly'
			: hour < 11
				? 'morning'
				: hour < 13
					? 'noon'
					: hour < 17
						? 'afternoon'
						: hour < 21
							? 'evening'
							: 'night';

// First word of the name with its first letter upper-cased, so "tim" greets as "Tim".
export const firstNameOf = (name?: string | null) => {
	const first = (name ?? '').trim().split(/\s+/)[0];
	return first.charAt(0).toLocaleUpperCase() + first.slice(1);
};

/**
 * Time-of-day greeting for the new-chat screens. The same phrasing all day, a different one
 * tomorrow. Keys are written out so `i18n:parse` keeps them.
 */
export function getGreeting(t: Translate, name: string, date = new Date()): string {
	const greetings = {
		lateNight: [
			t('chat.placeholder.greeting.lateNight.0', { name }),
			t('chat.placeholder.greeting.lateNight.1', { name }),
			t('chat.placeholder.greeting.lateNight.2', { name })
		],
		superEarly: [
			t('chat.placeholder.greeting.superEarly.0', { name }),
			t('chat.placeholder.greeting.superEarly.1', { name }),
			t('chat.placeholder.greeting.superEarly.2', { name })
		],
		morning: [
			t('chat.placeholder.greeting.morning.0', { name }),
			t('chat.placeholder.greeting.morning.1', { name }),
			t('chat.placeholder.greeting.morning.2', { name })
		],
		noon: [
			t('chat.placeholder.greeting.noon.0', { name }),
			t('chat.placeholder.greeting.noon.1', { name }),
			t('chat.placeholder.greeting.noon.2', { name })
		],
		afternoon: [
			t('chat.placeholder.greeting.afternoon.0', { name }),
			t('chat.placeholder.greeting.afternoon.1', { name }),
			t('chat.placeholder.greeting.afternoon.2', { name })
		],
		evening: [
			t('chat.placeholder.greeting.evening.0', { name }),
			t('chat.placeholder.greeting.evening.1', { name }),
			t('chat.placeholder.greeting.evening.2', { name })
		],
		night: [
			t('chat.placeholder.greeting.night.0', { name }),
			t('chat.placeholder.greeting.night.1', { name }),
			t('chat.placeholder.greeting.night.2', { name })
		]
	};
	return greetings[period(date.getHours())][date.getDate() % 3];
}
