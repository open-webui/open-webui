import { WEBUI_API_BASE_URL } from '$lib/constants';

// Mock data for workflows - replace with real API calls when backend is ready
const mockWorkflows = [
	{
		id: 'workflow-1',
		name: 'Data Processing Workflow',
		api_address: 'https://api.example.com/v1',
		api_key: 'sk-1234567890abcdef',
		description: 'Processes data from various sources',
		created_at: Date.now() - 86400000, // 1 day ago
		updated_at: Date.now() - 3600000, // 1 hour ago
		user: {
			name: 'John Doe',
			email: 'john.doe@example.com'
		}
	},
	{
		id: 'workflow-2',
		name: 'Content Generation',
		api_address: 'https://content-api.example.com',
		api_key: 'sk-abcdef1234567890',
		description: 'Generates content for marketing campaigns',
		created_at: Date.now() - 172800000, // 2 days ago
		updated_at: Date.now() - 7200000, // 2 hours ago
		user: {
			name: 'Jane Smith',
			email: 'jane.smith@example.com'
		}
	},
	{
		id: 'workflow-3',
		name: 'Email Automation',
		api_address: 'https://email-api.example.com/v2',
		api_key: 'sk-9876543210fedcba',
		description: 'Automates email sending and responses',
		created_at: Date.now() - 259200000, // 3 days ago
		updated_at: Date.now() - 10800000, // 3 hours ago
		user: {
			name: 'Mike Johnson',
			email: 'mike.johnson@example.com'
		}
	}
];

export const createNewWorkflow = async (token: string, workflow: object) => {
	// TODO: Replace with real API call when backend is ready
	console.log('Creating workflow:', workflow);
	
	// Simulate API delay
	await new Promise(resolve => setTimeout(resolve, 500));
	
	// Add to mock data
	const newWorkflow = {
		id: `workflow-${Date.now()}`,
		name: (workflow as any).name || '',
		api_address: (workflow as any).api_address || '',
		api_key: (workflow as any).api_key || '',
		description: (workflow as any).description || '',
		created_at: Date.now(),
		updated_at: Date.now(),
		user: {
			name: 'Current User',
			email: 'user@example.com'
		}
	};
	
	mockWorkflows.push(newWorkflow);
	
	return newWorkflow;
};

export const getWorkflows = async (token: string = '') => {
	// TODO: Replace with real API call when backend is ready
	console.log('Getting workflows with token:', token);
	
	// Simulate API delay
	await new Promise(resolve => setTimeout(resolve, 300));
	
	return mockWorkflows;
};

export const getWorkflowList = async (token: string = '') => {
	// TODO: Replace with real API call when backend is ready
	console.log('Getting workflow list with token:', token);
	
	// Simulate API delay
	await new Promise(resolve => setTimeout(resolve, 200));
	
	return mockWorkflows;
};

export const exportWorkflows = async (token: string = '') => {
	// TODO: Replace with real API call when backend is ready
	console.log('Exporting workflows with token:', token);
	
	// Simulate API delay
	await new Promise(resolve => setTimeout(resolve, 200));
	
	return mockWorkflows;
};

export const getWorkflowById = async (token: string, id: string) => {
	// TODO: Replace with real API call when backend is ready
	console.log('Getting workflow by id:', id, 'with token:', token);
	
	// Simulate API delay
	await new Promise(resolve => setTimeout(resolve, 200));
	
	const workflow = mockWorkflows.find(w => w.id === id);
	if (!workflow) {
		throw new Error('Workflow not found');
	}
	
	return workflow;
};

export const updateWorkflowById = async (token: string, id: string, workflow: object) => {
	// TODO: Replace with real API call when backend is ready
	console.log('Updating workflow:', id, 'with data:', workflow);
	
	// Simulate API delay
	await new Promise(resolve => setTimeout(resolve, 500));
	
	const index = mockWorkflows.findIndex(w => w.id === id);
	if (index === -1) {
		throw new Error('Workflow not found');
	}
	
	mockWorkflows[index] = {
		...mockWorkflows[index],
		...workflow,
		updated_at: Date.now()
	};
	
	return mockWorkflows[index];
};

export const deleteWorkflowById = async (token: string, id: string) => {
	// TODO: Replace with real API call when backend is ready
	console.log('Deleting workflow:', id, 'with token:', token);
	
	// Simulate API delay
	await new Promise(resolve => setTimeout(resolve, 300));
	
	const index = mockWorkflows.findIndex(w => w.id === id);
	if (index === -1) {
		throw new Error('Workflow not found');
	}
	
	mockWorkflows.splice(index, 1);
	
	return { success: true };
};

// Real API implementations (commented out until backend is ready)
/*
export const createNewWorkflow = async (token: string, workflow: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...workflow
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
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

export const getWorkflows = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/`, {
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

export const getWorkflowList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/list`, {
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

export const exportWorkflows = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/export`, {
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

export const getWorkflowById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/id/${id}`, {
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

export const updateWorkflowById = async (token: string, id: string, workflow: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/id/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...workflow
		})
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

export const deleteWorkflowById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/workflows/id/${id}/delete`, {
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
*/
