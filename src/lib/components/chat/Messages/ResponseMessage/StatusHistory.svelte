<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import StatusItem from './StatusHistory/StatusItem.svelte';
	import { models } from '$lib/stores';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	export let statusHistory = [];
	export let agents = [];
	export let expand = false;

	let showHistory = true;

	$: if (expand) {
		showHistory = true;
	} else {
		showHistory = false;
	}

	let history = [];
	let status = null;
	let visibleHistory = [];
	let activeAgents = [];

	$: if (JSON.stringify(statusHistory) !== JSON.stringify(history)) {
		history = statusHistory;
	}

	$: {
		const spawnEvents = (history ?? []).filter((item) => item?.action === 'agent_spawn');
		const activeAgentMap = new Map();

		for (const event of spawnEvents) {
			const agentName = event?.agent;
			if (!agentName) {
				continue;
			}

			if (event?.done === false) {
				activeAgentMap.set(agentName, true);
			} else if (event?.done === true) {
				activeAgentMap.delete(agentName);
			}
		}

		activeAgents = [...activeAgentMap.keys()];
		visibleHistory = (history ?? []).filter((item) => item?.action !== 'agent_spawn');
		status = visibleHistory.length > 0 ? visibleHistory.at(-1) : null;
	}

	const getAgentImageUrl = (agentName) => {
		const model = ($models ?? []).find((m) => m?.name === agentName);
		if (model?.id) {
			return `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}&lang=${$i18n.language}`;
		}

		return `${WEBUI_BASE_URL}/static/favicon.png`;
	};
</script>

{#if (visibleHistory && visibleHistory.length > 0) || (activeAgents && activeAgents.length > 0)}
	{#if !status || status?.hidden !== true}
		<div class="text-sm flex flex-col w-full">
			<button
				class="w-full"
				on:click={() => {
					showHistory = !showHistory;
				}}
			>
				<div class="flex items-start gap-2">
					{#if status}
						<StatusItem {status} />
					{:else}
						<div class="status-description flex items-center gap-2 py-0.5 w-full text-left">
							<div class="text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap">
								{$i18n.t('Thinking')}
							</div>
						</div>
					{/if}
				</div>
			</button>

			{#if activeAgents && activeAgents.length > 0}
				<div class="mt-1">
					<div class="flex flex-wrap gap-2">
						{#each activeAgents as agent}
							<div class="inline-flex items-center gap-1.5 text-xs font-medium">
								<img
									src={getAgentImageUrl(agent)}
									alt={agent}
									class="size-4 rounded-full object-cover shrink-0"
								/>
								<span class="shimmer text-sky-700 dark:text-sky-300">{agent}</span>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if showHistory}
				<div class="flex flex-row">
					{#if visibleHistory.length > 1}
						<div class="w-full">
							{#each visibleHistory as status, idx}
								<div class="flex items-stretch gap-2 mb-1">
									<div class=" ">
										<div class="pt-3 px-1 mb-1.5">
											<span class="relative flex size-1.5 rounded-full justify-center items-center">
												<span
													class="relative inline-flex size-1.5 rounded-full bg-gray-500 dark:bg-gray-400"
												></span>
											</span>
										</div>
										{#if idx !== visibleHistory.length - 1}
											<div
												class="w-[0.5px] ml-[6.5px] h-[calc(100%-14px)] bg-gray-300 dark:bg-gray-700"
											/>
										{/if}
									</div>

									<StatusItem {status} done={true} />
								</div>
							{/each}
						</div>
					{/if}
				</div>
			{/if}
		</div>
	{/if}
{/if}
