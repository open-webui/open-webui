export const DEFAULT_PERMISSIONS = {
	workspace: {
		models: false,
		knowledge: false,
		prompts: false,
		tools: false,
		models_import: false,
		models_export: false,
		prompts_import: false,
		prompts_export: false,
		tools_import: false,
		tools_export: false
	},
	sharing: {
		models: false,
		public_models: false,
		knowledge: false,
		public_knowledge: false,
		prompts: false,
		public_prompts: false,
		tools: false,
		public_tools: false,
		notes: false,
		public_notes: false
	},
	chat: {
		controls: true,
		valves: true,
		system_prompt: true,
		params: true,
		file_upload: true,
		delete: true,
		delete_message: true,
		continue_response: true,
		regenerate_response: true,
		rate_response: true,
		edit: true,
		share: true,
		export: true,
		stt: true,
		tts: true,
		call: true,
		multiple_models: true,
		temporary: true,
		temporary_enforced: false
	},
	features: {
		api_keys: false,
		notes: true,
		channels: true,
		folders: true,
		direct_tool_servers: false,
		web_search: true,
		image_generation: true,
		code_interpreter: true,
		memories: true
	},
	settings: {
		interface: true
	}
} as const;
