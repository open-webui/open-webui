<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { selectAgent } from '$lib/IONOS/services/agent';
	import { agents } from '$lib/IONOS/stores/agents';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte'

	const i18n = getContext('i18n');

	let selectedAgentId = null;
</script>

<div class="flex flex-row gap-4 items-center h-96">
	{#each $agents as { id, name, subtitle, description, avatarUrl }}
		<div
			class="flex-0 w-60 pb-4 mx-3 bg-white text-left rounded-3xl shadow-xl cursor-pointer transition group {(id === selectedAgentId) ? 'selected scale-100' : 'scale-75 hover:scale-90 focus:scale-90'}"
			data-id={id}
			tabindex="0"
			role="button"
			on:keypress={({ key }) => { if (key === "Enter") { selectedAgentId = id; } }}
			on:click={() => selectedAgentId = id}
		>
			<div class="rounded-3xl">
				<img
					class="rounded-3xl rounded-b-none"
					src={avatarUrl}
					alt="Model Avatar"
				/>
			</div>
			<div class="px-4 cursor-default">
				<h1 class="text-base font-semibold mt-4">
					{name}
				</h1>
				<h2 class="text-sm">
					{subtitle}
				</h2>
				<p class="text-xs mt-4 hidden group-[.selected]:block" aria-hidden={id !== selectedAgentId}>
					{description}
				</p>
				<div class="text-center hidden group-[.selected]:block" aria-hidden={id !== selectedAgentId}>
					<button
						class="flex flex-row items-center m-auto px-4 py-2 mt-4 bg-blue-900 hover:bg-blue-800 text-gray-100 transition rounded-3xl s-GWo4gqQzfpKs"
						on:click={() => selectAgent(id)}
					>
						<span class="pr-2">
							{$i18n.t('Chat now', { ns: 'ionos' })}
						</span>
						<ChevronRight className="w-4 h-4" />
					</button>
				</div>
			</div>
		</div>
	{/each}
</div>
