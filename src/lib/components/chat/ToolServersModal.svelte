<script lang="ts">
	import { getToolSpecs } from '$lib/apis/tools';
	import { resolveLocalizedResource } from '$lib/utils/localizedContent';
	import { getContext } from 'svelte';
	import { toolServers, tools } from '$lib/stores';

	import Modal from '../common/Modal.svelte';
	import Collapsible from '../common/Collapsible.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let selectedToolIds: string[] = [];
	export let onConnect: (id: string) => void = () => {};

	let discovery: Record<
		string,
		{ specs?: any[]; loading?: boolean; error?: 'auth' | 'unavailable' }
	> = {};

	const loadSpecs = async (tool: { id: string }) => {
		if (discovery[tool.id]?.loading) return;
		discovery = { ...discovery, [tool.id]: { loading: true } };
		try {
			const specs = await getToolSpecs(localStorage.token, tool.id);
			discovery = { ...discovery, [tool.id]: { specs } };
		} catch (error) {
			discovery = {
				...discovery,
				[tool.id]: {
					error:
						error && typeof error === 'object' && 'status' in error && error.status === 401
							? 'auth'
							: 'unavailable'
				}
			};
		}
	};

	const reconnect = (tool: { id: string }) => {
		show = false;
		onConnect(tool.id);
	};

	let selectedTools: any[] = [];

	$: selectedTools = (($tools ?? []) as any[]).filter((tool) => selectedToolIds.includes(tool.id));

	$: selectedToolServers = (($toolServers ?? []) as any[]).filter((server, idx) =>
		selectedToolIds.some((id) => {
			if (!id.startsWith('direct_server:')) return false;
			const serverId = id.slice('direct_server:'.length);
			return !isNaN(parseInt(serverId)) ? parseInt(serverId) === idx : serverId === server?.id;
		})
	);

	const i18n = getContext<any>('i18n');

	const authStatus = (tool: { id: string; authenticated?: boolean }) =>
		tool?.authenticated === false
			? {
					label: $i18n.t('Auth required'),
					dot: 'bg-amber-500'
				}
			: tool?.authenticated === true
				? {
						label: $i18n.t('Connected'),
						dot: 'bg-green-500'
					}
				: null;
</script>

