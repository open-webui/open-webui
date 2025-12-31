import { WEBUI_API_BASE_URL } from '$lib/constants';

// Types
export type PromptType = 'base' | 'proficiency' | 'style' | null;

export interface PersonaPrompt {
	command: string;
	title: string;
	content: string;
	prompt_type: PromptType;
	persona_value: string | null;
	access_control?: object;
}

export interface PromptGroup {
	id: string;
	name: string;
	description?: string;
	created_at?: number;
	updated_at?: number;
}

export interface PromptGroupMapping {
	id: string;
	group_id: string;
	prompt_command: string;
	order: number;
}

export interface PromptGroupWithMappings extends PromptGroup {
	mappings: PromptGroupMapping[];
}

// Available personas response type
export interface PersonaOption {
	value: string;
	prompts: PersonaPrompt[];
}

export interface AvailablePersonas {
	proficiency_levels: PersonaOption[];
	response_styles: PersonaOption[];
}

// Compose response type
export interface ComposeResult {
	combined_content: string;
	used_prompts: PersonaPrompt[];
}

// ============================================
// Dummy Data (백엔드 연동 전 폴백용)
// ============================================

const DUMMY_PROMPTS: PersonaPrompt[] = [
	{
		command: '/math-base',
		title: '수학 튜터 기본',
		content:
			'You are a helpful math tutor. Help students understand mathematical concepts clearly and patiently.',
		prompt_type: 'base',
		persona_value: null
	},
	{
		command: '/math-level-1',
		title: '초급 (하)',
		content:
			'Use simple language and step-by-step explanations. Avoid complex terminology. Break down problems into small, manageable steps.',
		prompt_type: 'proficiency',
		persona_value: '1'
	},
	{
		command: '/math-level-2',
		title: '중급 (중)',
		content:
			'Provide moderate detail with some technical terms. Assume basic familiarity with foundational concepts.',
		prompt_type: 'proficiency',
		persona_value: '2'
	},
	{
		command: '/math-level-3',
		title: '고급 (상)',
		content:
			'Use advanced mathematical terminology freely. Provide rigorous proofs and derivations when appropriate.',
		prompt_type: 'proficiency',
		persona_value: '3'
	},
	{
		command: '/style-diagnosis',
		title: '학생 진단 브리핑',
		content:
			"Provide diagnostic analysis of the student's understanding. Identify knowledge gaps and misconceptions. Give a brief assessment of their current level.",
		prompt_type: 'style',
		persona_value: 'diagnosis'
	},
	{
		command: '/style-feedback',
		title: '학습 향상 피드백',
		content:
			'Focus on constructive feedback for improvement. Highlight what the student did well and areas for growth. Provide specific suggestions for better learning outcomes.',
		prompt_type: 'style',
		persona_value: 'feedback'
	},
	{
		command: '/style-selfdirected',
		title: '자기주도 학습 유도',
		content:
			'Guide the student to discover answers themselves. Ask leading questions instead of giving direct answers. Encourage independent thinking and problem-solving skills.',
		prompt_type: 'style',
		persona_value: 'selfdirected'
	}
];

const DUMMY_GROUPS: PromptGroupWithMappings[] = [
	{
		id: 'group-1',
		name: '수학 튜터 표준 (전체)',
		description: '모든 난이도와 스타일을 포함하는 완전한 프롬프트 그룹',
		created_at: Date.now(),
		updated_at: Date.now(),
		mappings: [
			{ id: 'map-1', group_id: 'group-1', prompt_command: '/math-base', order: 0 },
			{ id: 'map-2', group_id: 'group-1', prompt_command: '/math-level-1', order: 10 },
			{ id: 'map-3', group_id: 'group-1', prompt_command: '/math-level-2', order: 11 },
			{ id: 'map-4', group_id: 'group-1', prompt_command: '/math-level-3', order: 12 },
			{ id: 'map-5', group_id: 'group-1', prompt_command: '/style-diagnosis', order: 20 },
			{ id: 'map-6', group_id: 'group-1', prompt_command: '/style-feedback', order: 21 },
			{ id: 'map-7', group_id: 'group-1', prompt_command: '/style-selfdirected', order: 22 }
		]
	},
	{
		id: 'group-2',
		name: '테스트 그룹 (미완성)',
		description: '일부 프롬프트만 포함된 테스트용 그룹',
		created_at: Date.now(),
		updated_at: Date.now(),
		mappings: [
			{ id: 'map-8', group_id: 'group-2', prompt_command: '/math-base', order: 0 },
			{ id: 'map-9', group_id: 'group-2', prompt_command: '/math-level-2', order: 10 },
			{ id: 'map-10', group_id: 'group-2', prompt_command: '/style-selfdirected', order: 20 }
		]
	}
];

