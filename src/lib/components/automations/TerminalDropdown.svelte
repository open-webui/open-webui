<script lang="ts">
	import { getContext } from 'svelte';

	import type { TerminalServer } from '$lib/apis/terminal/index';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';

	const i18n = getContext('i18n');

	export let terminalServers: TerminalServer[] = [];
	export let terminalServerId = '';
	export let terminalCwd = '';

	export let side: 'top' | 'bottom' = 'top';
	export let align: 'start' | 'end' = 'start';

	/** Optional callback when selection changes */
	export let onChange: () => void = () => {};

	let showDropdown = false;

	$: terminalLabel = terminalServerId
		? terminalServers.find((s) => s.id === terminalServerId)?.name || 'Terminal'
		: $i18n.t('Terminal');
</script>

{#if terminalServers.length > 0}
	<Dropdown bind:show={showDropdown} {side} {align}>
		<button
			type="button"
			class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-2xl text-xs transition
				{terminalServerId ? 'text-black dark:text-gray-100' : 'text-gray-600 dark:text-gray-400'}
				hover:bg-black/5 dark:hover:bg-white/5"
		>
			<Cloud className="size-3.5 shrink-0" strokeWidth="2" />
			<span class="whitespace-nowrap max-w-32 truncate">{terminalLabel}</span>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				fill="none"
				viewBox="0 0 24 24"
				stroke-width="2"
				stroke="currentColor"
				class="size-2.5"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
			</svg>
		</button>

		<div
			slot="content"
			class="rounded-2xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 min-w-56 max-w-56 p-1"
		>
			<div class="px-2 text-xs text-gray-500 py-1">
				{$i18n.t('Terminal')}
			</div>

			{#each terminalServers as server (server.id)}
				<button
					class="flex w-full justify-between gap-2 items-center px-3 py-1.5 text-sm cursor-pointer rounded-xl {terminalServerId ===
					server.id
						? 'bg-gray-50 dark:bg-gray-800/50'
						: 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}"
					type="button"
					on:click={() => {
						if (terminalServerId === server.id) {
							terminalServerId = '';
							terminalCwd = '';
						} else {
							terminalServerId = server.id;
						}
						showDropdown = false;
						onChange();
					}}
				>
					<div class="flex flex-1 gap-2 items-center truncate">
						<Cloud className="size-4 shrink-0" strokeWidth="2" />
						<span class="truncate">{server.name || server.id}</span>
					</div>
					{#if terminalServerId === server.id}
						<div class="shrink-0 text-emerald-600 dark:text-emerald-400">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-4"
							>
								<path
									fill-rule="evenodd"
									d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					{/if}
				</button>
			{/each}

			{#if terminalServerId}
				<div class="border-t border-gray-100 dark:border-gray-800 mt-1 pt-1">
					<div class="px-2.5 py-1 text-xs text-gray-500">
						{$i18n.t('Working Directory')}
					</div>
					<div class="px-2">
						<input
							type="text"
							bind:value={terminalCwd}
							placeholder="/home/user/project"
							class="w-full bg-transparent outline-hidden text-xs py-1.5 placeholder:text-gray-400 dark:placeholder:text-gray-600"
							on:click={(e) => e.stopPropagation()}
							on:input={onChange}
						/>
					</div>
				</div>
			{/if}
		</div>
	</Dropdown>
{/if}
