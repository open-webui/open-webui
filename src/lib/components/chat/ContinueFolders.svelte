<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { activeFolders, folders, machines, refreshActiveFolders } from '$lib/stores';
	import { formatDateDetails, formatElapsedShort, formatShortDate } from '$lib/utils';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: any = getContext('i18n');

	// As in Recent: "45s", "12m", "3h", "5d" for the last week, then a short date.
	const formatTime = (seconds: number) =>
		Date.now() / 1000 - seconds < 7 * 86400
			? formatElapsedShort(seconds)
			: formatShortDate(seconds, $i18n.language);

	// The machine's own home isn't known here, so shorten the usual ones.
	const shortenHome = (path: string) =>
		path.replace(/^(\/(home|Users)\/[^/]+|\/root)(?=\/|$)/, '~');

	onMount(() => {
		refreshActiveFolders(localStorage.token);
	});
</script>

{#if $activeFolders.length}
	<div class="w-full px-1 mb-3 text-left">
		<h3 id="continue-folders-heading" class="mb-1 -mx-1 text-xs text-base-400 dark:text-base-500">
			{$i18n.t('Continue')}
		</h3>

		<ul aria-labelledby="continue-folders-heading">
			{#each $activeFolders as folder (folder.id)}
				{@const machine = ($machines ?? []).find(({ id }) => id === folder.machine_id)}
				{@const unread = ($folders as any[]).find(({ id }) => id === folder.id)?.unread_count ?? 0}
				<li>
					<a
						href="/folders/{folder.id}"
						class="group flex items-center gap-2 h-7 -mx-2 px-2 rounded-lg text-sm transition-colors duration-75 hover:bg-base-50 dark:hover:bg-base-850"
						title={[
							folder.name,
							machine?.name,
							folder.directory,
							formatDateDetails(folder.updated_at, $i18n.language)
						]
							.filter(Boolean)
							.join('\n')}
					>
						{#if folder.waiting}
							<span
								class="size-1.5 shrink-0 rounded-full bg-yellow-500"
								role="status"
								aria-label={$i18n.t('Waiting for approval')}
							></span>
						{:else if folder.running}
							<span class="shrink-0"><Spinner className="size-3" /></span>
						{/if}
						<span class="flex flex-1 min-w-0 items-center gap-2">
							<span
								dir="auto"
								class="min-w-0 truncate text-base-500 dark:text-base-400 transition-colors duration-75 group-hover:text-base-900 dark:group-hover:text-base-100"
							>
								{folder.name}
							</span>
							{#if unread > 0}
								<span
									class="inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded-md bg-sky-500/10 px-1 text-[0.625rem] font-semibold leading-4 text-sky-600 dark:bg-sky-400/10 dark:text-sky-300"
									title={$i18n.t('Unread or waiting for approval')}
								>
									{unread.toLocaleString($i18n.language)}
								</span>
							{/if}
							<span
								class="flex-1 min-w-0 translate-y-[0.03125rem] truncate font-mono text-[0.6875rem] text-base-400 dark:text-base-600"
							>
								{[machine?.name, shortenHome(folder.directory ?? '')].filter(Boolean).join(' ')}
							</span>
						</span>
						{#if folder.terminals}
							<span
								class="flex shrink-0 items-center gap-0.5 text-xs tabular-nums text-base-400 dark:text-base-600"
								role="img"
								aria-label="{$i18n.t('Terminal')}: {folder.terminals}"
							>
								<svg
									class="size-3"
									viewBox="0 0 16 16"
									fill="none"
									stroke="currentColor"
									stroke-width="1.25"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"><path d="m3 4.5 3.5 3.5L3 11.5M8.5 12H13" /></svg
								>
								{folder.terminals}
							</span>
						{/if}
						{#if !folder.terminals && !folder.ports.length && folder.tabs.length}
							<span
								dir="auto"
								class="max-w-[40%] shrink-0 truncate text-xs text-base-400 dark:text-base-600"
							>
								{folder.tabs.join(' · ')}
							</span>
						{/if}
						{#if folder.ports.length}
							<span class="shrink-0 text-xs tabular-nums text-base-400 dark:text-base-600">
								{folder.ports.map((port) => `:${port}`).join(' ')}
							</span>
						{/if}
						<span class="shrink-0 text-xs tabular-nums text-base-400 dark:text-base-600">
							{formatTime(folder.updated_at)}
						</span>
					</a>
				</li>
			{/each}
		</ul>
	</div>
{/if}
