<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import { DEFAULT_PERMISSIONS } from '$lib/constants/permissions';

	export let permissions = {};
	export let defaultPermissions = {};

	// Local state initialized from prop with defaults filled in
	let localPermissions = $state(fillMissingProperties(permissions, DEFAULT_PERMISSIONS));

	function fillMissingProperties(obj: any, defaults: any) {
		return {
			...defaults,
			...obj,
			workspace: { ...defaults.workspace, ...obj.workspace },
			sharing: { ...defaults.sharing, ...obj.sharing },
			chat: { ...defaults.chat, ...obj.chat },
			features: { ...defaults.features, ...obj.features },
			settings: { ...defaults.settings, ...obj.settings }
		};
	}

	// Update local state when prop changes
	$: permissions, (localPermissions = fillMissingProperties(permissions, DEFAULT_PERMISSIONS));

	onMount(() => {
		localPermissions = fillMissingProperties(permissions, DEFAULT_PERMISSIONS);
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
				<Switch bind:state={localPermissions.workspace.models} />
			</div>

			{#if localPermissions.workspace.models}
				<div class="ml-2 flex flex-col gap-2 pt-0.5 pb-1">
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Import Models')}
						</div>
						<Switch bind:state={localPermissions.workspace.models_import} />
					</div>
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Export Models')}
						</div>
						<Switch bind:state={localPermissions.workspace.models_export} />
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
				<Switch bind:state={localPermissions.workspace.knowledge} />
			</div>
			{#if defaultPermissions?.workspace?.knowledge && !localPermissions.workspace.knowledge}
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
				<Switch bind:state={localPermissions.workspace.prompts} />
			</div>

			{#if localPermissions.workspace.prompts}
				<div class="ml-2 flex flex-col gap-2 pt-0.5 pb-1">
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Import Prompts')}
						</div>
						<Switch bind:state={localPermissions.workspace.prompts_import} />
					</div>
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Export Prompts')}
						</div>
						<Switch bind:state={localPermissions.workspace.prompts_export} />
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
				<Switch bind:state={localPermissions.workspace.tools} />
			</Tooltip>

			{#if localPermissions.workspace.tools}
				<div class="ml-2 flex flex-col gap-2 pt-0.5 pb-1">
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Import Tools')}
						</div>
						<Switch bind:state={localPermissions.workspace.tools_import} />
					</div>
					<div class="flex w-full justify-between">
						<div class="self-center text-xs">
							{$i18n.t('Export Tools')}
						</div>
						<Switch bind:state={localPermissions.workspace.tools_export} />
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
				<Switch bind:state={localPermissions.sharing.models} />
			</div>
			{#if defaultPermissions?.sharing?.models && !localPermissions.sharing.models}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if localPermissions.sharing.models}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Models Public Sharing')}
					</div>
					<Switch bind:state={localPermissions.sharing.public_models} />
				</div>
				{#if defaultPermissions?.sharing?.public_models && !localPermissions.sharing.public_models}
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
				<Switch bind:state={localPermissions.sharing.knowledge} />
			</div>
			{#if defaultPermissions?.sharing?.knowledge && !localPermissions.sharing.knowledge}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if localPermissions.sharing.knowledge}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Knowledge Public Sharing')}
					</div>
					<Switch bind:state={localPermissions.sharing.public_knowledge} />
				</div>
				{#if defaultPermissions?.sharing?.public_knowledge && !localPermissions.sharing.public_knowledge}
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
				<Switch bind:state={localPermissions.sharing.prompts} />
			</div>
			{#if defaultPermissions?.sharing?.prompts && !localPermissions.sharing.prompts}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if localPermissions.sharing.prompts}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Prompts Public Sharing')}
					</div>
					<Switch bind:state={localPermissions.sharing.public_prompts} />
				</div>
				{#if defaultPermissions?.sharing?.public_prompts && !localPermissions.sharing.public_prompts}
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
				<Switch bind:state={localPermissions.sharing.tools} />
			</div>
			{#if defaultPermissions?.sharing?.tools && !localPermissions.sharing.tools}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if localPermissions.sharing.tools}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Tools Public Sharing')}
					</div>
					<Switch bind:state={localPermissions.sharing.public_tools} />
				</div>
				{#if defaultPermissions?.sharing?.public_tools && !localPermissions.sharing.public_tools}
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
				<Switch bind:state={localPermissions.sharing.notes} />
			</div>
			{#if defaultPermissions?.sharing?.notes && !localPermissions.sharing.notes}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if localPermissions.sharing.notes}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Notes Public Sharing')}
					</div>
					<Switch bind:state={localPermissions.sharing.public_notes} />
				</div>
				{#if defaultPermissions?.sharing?.public_notes && !localPermissions.sharing.public_notes}
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
				<Switch bind:state={localPermissions.chat.file_upload} />
			</div>
			{#if defaultPermissions?.chat?.file_upload && !localPermissions.chat.file_upload}
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
				<Switch bind:state={localPermissions.chat.controls} />
			</div>
			{#if defaultPermissions?.chat?.controls && !localPermissions.chat.controls}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if localPermissions.chat.controls}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Allow Chat Valves')}
					</div>
					<Switch bind:state={localPermissions.chat.valves} />
				</div>
				{#if defaultPermissions?.chat?.valves && !localPermissions.chat.valves}
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
					<Switch bind:state={localPermissions.chat.system_prompt} />
				</div>
				{#if defaultPermissions?.chat?.system_prompt && !localPermissions.chat.system_prompt}
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
					<Switch bind:state={localPermissions.chat.params} />
				</div>
				{#if defaultPermissions?.chat?.params && !localPermissions.chat.params}
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
				<Switch bind:state={localPermissions.chat.edit} />
			</div>
			{#if defaultPermissions?.chat?.edit && !localPermissions.chat.edit}
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
				<Switch bind:state={localPermissions.chat.delete} />
			</div>
			{#if defaultPermissions?.chat?.delete && !localPermissions.chat.delete}
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
				<Switch bind:state={localPermissions.chat.delete_message} />
			</div>
			{#if defaultPermissions?.chat?.delete_message && !localPermissions.chat.delete_message}
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
				<Switch bind:state={localPermissions.chat.continue_response} />
			</div>
			{#if defaultPermissions?.chat?.continue_response && !localPermissions.chat.continue_response}
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
				<Switch bind:state={localPermissions.chat.regenerate_response} />
			</div>
			{#if defaultPermissions?.chat?.regenerate_response && !localPermissions.chat.regenerate_response}
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
				<Switch bind:state={localPermissions.chat.rate_response} />
			</div>
			{#if defaultPermissions?.chat?.rate_response && !localPermissions.chat.rate_response}
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
				<Switch bind:state={localPermissions.chat.share} />
			</div>
			{#if defaultPermissions?.chat?.share && !localPermissions.chat.share}
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
				<Switch bind:state={localPermissions.chat.export} />
			</div>
			{#if defaultPermissions?.chat?.export && !localPermissions.chat.export}
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
				<Switch bind:state={localPermissions.chat.stt} />
			</div>
			{#if defaultPermissions?.chat?.stt && !localPermissions.chat.stt}
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
				<Switch bind:state={localPermissions.chat.tts} />
			</div>
			{#if defaultPermissions?.chat?.tts && !localPermissions.chat.tts}
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
				<Switch bind:state={localPermissions.chat.call} />
			</div>
			{#if defaultPermissions?.chat?.call && !localPermissions.chat.call}
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
				<Switch bind:state={localPermissions.chat.multiple_models} />
			</div>
			{#if defaultPermissions?.chat?.multiple_models && !localPermissions.chat.multiple_models}
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
				<Switch bind:state={localPermissions.chat.temporary} />
			</div>
			{#if defaultPermissions?.chat?.temporary && !localPermissions.chat.temporary}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>

		{#if localPermissions.chat.temporary}
			<div class="flex flex-col w-full">
				<div class="flex w-full justify-between my-1">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Enforce Temporary Chat')}
					</div>
					<Switch bind:state={localPermissions.chat.temporary_enforced} />
				</div>
				{#if defaultPermissions?.chat?.temporary_enforced && !localPermissions.chat.temporary_enforced}
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
				<Switch bind:state={localPermissions.features.api_keys} />
			</div>
			{#if defaultPermissions?.features?.api_keys && !localPermissions.features.api_keys}
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
				<Switch bind:state={localPermissions.features.notes} />
			</div>
			{#if defaultPermissions?.features?.notes && !localPermissions.features.notes}
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
				<Switch bind:state={localPermissions.features.channels} />
			</div>
			{#if defaultPermissions?.features?.channels && !localPermissions.features.channels}
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
				<Switch bind:state={localPermissions.features.folders} />
			</div>
			{#if defaultPermissions?.features?.folders && !localPermissions.features.folders}
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
				<Switch bind:state={localPermissions.features.direct_tool_servers} />
			</div>
			{#if defaultPermissions?.features?.direct_tool_servers && !localPermissions.features.direct_tool_servers}
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
				<Switch bind:state={localPermissions.features.web_search} />
			</div>
			{#if defaultPermissions?.features?.web_search && !localPermissions.features.web_search}
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
				<Switch bind:state={localPermissions.features.image_generation} />
			</div>
			{#if defaultPermissions?.features?.image_generation && !localPermissions.features.image_generation}
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
				<Switch bind:state={localPermissions.features.code_interpreter} />
			</div>
			{#if defaultPermissions?.features?.code_interpreter && !localPermissions.features.code_interpreter}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>
	</div>

	<hr class=" border-gray-100/30 dark:border-gray-850/30" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Settings Permissions')}</div>

		<div class="flex flex-col w-full">
			<div class="flex w-full justify-between my-1">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Interface Settings Access')}
				</div>
				<Switch bind:state={localPermissions.settings.interface} />
			</div>
			{#if defaultPermissions?.settings?.interface && !localPermissions.settings.interface}
				<div>
					<div class="text-xs text-gray-500">
						{$i18n.t('This is a default user permission and will remain enabled.')}
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
