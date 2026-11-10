<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import Activity from '$lib/components/icons/Activity.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';

	const i18n = getContext<any>('i18n');

	export let label = '';
	export let onRestart: (() => void) | null = null;
	export let onInfo: (() => void) | null = null;
	export let onSettings: (() => void) | null = null;

	let show = false;

	const item =
		'select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 transition';
	const run = (event: MouseEvent, action: () => void) => {
		event.stopPropagation();
		event.preventDefault();
		show = false;
		action();
	};
</script>

{#if onRestart || onInfo || onSettings}
	<Dropdown bind:show align="start" sideOffset={-2}>
		<Tooltip content={$i18n.t('More')}>
			<button
				type="button"
				aria-label={$i18n.t('More options for {{name}}', { name: label })}
				class="flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus-visible:outline focus-visible:outline-2"
				on:click={(e) => {
					e.preventDefault();
					e.stopPropagation();
					show = !show;
				}}><EllipsisHorizontal className="size-3.5" /></button
			>
		</Tooltip>

		<div slot="content">
			<DropdownMenu className="min-w-44">
				{#if onRestart}
					<button type="button" class={item} on:click={(e) => run(e, onRestart)}
						><ArrowPath className="size-3.5" />{$i18n.t('Restart')}</button
					>
				{/if}
				{#if onInfo}
					<button type="button" class={item} on:click={(e) => run(e, onInfo)}
						><Activity className="size-3.5" />{$i18n.t('System info')}</button
					>
				{/if}
				{#if onSettings}
					{#if onRestart || onInfo}
						<hr class="border-gray-50 dark:border-gray-800/30 mx-1 my-0.5" />
					{/if}
					<button type="button" class={item} on:click={(e) => run(e, onSettings)}
						><Cog6 className="size-3.5" />{$i18n.t('Terminal settings')}</button
					>
				{/if}
			</DropdownMenu>
		</div>
	</Dropdown>
{/if}