// Local state for CRUD operations (백엔드 연동 전)
let localPrompts = [...DUMMY_PROMPTS];
let localGroups = [...DUMMY_GROUPS];
let localDefaultGroupId: string | null = 'group-1';

// ============================================
// Helper function for API calls with fallback
// ============================================

const apiCall = async <T>(
	endpoint: string,
	token: string,
	options: RequestInit = {}
): Promise<T> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/prompt-groups${endpoint}`, {
		...options,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			'Cache-Control': 'no-cache',
			authorization: `Bearer ${token}`,
			...options.headers
		}
	});

	// Check if response is JSON
	const contentType = res.headers.get('content-type');
	if (!contentType || !contentType.includes('application/json')) {
		throw new Error('API not available');
	}

	if (!res.ok) {
		const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
		throw new Error(error.detail || 'API call failed');
	}

	return res.json();
};

// ============================================
// Prompt Groups CRUD
// ============================================

export const getPromptGroups = async (token: string): Promise<PromptGroupWithMappings[]> => {
	try {
		const results = await apiCall<PromptGroupWithMappings[]>('/list', token);
		// 각 그룹에 mappings가 없으면 빈 배열 추가
		return results.map((g) => ({ ...g, mappings: g.mappings ?? [] }));
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		return [...localGroups];
	}
};

export const getPromptGroupById = async (
	token: string,
	id: string
): Promise<PromptGroupWithMappings> => {
	try {
		const result = await apiCall<PromptGroupWithMappings>(`/${id}`, token);
		return { ...result, mappings: result.mappings ?? [] };
	} catch {
		const group = localGroups.find((g) => g.id === id);
		if (!group) throw new Error('Group not found');
		return group;
	}
};

export const createPromptGroup = async (
	token: string,
	data: { name: string; description?: string }
): Promise<PromptGroupWithMappings> => {
	try {
		const result = await apiCall<PromptGroupWithMappings>('/create', token, {
			method: 'POST',
			body: JSON.stringify(data)
		});
		// API 응답에 mappings가 없으면 빈 배열 추가
		return { ...result, mappings: result.mappings ?? [] };
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		const newGroup: PromptGroupWithMappings = {
			id: `group-${Date.now()}`,
			name: data.name,
			description: data.description,
			created_at: Date.now(),
			updated_at: Date.now(),
			mappings: []
		};
		localGroups = [...localGroups, newGroup];
		return newGroup;
	}
};

export const updatePromptGroup = async (
	token: string,
	id: string,
	data: { name?: string; description?: string }
): Promise<PromptGroupWithMappings> => {
	try {
		const result = await apiCall<PromptGroupWithMappings>(`/${id}/update`, token, {
			method: 'POST',
			body: JSON.stringify(data)
		});
		return { ...result, mappings: result.mappings ?? [] };
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		const index = localGroups.findIndex((g) => g.id === id);
		if (index === -1) throw new Error('Group not found');
		localGroups[index] = { ...localGroups[index], ...data, updated_at: Date.now() };
		return localGroups[index];
	}
};

export const deletePromptGroup = async (token: string, id: string): Promise<boolean> => {
	try {
		await apiCall<{ success: boolean }>(`/${id}/delete`, token, { method: 'DELETE' });
		return true;
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		localGroups = localGroups.filter((g) => g.id !== id);
		if (localDefaultGroupId === id) localDefaultGroupId = null;
		return true;
	}
};

// ============================================
// Get Group Prompts
// ============================================

export const getGroupPrompts = async (
	token: string,
	groupId: string
): Promise<PersonaPrompt[]> => {
	try {
		return await apiCall<PersonaPrompt[]>(`/${groupId}/prompts`, token);
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		const group = localGroups.find((g) => g.id === groupId);
		if (!group) throw new Error('Group not found');
		const promptCommands = group.mappings.map((m) => m.prompt_command);
		return localPrompts.filter((p) => promptCommands.includes(p.command));
	}
};

// ============================================
// Prompt Group Mappings
// ============================================

export const addPromptToGroup = async (
	token: string,
	groupId: string,
	promptCommand: string,
	order: number
): Promise<PromptGroupMapping> => {
	try {
		return await apiCall<PromptGroupMapping>(`/${groupId}/prompts/add`, token, {
			method: 'POST',
			body: JSON.stringify({ prompt_command: promptCommand, order })
		});
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		const groupIndex = localGroups.findIndex((g) => g.id === groupId);
		if (groupIndex === -1) throw new Error('Group not found');
		const newMapping: PromptGroupMapping = {
			id: `map-${Date.now()}`,
			group_id: groupId,
			prompt_command: promptCommand,
			order
		};
		localGroups[groupIndex].mappings = [...localGroups[groupIndex].mappings, newMapping];
		return newMapping;
	}
};

export const removePromptFromGroup = async (
	token: string,
	groupId: string,
	promptCommand: string
): Promise<boolean> => {
	try {
		// URL encode the prompt command (remove leading slash for URL path)
		const command = promptCommand.startsWith('/') ? promptCommand.slice(1) : promptCommand;
		await apiCall<boolean>(`/${groupId}/prompts/${encodeURIComponent(command)}`, token, {
			method: 'DELETE'
		});
		return true;
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		const groupIndex = localGroups.findIndex((g) => g.id === groupId);
		if (groupIndex === -1) throw new Error('Group not found');
		localGroups[groupIndex].mappings = localGroups[groupIndex].mappings.filter(
			(m) => m.prompt_command !== promptCommand
		);
		return true;
	}
};

export const reorderPromptsInGroup = async (
	token: string,
	groupId: string,
	mappings: { prompt_command: string; order: number }[]
): Promise<boolean> => {
	try {
		await apiCall<{ success: boolean }>(`/${groupId}/prompts/reorder`, token, {
			method: 'POST',
			body: JSON.stringify({ mappings })
		});
		return true;
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		const groupIndex = localGroups.findIndex((g) => g.id === groupId);
		if (groupIndex === -1) throw new Error('Group not found');
		localGroups[groupIndex].mappings = localGroups[groupIndex].mappings.map((m) => {
			const update = mappings.find((u) => u.prompt_command === m.prompt_command);
			return update ? { ...m, order: update.order } : m;
		});
		return true;
	}
};

// ============================================
// Default Prompt Group
// ============================================

export const getDefaultPromptGroup = async (token: string): Promise<string | null> => {
	try {
		const result = await apiCall<{ default_group_id: string | null }>('/default', token);
		return result.default_group_id;
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		return localDefaultGroupId;
	}
};

export const setDefaultPromptGroup = async (
	token: string,
	groupId: string | null
): Promise<boolean> => {
	try {
		await apiCall<{ success: boolean }>('/default/set', token, {
			method: 'POST',
			body: JSON.stringify({ group_id: groupId })
		});
		return true;
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		localDefaultGroupId = groupId;
		return true;
	}
};

// ============================================
// Persona Prompts (모든 프롬프트)
// ============================================

export const getPersonaPrompts = async (token: string): Promise<PersonaPrompt[]> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		});

		const contentType = res.headers.get('content-type');
		if (!contentType || !contentType.includes('application/json')) {
			throw new Error('API not available');
		}

		if (!res.ok) {
			throw new Error('Failed to fetch prompts');
		}

		return await res.json();
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		return [...localPrompts];
	}
};

export const createPersonaPrompt = async (
	token: string,
	data: Omit<PersonaPrompt, 'access_control'> & { access_control?: object }
): Promise<PersonaPrompt> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/create`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				command: data.command.startsWith('/') ? data.command : `/${data.command}`,
				title: data.title,
				content: data.content,
				prompt_type: data.prompt_type,
				persona_value: data.persona_value,
				access_control: data.access_control
			})
		});

		const contentType = res.headers.get('content-type');
		if (!contentType || !contentType.includes('application/json')) {
			throw new Error('API not available');
		}

		if (!res.ok) {
			const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
			throw new Error(error.detail || 'Failed to create prompt');
		}

		return res.json();
	} catch (e) {
		console.warn('[prompt-groups] API not available, using local data');
		const command = data.command.startsWith('/') ? data.command : `/${data.command}`;
		const existing = localPrompts.find((p) => p.command === command);
		if (existing) throw new Error('Prompt with this command already exists');

		const newPrompt: PersonaPrompt = {
			command,
			title: data.title,
			content: data.content,
			prompt_type: data.prompt_type,
			persona_value: data.persona_value
		};
		localPrompts = [...localPrompts, newPrompt];
		return newPrompt;
	}
};

