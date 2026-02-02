<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	// Default values for permissions
	const defaultPermissions = {
		workspace: {
			models: false,
			knowledge: false,
			prompts: false,
			tools: false
		},
		sharing: {
			public_models: false,
			public_knowledge: false,
			public_prompts: false,
			public_tools: false
		},
		chat: {
			controls: true,
			file_upload: true,
			delete: true,
			edit: true,
			stt: true,
			tts: true,
			call: true,
			multiple_models: true,
			temporary: true,
			temporary_enforced: false
		},
		features: {
			direct_tool_servers: false,
			web_search: true,
			image_generation: true,
			code_interpreter: true
		}
	};

	export let permissions = {};

	// Reactive statement to ensure all fields are present in `permissions`
	$: {
		permissions = fillMissingProperties(permissions, defaultPermissions);
	}

	function fillMissingProperties(obj: any, defaults: any) {
		return {
			...defaults,
			...obj,
			workspace: { ...defaults.workspace, ...obj.workspace },
			sharing: { ...defaults.sharing, ...obj.sharing },
			chat: { ...defaults.chat, ...obj.chat },
			features: { ...defaults.features, ...obj.features }
		};
	}

	onMount(() => {
		permissions = fillMissingProperties(permissions, defaultPermissions);
	});
</script>

<div class="space-y-4">
	<!-- Workspace Permissions Section -->
	<div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
		<div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-blue-100 dark:bg-blue-900/40 rounded-lg">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-blue-600 dark:text-blue-400">
						<path stroke-linecap="round" stroke-linejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
					</svg>
				</div>
				<div>
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Workspace Permissions')}
					</h3>
					<p class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
						Control access to workspace resources
					</p>
				</div>
			</div>
		</div>
		<div class="p-6 space-y-3">
			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Models Access')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to access and manage models
					</div>
				</div>
				<Switch bind:state={permissions.workspace.models} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Knowledge Access')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to access and manage knowledge bases
					</div>
				</div>
				<Switch bind:state={permissions.workspace.knowledge} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Prompts Access')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to access and manage prompts
					</div>
				</div>
				<Switch bind:state={permissions.workspace.prompts} />
			</div>

			<Tooltip
				content={$i18n.t(
					'Warning: Enabling this will allow users to upload arbitrary code on the server.'
				)}
				placement="top-start"
			>
				<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
					<div class="flex-1">
						<div class="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-1.5">
							{$i18n.t('Tools Access')}
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5 text-amber-500">
								<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
							</svg>
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Allow users to access and manage tools
						</div>
					</div>
					<Switch bind:state={permissions.workspace.tools} />
				</div>
			</Tooltip>
		</div>
	</div>

	<!-- Sharing Permissions Section -->
	<div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
		<div class="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-green-100 dark:bg-green-900/40 rounded-lg">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-green-600 dark:text-green-400">
						<path stroke-linecap="round" stroke-linejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
					</svg>
				</div>
				<div>
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Sharing Permissions')}
					</h3>
					<p class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
						Control public sharing capabilities
					</p>
				</div>
			</div>
		</div>
		<div class="p-6 space-y-3">
			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Models Public Sharing')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to share models publicly
					</div>
				</div>
				<Switch bind:state={permissions.sharing.public_models} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Knowledge Public Sharing')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to share knowledge bases publicly
					</div>
				</div>
				<Switch bind:state={permissions.sharing.public_knowledge} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Prompts Public Sharing')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to share prompts publicly
					</div>
				</div>
				<Switch bind:state={permissions.sharing.public_prompts} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Tools Public Sharing')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to share tools publicly
					</div>
				</div>
				<Switch bind:state={permissions.sharing.public_tools} />
			</div>
		</div>
	</div>

	<!-- Chat Permissions Section -->
	<div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
		<div class="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-purple-100 dark:bg-purple-900/40 rounded-lg">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-purple-600 dark:text-purple-400">
						<path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
					</svg>
				</div>
				<div>
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Chat Permissions')}
					</h3>
					<p class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
						Control chat features and capabilities
					</p>
				</div>
			</div>
		</div>
		<div class="p-6 space-y-3">
			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow File Upload')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Enable file attachments in chats
					</div>
				</div>
				<Switch bind:state={permissions.chat.file_upload} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow Chat Controls')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Enable advanced chat control features
					</div>
				</div>
				<Switch bind:state={permissions.chat.controls} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow Chat Delete')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to delete their chats
					</div>
				</div>
				<Switch bind:state={permissions.chat.delete} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow Chat Edit')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow users to edit their messages
					</div>
				</div>
				<Switch bind:state={permissions.chat.edit} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow Speech to Text')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Enable voice input for messages
					</div>
				</div>
				<Switch bind:state={permissions.chat.stt} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow Text to Speech')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Enable voice output for responses
					</div>
				</div>
				<Switch bind:state={permissions.chat.tts} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow Call')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Enable voice call functionality
					</div>
				</div>
				<Switch bind:state={permissions.chat.call} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow Multiple Models in Chat')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow using multiple models simultaneously
					</div>
				</div>
				<Switch bind:state={permissions.chat.multiple_models} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Allow Temporary Chat')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Enable temporary chat sessions
					</div>
				</div>
				<Switch bind:state={permissions.chat.temporary} />
			</div>

			{#if permissions.chat.temporary}
				<div class="flex w-full justify-between items-center p-3 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 ml-4">
					<div class="flex-1">
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Enforce Temporary Chat')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Make all chats temporary by default
						</div>
					</div>
					<Switch bind:state={permissions.chat.temporary_enforced} />
				</div>
			{/if}
		</div>
	</div>

	<!-- Features Permissions Section -->
	<div class="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
		<div class="bg-gradient-to-r from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/20 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
			<div class="flex items-center gap-3">
				<div class="p-2 bg-orange-100 dark:bg-orange-900/40 rounded-lg">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-orange-600 dark:text-orange-400">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
					</svg>
				</div>
				<div>
					<h3 class="text-base font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Features Permissions')}
					</h3>
					<p class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
						Control advanced feature access
					</p>
				</div>
			</div>
		</div>
		<div class="p-6 space-y-3">
			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Direct Tool Servers')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow direct connections to tool servers
					</div>
				</div>
				<Switch bind:state={permissions.features.direct_tool_servers} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Web Search')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Enable web search capabilities
					</div>
				</div>
				<Switch bind:state={permissions.features.web_search} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Image Generation')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Allow AI image generation
					</div>
				</div>
				<Switch bind:state={permissions.features.image_generation} />
			</div>

			<div class="flex w-full justify-between items-center p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
				<div class="flex-1">
					<div class="text-sm font-medium text-gray-900 dark:text-white">
						{$i18n.t('Code Interpreter')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Enable code execution capabilities
					</div>
				</div>
				<Switch bind:state={permissions.features.code_interpreter} />
			</div>
		</div>
	</div>
</div>