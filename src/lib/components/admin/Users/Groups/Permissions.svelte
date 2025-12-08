<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getMCPConfig } from '$lib/apis/mcp';
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
		chat: {
			controls: true,
			delete: true,
			edit: true,
			temporary: true,
			file_upload: true
		},
		features: {
			web_search: true,
			image_generation: true
		},
		mcp: {
			time_server: false,
			news_server: false,
			mpo_sharepoint_server: false
		}
	};

	export let permissions = {};

	// State for MCP configuration
	let mcpEnabled = false;
	let mcpConfigLoading = true;

	// Function to check if MCP is globally enabled
	const checkMCPEnabled = async () => {
		try {
			const mcpConfig = await getMCPConfig(localStorage.token);
			mcpEnabled = mcpConfig?.ENABLE_MCP_API || false;
		} catch (error) {
			console.error('Failed to fetch MCP config:', error);
			mcpEnabled = false;
		} finally {
			mcpConfigLoading = false;
		}
	};

	// Reactive statement to ensure all fields are present in `permissions`
	$: {
		permissions = fillMissingProperties(permissions, defaultPermissions);
	}

	function fillMissingProperties(obj: any, defaults: any) {
		return {
			...defaults,
			...obj,
			workspace: { ...defaults.workspace, ...obj.workspace },
			chat: { ...defaults.chat, ...obj.chat },
			features: { ...defaults.features, ...obj.features },
			mcp: { ...defaults.mcp, ...obj.mcp }
		};
	}

	onMount(() => {
		permissions = fillMissingProperties(permissions, defaultPermissions);
		checkMCPEnabled();
	});
</script>

<div>
	<!-- <div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Model Permissions')}</div>

		<div class="mb-2">
			<div class="flex justify-between items-center text-xs pr-2">
				<div class=" text-xs font-medium">{$i18n.t('Model Filtering')}</div>

				<Switch bind:state={permissions.model.filter} />
			</div>
		</div>

		{#if permissions.model.filter}
			<div class="mb-2">
				<div class=" space-y-1.5">
					<div class="flex flex-col w-full">
						<div class="mb-1 flex justify-between">
							<div class="text-xs text-gray-500">{$i18n.t('Model IDs')}</div>
						</div>

						{#if model_ids.length > 0}
							<div class="flex flex-col">
								{#each model_ids as modelId, modelIdx}
									<div class=" flex gap-2 w-full justify-between items-center">
										<div class=" text-sm flex-1 rounded-lg">
											{modelId}
										</div>
										<div class="flex-shrink-0">
											<button
												type="button"
												on:click={() => {
													model_ids = model_ids.filter((_, idx) => idx !== modelIdx);
												}}
											>
												<Minus strokeWidth="2" className="size-3.5" />
											</button>
										</div>
									</div>
								{/each}
							</div>
						{:else}
							<div class="text-gray-500 text-xs text-center py-2 px-10">
								{$i18n.t('No model IDs')}
							</div>
						{/if}
					</div>
				</div>
				<hr class=" border-gray-100 dark:border-gray-700/10 mt-2.5 mb-1 w-full" />

				<div class="flex items-center">
					<select
						class="w-full py-1 text-sm rounded-lg bg-transparent {selectedModelId
							? ''
							: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none"
						bind:value={selectedModelId}
					>
						<option value="">{$i18n.t('Select a model')}</option>
						{#each $models.filter((m) => m?.owned_by !== 'arena') as model}
							<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
						{/each}
					</select>

					<div>
						<button
							type="button"
							on:click={() => {
								if (selectedModelId && !permissions.model.model_ids.includes(selectedModelId)) {
									permissions.model.model_ids = [...permissions.model.model_ids, selectedModelId];
									selectedModelId = '';
								}
							}}
						>
							<Plus className="size-3.5" strokeWidth="2" />
						</button>
					</div>
				</div>
			</div>
		{/if}

		<div class=" space-y-1 mb-3">
			<div class="">
				<div class="flex justify-between items-center text-xs">
					<div class=" text-xs font-medium">{$i18n.t('Default Model')}</div>
				</div>
			</div>

			<div class="flex-1 mr-2">
				<select
					class="w-full bg-transparent outline-none py-0.5 text-sm"
					bind:value={permissions.model.default_id}
					placeholder="Select a model"
				>
					<option value="" disabled selected>{$i18n.t('Select a model')}</option>
					{#each permissions.model.filter ? $models.filter( (model) => filterModelIds.includes(model.id) ) : $models.filter((model) => model.id) as model}
						<option value={model.id} class="bg-gray-100 dark:bg-gray-700">{model.name}</option>
					{/each}
				</select>
			</div>
		</div>
	</div>

	<hr class=" border-gray-50 dark:border-gray-850 my-2" /> -->

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Workspace Permissions')}</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Models Access')}
			</div>
			<Switch bind:state={permissions.workspace.models} />
		</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Knowledge Access')}
			</div>
			<Switch bind:state={permissions.workspace.knowledge} />
		</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Prompts Access')}
			</div>
			<Switch bind:state={permissions.workspace.prompts} />
		</div>

		<div class=" ">
			<Tooltip
				className=" flex w-full justify-between my-2 pr-2"
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
		</div>
	</div>

	<hr class=" border-gray-50 dark:border-gray-850 my-2" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Chat Permissions')}</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Allow Chat Controls')}
			</div>

			<Switch bind:state={permissions.chat.controls} />
		</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Allow File Upload')}
			</div>

			<Switch bind:state={permissions.chat.file_upload} />
		</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Allow Chat Delete')}
			</div>

			<Switch bind:state={permissions.chat.delete} />
		</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Allow Chat Edit')}
			</div>

			<Switch bind:state={permissions.chat.edit} />
		</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Allow Temporary Chat')}
			</div>

			<Switch bind:state={permissions.chat.temporary} />
		</div>
	</div>

	<hr class=" border-gray-50 dark:border-gray-850 my-2" />

	<div>
		<div class=" mb-2 text-sm font-medium">{$i18n.t('Features Permissions')}</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Web Search')}
			</div>

			<Switch bind:state={permissions.features.web_search} />
		</div>

		<div class="  flex w-full justify-between my-2 pr-2">
			<div class=" self-center text-xs font-medium">
				{$i18n.t('Image Generation')}
			</div>

			<Switch bind:state={permissions.features.image_generation} />
		</div>
	</div>

	<hr class=" border-gray-50 dark:border-gray-850 my-2" />

	{#if !mcpConfigLoading && mcpEnabled}
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('MCP Permissions')}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
				{$i18n.t(
					'Control access to specific MCP (Model Context Protocol) servers. These are always disabled by default.'
				)}
			</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('MCP: Current Time')}
				</div>

				<Switch bind:state={permissions.mcp.time_server} />
			</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('MCP: News Headlines')}
				</div>

				<Switch bind:state={permissions.mcp.news_server} />
			</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('MCP: MPO SharePoint')}
				</div>

				<Switch bind:state={permissions.mcp.mpo_sharepoint_server} />
			</div>
		</div>
	{/if}
</div>
