<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { copyToClipboard } from '$lib/utils';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import LinkIcon from '$lib/components/icons/Link.svelte';

	const i18n = getContext('i18n');

	export let enabled = false;
	export let allowGet = false;
	/** The saved automation's URL; empty until it is saved with a webhook. */
	export let url = '';
	export let onRegenerate: (() => void) | null = null;

	export let side: 'top' | 'bottom' = 'top';
	export let align: 'start' | 'end' = 'start';
	/** Render the trigger as a bare value, for label | value rows. */
	export let plain = false;

	export let onChange: () => void = () => {};

	let showDropdown = false;

	const copyUrl = async () => {
		if (await copyToClipboard(url)) toast.success($i18n.t('Copied'));
	};
</script>

<Dropdown bind:show={showDropdown} {side} {align}>
	<button
		type="button"
		aria-label={$i18n.t('Webhook')}
		class={plain
			? 'flex w-full min-w-0 items-center text-left text-xs font-normal leading-6 text-base-700 dark:text-base-300'
			: `flex items-center gap-1.5 px-2.5 py-1.5 rounded-2xl text-xs transition ${enabled ? 'text-base-1000 dark:text-base-100' : 'text-base-600 dark:text-base-400'} hover:text-base-900 dark:hover:text-base-100`}
	>
		{#if plain}
			<span
				class="truncate {enabled ? '' : 'text-base-400 dark:text-base-500'} {enabled && url
					? 'font-mono'
					: ''}">{enabled ? url || $i18n.t('On') : $i18n.t('Off')}</span
			>
		{:else}
			<LinkIcon className="size-3.5 shrink-0" strokeWidth="2" />
			{#if enabled}
				<span class="whitespace-nowrap">{$i18n.t('Webhook')}</span>
			{/if}
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
		{/if}
	</button>

	<div
		slot="content"
		class="rounded-xl shadow-lg border border-base-200 dark:border-base-800 flex flex-col bg-base-0 dark:bg-base-850 w-64 p-0.5"
	>
		<div class="flex items-center justify-between gap-2 px-2 py-1 text-xs">
			<span>{$i18n.t('Webhook')}</span>
			<Switch bind:state={enabled} ariaLabel={$i18n.t('Webhook')} on:change={onChange} />
		</div>

		{#if enabled}
			<div class="flex items-center justify-between gap-2 px-2 py-1 text-xs">
				<span>{$i18n.t('Allow GET')}</span>
				<Switch bind:state={allowGet} ariaLabel={$i18n.t('Allow GET')} on:change={onChange} />
			</div>

			<div class="px-2 pt-0.5 pb-1.5">
				{#if url}
					<button
						type="button"
						class="w-full truncate text-left font-mono text-[0.6875rem] text-base-700 dark:text-base-300"
						title={$i18n.t('Copy')}
						on:click={copyUrl}>{url}</button
					>
					<div class="mt-1 flex gap-3 text-[0.6875rem] text-base-500">
						<button
							type="button"
							class="hover:text-base-800 dark:hover:text-base-200"
							on:click={copyUrl}>{$i18n.t('Copy')}</button
						>
						{#if onRegenerate}
							<button
								type="button"
								class="hover:text-base-800 dark:hover:text-base-200"
								on:click={() => onRegenerate?.()}>{$i18n.t('Regenerate')}</button
							>
						{/if}
					</div>
				{:else}
					<div class="text-[0.6875rem] text-base-500">
						{$i18n.t('The URL appears once saved.')}
					</div>
				{/if}
			</div>
		{/if}
	</div>
</Dropdown>
