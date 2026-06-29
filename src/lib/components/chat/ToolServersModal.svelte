<script lang="ts">
	import { getContext } from 'svelte';
	import { toolServers, tools } from '$lib/stores';

	import Modal from '../common/Modal.svelte';
	import Collapsible from '../common/Collapsible.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let selectedToolIds = [];

	let selectedTools = [];

	$: selectedTools = ($tools ?? []).filter((tool) => selectedToolIds.includes(tool.id));

	const i18n = getContext('i18n');

	const authStatus = (tool) =>
		tool?.authenticated === false
			? {
					label: $i18n.t('Auth required'),
					dot: 'bg-amber-500',
					pill: 'text-amber-700 dark:text-amber-300'
				}
			: tool?.authenticated === true
				? {
						label: $i18n.t('Connected'),
						dot: 'bg-green-500',
						pill: 'text-green-700 dark:text-green-300'
					}
				: {
						label: $i18n.t('No auth'),
						dot: 'bg-gray-400',
						pill: 'text-gray-500 dark:text-gray-400'
					};
</script>

<Modal bind:show size="md">
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class=" text-lg font-medium self-center">{$i18n.t('Available Tools')}</div>
			<button
				class="self-center"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		{#if selectedTools.length > 0}
			{#if $toolServers.length > 0}
				<div class=" flex justify-between dark:text-gray-300 px-5 pb-1">
					<div class=" text-base font-medium self-center">{$i18n.t('Tools')}</div>
				</div>
			{/if}

			<div class="px-5 pb-3 w-full flex flex-col justify-center">
				<div class=" text-sm dark:text-gray-300 mb-1">
					{#each selectedTools as tool}
						{@const status = authStatus(tool)}
						{@const toolSpecs = tool?.specs ?? []}
						<Collapsible
							buttonClassName="w-full mb-1 rounded-lg px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-800/50"
							chevron={toolSpecs.length > 0}
							disabled={toolSpecs.length === 0}
						>
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2 min-w-0">
									<span class="size-2 rounded-full {status.dot}"></span>
									<div class="text-sm font-medium dark:text-gray-100 text-gray-800 truncate">
										{tool?.name}
									</div>
								</div>

								{#if tool?.meta?.description}
									<div class="text-xs text-gray-500 truncate">
										{tool?.meta?.description}
									</div>
								{/if}
							</div>

							<div class="ml-3 flex shrink-0 items-center gap-2 text-[11px]">
								<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Enabled')}</span>
								<span class={status.pill}>{status.label}</span>
								{#if toolSpecs.length > 0}
									<span class="text-gray-500 dark:text-gray-400">
										{$i18n.t('{{COUNT}} tools', { COUNT: toolSpecs.length })}
									</span>
								{/if}
							</div>

							<div slot="content" class="pl-4 pr-2 pb-2 text-xs text-gray-500 dark:text-gray-400">
								{#if toolSpecs.length > 0}
									{#each toolSpecs as toolSpec}
										<div class="mt-1 truncate">
											{toolSpec?.name ?? toolSpec?.function?.name}
										</div>
									{/each}
								{/if}
							</div>
						</Collapsible>
					{/each}
				</div>
			</div>
		{/if}

		{#if $toolServers.length > 0}
			<div class=" flex justify-between dark:text-gray-300 px-5 pb-0.5">
				<div class=" text-base font-medium self-center">{$i18n.t('Tool Servers')}</div>
			</div>

			<div class="px-5 pb-5 w-full flex flex-col justify-center">
				<div class=" text-xs text-gray-600 dark:text-gray-300 mb-2">
					{$i18n.t('Open WebUI can use tools provided by any OpenAPI server.')} <br /><a
						class="underline"
						href="https://github.com/open-webui/openapi-servers"
						target="_blank">{$i18n.t('Learn more about OpenAPI tool servers.')}</a
					>
				</div>
				<div class=" text-sm dark:text-gray-300 mb-1">
					{#each $toolServers as toolServer}
						<Collapsible buttonClassName="w-full" chevron>
							<div>
								<div class="text-sm font-medium dark:text-gray-100 text-gray-800">
									{toolServer?.openapi?.info?.title} - v{toolServer?.openapi?.info?.version}
								</div>

								<div class="text-xs text-gray-500">
									{toolServer?.openapi?.info?.description}
								</div>

								<div class="text-xs text-gray-500">
									{toolServer?.url}
								</div>
							</div>

							<div slot="content">
								{#each toolServer?.specs ?? [] as tool_spec}
									<div class="my-1">
										<div class="font-medium text-gray-800 dark:text-gray-100">
											{tool_spec?.name}
										</div>

										<div>
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