export const updatePersonaPrompt = async (
	token: string,
	command: string,
	data: Partial<PersonaPrompt>
): Promise<PersonaPrompt> => {
	try {
		const res = await fetch(
			`${WEBUI_API_BASE_URL}/prompts/command${encodeURIComponent(command)}/update`,
			{
				method: 'POST',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					authorization: `Bearer ${token}`
				},
				body: JSON.stringify(data)
			}
		);

		const contentType = res.headers.get('content-type');
		if (!contentType || !contentType.includes('application/json')) {
			throw new Error('API not available');
		}

		if (!res.ok) {
			throw new Error('Failed to update prompt');
		}

		return res.json();
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		const index = localPrompts.findIndex((p) => p.command === command);
		if (index === -1) throw new Error('Prompt not found');
		localPrompts[index] = { ...localPrompts[index], ...data };
		return localPrompts[index];
	}
};

export const deletePersonaPrompt = async (token: string, command: string): Promise<boolean> => {
	try {
		const res = await fetch(
			`${WEBUI_API_BASE_URL}/prompts/command/${encodeURIComponent(command)}/delete`,
			{
				method: 'DELETE',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					authorization: `Bearer ${token}`
				}
			}
		);

		const contentType = res.headers.get('content-type');
		if (!contentType || !contentType.includes('application/json')) {
			throw new Error('API not available');
		}

		if (!res.ok) {
			throw new Error('Failed to delete prompt');
		}

		return true;
	} catch {
		console.warn('[prompt-groups] API not available, using local data');
		localPrompts = localPrompts.filter((p) => p.command !== command);
		localGroups = localGroups.map((g) => ({
			...g,
			mappings: g.mappings.filter((m) => m.prompt_command !== command)
		}));
		return true;
	}
};

