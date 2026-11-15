<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import {
		terminalRequest,
		type TerminalConnection,
		type TerminalSystemInfo
	} from '$lib/apis/terminal';
	import Icon from './FileNav/Icon.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	export let connection: TerminalConnection;
	export let chatId: string | null = null;
	export let label: string;
	export let onClose: () => void;
	const i18n = getContext<any>('i18n');
	let data: TerminalSystemInfo | null = null;
	let error = '';
	let loading = true;
	let sort: 'cpu_percent' | 'memory_bytes' = 'cpu_percent';
	let timer: ReturnType<typeof setTimeout>;
	let controller: AbortController | null = null;
	let destroyed = false;

	const refresh = async () => {
		clearTimeout(timer);
		controller?.abort();
		if (destroyed || document.hidden) return;
		const request = new AbortController();
		controller = request;
		loading = true;
		try {
			const next = await terminalRequest<TerminalSystemInfo>(connection, chatId, '/system/info', {
				signal: request.signal
			});
			if (request.signal.aborted || destroyed) return;
			data = next;
			error = '';
		} catch (reason) {
			if (!request.signal.aborted && !destroyed)
				error = reason instanceof Error ? reason.message : String(reason);
		} finally {
			if (!request.signal.aborted && !destroyed) {
				loading = false;
				if (!error) timer = setTimeout(refresh, 5000);
			}
		}
	};
	const bytes = (value: number | null | undefined) => {
		if (value == null) return '—';
		const unit = value >= 1024 ** 3 ? 'GiB' : 'MiB';
		return `${(value / (unit === 'GiB' ? 1024 ** 3 : 1024 ** 2)).toFixed(1)} ${unit}`;
	};
	const duration = (value: number | null) => {
		if (value == null) return '—';
		const minutes = Math.floor(value / 60);
		if (minutes >= 1440)
			return `${Math.floor(minutes / 1440)}d ${Math.floor((minutes % 1440) / 60)}h`;
		if (minutes >= 60) return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
		return `${minutes}m`;
	};
	const percentage = (used: number | undefined, total: number | undefined) =>
		used != null && total ? Math.min(100, Math.max(0, (used / total) * 100)) : null;
	$: metrics = data
		? [
				{
					label: $i18n.t('CPU'),
					value: data.cpu.percent == null ? '—' : `${data.cpu.percent.toFixed(1)}%`,
					percent: data.cpu.percent,
					scope: data.cpu.scope,
					title: ''
				},
				{
					label: $i18n.t('Memory'),
					value: data.memory ? `${bytes(data.memory.used)} / ${bytes(data.memory.total)}` : '—',
					percent: percentage(data.memory?.used, data.memory?.total),
					scope: data.memory?.scope,
					title: ''
				},
				{
					label: $i18n.t('Disk'),
					value: data.disk ? `${bytes(data.disk.used)} / ${bytes(data.disk.total)}` : '—',
					percent: percentage(data.disk?.used, data.disk?.total),
					scope: null,
					title: data.disk?.path
				}
			]
		: [];
	$: processes = [...(data?.processes ?? [])]
		.sort((a, b) => (b[sort] ?? -1) - (a[sort] ?? -1))
		.slice(0, 10);
	onMount(() => {
		void refresh();
	});
	onDestroy(() => {
		destroyed = true;
		clearTimeout(timer);
		controller?.abort();
	});
</script>

<svelte:document on:visibilitychange={refresh} />

<Modal
	size="sm"
	ariaLabel={$i18n.t('System info for {{name}}', { name: label })}
	onRequestClose={onClose}
