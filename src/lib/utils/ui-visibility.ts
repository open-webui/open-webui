// Stable control IDs describe user actions or preferences, not component locations.
export const CONTROL_LABELS = {
	'model_editor.capabilities.vision': 'settings.admin.models.capabilities.vision.label',
	'model_editor.capabilities.file_upload': 'settings.admin.models.capabilities.fileUpload.label',
	'model_editor.capabilities.file_context': 'settings.admin.models.capabilities.fileContext.label',
	'model_editor.capabilities.web_search': 'settings.admin.models.capabilities.webSearch.label',
	'model_editor.capabilities.image_generation':
		'settings.admin.models.capabilities.imageGeneration.label',
	'model_editor.capabilities.code_interpreter':
		'settings.admin.models.capabilities.codeInterpreter.label',
	'model_editor.capabilities.terminal': 'settings.admin.models.capabilities.terminal.label',
	'model_editor.capabilities.usage': 'settings.admin.models.capabilities.usage.label',
	'model_editor.capabilities.citations': 'settings.admin.models.capabilities.citations.label',
	'model_editor.capabilities.status_updates':
		'settings.admin.models.capabilities.statusUpdates.label',
	'model_editor.capabilities.memory': 'settings.admin.models.capabilities.memory.label',
	'model_editor.capabilities.builtin_tools':
		'settings.admin.models.capabilities.builtinTools.label',
	'model_editor.defaults.web_search': 'settings.admin.models.capabilities.webSearch.label',
	'model_editor.defaults.image_generation':
		'settings.admin.models.capabilities.imageGeneration.label',
	'model_editor.defaults.code_interpreter':
		'settings.admin.models.capabilities.codeInterpreter.label',
	'model_editor.tools.time': 'settings.admin.models.builtinTools.time.label',
	'model_editor.tools.user_input': 'settings.admin.models.builtinTools.userInput.label',
	'model_editor.tools.memory': 'settings.admin.models.builtinTools.memory.label',
	'model_editor.tools.chats': 'settings.admin.models.builtinTools.chats.label',
	'model_editor.tools.notes': 'settings.admin.models.builtinTools.notes.label',
	'model_editor.tools.knowledge': 'settings.admin.models.builtinTools.knowledge.label',
	'model_editor.tools.files': 'settings.admin.models.builtinTools.files.label',
	'model_editor.tools.channels': 'settings.admin.models.builtinTools.channels.label',
	'model_editor.tools.notifications': 'settings.admin.models.builtinTools.notifications.label',
	'model_editor.tools.web_search': 'settings.admin.models.builtinTools.webSearch.label',
	'model_editor.tools.image_generation': 'settings.admin.models.builtinTools.imageGeneration.label',
	'model_editor.tools.code_interpreter': 'settings.admin.models.builtinTools.codeInterpreter.label',
	'model_editor.tools.tasks': 'settings.admin.models.builtinTools.tasks.label',
	'model_editor.tools.automations': 'settings.admin.models.builtinTools.automations.label',
	'model_editor.tools.calendar': 'settings.admin.models.builtinTools.calendar.label',
	'model_editor.tools.subagents': 'settings.admin.models.builtinTools.subagents.label',
	'model_editor.tools.skills': 'settings.admin.models.builtinTools.skills.label',
	'chat.capture': 'Capture',
	'chat.compare': 'Compare text',
	'chat.attach_webpage': 'Attach Webpage',
	'chat.attach_files': 'Attach Files',
	'chat.attach_notes': 'Attach Notes',
	'chat.attach_knowledge': 'Attach Knowledge',
	'chat.reference_chats': 'Reference Chats',
	'chat.status': '/status',
	'chat.model_command': '/model',
	'chat.settings_command': '/settings',
	'chat.usage': 'settings.admin.models.capabilities.usage.label',
	'chat.merge': 'Merge Responses',
	'chat.code_preview': 'Preview',
	'chat.fork': 'Fork chat',
	'chat.artifacts': 'Artifacts',
	'chat.archive': 'Archive',
	'chat.tags': 'Tags',
	'models.set_default': 'Set as default',
	'models.pin': 'Keep in Sidebar',
	'settings.usage': 'settings.personal.usage.title',
	'settings.speech_to_text_engine': 'settings.personal.audio.speechToTextEngine.label',
	'settings.text_to_speech_engine': 'settings.personal.audio.textToSpeechEngine.label',
	'settings.user_location': 'settings.personal.interface.allowUserLocation.label',
	'settings.chat_bubble': 'settings.personal.interface.chatBubbleUi.label',
	'settings.widescreen': 'settings.personal.interface.widescreenMode.label',
	'settings.floating_action_buttons': 'settings.personal.interface.floatingQuickActions.label',
	'settings.rich_text_input': 'settings.personal.interface.richTextInputForChat.label',
	'settings.large_text_as_file': 'settings.personal.interface.pasteLargeTextAsFile.label',
	'settings.detect_artifacts': 'settings.personal.interface.detectArtifactsAutomatically.label',
	'settings.iframe_sandbox_allow_scripts':
		'settings.personal.interface.iframeSandboxAllowScripts.label',
	'settings.iframe_sandbox_allow_same_origin':
		'settings.personal.interface.iframeSandboxAllowSameOrigin.label',
	'settings.iframe_sandbox_allow_forms':
		'settings.personal.interface.iframeSandboxAllowForms.label',
	'settings.iframe_sandbox_allow_downloads':
		'settings.personal.interface.iframeSandboxAllowDownloads.label'
} as const;

export type ControlId = keyof typeof CONTROL_LABELS;
export type Visibility = Partial<Record<ControlId, boolean>>;
export type VisibilityContext = {
	user?: { role?: string } | null;
	config?: { ui?: { visibility?: Visibility } } | null;
};

export const CONTROL_GROUPS = [
	['model_editor.capabilities.', 'settings.admin.models.capabilities.title'],
	['model_editor.defaults.', 'settings.admin.models.defaultFeatures.title'],
	['model_editor.tools.', 'settings.admin.models.builtinTools.title'],
	['chat.', 'Chat'],
	['models.', 'Models'],
	['settings.', 'Settings']
] as const;

export const isControlVisible = (id: ControlId, { user, config }: VisibilityContext) =>
	user?.role === 'admin' || config?.ui?.visibility?.[id] !== false;
