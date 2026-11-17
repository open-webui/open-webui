<script lang="ts">
	import { getContext } from 'svelte';

	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ArrowRight from '$lib/components/icons/ArrowRight.svelte';

	const i18n: any = getContext('i18n');

	export let settings: Record<string, any> | null = null;
	export let savedConfig: Record<string, any> | null = null;
	export let labels: Record<string, string> = {};
	export let sensitiveKeys: string[] = [];
	export let disabled: boolean = false;
	export let loading: boolean = false;

	let saveButton: HTMLButtonElement;
	let showConfirm: boolean = false;

	// numbers typed into text fields and cleared fields compare equal to what was loaded
	const serialize = (value: any) =>
		value !== null && typeof value === 'object' ? JSON.stringify(value) : String(value ?? '');

	$: changedKeys = savedConfig
		? Object.keys({ ...savedConfig, ...settings }).filter(
				(key) => serialize(savedConfig[key]) !== serialize(settings?.[key])
			)
		: [];

	const formatValue = (value: any) => {
		if (value === null || value === undefined || value === '') {
			return $i18n.t('Empty');
		}
		if (typeof value === 'boolean') {
			return value ? $i18n.t('On') : $i18n.t('Off');
		}
		if (typeof value === 'object') {
			return JSON.stringify(value, null, 2);
		}
		return String(value);
	};
</script>

{#if changedKeys.length > 0}
	<button
		class="h-7 shrink-0 rounded-lg px-2 text-xs text-gray-500 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
		type="button"
		{disabled}
		on:click={() => {
			showConfirm = true;
		}}
	>
		{$i18n.t('{{count}} Changes', { count: changedKeys.length })}
	</button>
{/if}

<button
	bind:this={saveButton}
	class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:cursor-not-allowed disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
	type="submit"
	{disabled}
	on:click={(event) => {
		if (changedKeys.length > 0 && saveButton.form!.checkValidity()) {
			event.preventDefault();
			showConfirm = true;
		}
	}}
>
	{$i18n.t('Save')}

	{#if loading}
		<span class="shrink-0">
			<Spinner className="size-3" />
		</span>
	{/if}
</button>

{#snippet settingValue(key: string, value: any)}
	{#if sensitiveKeys.includes(key) && value}
		<SensitiveInput value={String(value)} readOnly />
	{:else}
		<div class="break-words whitespace-pre-wrap">{formatValue(value)}</div>
	{/if}
{/snippet}

<ConfirmDialog
	bind:show={showConfirm}
	title={$i18n.t('Unsaved changes')}
	confirmLabel={$i18n.t('Save')}
	onConfirm={() => {
		saveButton.form!.requestSubmit();
	}}
>
	<div class="flex max-h-[60vh] flex-col gap-3 overflow-y-auto">
		{#each changedKeys as key (key)}
			<div class="flex flex-col gap-1">
				<div class="flex items-baseline gap-1.5 text-xs text-gray-600 dark:text-gray-400">
					{labels[key] ?? key}
					{#if labels[key]}
						<span class="truncate font-mono text-[0.625rem] text-gray-400 dark:text-gray-600">
							{key}
						</span>
					{/if}
				</div>
				<div class="flex items-start gap-2 text-xs">
					<div
						class="min-w-0 flex-1 rounded-lg bg-gray-50 px-2 py-1 text-gray-500 dark:bg-gray-850 dark:text-gray-400"
					>
						{@render settingValue(key, savedConfig?.[key])}
					</div>
					<ArrowRight className="mt-1.5 size-3 shrink-0 text-gray-400" />
					<div class="min-w-0 flex-1 rounded-lg bg-gray-50 px-2 py-1 dark:bg-gray-850">
						{@render settingValue(key, settings?.[key])}
					</div>
				</div>
			</div>
		{/each}
	</div>
</ConfirmDialog>
