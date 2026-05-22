<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		deleteModel,
		getOllamaCatalogue,
		getOllamaPullStatus,
		pullModel
	} from '$lib/apis/ollama';

	const i18n = getContext('i18n');

	let loading = false;
	let search = '';
	let view = 'all';
	let models: any[] = [];
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	let pulling: Record<string, { status: string; progress?: number }> = {};
	let liveDiscovery = true;
	let trustedOnly = false;
	let minDownloads = 0;
	let minLikes = 0;
	let qualityMode = 'off';
	let systemProfile: { ram_gb?: number | null; gpu_vram_gb?: number | null } | null = null;

	const loadCatalogue = async (forceRefresh = false) => {
		loading = true;
		try {
			const [catalogue, pullStatuses] = await Promise.all([
				getOllamaCatalogue(localStorage.token, 0, {
					live: liveDiscovery,
					refresh: forceRefresh,
					trusted_only: trustedOnly,
					min_downloads: minDownloads,
					min_likes: minLikes,
					quality: qualityMode,
					raw: true
				}),
				getOllamaPullStatus(localStorage.token, null, 0)
			]);

			const statusMap = Object.fromEntries((pullStatuses ?? []).map((s) => [s.model, s]));
			systemProfile = catalogue?.system_profile ?? null;
			models = (catalogue?.models ?? []).map((m) => {
				const pullStatus = m.pull_status ?? statusMap[m.alias] ?? statusMap[m.installed_as];
				return { ...m, pull_status: pullStatus };
			});
		} catch (e) {
			console.error(e);
			toast.error($i18n.t('Failed to load model catalogue'));
		} finally {
			loading = false;
		}
	};

	const modelMatches = (m: any) => {
		const q = search.trim().toLowerCase();
		if (!q) return true;
		const blob = [
			m.alias,
			m.display_name,
			m.repo,
			m.filename,
			...(m.tags ?? []),
			...(deriveCapabilities(m) ?? [])
		]
			.filter(Boolean)
			.join(' ')
			.toLowerCase();
		return blob.includes(q);
	};

	const deriveCapabilities = (m: any) => {
		if (Array.isArray(m.capabilities) && m.capabilities.length > 0) {
			return m.capabilities;
		}
		const tags = (m.tags ?? []).map((t) => `${t}`.toLowerCase());
		const out = [];
		if (tags.includes('code') || tags.includes('coder')) out.push('coding');
		if (tags.includes('reasoning') || tags.includes('deepseek')) out.push('reasoning');
		if (tags.includes('general')) out.push('chat');
		if ((m.context_length ?? 0) >= 16384) out.push('long-context');
		if (tags.includes('latest')) out.push('newer');
		return out;
	};

	const formatDate = (value: string | null | undefined) => {
		if (!value) return 'unknown';
		const dt = new Date(value);
		if (Number.isNaN(dt.getTime())) return value;
		return dt.toISOString().slice(0, 10);
	};

	const getProgress = (m: any) => {
		if (m.pull_status?.total && m.pull_status?.completed) {
			return Math.max(0, Math.min(100, Math.round((m.pull_status.completed / m.pull_status.total) * 100)));
		}
		const key = m.pull_name ?? m.alias;
		if (pulling[key]?.progress !== undefined) return pulling[key].progress;
		return null;
	};

	const startPull = async (pullName: string) => {
		if (pulling[pullName]) return;
		pulling = { ...pulling, [pullName]: { status: 'starting' } };

		try {
			const [res] = await pullModel(localStorage.token, pullName, 0);
			const reader = res?.body?.pipeThrough(new TextDecoderStream()).getReader();
			let buffer = '';

			if (reader) {
				while (true) {
					const { value, done } = await reader.read();
					if (done) break;
					buffer += value ?? '';
					const lines = buffer.split('\n');
					buffer = lines.pop() ?? '';

					for (const line of lines) {
						if (!line.trim()) continue;
						try {
							const evt = JSON.parse(line);
							if (evt.error || evt.detail) {
								throw new Error(evt.error ?? evt.detail);
							}
							const progress =
								evt.total && evt.completed
									? Math.max(0, Math.min(100, Math.round((evt.completed / evt.total) * 100)))
									: undefined;
							pulling = {
								...pulling,
								[pullName]: {
									status: evt.status ?? 'pulling',
									...(progress !== undefined ? { progress } : {})
								}
							};
						} catch {
							// Skip malformed lines from streamed output.
						}
					}
				}
			}

			toast.success($i18n.t('Download started for {{alias}}', { alias: pullName }));
		} catch (e: any) {
			toast.error($i18n.t('Download failed: {{error}}', { error: e?.message ?? e }));
		} finally {
			delete pulling[pullName];
			pulling = { ...pulling };
			await loadCatalogue();
		}
	};

	const removeModel = async (m: any) => {
		const modelId = m.installed_as;
		if (!modelId) return;

		if (!window.confirm($i18n.t('Delete {{name}} from disk?', { name: m.display_name ?? modelId }))) {
			return;
		}

		try {
			await deleteModel(localStorage.token, modelId);
			toast.success($i18n.t('Deleted {{name}}', { name: m.display_name ?? modelId }));
			await loadCatalogue();
		} catch (e: any) {
			toast.error($i18n.t('Delete failed: {{error}}', { error: e?.message ?? e }));
		}
	};

	$: filtered = models
		.filter((m) => (view === 'installed' ? m.installed : view === 'downloadable' ? m.downloadable : true))
		.filter((m) => modelMatches(m));

	onMount(async () => {
		await loadCatalogue();
		pollTimer = setInterval(() => {
			loadCatalogue(false);
		}, 10000);
	});

	onDestroy(() => {
		if (pollTimer) clearInterval(pollTimer);
	});
