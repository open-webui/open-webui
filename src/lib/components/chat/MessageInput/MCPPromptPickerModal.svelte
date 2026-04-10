<script lang="ts">
	import { getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import Pin from '$lib/components/icons/Pin.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let loading = false;
	export let serverName = '';
	export let prompts = [];

	export let onSelect = async () => {};
	export let onPin = async () => {};
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
				<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t(
						'Click a prompt to use it on the next turn, or pin it to re-apply it on every turn in this chat.'
					)}
				</div>

				<div class="flex max-h-96 flex-col gap-2 overflow-y-auto pr-1">
					{#each prompts as prompt (prompt.name)}
						<div
							class="w-full rounded-2xl border border-gray-100 px-4 py-3 transition hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-900/50"
						>
							<div class="flex items-start gap-3">
								<div class="mt-0.5 shrink-0 text-sky-500 dark:text-sky-300">
									<Sparkles className="size-4" strokeWidth="1.75" />
								</div>

								<button
									type="button"
									class="min-w-0 flex-1 text-left"
									on:click={() => onSelect(prompt)}
								>
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
								</button>

								<div class="shrink-0">
									<Tooltip content={$i18n.t('Pin to this chat')}>
										<button
											type="button"
											class="rounded-full p-2 text-amber-600 transition hover:bg-amber-50 hover:text-amber-700 dark:text-amber-300 dark:hover:bg-amber-400/10 dark:hover:text-amber-200"
											aria-label={$i18n.t('Pin prompt to this chat')}
											on:click={() => onPin(prompt)}
										>
											<Pin className="size-4" strokeWidth="1.75" />
										</button>
									</Tooltip>
								</div>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</Modal>