export const getPromptsByType = async (
	token: string,
	promptType: PromptType
): Promise<PersonaPrompt[]> => {
	const prompts = await getPersonaPrompts(token);
	return prompts.filter((p) => p.prompt_type === promptType);
};

// ============================================
// Available Personas (동적 페르소나 옵션 조회)
// ============================================

export const getAvailablePersonas = async (token: string): Promise<AvailablePersonas> => {
	try {
		return await apiCall<AvailablePersonas>('/personas/list', token);
	} catch {
		// Build from local data
		const proficiencyPrompts = localPrompts.filter((p) => p.prompt_type === 'proficiency');
		const stylePrompts = localPrompts.filter((p) => p.prompt_type === 'style');

		const proficiencyLevels: PersonaOption[] = [];
		const responseStyles: PersonaOption[] = [];

		proficiencyPrompts.forEach((p) => {
			if (p.persona_value) {
				const existing = proficiencyLevels.find((l) => l.value === p.persona_value);
				if (existing) {
					existing.prompts.push(p);
				} else {
					proficiencyLevels.push({ value: p.persona_value, prompts: [p] });
				}
			}
		});

		stylePrompts.forEach((p) => {
			if (p.persona_value) {
				const existing = responseStyles.find((s) => s.value === p.persona_value);
				if (existing) {
					existing.prompts.push(p);
				} else {
					responseStyles.push({ value: p.persona_value, prompts: [p] });
				}
			}
		});

		return { proficiency_levels: proficiencyLevels, response_styles: responseStyles };
	}
};

