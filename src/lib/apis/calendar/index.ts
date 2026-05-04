import { WEBUI_API_BASE_URL } from '$lib/constants';

export type CalendarModel = {
	id: string;
	user_id: string;
	name: string;
	color: string | null;
	is_default: boolean;
	is_system: boolean;
	data: Record<string, any> | null;
	meta: Record<string, any> | null;
	access_grants: any[];
	created_at: number;
	updated_at: number;
};

export type CalendarEventAttendeeModel = {
	id: string;
	event_id: string;
	user_id: string;
	status: string;
	meta: Record<string, any> | null;
	created_at: number;
	updated_at: number;
};

export type CalendarEventModel = {
	id: string;
	calendar_id: string;
	user_id: string;
	title: string;
	description: string | null;
	start_at: number;
	end_at: number | null;
	all_day: boolean;
	rrule: string | null;
	color: string | null;
	location: string | null;
	data: Record<string, any> | null;
	meta: Record<string, any> | null;
	is_cancelled: boolean;
	attendees: CalendarEventAttendeeModel[];
	created_at: number;
	updated_at: number;
	// Set by expand_recurring_event for recurring instances
	instance_id?: string;
};

export type CalendarEventForm = {
	calendar_id: string;
	title: string;
	description?: string;
	start_at: number;
	end_at?: number;
	all_day?: boolean;
	rrule?: string;
	color?: string;
	location?: string;
	data?: Record<string, any>;
	meta?: Record<string, any>;
	attendees?: { user_id: string; status?: string }[];
};

export type CalendarForm = {
	name: string;
	color?: string;
	data?: Record<string, any>;
	meta?: Record<string, any>;
	access_grants?: { target_type: string; target_id: string; permission: string }[];
};

// ── Calendars ─────────────────────────────────

export const getCalendars = async (token: string): Promise<CalendarModel[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createCalendar = async (token: string, form: CalendarForm): Promise<CalendarModel> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateCalendar = async (
	token: string,
	calendarId: string,
	form: Partial<CalendarForm>
): Promise<CalendarModel> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/${calendarId}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteCalendar = async (token: string, calendarId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/${calendarId}/delete`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.status ?? false;
};

export const setDefaultCalendar = async (
	token: string,
	calendarId: string
): Promise<CalendarModel> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/${calendarId}/default`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// ── Events ─────────────────────────────────

export const getCalendarEvents = async (
	token: string,
	start: string,
	end: string,
	calendarIds?: string[]
): Promise<CalendarEventModel[]> => {
	let error = null;

	const params = new URLSearchParams();
	params.append('start', start);
	params.append('end', end);
	if (calendarIds && calendarIds.length > 0) {
		params.append('calendar_ids', calendarIds.join(','));
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/events?${params.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createCalendarEvent = async (
	token: string,
	form: CalendarEventForm
): Promise<CalendarEventModel> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/events/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getCalendarEventById = async (
	token: string,
	eventId: string
): Promise<CalendarEventModel> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/events/${eventId}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateCalendarEvent = async (
	token: string,
	eventId: string,
	form: Partial<CalendarEventForm>
): Promise<CalendarEventModel> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/events/${eventId}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteCalendarEvent = async (token: string, eventId: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/events/${eventId}/delete`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.status ?? false;
};

export const rsvpCalendarEvent = async (
	token: string,
	eventId: string,
	status: string
): Promise<{ status: boolean; rsvp: string }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/events/${eventId}/rsvp`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ status })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const searchCalendarEvents = async (
	token: string,
	query: string | null,
	skip: number = 0,
	limit: number = 30
): Promise<{ items: CalendarEventModel[]; total: number }> => {
	let error = null;

	const params = new URLSearchParams();
	if (query) params.append('query', query);
	params.append('skip', skip.toString());
	params.append('limit', limit.toString());

	const res = await fetch(`${WEBUI_API_BASE_URL}/calendars/events/search?${params.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
