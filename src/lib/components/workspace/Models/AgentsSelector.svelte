<script lang="ts">
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { getContext } from 'svelte';

	export let agents = [];
	export let selectedAgentIds = [];
	export let currentModelId: string | null = null;

	let _agents = {};

	const i18n = getContext('i18n');

	$: {
		const selfAgentId = currentModelId ? `agent:${currentModelId}` : null;

		const availableAgents = (agents ?? []).filter(
			(agent) =>
				agent.authenticated === undefined &&
				String(agent?.id ?? '').length > 0 &&
				(!selfAgentId || `agent:${agent.id}` !== selfAgentId)
		);

		_agents = availableAgents.reduce((acc, agent) => {
			const agentToolId = `agent:${agent.id}`;
			acc[agentToolId] = {
				...agent,
				selected: selectedAgentIds.includes(agentToolId)
			};

			return acc;
		}, {});
	}
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class="self-center text-xs font-medium text-gray-500">{$i18n.t('Agents')}</div>
	</div>

	<div class="flex flex-col mb-1">
		{#if Object.keys(_agents).length > 0}
			<div class="flex items-center flex-wrap">
				{#each Object.keys(_agents) as agent}
					<div class="flex items-center gap-2 mr-3">
						<div class="self-center flex items-center">
							<Checkbox
								state={_agents[agent].selected ? 'checked' : 'unchecked'}
								on:change={(e) => {
									_agents[agent].selected = e.detail === 'checked';
									selectedAgentIds = Object.keys(_agents).filter((t) => _agents[t].selected);
								}}
							/>
						</div>

						<Tooltip content={_agents[agent]?.meta?.description ?? _agents[agent].id}>
							<div class="py-0.5 text-sm w-full capitalize font-medium">
								{_agents[agent].name}
							</div>
						</Tooltip>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<div class="text-xs dark:text-gray-700">
		{$i18n.t('To select agents here, add them to the "Agents" workspace first.')}
	</div>
</div>