export const getGroupAvailablePersonas = async (
	token: string,
	groupId: string
): Promise<AvailablePersonas> => {
	try {
		return await apiCall<AvailablePersonas>(`/${groupId}/personas/list`, token);
	} catch {
		const group = localGroups.find((g) => g.id === groupId);
		if (!group) throw new Error('Group not found');

		const groupPromptCommands = group.mappings.map((m) => m.prompt_command);
		const groupPrompts = localPrompts.filter((p) => groupPromptCommands.includes(p.command));

		const proficiencyPrompts = groupPrompts.filter((p) => p.prompt_type === 'proficiency');
		const stylePrompts = groupPrompts.filter((p) => p.prompt_type === 'style');

		const proficiencyLevels: PersonaOption[] = [];
		const responseStyles: PersonaOption[] = [];

		proficiencyPrompts.forEach((p) => {
			if (p.persona_value) {
				const existing = proficiencyLevels.find((l) => l.value === p.persona_value);
				if (existing) {
					existing.prompts.push(p);
				} else {
					proficiencyLevels.push({ value: p.persona_value, prompts: [p] });
				}
			}
		});

		stylePrompts.forEach((p) => {
			if (p.persona_value) {
				const existing = responseStyles.find((s) => s.value === p.persona_value);
				if (existing) {
					existing.prompts.push(p);
				} else {
					responseStyles.push({ value: p.persona_value, prompts: [p] });
				}
			}
		});

		return { proficiency_levels: proficiencyLevels, response_styles: responseStyles };
	}
};

// ============================================
// Prompt Composition (프롬프트 조합)
// ============================================

export const composePrompts = async (
	token: string,
	groupId: string,
	proficiencyValue: string,
	styleValue: string
): Promise<ComposeResult> => {
	try {
		return await apiCall<ComposeResult>(`/${groupId}/compose`, token, {
			method: 'POST',
			body: JSON.stringify({
				proficiency_value: proficiencyValue,
				style_value: styleValue
			})
		});
	} catch {
		const group = localGroups.find((g) => g.id === groupId);
		if (!group) throw new Error('Group not found');

		const groupPromptCommands = group.mappings.map((m) => m.prompt_command);
		const groupPrompts = localPrompts.filter((p) => groupPromptCommands.includes(p.command));

		const basePrompts = groupPrompts.filter((p) => p.prompt_type === 'base');
		const proficiencyPrompt = groupPrompts.find(
			(p) => p.prompt_type === 'proficiency' && p.persona_value === proficiencyValue
		);
		const stylePrompt = groupPrompts.find(
			(p) => p.prompt_type === 'style' && p.persona_value === styleValue
		);

		const usedPrompts: PersonaPrompt[] = [...basePrompts];
		if (proficiencyPrompt) usedPrompts.push(proficiencyPrompt);
		if (stylePrompt) usedPrompts.push(stylePrompt);

		const combinedContent = usedPrompts.map((p) => p.content).join('\n\n');

		return { combined_content: combinedContent, used_prompts: usedPrompts };
	}
};
