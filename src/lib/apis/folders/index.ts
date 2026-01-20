import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

export const createNewFolder = async (token: string, name: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/folders/`, {
		method: 'POST',
		data: {
			name: name
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFolders = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/folders/`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const getFolderById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/folders/${id}`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

export const updateFolderNameById = async (token: string, id: string, name: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/folders/${id}/update`, {
		method: 'POST',
		data: {
			name: name
		}
	})
		.then(async (res) => {
			return res.data;
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

export const updateFolderIsExpandedById = async (
	token: string,
	id: string,
	isExpanded: boolean
) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/folders/${id}/update/expanded`, {
		method: 'POST',
		data: {
			is_expanded: isExpanded
		}
	})
		.then(async (res) => {
			return res.data;
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

export const updateFolderParentIdById = async (token: string, id: string, parentId?: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/folders/${id}/update/parent`, {
		method: 'POST',
		data: {
			parent_id: parentId
		}
	})
		.then(async (res) => {
			return res.data;
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

type FolderItems = {
	chat_ids: string[];
	file_ids: string[];
};

export const updateFolderItemsById = async (token: string, id: string, items: FolderItems) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/folders/${id}/update/items`, {
		method: 'POST',
		data: {
			items: items
		}
	})
		.then(async (res) => {
			return res.data;
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

export const deleteFolderById = async (token: string, id: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/folders/${id}`, {
		method: 'DELETE'
	})
		.then(async (res) => {
			return res.data;
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
