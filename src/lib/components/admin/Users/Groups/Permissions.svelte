<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

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

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Models Access')}
				</div>
				<Switch bind:state={permissions.workspace.models} />
			</div>
			{#if defaultPermissions?.workspace?.models && !permissions.workspace.models}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Knowledge Access')}
				</div>
				<Switch bind:state={permissions.workspace.knowledge} />
			</div>
			{#if defaultPermissions?.workspace?.knowledge && !permissions.workspace.knowledge}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Prompts Access')}
				</div>
				<Switch bind:state={permissions.workspace.prompts} />
			</div>
			{#if defaultPermissions?.workspace?.prompts && !permissions.workspace.prompts}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<Tooltip
				className="flex w-full justify-between my-2 pr-2"
				content={$i18n.t(
					'Warning: Enabling this will allow users to upload arbitrary code on the server.'
				)}
				placement="top-start"
			>
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Tools Access')}
				</div>
				<Switch bind:state={permissions.workspace.tools} />
			</Tooltip>
			{#if defaultPermissions?.workspace?.tools && !permissions.workspace.tools}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>
	</div>

	<hr class=" border-gray-100 dark:border-gray-850" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Sharing Permissions')}</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Models Public Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.public_models} />
			</div>
			{#if defaultPermissions?.sharing?.public_models && !permissions.sharing.public_models}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Knowledge Public Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.public_knowledge} />
			</div>
			{#if defaultPermissions?.sharing?.public_knowledge && !permissions.sharing.public_knowledge}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Prompts Public Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.public_prompts} />
			</div>
			{#if defaultPermissions?.sharing?.public_prompts && !permissions.sharing.public_prompts}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Tools Public Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.public_tools} />
			</div>
			{#if defaultPermissions?.sharing?.public_tools && !permissions.sharing.public_tools}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Notes Public Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.public_notes} />
			</div>
			{#if defaultPermissions?.sharing?.public_notes && !permissions.sharing.public_notes}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>
	</div>

	<hr class=" border-gray-100 dark:border-gray-850" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Chat Permissions')}</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow File Upload')}
				</div>
				<Switch bind:state={permissions.chat.file_upload} />
			</div>
			{#if defaultPermissions?.chat?.file_upload && !permissions.chat.file_upload}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Controls')}
				</div>
				<Switch bind:state={permissions.chat.controls} />
			</div>
			{#if defaultPermissions?.chat?.controls && !permissions.chat.controls}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.chat.controls}
			<div class="flex flex-col w-full pl-4">
				<div class="flex w-full justify-between my-2 pr-2">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Allow Chat Valves')}
					</div>
					<Switch bind:state={permissions.chat.valves} />
				</div>
				{#if defaultPermissions?.chat?.valves && !permissions.chat.valves}
					<div class="pb-1 pl-1 pr-2 pt-1">
						<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
							⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
						</div>
					</div>
				{/if}
			</div>

			<div class="flex flex-col w-full pl-4">
				<div class="flex w-full justify-between my-2 pr-2">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Allow Chat System Prompt')}
					</div>
					<Switch bind:state={permissions.chat.system_prompt} />
				</div>
				{#if defaultPermissions?.chat?.system_prompt && !permissions.chat.system_prompt}
					<div class="pb-1 pl-1 pr-2 pt-1">
						<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
							⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
						</div>
					</div>
				{/if}
			</div>

			<div class="flex flex-col w-full pl-4">
				<div class="flex w-full justify-between my-2 pr-2">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Allow Chat Params')}
					</div>
					<Switch bind:state={permissions.chat.params} />
				</div>
				{#if defaultPermissions?.chat?.params && !permissions.chat.params}
					<div class="pb-1 pl-1 pr-2 pt-1">
						<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
							⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Edit')}
				</div>
				<Switch bind:state={permissions.chat.edit} />
			</div>
			{#if defaultPermissions?.chat?.edit && !permissions.chat.edit}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Delete')}
				</div>
				<Switch bind:state={permissions.chat.delete} />
			</div>
			{#if defaultPermissions?.chat?.delete && !permissions.chat.delete}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Delete Messages')}
				</div>
				<Switch bind:state={permissions.chat.delete_message} />
			</div>
			{#if defaultPermissions?.chat?.delete_message && !permissions.chat.delete_message}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Continue Response')}
				</div>
				<Switch bind:state={permissions.chat.continue_response} />
			</div>
			{#if defaultPermissions?.chat?.continue_response && !permissions.chat.continue_response}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Regenerate Response')}
				</div>
				<Switch bind:state={permissions.chat.regenerate_response} />
			</div>
			{#if defaultPermissions?.chat?.regenerate_response && !permissions.chat.regenerate_response}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Rate Response')}
				</div>
				<Switch bind:state={permissions.chat.rate_response} />
			</div>
			{#if defaultPermissions?.chat?.rate_response && !permissions.chat.rate_response}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Share')}
				</div>
				<Switch bind:state={permissions.chat.share} />
			</div>
			{#if defaultPermissions?.chat?.share && !permissions.chat.share}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Export')}
				</div>
				<Switch bind:state={permissions.chat.export} />
			</div>
			{#if defaultPermissions?.chat?.export && !permissions.chat.export}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Speech to Text')}
				</div>
				<Switch bind:state={permissions.chat.stt} />
			</div>
			{#if defaultPermissions?.chat?.stt && !permissions.chat.stt}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Text to Speech')}
				</div>
				<Switch bind:state={permissions.chat.tts} />
			</div>
			{#if defaultPermissions?.chat?.tts && !permissions.chat.tts}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Call')}
				</div>
				<Switch bind:state={permissions.chat.call} />
			</div>
			{#if defaultPermissions?.chat?.call && !permissions.chat.call}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Multiple Models in Chat')}
				</div>
				<Switch bind:state={permissions.chat.multiple_models} />
			</div>
			{#if defaultPermissions?.chat?.multiple_models && !permissions.chat.multiple_models}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Temporary Chat')}
				</div>
				<Switch bind:state={permissions.chat.temporary} />
			</div>
			{#if defaultPermissions?.chat?.temporary && !permissions.chat.temporary}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.chat.temporary}
			<div class="flex flex-col w-full pl-4">
				<div class="flex w-full justify-between my-2 pr-2">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enforce Temporary Chat')}
					</div>
					<Switch bind:state={permissions.chat.temporary_enforced} />
				</div>
				{#if defaultPermissions?.chat?.temporary_enforced && !permissions.chat.temporary_enforced}
					<div class="pb-1 pl-1 pr-2 pt-1">
						<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
							⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<hr class=" border-gray-100 dark:border-gray-850" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Features Permissions')}</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Direct Tool Servers')}
				</div>
				<Switch bind:state={permissions.features.direct_tool_servers} />
			</div>
			{#if defaultPermissions?.features?.direct_tool_servers && !permissions.features.direct_tool_servers}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Web Search')}
				</div>
				<Switch bind:state={permissions.features.web_search} />
			</div>
			{#if defaultPermissions?.features?.web_search && !permissions.features.web_search}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Image Generation')}
				</div>
				<Switch bind:state={permissions.features.image_generation} />
			</div>
			{#if defaultPermissions?.features?.image_generation && !permissions.features.image_generation}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Code Interpreter')}
				</div>
				<Switch bind:state={permissions.features.code_interpreter} />
			</div>
			{#if defaultPermissions?.features?.code_interpreter && !permissions.features.code_interpreter}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Notes')}
				</div>
				<Switch bind:state={permissions.features.notes} />
			</div>
			{#if defaultPermissions?.features?.notes && !permissions.features.notes}
				<div class="pb-1 pl-1 pr-2 pt-1">
					<div class="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded px-2 py-1">
						⚠️ {$i18n.t('This permission is enabled for the default "user" role and will remain active.')}
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
