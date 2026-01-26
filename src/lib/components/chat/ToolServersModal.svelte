<script lang="ts">
	import { getContext, onMount, createEventDispatcher } from 'svelte';
	import { models, config, toolServers, tools } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import { deleteSharedChatById, getChatById, shareChatById } from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import Collapsible from '../common/Collapsible.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';

	export let show = false;
	export let selectedToolIds: string[] = [];

	const dispatch = createEventDispatcher();

	let selectedTools: any[] = [];

	$: selectedTools = ($tools ?? []).filter((tool) => selectedToolIds.includes(tool.id));

	const i18n = getContext('i18n');

	function removeTool(toolId: string) {
		selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
		dispatch('change', selectedToolIds);
	}
</script>

<Modal bind:show size="sm">
	<div class="p-4">
		<!-- 标题栏 -->
		<div class="flex items-center justify-between mb-4">
			<div class="flex items-center gap-2">
				<div class="p-1.5 rounded-lg bg-sky-100 dark:bg-sky-500/20">
					<Wrench className="size-4 text-sky-500" strokeWidth="1.75" />
				</div>
				<span class="text-base font-medium text-gray-800 dark:text-gray-100">
					{$i18n.t('Available Tools')}
				</span>
				<span class="text-xs text-gray-400 bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded">
					{selectedTools.length}
				</span>
			</div>
			<button
				class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-5 text-gray-500" />
			</button>
		</div>

		<!-- 工具列表 -->
		{#if selectedTools.length > 0}
			<div class="space-y-2">
				{#each selectedTools as tool}
					<div class="group flex items-start gap-3 p-3 rounded-xl bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
						<div class="flex-1 min-w-0">
							<div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
								{tool?.name}
							</div>
							{#if tool?.meta?.description}
								<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
									{tool?.meta?.description}
								</div>
							{/if}
						</div>
						<button
							class="shrink-0 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-500/20 text-gray-400 hover:text-red-500 transition-all"
							on:click={() => removeTool(tool.id)}
							title={$i18n.t('Remove')}
						>
							<XMark className="size-4" />
						</button>
					</div>
				{/each}
			</div>
		{:else}
			<div class="text-center py-8 text-gray-400">
				<Wrench className="size-8 mx-auto mb-2 opacity-50" />
				<p class="text-sm">{$i18n.t('No tools selected')}</p>
			</div>
		{/if}

		<!-- Tool Servers -->
		{#if $toolServers.length > 0}
			<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wide">
					{$i18n.t('Tool Servers')}
				</div>
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
					{$i18n.t('Open WebUI can use tools provided by any OpenAPI server.')}
					<a
						class="text-sky-500 hover:underline"
						href="https://github.com/open-webui/openapi-servers"
						target="_blank"
					>
						{$i18n.t('Learn more')}
					</a>
				</div>
				<div class="space-y-2">
					{#each $toolServers as toolServer}
						<Collapsible buttonClassName="w-full" chevron>
							<div class="text-left">
								<div class="text-sm font-medium text-gray-800 dark:text-gray-100">
									{toolServer?.openapi?.info?.title}
									<span class="text-xs text-gray-400 font-normal">
										v{toolServer?.openapi?.info?.version}
									</span>
								</div>
								<div class="text-xs text-gray-500 truncate">
									{toolServer?.openapi?.info?.description}
								</div>
							</div>

							<div slot="content" class="mt-2 space-y-1.5">
								{#each toolServer?.specs ?? [] as tool_spec}
									<div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700/50">
										<div class="text-xs font-medium text-gray-700 dark:text-gray-200">
											{tool_spec?.name}
										</div>
										<div class="text-xs text-gray-500">
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
