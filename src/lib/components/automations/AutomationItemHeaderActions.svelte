<script lang="ts">
	import { getContext } from 'svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Play from '$lib/components/icons/Play.svelte';
	import type i18nType from '$lib/i18n';

	const i18n: typeof i18nType = getContext('i18n');

	export let isActive = true;
	export let loading = false;
	export let toggleHandler = () => {};
	export let runNowHandler = () => {};
	export let editHandler = () => {};
	export let deleteHandler = () => {};
</script>

<div class="ml-auto flex shrink-0 items-center">
	<Tooltip content={isActive ? $i18n.t('Active') : $i18n.t('Paused')}>
		<div class="flex h-7 items-center px-1 mr-1">
			<Switch
				state={isActive}
				on:change={toggleHandler}
				ariaLabel={isActive ? $i18n.t('Active') : $i18n.t('Paused')}
			/>
		</div>
	</Tooltip>

	<Tooltip content={$i18n.t('Run now')}>
		<button
			class="flex size-7 items-center justify-center text-gray-400 transition disabled:opacity-60"
			on:click={runNowHandler}
			type="button"
			disabled={loading}
			aria-label={$i18n.t('Run now')}
		>
			{#if loading}
				<Spinner className="size-3" />
			{:else}
				<Play className="size-3.5" strokeWidth="1.5" />
			{/if}
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Edit')}>
		<button
			class="flex size-7 items-center justify-center text-gray-400 transition"
			on:click={editHandler}
			type="button"
			aria-label={$i18n.t('Edit')}
		>
			<Pencil className="size-3.5" strokeWidth="1.7" />
		</button>
	</Tooltip>

	<Tooltip content={$i18n.t('Delete')}>
		<button
			class="flex size-7 items-center justify-center text-gray-400 transition"
			on:click={deleteHandler}
			type="button"
			aria-label={$i18n.t('Delete')}
		>
			<GarbageBin className="size-3.5" />
		</button>
	</Tooltip>
</div>
