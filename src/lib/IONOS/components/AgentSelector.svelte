<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { selectAgent } from '$lib/IONOS/services/agent';
	import { agents } from '$lib/IONOS/stores/agents';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte'

	const i18n = getContext('i18n');
</script>

<div class="flex flex-row gap-4 items-center justify-center flex-wrap">
	{#each $agents as { id, name, subtitle, description, avatarUrl }}
		<div class="min-h-96 flex items-center">
			<div
				class="flex-0 group w-52 pb-4 mx-6 bg-white text-left rounded-3xl shadow-xl cursor-pointer transition group"
				data-id={id}
				tabindex="0"
				role="button"
			>
				<div class="overflow-hidden transition-[width,height] duration-[500ms] h-36 rounded-t-3xl">
					<img
						class="rounded-3xl rounded-b-none"
						src={avatarUrl}
						alt="Model Avatar"
					/>
				</div>
				<div class="px-4 cursor-default overflow-hidden">
					<h1 class="text-sm font-semibold mt-2">
						{name}
					</h1>
					<h2 class="text-sm">
						{subtitle}
					</h2>
					<div class="mt-0 overflow-hidden duration-[500ms] transition-[height,margin-top] h-0 group-hover:h-40 group-hover:mt-4 group-focus:h-40 group-focus:mt-4 focus-within:h-40 focus-within:mt-4 max-xs:h-40 max-xs:mt-4 max-xs:h-40 max-xs:mt-4">
						<p class="text-xs">
							{description}
						</p>
						<div class="text-center">
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
			</div>
		</div>
	{/each}
</div>
