<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import PermissionSwitch from './PermissionSwitch.svelte';

	// Default values for permissions
	const DEFAULT_PERMISSIONS = {
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
			public_tools: false,
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
			direct_tool_servers: false,
			web_search: true,
			image_generation: true,
			code_interpreter: true,
			notes: true
		}
	};

	export let permissions = {};
	export let defaultPermissions = {};

	// Reactive statement to ensure all fields are present in `permissions`
	$: {
		permissions = fillMissingProperties(permissions, DEFAULT_PERMISSIONS);
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
		permissions = fillMissingProperties(permissions, DEFAULT_PERMISSIONS);
	});
</script>

<div class="space-y-2">
	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Workspace Permissions')}</div>
		<div class="flex flex-col space-y-2">
			<PermissionSwitch
				label={$i18n.t('Models Access')}
				bind:state={permissions.workspace.models}
				defaultState={defaultPermissions?.workspace?.models}
			/>
			<PermissionSwitch
				label={$i18n.t('Knowledge Access')}
				bind:state={permissions.workspace.knowledge}
				defaultState={defaultPermissions?.workspace?.knowledge}
			/>
			<PermissionSwitch
				label={$i18n.t('Prompts Access')}
				bind:state={permissions.workspace.prompts}
				defaultState={defaultPermissions?.workspace?.prompts}
			/>
			<PermissionSwitch
				label={$i18n.t('Tools Access')}
				bind:state={permissions.workspace.tools}
				defaultState={defaultPermissions?.workspace?.tools}
				tooltip={$i18n.t(
					'Warning: Enabling this will allow users to upload arbitrary code on the server.'
				)}
			/>
		</div>
	</div>

	<hr class=" border-gray-100 dark:border-gray-850" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Sharing Permissions')}</div>
		<div class="flex flex-col space-y-2">
			<PermissionSwitch
				label={$i18n.t('Models Public Sharing')}
				bind:state={permissions.sharing.public_models}
				defaultState={defaultPermissions?.sharing?.public_models}
			/>
			<PermissionSwitch
				label={$i18n.t('Knowledge Public Sharing')}
				bind:state={permissions.sharing.public_knowledge}
				defaultState={defaultPermissions?.sharing?.public_knowledge}
			/>
			<PermissionSwitch
				label={$i18n.t('Prompts Public Sharing')}
				bind:state={permissions.sharing.public_prompts}
				defaultState={defaultPermissions?.sharing?.public_prompts}
			/>
			<PermissionSwitch
				label={$i18n.t('Tools Public Sharing')}
				bind:state={permissions.sharing.public_tools}
				defaultState={defaultPermissions?.sharing?.public_tools}
			/>
			<PermissionSwitch
				label={$i18n.t('Notes Public Sharing')}
				bind:state={permissions.sharing.public_notes}
				defaultState={defaultPermissions?.sharing?.public_notes}
			/>
		</div>
	</div>

	<hr class=" border-gray-100 dark:border-gray-850" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Chat Permissions')}</div>
		<div class="flex flex-col space-y-2">
			<PermissionSwitch
				label={$i18n.t('Allow File Upload')}
				bind:state={permissions.chat.file_upload}
				defaultState={defaultPermissions?.chat?.file_upload}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Chat Controls')}
				bind:state={permissions.chat.controls}
				defaultState={defaultPermissions?.chat?.controls}
			/>

			{#if permissions.chat.controls}
				<div class="flex flex-col space-y-2 pl-4">
					<PermissionSwitch
						label={$i18n.t('Allow Chat Valves')}
						bind:state={permissions.chat.valves}
						defaultState={defaultPermissions?.chat?.valves}
					/>
					<PermissionSwitch
						label={$i18n.t('Allow Chat System Prompt')}
						bind:state={permissions.chat.system_prompt}
						defaultState={defaultPermissions?.chat?.system_prompt}
					/>
					<PermissionSwitch
						label={$i18n.t('Allow Chat Params')}
						bind:state={permissions.chat.params}
						defaultState={defaultPermissions?.chat?.params}
					/>
				</div>
			{/if}

			<PermissionSwitch
				label={$i18n.t('Allow Chat Edit')}
				bind:state={permissions.chat.edit}
				defaultState={defaultPermissions?.chat?.edit}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Chat Delete')}
				bind:state={permissions.chat.delete}
				defaultState={defaultPermissions?.chat?.delete}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Delete Messages')}
				bind:state={permissions.chat.delete_message}
				defaultState={defaultPermissions?.chat?.delete_message}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Continue Response')}
				bind:state={permissions.chat.continue_response}
				defaultState={defaultPermissions?.chat?.continue_response}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Regenerate Response')}
				bind:state={permissions.chat.regenerate_response}
				defaultState={defaultPermissions?.chat?.regenerate_response}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Rate Response')}
				bind:state={permissions.chat.rate_response}
				defaultState={defaultPermissions?.chat?.rate_response}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Chat Share')}
				bind:state={permissions.chat.share}
				defaultState={defaultPermissions?.chat?.share}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Chat Export')}
				bind:state={permissions.chat.export}
				defaultState={defaultPermissions?.chat?.export}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Speech to Text')}
				bind:state={permissions.chat.stt}
				defaultState={defaultPermissions?.chat?.stt}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Text to Speech')}
				bind:state={permissions.chat.tts}
				defaultState={defaultPermissions?.chat?.tts}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Call')}
				bind:state={permissions.chat.call}
				defaultState={defaultPermissions?.chat?.call}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Multiple Models in Chat')}
				bind:state={permissions.chat.multiple_models}
				defaultState={defaultPermissions?.chat?.multiple_models}
			/>
			<PermissionSwitch
				label={$i18n.t('Allow Temporary Chat')}
				bind:state={permissions.chat.temporary}
				defaultState={defaultPermissions?.chat?.temporary}
			/>

			{#if permissions.chat.temporary}
				<div class="pl-4">
					<PermissionSwitch
						label={$i18n.t('Enforce Temporary Chat')}
						bind:state={permissions.chat.temporary_enforced}
						defaultState={defaultPermissions?.chat?.temporary_enforced}
					/>
				</div>
			{/if}
		</div>
	</div>

	<hr class=" border-gray-100 dark:border-gray-850" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Features Permissions')}</div>
		<div class="flex flex-col space-y-2">
			<PermissionSwitch
				label={$i18n.t('Direct Tool Servers')}
				bind:state={permissions.features.direct_tool_servers}
				defaultState={defaultPermissions?.features?.direct_tool_servers}
			/>
			<PermissionSwitch
				label={$i18n.t('Web Search')}
				bind:state={permissions.features.web_search}
				defaultState={defaultPermissions?.features?.web_search}
			/>
			<PermissionSwitch
				label={$i18n.t('Image Generation')}
				bind:state={permissions.features.image_generation}
				defaultState={defaultPermissions?.features?.image_generation}
			/>
			<PermissionSwitch
				label={$i18n.t('Code Interpreter')}
				bind:state={permissions.features.code_interpreter}
				defaultState={defaultPermissions?.features?.code_interpreter}
			/>
			<PermissionSwitch
				label={$i18n.t('Notes')}
				bind:state={permissions.features.notes}
				defaultState={defaultPermissions?.features?.notes}
			/>
		</div>
	</div>
</div>