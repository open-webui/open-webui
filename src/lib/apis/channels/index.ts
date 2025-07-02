import { WEBUI_API_BASE_URL } from '$lib/constants';

type ChannelForm = {
	name: string;
	data?: object;
	meta?: object;
	access_control?: object;
};

export const createNewChannel = async (token: string = '', channel: ChannelForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/channels/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ ...channel })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getChannels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/channels/`, {
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
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getChannelById = async (token: string = '', channel_id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/channels/${channel_id}`, {
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
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateChannelById = async (
	token: string = '',
	channel_id: string,
	channel: ChannelForm
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/channels/${channel_id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ ...channel })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteChannelById = async (token: string = '', channel_id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/channels/${channel_id}/delete`, {
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
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getChannelMessages = async (
	token: string = '',
	channel_id: string,
	skip: number = 0,
	limit: number = 50
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages?skip=${skip}&limit=${limit}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getChannelThreadMessages = async (
	token: string = '',
	channel_id: string,
	message_id: string,
	skip: number = 0,
	limit: number = 50
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/thread?skip=${skip}&limit=${limit}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type MessageForm = {
	parent_id?: string;
	content: string;
	data?: object;
	meta?: object;
};

export const sendMessage = async (token: string = '', channel_id: string, message: MessageForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/post`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ ...message })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateMessage = async (
	token: string = '',
	channel_id: string,
	message_id: string,
	message: MessageForm
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/update`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ ...message })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const addReaction = async (
	token: string = '',
	channel_id: string,
	message_id: string,
	name: string
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/reactions/add`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ name })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const removeReaction = async (
	token: string = '',
	channel_id: string,
	message_id: string,
	name: string
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/reactions/remove`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ name })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteMessage = async (token: string = '', channel_id: string, message_id: string) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/channels/${channel_id}/messages/${message_id}/delete`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
