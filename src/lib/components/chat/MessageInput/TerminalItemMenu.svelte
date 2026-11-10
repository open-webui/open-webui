<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import Activity from '$lib/components/icons/Activity.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Stop from '$lib/components/icons/Stop.svelte';
	import Play from '$lib/components/icons/Play.svelte';

	const i18n = getContext<any>('i18n');

	export let label = '';
	/** Reads this chat's machine status when the menu opens; enables Restart, Stop, and Start. */
	export let loadStatus: (() => Promise<string | null>) | null = null;
	export let onRestart: (() => void) | null = null;
	export let onStop: (() => void) | null = null;
	export let onStart: (() => void) | null = null;
	export let onInfo: (() => void) | null = null;
	export let onFiles: (() => void) | null = null;
	export let onSettings: (() => void) | null = null;

	let show = false;
	let status: string | null = null;
	let checking = false;

	$: if (show && loadStatus) check();
	$: running = !loadStatus || status === 'running';

	async function check() {
		checking = true;
		status = await loadStatus!().catch(() => null);
		checking = false;
	}

	const item =
		'select-none flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 transition';
	const run = (event: MouseEvent, action: () => void) => {
		event.stopPropagation();
		event.preventDefault();
		show = false;
		action();
	};
</script>

{#if loadStatus || onInfo || onFiles || onSettings}
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
				{#if loadStatus && checking}
					<div class="flex h-[1.6875rem] items-center px-2"><Spinner className="size-3.5" /></div>
				{:else if loadStatus}
					{#if status === 'running'}
						{#if onRestart}
							<button type="button" class={item} on:click={(e) => run(e, onRestart)}
								><ArrowPath className="size-3.5" />{$i18n.t('Restart')}</button
							>
						{/if}
						{#if onStop}
							<button type="button" class={item} on:click={(e) => run(e, onStop)}
								><Stop className="size-3.5" />{$i18n.t('Stop')}</button
							>
						{/if}
					{:else if onStart}
						<button type="button" class={item} on:click={(e) => run(e, onStart)}
							><Play className="size-3.5" />{$i18n.t('Start')}</button
						>
					{/if}
				{/if}
				{#if !checking && running}
					{#if onInfo}
						<button type="button" class={item} on:click={(e) => run(e, onInfo)}
							><Activity className="size-3.5" />{$i18n.t('System info')}</button
						>
					{/if}
					{#if onFiles}
						<button type="button" class={item} on:click={(e) => run(e, onFiles)}
							><Folder className="size-3.5" />{$i18n.t('View files')}</button
						>
					{/if}
				{/if}
				{#if onSettings}
					<hr class="border-gray-50 dark:border-gray-800/30 mx-1 my-0.5" />
					<button type="button" class={item} on:click={(e) => run(e, onSettings)}
						><Cog6 className="size-3.5" />{$i18n.t('Terminal settings')}</button
					>
				{/if}
			</DropdownMenu>
		</div>
	</Dropdown>
{/if}
