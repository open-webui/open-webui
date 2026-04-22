<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import type { MCPPrompt } from '$lib/apis/tools';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let show = false;
	export let loading = false;
	export let serverName = '';
	export let prompts: MCPPrompt[] = [];

	export let onSelect: (prompt: MCPPrompt) => Promise<void> | void = async () => {};
	export let onClose = () => {};
</script>

<Modal bind:show size="md">
	<div>
		<div class="flex items-center justify-between px-5 pt-4 pb-2 dark:text-gray-300">
			<div>
				<div class="text-lg font-medium">{$i18n.t('MCP Prompts')}</div>
				<div class="text-xs text-gray-500 dark:text-gray-400">{serverName}</div>
			</div>

			<button
				class="self-center"
				type="button"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
					onClose();
				}}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="px-5 pb-5 dark:text-gray-200">
			{#if loading}
				<div class="py-8">
					<Spinner />
				</div>
			{:else if prompts.length === 0}
				<div
					class="rounded-2xl border border-dashed border-gray-200 px-4 py-8 text-center text-sm text-gray-500 dark:border-gray-800 dark:text-gray-400"
				>
					{$i18n.t('No MCP prompts are available for this server.')}
				</div>
			{:else}
				<div class="flex max-h-96 flex-col gap-2 overflow-y-auto pr-1">
					{#each prompts as prompt (prompt.name)}
						<button
							type="button"
							class="w-full rounded-2xl border border-gray-100 px-4 py-3 transition hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900/50"
							on:click={() => onSelect(prompt)}
						>
							<div class="flex items-start gap-3">
								<div class="mt-0.5 shrink-0 text-sky-500 dark:text-sky-300">
									<Sparkles className="size-4" strokeWidth="1.75" />
								</div>

								<div class="min-w-0 flex-1 text-left">
									<div class="truncate text-sm font-medium text-gray-900 dark:text-gray-100">
										{prompt.title ?? prompt.name}
									</div>

									<div class="truncate text-xs text-gray-500 dark:text-gray-400">
										{prompt.name}
									</div>

									{#if prompt.description}
										<div class="mt-1 line-clamp-3 text-xs text-gray-600 dark:text-gray-300">
											{prompt.description}
										</div>
									{/if}

									{#if (prompt.arguments ?? []).length > 0}
										<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
											{$i18n.t('{{COUNT}} argument(s)', {
												COUNT: (prompt.arguments ?? []).length
											})}
										</div>
									{/if}
								</div>
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</Modal>