</script>

<div class="text-sm">
	<div class="mb-4 flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
		<div>
			<div class="text-lg font-medium">{$i18n.t('Model Explorer')}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">
				{$i18n.t('Browse compatible models, metadata, capabilities, and storage actions')}
			</div>
		</div>
		<button
			class="px-3 py-1.5 rounded-lg bg-gray-900 text-white dark:bg-white dark:text-gray-900 text-xs font-medium"
			on:click={() => loadCatalogue(true)}
		>
			{$i18n.t('Refresh Live Catalogue')}
		</button>
	</div>
	{#if systemProfile}
		<div class="mb-3 text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('System profile')}: RAM {systemProfile?.ram_gb ?? 'unknown'} GB, GPU VRAM {systemProfile?.gpu_vram_gb ?? 'unknown'} GB
		</div>
	{/if}

	<div class="mb-3 flex flex-col gap-2 lg:flex-row lg:flex-wrap">
		<input
			class="flex-1 px-3 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 outline-hidden"
			placeholder={$i18n.t('Search by alias, repo, tags, capabilities...')}
			bind:value={search}
		/>
		<select class="px-3 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 outline-hidden" bind:value={view}>
			<option value="all">{$i18n.t('All')}</option>
			<option value="installed">{$i18n.t('Installed')}</option>
			<option value="downloadable">{$i18n.t('Downloadable')}</option>
		</select>
		<label class="px-3 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 inline-flex items-center gap-2">
			<input type="checkbox" bind:checked={liveDiscovery} on:change={() => loadCatalogue(true)} />
			{$i18n.t('Include live discovery')}
		</label>
		<label class="px-3 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 inline-flex items-center gap-2">
			<input type="checkbox" bind:checked={trustedOnly} on:change={() => loadCatalogue(true)} />
			{$i18n.t('Trusted publishers only')}
		</label>
		<label class="px-3 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 inline-flex items-center gap-2">
			{$i18n.t('Min downloads')}
			<input
				type="number"
				min="0"
				class="w-24 bg-transparent outline-hidden"
				bind:value={minDownloads}
				on:change={() => loadCatalogue(true)}
			/>
		</label>
		<label class="px-3 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 inline-flex items-center gap-2">
			{$i18n.t('Min likes')}
			<input
				type="number"
				min="0"
				class="w-20 bg-transparent outline-hidden"
				bind:value={minLikes}
				on:change={() => loadCatalogue(true)}
			/>
		</label>
		<select
			class="px-3 py-2 rounded-xl bg-gray-100 dark:bg-gray-850 outline-hidden"
			bind:value={qualityMode}
			on:change={() => loadCatalogue(true)}
		>
			<option value="off">{$i18n.t('Quality filter off')}</option>
			<option value="strict">{$i18n.t('Strict quality')}</option>
		</select>
	</div>

	<div class="rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden">
		<div class="max-h-[65vh] overflow-auto">
			<table class="w-full text-left text-xs">
				<thead class="sticky top-0 bg-gray-50 dark:bg-gray-900/95">
					<tr class="border-b border-gray-200 dark:border-gray-800">
						<th class="px-3 py-2">{$i18n.t('Model')}</th>
						<th class="px-3 py-2">{$i18n.t('Capabilities')}</th>
						<th class="px-3 py-2">{$i18n.t('Metadata')}</th>
						<th class="px-3 py-2">{$i18n.t('Status')}</th>
						<th class="px-3 py-2">{$i18n.t('Actions')}</th>
					</tr>
				</thead>
				<tbody>
					{#if loading && filtered.length === 0}
						<tr><td class="px-3 py-3 text-gray-500" colspan="5">{$i18n.t('Loading...')}</td></tr>
					{:else if filtered.length === 0}
						<tr><td class="px-3 py-3 text-gray-500" colspan="5">{$i18n.t('No models found')}</td></tr>
					{:else}
						{#each filtered as m (m.alias)}
							<tr class="border-b border-gray-100 dark:border-gray-850 align-top">
								<td class="px-3 py-2 min-w-[220px]">
									<div class="font-medium">{m.display_name ?? m.alias}</div>
									<div class="text-gray-500 dark:text-gray-400">{m.alias}</div>
								</td>
								<td class="px-3 py-2 min-w-[180px]">
									<div class="flex flex-wrap gap-1">
										{#each deriveCapabilities(m) as cap}
											<span class="px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-800">{cap}</span>
										{/each}
										{#if deriveCapabilities(m).length === 0}
											<span class="text-gray-400">-</span>
										{/if}
									</div>
								</td>
								<td class="px-3 py-2 min-w-[320px]">
									<div><span class="text-gray-500">repo:</span> {m.repo}</div>
									<div><span class="text-gray-500">file:</span> {m.filename}</div>
									<div><span class="text-gray-500">context:</span> {m.context_length ?? 'unknown'}</div>
									<div><span class="text-gray-500">updated:</span> {formatDate(m?.metadata?.knowledge_last_update)}</div>
									<div><span class="text-gray-500">downloads:</span> {m?.metadata?.downloads ?? 'unknown'}</div>
									<div><span class="text-gray-500">likes:</span> {m?.metadata?.likes ?? 'unknown'}</div>
									{#if m?.metadata?.pipeline_tag}
										<div><span class="text-gray-500">pipeline:</span> {m.metadata.pipeline_tag}</div>
									{/if}
									<div class="mt-1 flex flex-wrap gap-1">
										{#each m.tags ?? [] as tag}
											<span class="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-850">{tag}</span>
										{/each}
									</div>
								</td>
								<td class="px-3 py-2 min-w-[150px]">
									<div>{m.installed ? $i18n.t('Installed') : $i18n.t('Not installed')}</div>
									{#if m.runtime_fit}
										<div class="mt-1 text-gray-500 dark:text-gray-400">
											{$i18n.t('Fit')}: {m.runtime_fit.recommendation}
										</div>
										<div class="text-gray-500 dark:text-gray-400">{m.runtime_fit.reason}</div>
										{#if m.runtime_fit.estimated_model_gb}
											<div class="text-gray-500 dark:text-gray-400">
												{$i18n.t('Estimated size')}: {m.runtime_fit.estimated_model_gb} GB
											</div>
										{/if}
									{/if}
									{#if m.pull_status?.status}
										<div class="text-gray-500 dark:text-gray-400 mt-1">{m.pull_status.status}</div>
									{/if}
									{#if getProgress(m) !== null}
										<div class="mt-1 text-gray-500 dark:text-gray-400">{getProgress(m)}%</div>
									{/if}
								</td>
								<td class="px-3 py-2 min-w-[160px]">
									<div class="flex gap-2">
										{#if m.downloadable}
											<button
												class="px-2 py-1 rounded-lg bg-gray-900 text-white dark:bg-white dark:text-gray-900"
												on:click={() => startPull(m.pull_name ?? m.alias)}
											>
												{$i18n.t('Download')}
											</button>
										{/if}
										{#if m.installed && m.deletable !== false}
											<button
												class="px-2 py-1 rounded-lg border border-red-400 text-red-600 dark:text-red-300"
												on:click={() => removeModel(m)}
											>
												{$i18n.t('Delete')}
											</button>
										{/if}
									</div>
								</td>
							</tr>
						{/each}
					{/if}
				</tbody>
			</table>
		</div>
	</div>
</div>