<Modal bind:show size="md">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-4 pt-3 pb-1">
			<div class=" text-sm font-medium self-center">{$i18n.t('Available Tools')}</div>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		{#if selectedTools.length > 0}
			{#if selectedToolServers.length > 0}
				<div class=" flex justify-between dark:text-gray-300 px-5 pb-1">
					<div class=" text-base font-normal self-center">{$i18n.t('Tools')}</div>
				</div>
			{/if}

			<div class="px-3 pb-3 w-full flex flex-col justify-center">
				<div class=" text-sm dark:text-gray-300 mb-1">
					{#each selectedTools as tool (tool.id)}
						{@const isMcp = tool.id.startsWith('server:mcp:')}
						{@const state = discovery[tool.id]}
						{@const needsAuth = tool.authenticated === false || state?.error === 'auth'}
						{@const status = authStatus(needsAuth ? { ...tool, authenticated: false } : tool)}
						{@const toolSpecs = needsAuth ? undefined : isMcp ? state?.specs : tool.specs}
						<Collapsible
							buttonClassName="w-full mb-1 rounded-lg px-2 py-1.5"
							chevron
							onChange={(open: boolean) => {
								if (open && isMcp && !needsAuth && !state) loadSpecs(tool);
							}}
						>
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2 min-w-0">
									<div class="text-sm font-normal dark:text-gray-100 text-gray-800 truncate">
										{resolveLocalizedResource(tool, $i18n.language)}
									</div>
									{#if status}
										<Tooltip content={status.label} className="flex shrink-0 p-1 -m-1">
											<span
												class="size-1.5 rounded-full {status.dot}"
												role="img"
												aria-label={status.label}
											></span>
										</Tooltip>
									{/if}
									{#if needsAuth}
										<span class="text-[0.6875rem] text-amber-700 dark:text-amber-300 shrink-0"
											>{$i18n.t('Auth required')}</span
										>
									{:else if toolSpecs !== undefined}
										<span class="text-[0.6875rem] text-gray-500 dark:text-gray-400 shrink-0">
											{toolSpecs.length === 1
												? $i18n.t('1 tool')
												: $i18n.t('{{COUNT}} tools', { COUNT: toolSpecs.length })}
										</span>
									{/if}
								</div>
								{#if resolveLocalizedResource(tool, $i18n.language, 'description')}
									<div class="text-xs text-gray-500 truncate">
										{resolveLocalizedResource(tool, $i18n.language, 'description')}
									</div>
								{/if}
							</div>
							<div slot="content" class="px-2 pb-2 text-xs text-gray-500 dark:text-gray-400">
								{#if needsAuth}
									<button
										class="my-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition underline"
										on:click={() => reconnect(tool)}>{$i18n.t('Reconnect')}</button
									>
								{:else if state?.loading}
									<p class="my-1" role="status">{$i18n.t('Loading tools...')}</p>
								{:else if state?.error}
									<div class="flex items-center justify-between gap-2 my-1" role="status">
										<span>{$i18n.t('Unable to load tools')}</span>
										<button
											class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition underline"
											on:click={() => loadSpecs(tool)}>{$i18n.t('Retry')}</button
										>
									</div>
								{:else if toolSpecs?.length > 0}
									<div class="max-h-64 space-y-2 overflow-y-auto overscroll-contain py-1">
										{#each toolSpecs as toolSpec}
											<div class="min-w-0">
												<div
													class="text-xs font-normal leading-4 text-gray-700 dark:text-gray-300 break-words"
												>
													{toolSpec?.name ?? toolSpec?.function?.name}
												</div>
												{#if toolSpec?.description ?? toolSpec?.function?.description}
													<div class="text-[0.6875rem] leading-4 text-gray-500 break-words">
														{toolSpec?.description ?? toolSpec?.function?.description}
													</div>
												{/if}
											</div>
										{/each}
									</div>
								{:else}
									<p class="my-1">{$i18n.t('No tools found')}</p>
								{/if}
							</div>
						</Collapsible>
					{/each}
				</div>
			</div>
		{/if}

		{#if selectedToolServers.length > 0}
			<div class=" flex justify-between dark:text-gray-300 px-5 pb-0.5">
				<div class=" text-base font-normal self-center">{$i18n.t('Tool Servers')}</div>
			</div>

			<div class="px-5 pb-5 w-full flex flex-col justify-center">
				<div class=" text-xs text-gray-600 dark:text-gray-300 mb-2">
					<!-- LICENSE covers this Open WebUI wordmark.
					Do not alter, remove, obscure, or replace it except as LICENSE permits:
					https://docs.openwebui.com/license. -->
					{$i18n.t('Open WebUI can use tools provided by any OpenAPI server.')} <br /><a
						class="underline"
						href="https://github.com/open-webui/openapi-servers"
						target="_blank">{$i18n.t('Learn more about OpenAPI tool servers.')}</a
					>
				</div>
				<div class=" text-sm dark:text-gray-300 mb-1">
					{#each selectedToolServers as toolServer}
						<Collapsible buttonClassName="w-full" chevron>
							<div>
								<div class="text-sm font-normal dark:text-gray-100 text-gray-800">
									{toolServer?.openapi?.info?.title} - v{toolServer?.openapi?.info?.version}
								</div>

								<div class="text-xs text-gray-500">
									{toolServer?.openapi?.info?.description}
								</div>

								<div class="text-xs text-gray-500">
									{toolServer?.url}
								</div>
							</div>

							<div
								slot="content"
								class="max-h-64 space-y-2 overflow-y-auto overscroll-contain py-1"
							>
								{#each toolServer?.specs ?? [] as tool_spec}
									<div class="min-w-0">
										<div
											class="text-xs font-normal leading-4 text-gray-700 dark:text-gray-300 break-words"
										>
											{tool_spec?.name}
										</div>

										<div class="text-[0.6875rem] leading-4 text-gray-500 break-words">
											{tool_spec?.description}
										</div>
									</div>
								{/each}
							</div>
						</Collapsible>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</Modal>
