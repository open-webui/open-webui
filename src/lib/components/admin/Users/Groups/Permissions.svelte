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
			code_interpreter: true
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
	<!-- {$i18n.t('Default Model')}
	{$i18n.t('Model Filtering')}
	{$i18n.t('Model Permissions')}
	{$i18n.t('No model IDs')} -->

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Workspace Permissions')}</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Models Access')}
				</div>
				<Switch bind:state={permissions.workspace.models} />
			</div>

			{#if permissions.workspace.models}
				<div class="ml-2 flex flex-col gap-2 pt-0.5 pb-1">
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Import Models')}
						</div>
						<Switch bind:state={permissions.workspace.models_import} />
					</div>
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Export Models')}
						</div>
						<Switch bind:state={permissions.workspace.models_export} />
					</div>
				</div>
			{:else if defaultPermissions?.workspace?.models}
				<div class="pb-0.5">
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Knowledge Access')}
				</div>
				<Switch bind:state={permissions.workspace.knowledge} />
			</div>
			{#if defaultPermissions?.workspace?.knowledge && !permissions.workspace.knowledge}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Prompts Access')}
				</div>
				<Switch bind:state={permissions.workspace.prompts} />
			</div>

			{#if permissions.workspace.prompts}
				<div class="ml-2 flex flex-col gap-2 pt-0.5 pb-1">
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Import Prompts')}
						</div>
						<Switch bind:state={permissions.workspace.prompts_import} />
					</div>
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Export Prompts')}
						</div>
						<Switch bind:state={permissions.workspace.prompts_export} />
					</div>
				</div>
			{:else if defaultPermissions?.workspace?.prompts}
				<div class="pb-0.5">
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<Tooltip
				className="flex w-full justify-between my-1"
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

			{#if permissions.workspace.tools}
				<div class="ml-2 flex flex-col gap-2 pt-0.5 pb-1">
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Import Tools')}
						</div>
						<Switch bind:state={permissions.workspace.tools_import} />
					</div>
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Export Tools')}
						</div>
						<Switch bind:state={permissions.workspace.tools_export} />
					</div>
				</div>
			{:else if defaultPermissions?.workspace?.tools}
				<div class="pb-0.5">
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>
	</div>

	<hr class=" border-gray-100/30 dark:border-gray-850/30" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Sharing Permissions')}</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Models Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.models} />
			</div>
			{#if defaultPermissions?.sharing?.models && !permissions.sharing.models}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.sharing.models}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Models Public Sharing')}
					</div>
					<Switch bind:state={permissions.sharing.public_models} />
				</div>
				{#if defaultPermissions?.sharing?.public_models && !permissions.sharing.public_models}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Knowledge Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.knowledge} />
			</div>
			{#if defaultPermissions?.sharing?.knowledge && !permissions.sharing.knowledge}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.sharing.knowledge}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Knowledge Public Sharing')}
					</div>
					<Switch bind:state={permissions.sharing.public_knowledge} />
				</div>
				{#if defaultPermissions?.sharing?.public_knowledge && !permissions.sharing.public_knowledge}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Prompts Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.prompts} />
			</div>
			{#if defaultPermissions?.sharing?.prompts && !permissions.sharing.prompts}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.sharing.prompts}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Prompts Public Sharing')}
					</div>
					<Switch bind:state={permissions.sharing.public_prompts} />
				</div>
				{#if defaultPermissions?.sharing?.public_prompts && !permissions.sharing.public_prompts}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Tools Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.tools} />
			</div>
			{#if defaultPermissions?.sharing?.tools && !permissions.sharing.tools}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.sharing.tools}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Tools Public Sharing')}
					</div>
					<Switch bind:state={permissions.sharing.public_tools} />
				</div>
				{#if defaultPermissions?.sharing?.public_tools && !permissions.sharing.public_tools}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Notes Sharing')}
				</div>
				<Switch bind:state={permissions.sharing.notes} />
			</div>
			{#if defaultPermissions?.sharing?.notes && !permissions.sharing.notes}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.sharing.notes}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Notes Public Sharing')}
					</div>
					<Switch bind:state={permissions.sharing.public_notes} />
				</div>
				{#if defaultPermissions?.sharing?.public_notes && !permissions.sharing.public_notes}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<hr class=" border-gray-100/30 dark:border-gray-850/30" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Chat Permissions')}</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow File Upload')}
				</div>
				<Switch bind:state={permissions.chat.file_upload} />
			</div>
			{#if defaultPermissions?.chat?.file_upload && !permissions.chat.file_upload}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Controls')}
				</div>
				<Switch bind:state={permissions.chat.controls} />
			</div>
			{#if defaultPermissions?.chat?.controls && !permissions.chat.controls}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.chat.controls}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Allow Chat Valves')}
					</div>
					<Switch bind:state={permissions.chat.valves} />
				</div>
				{#if defaultPermissions?.chat?.valves && !permissions.chat.valves}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>

			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Allow Chat System Prompt')}
					</div>
					<Switch bind:state={permissions.chat.system_prompt} />
				</div>
				{#if defaultPermissions?.chat?.system_prompt && !permissions.chat.system_prompt}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>

			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Allow Chat Params')}
					</div>
					<Switch bind:state={permissions.chat.params} />
				</div>
				{#if defaultPermissions?.chat?.params && !permissions.chat.params}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Edit')}
				</div>
				<Switch bind:state={permissions.chat.edit} />
			</div>
			{#if defaultPermissions?.chat?.edit && !permissions.chat.edit}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Delete')}
				</div>
				<Switch bind:state={permissions.chat.delete} />
			</div>
			{#if defaultPermissions?.chat?.delete && !permissions.chat.delete}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Delete Messages')}
				</div>
				<Switch bind:state={permissions.chat.delete_message} />
			</div>
			{#if defaultPermissions?.chat?.delete_message && !permissions.chat.delete_message}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Continue Response')}
				</div>
				<Switch bind:state={permissions.chat.continue_response} />
			</div>
			{#if defaultPermissions?.chat?.continue_response && !permissions.chat.continue_response}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Regenerate Response')}
				</div>
				<Switch bind:state={permissions.chat.regenerate_response} />
			</div>
			{#if defaultPermissions?.chat?.regenerate_response && !permissions.chat.regenerate_response}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Rate Response')}
				</div>
				<Switch bind:state={permissions.chat.rate_response} />
			</div>
			{#if defaultPermissions?.chat?.rate_response && !permissions.chat.rate_response}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Share')}
				</div>
				<Switch bind:state={permissions.chat.share} />
			</div>
			{#if defaultPermissions?.chat?.share && !permissions.chat.share}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Chat Export')}
				</div>
				<Switch bind:state={permissions.chat.export} />
			</div>
			{#if defaultPermissions?.chat?.export && !permissions.chat.export}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Speech to Text')}
				</div>
				<Switch bind:state={permissions.chat.stt} />
			</div>
			{#if defaultPermissions?.chat?.stt && !permissions.chat.stt}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Text to Speech')}
				</div>
				<Switch bind:state={permissions.chat.tts} />
			</div>
			{#if defaultPermissions?.chat?.tts && !permissions.chat.tts}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Call')}
				</div>
				<Switch bind:state={permissions.chat.call} />
			</div>
			{#if defaultPermissions?.chat?.call && !permissions.chat.call}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Multiple Models in Chat')}
				</div>
				<Switch bind:state={permissions.chat.multiple_models} />
			</div>
			{#if defaultPermissions?.chat?.multiple_models && !permissions.chat.multiple_models}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Allow Temporary Chat')}
				</div>
				<Switch bind:state={permissions.chat.temporary} />
			</div>
			{#if defaultPermissions?.chat?.temporary && !permissions.chat.temporary}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if permissions.chat.temporary}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enforce Temporary Chat')}
					</div>
					<Switch bind:state={permissions.chat.temporary_enforced} />
				</div>
				{#if defaultPermissions?.chat?.temporary_enforced && !permissions.chat.temporary_enforced}
					<div>
						<div class="text-xs text-gray-500">
							{$i18n.t('This is a default user permission and will remain enabled.')}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>

	<hr class=" border-gray-100/30 dark:border-gray-850/30" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Features Permissions')}</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('API Keys')}
				</div>
				<Switch bind:state={permissions.features.api_keys} />
			</div>
			{#if defaultPermissions?.features?.api_keys && !permissions.features.api_keys}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Notes')}
				</div>
				<Switch bind:state={permissions.features.notes} />
			</div>
			{#if defaultPermissions?.features?.notes && !permissions.features.notes}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Channels')}
				</div>
				<Switch bind:state={permissions.features.channels} />
			</div>
			{#if defaultPermissions?.features?.channels && !permissions.features.channels}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Folders')}
				</div>
				<Switch bind:state={permissions.features.folders} />
			</div>
			{#if defaultPermissions?.features?.folders && !permissions.features.folders}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Direct Tool Servers')}
				</div>
				<Switch bind:state={permissions.features.direct_tool_servers} />
			</div>
			{#if defaultPermissions?.features?.direct_tool_servers && !permissions.features.direct_tool_servers}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Web Search')}
				</div>
				<Switch bind:state={permissions.features.web_search} />
			</div>
			{#if defaultPermissions?.features?.web_search && !permissions.features.web_search}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Image Generation')}
				</div>
				<Switch bind:state={permissions.features.image_generation} />
			</div>
			{#if defaultPermissions?.features?.image_generation && !permissions.features.image_generation}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Code Interpreter')}
				</div>
				<Switch bind:state={permissions.features.code_interpreter} />
			</div>
			{#if defaultPermissions?.features?.code_interpreter && !permissions.features.code_interpreter}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
