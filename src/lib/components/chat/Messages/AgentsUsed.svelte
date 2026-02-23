<script lang="ts">
	import { getContext } from 'svelte';
	import { models } from '$lib/stores';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let agents: string[] = [];

	let showAgents = false;
	$: uniqueAgents = [...new Set((agents ?? []).filter(Boolean))];

	const getAgentImageUrl = (agentName: string) => {
		const model = ($models ?? []).find((m) => m?.name === agentName);
		if (model?.id) {
			return `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}&lang=${$i18n.language}`;
		}

		return `${WEBUI_BASE_URL}/static/favicon.png`;
	};
</script>

{#if uniqueAgents.length > 0}
	<div class="py-1 -mx-0.5 inline-flex gap-1 items-center">
		<button
			class="text-xs font-medium text-gray-600 dark:text-gray-300 px-3.5 h-8 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition flex items-center gap-1 border border-gray-50 dark:border-gray-850/30"
			on:click={() => {
				showAgents = !showAgents;
			}}
		>
			<div class="flex -space-x-1 items-center">
				{#each uniqueAgents.slice(0, 3) as agent}
					<img
						src={getAgentImageUrl(agent)}
						alt={agent}
						class="size-4 rounded-full shrink-0 border border-white dark:border-gray-850 bg-white dark:bg-gray-900 object-cover"
					/>
				{/each}
			</div>
			<div>
				{#if uniqueAgents.length === 1}
					{$i18n.t('1 Agent')}
				{:else}
					{$i18n.t('{{COUNT}} Agents', { COUNT: uniqueAgents.length })}
				{/if}
			</div>
		</button>
	</div>
{/if}

{#if showAgents}
	<div class="py-1.5">
		<div class="text-xs gap-2 flex flex-col">
			{#each uniqueAgents as agent, idx}
				<div class="outline-hidden flex dark:text-gray-300 bg-transparent text-gray-600 rounded-xl gap-1.5 items-center">
					<div class="font-medium bg-gray-50 dark:bg-gray-850 rounded-md px-1">{idx + 1}</div>
					<img
						src={getAgentImageUrl(agent)}
						alt={agent}
						class="size-4 rounded-full object-cover shrink-0"
					/>
					<div class="flex-1 truncate text-left">{agent}</div>
				</div>
			{/each}
		</div>
	</div>
{/if}
