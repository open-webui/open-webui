<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Play from '$lib/components/icons/Play.svelte';
	import type i18nType from '$lib/i18n';

	const i18n: typeof i18nType = getContext('i18n');

	export let loading = false;
	export let dirty = false;
	export let saving = false;
	export let runNowHandler = () => {};
	export let copyLinkHandler = () => {};
	export let saveHandler = () => {};
	export let duplicateHandler = () => {};
	export let deleteHandler = () => {};

	// Same soft round buttons as the folder view's top bar.
	const iconButton =
		'relative flex size-6.5 shrink-0 items-center justify-center rounded-full border border-gray-100 bg-gray-50/60 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-900 aria-expanded:bg-gray-100 aria-expanded:text-gray-900 aria-disabled:opacity-60 dark:border-gray-850 dark:bg-gray-850/50 dark:text-gray-400 dark:hover:bg-gray-850 dark:hover:text-white dark:aria-expanded:bg-gray-850 dark:aria-expanded:text-white';
</script>

<div class="ml-auto flex shrink-0 items-center gap-1">
	{#if dirty}
		<button
			class="mr-0.5 flex h-6.5 items-center gap-1.5 rounded-full bg-gray-900 px-3 text-xs text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
			type="button"
			disabled={saving}
			on:click={saveHandler}
		>
			{$i18n.t('Save')}
			{#if saving}<Spinner className="size-3" />{/if}
		</button>
	{/if}

	<Tooltip content={$i18n.t('Run now')}>
		<button
			class={iconButton}
			on:click={runNowHandler}
			type="button"
			aria-disabled={loading}
			aria-label={$i18n.t('Run now')}
		>
			{#if loading}
				<Spinner className="size-3" />
			{:else}
				<Play className="size-3" strokeWidth="1.5" />
			{/if}
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Copy link')}>
		<button
			class={iconButton}
			on:click={copyLinkHandler}
			type="button"
			aria-label={$i18n.t('Copy link')}
		>
			<Link className="size-3.5" strokeWidth="1.5" />
		</button>
	</Tooltip>

	<Dropdown align="end" closeOnSelect>
		<button class={iconButton} type="button" aria-label={$i18n.t('More')}>
			<EllipsisHorizontal className="size-3.5" strokeWidth="2" />
		</button>
		<DropdownMenu slot="content" className="w-40">
			<button type="button" on:click={duplicateHandler}>
				<DocumentDuplicate className="size-3.5" />{$i18n.t('Duplicate')}
			</button>
			<button type="button" on:click={deleteHandler}>
				<GarbageBin className="size-3.5" />{$i18n.t('Delete')}
			</button>
		</DropdownMenu>
	</Dropdown>
</div>
