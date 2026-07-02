import type { CalendarEventModel } from '$lib/apis/calendar';

const NS = 1_000_000;
const DEFAULT_CALENDAR_COLOR = '#3b82f6';

type MiniCalendarEvent = Pick<
	CalendarEventModel,
	'calendar_id' | 'start_at' | 'end_at' | 'color'
>;

function dayKey(date: Date): string {
	return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime().toString();
}

export function miniCalendarVisibleRange(date: Date): { start: Date; end: Date } {
	const monthStart = new Date(date.getFullYear(), date.getMonth(), 1);
	const start = new Date(monthStart);
	start.setDate(start.getDate() - start.getDay());
	start.setHours(0, 0, 0, 0);

	const end = new Date(start);
	end.setDate(end.getDate() + 42);
	end.setHours(0, 0, 0, 0);

	return { start, end };
}

export function miniCalendarEventIndicators(
	events: MiniCalendarEvent[],
	visibleCalendarIds: Set<string>,
	calendarColors: Map<string, string | null | undefined> = new Map()
): Map<string, string[]> {
	const indicators = new Map<string, string[]>();

	for (const event of events) {
		if (!visibleCalendarIds.has(event.calendar_id)) {
			continue;
		}

		const color = event.color || calendarColors.get(event.calendar_id) || DEFAULT_CALENDAR_COLOR;
		const startDate = new Date(event.start_at / NS);
		const endDate = new Date((event.end_at || event.start_at) / NS);
		const cursor = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate());
		const last = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate()).getTime();

		while (cursor.getTime() <= last) {
			const key = dayKey(cursor);
			const colors = indicators.get(key) ?? [];
			if (!colors.includes(color)) {
				colors.push(color);
				indicators.set(key, colors);
			}
			cursor.setDate(cursor.getDate() + 1);
		}
	}

	return indicators;
}

export function miniCalendarDayKey(date: Date): string {
	return dayKey(date);
}