>
	<section
		aria-label={$i18n.t('System info for {{name}}', { name: label })}
		class="text-xs text-gray-600 dark:text-gray-400"
	>
		<div class="flex items-start gap-3 px-4 pt-3 pb-1">
			<div class="min-w-0 flex-1">
				<h2 class="truncate text-sm font-medium text-gray-900 dark:text-white" title={label}>
					{label}
				</h2>
				{#if data}<div
						class="mt-0.5 truncate text-xs text-gray-500 dark:text-gray-400"
						title={data.hostname}
					>
						{data.hostname}
					</div>{/if}
			</div>
			<button
				type="button"
				aria-label={$i18n.t('Refresh')}
				disabled={loading}
				on:click={refresh}
				title={data
					? `${$i18n.t('Last updated')}: ${new Date(data.sampled_at * 1000).toLocaleTimeString()}`
					: $i18n.t('Refresh')}
				class="flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
			>
				<Icon name="refresh" size={12} />
			</button>
			<button
				type="button"
				aria-label={$i18n.t('Close')}
				on:click={onClose}
				class="shrink-0 rounded-lg py-1 text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			>
				<XMark className="size-4" />
			</button>
		</div>
		<div class="px-4 pt-1 pb-4">
			{#if error}<div role="alert" class="px-2 py-2 text-xs break-words">
					<div>{$i18n.t('System info unavailable')}</div>
					<div class="mt-0.5 text-[0.6875rem] text-gray-500">{error}</div>
				</div>{/if}
			{#if !data && loading}<div class="flex justify-center py-4">
					<Spinner className="size-4" />
				</div>{/if}
			{#if data}
				<div class="flex flex-col gap-4">
					{#each metrics as metric}
						<div title={metric.title}>
							<div class="flex items-center justify-between gap-3 mb-1.5 text-xs">
								<span class="text-gray-500 dark:text-gray-400"
									>{metric.label}{#if data.environment === 'container' && metric.scope === 'host'}
										{' · ' + $i18n.t('Host')}{/if}</span
								>
								<span class="tabular-nums text-gray-700 dark:text-gray-300">{metric.value}</span>
							</div>
							<div
								role="progressbar"
								aria-label={metric.label}
								aria-valuemin={0}
								aria-valuemax={100}
								aria-valuenow={metric.percent ?? undefined}
								aria-valuetext={metric.value}
								class="h-1 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden"
							>
								<div
									class="h-full rounded-full bg-gray-400 dark:bg-gray-500 transition-all"
									style:width={`${metric.percent ?? 0}%`}
								></div>
							</div>
						</div>
					{/each}
					<div
						class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400"
						title={`${data.os} · ${data.environment === 'container' ? $i18n.t('Container') : $i18n.t('Host')}`}
					>
						<!-- Retired labels: keep their translations.
						{$i18n.t('CPU cores')}
						{$i18n.t('{{count}} cores')}
						-->
						<span>{$i18n.t('{{count}} cores', { count: data.cpu.cores ?? '—' })}</span>
						<span>{data.arch}</span>
						<span title={`${$i18n.t('Service uptime')}: ${duration(data.service_uptime_seconds)}`}
							>{data.environment === 'container' ? $i18n.t('Host uptime') : $i18n.t('Uptime')}: {duration(
								data.uptime_seconds
							)}</span
						>
					</div>
					<!-- Retired label: keep its translation. {$i18n.t('Details')} -->
					<details class="group/network">
						<summary
							class="flex cursor-pointer list-none items-center gap-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 [&::-webkit-details-marker]:hidden"
						>
							<ChevronDown
								className="size-3 -rotate-90 transition-transform group-open/network:rotate-0"
							/>
							{$i18n.t('Network')}
						</summary>
						<dl
							aria-label={$i18n.t('Network')}
							class="mt-1.5 space-y-1 text-xs text-gray-500 dark:text-gray-400"
						>
							{#if data.network === null}<div>
									{$i18n.t('Network')}: {$i18n.t('Unavailable')}
								</div>{:else}
								{#each data.network as network}<div class="flex items-baseline gap-3 min-w-0">
										<dt
											title={network.up === null
												? '—'
												: network.up
													? $i18n.t('Up')
													: $i18n.t('Down')}
										>
											{network.name}
										</dt>
										<dd class="break-all text-gray-600 dark:text-gray-400">
											{network.addresses.join(' · ') || '—'}
										</dd>
									</div>{/each}
							{/if}
						</dl>
					</details>
					<div class="space-y-1.5">
						<h3 class="text-xs font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Processes')}
						</h3>
						{#if data.processes === null}<p class="text-[0.6875rem] text-gray-500">
								{$i18n.t('Processes')}: {$i18n.t('Unavailable')}
							</p>
						{:else if !processes.length}<p class="text-[0.6875rem] text-gray-500">
								{$i18n.t('No processes')}
							</p>
						{:else}
							<table
								class="w-full table-fixed text-xs tabular-nums text-gray-600 dark:text-gray-400"
							>
								<caption class="sr-only"
									>{data.process_scope === 'user'
										? $i18n.t('Your processes')
										: $i18n.t('Top processes')} · {$i18n.t('CPU: 100% = one core')}</caption
								>
								<thead class="text-gray-500 dark:text-gray-500"
									><tr>
										<th
											class="w-16 pr-2 text-right font-normal"
											aria-sort={sort === 'cpu_percent' ? 'descending' : 'none'}
										>
											<button
												type="button"
												title={$i18n.t('CPU: 100% = one core')}
												class="inline-flex items-center gap-0.5 pb-1"
												on:click={() => (sort = 'cpu_percent')}
											>
												{$i18n.t('CPU')}{#if sort === 'cpu_percent'}<ChevronDown
														className="size-2.5"
													/>{/if}
											</button>
										</th>
										<th
											class="w-20 pr-3 text-right font-normal"
											aria-sort={sort === 'memory_bytes' ? 'descending' : 'none'}
										>
											<button
												type="button"
												class="inline-flex items-center gap-0.5 pb-1"
												on:click={() => (sort = 'memory_bytes')}
											>
												{$i18n.t('Memory')}{#if sort === 'memory_bytes'}<ChevronDown
														className="size-2.5"
													/>{/if}
											</button>
										</th>
										<th class="pb-1 text-left font-normal">{$i18n.t('Name')}</th>
									</tr></thead
								>
								<tbody
									>{#each processes as process (process.pid)}<tr>
											<td class="pr-2 py-1 text-right text-gray-700 dark:text-gray-300"
												>{process.cpu_percent == null
													? '—'
													: `${process.cpu_percent.toFixed(1)}%`}</td
											>
											<td class="pr-3 py-1 text-right">{bytes(process.memory_bytes)}</td>
											<td class="truncate py-1" title={`${process.name} · PID ${process.pid}`}
												>{process.name}</td
											>
										</tr>{/each}</tbody
								>
							</table>
						{/if}
					</div>
				</div>
			{/if}
		</div>
	</section>
</Modal>
