<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { OPENAI_API_BASE_URL } from '$lib/constants';

	const i18n: any = getContext('i18n');

	// Ordered list. First entry is the primary provider; subsequent ones are
	// tried in order if earlier ones fail with a retryable error.
	export let providers: Array<{
		connection_url: string;
		model_name: string;
		capabilities: string[];
	}> = [];

	type HealthEntry = {
		effective_status?: 'healthy' | 'unhealthy' | 'unknown' | 'disabled';
		last_error?: string;
		last_error_status?: number;
		last_success_at?: number;
		seconds_until_retry?: number | null;
		latency_ms?: number;
	};

	let healthByUrl: Record<string, HealthEntry> = {};
	let availableUrls: string[] = [];
	let loading = true;

	async function loadHealth() {
		try {
			const res = await fetch(`${OPENAI_API_BASE_URL}/health`, {
				method: 'GET',
				headers: {
					Accept: 'application/json',
					authorization: `Bearer ${localStorage.token}`
				}
			});
			if (!res.ok) throw new Error(await res.text());
			healthByUrl = await res.json();
			availableUrls = Object.keys(healthByUrl);
		} catch (err) {
			console.warn('Failed to load provider health', err);
			healthByUrl = {};
			availableUrls = [];
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadHealth();
		// Re-poll every 30s so the dots reflect the current state of the world.
		const interval = setInterval(loadHealth, 30_000);
		return () => clearInterval(interval);
	});

	function addProvider() {
		providers = [
			...providers,
			{
				connection_url: availableUrls[0] ?? '',
				model_name: '',
				capabilities: []
			}
		];
	}

	function removeProvider(idx: number) {
		providers = providers.filter((_, i) => i !== idx);
	}

	function move(idx: number, direction: number) {
		const newIdx = idx + direction;
		if (newIdx < 0 || newIdx >= providers.length) return;
		const copy = [...providers];
		[copy[idx], copy[newIdx]] = [copy[newIdx], copy[idx]];
		providers = copy;
	}

	function toggleCapability(providerIdx: number, cap: string) {
		const p = providers[providerIdx];
		if (p.capabilities.includes(cap)) {
			p.capabilities = p.capabilities.filter((c) => c !== cap);
		} else {
			p.capabilities = [...p.capabilities, cap];
		}
		providers = providers;
	}

	function statusDotClass(url: string): string {
		const status = healthByUrl[url]?.effective_status ?? 'unknown';
		return (
			{
				healthy: 'bg-green-500',
				unhealthy: 'bg-red-500',
				disabled: 'bg-gray-400',
				unknown: 'bg-yellow-400'
			}[status] ?? 'bg-gray-400'
		);
	}

	function statusTitle(url: string): string {
		const entry = healthByUrl[url];
		if (!entry) return $i18n.t('Unknown status');
		const parts: string[] = [
			$i18n.t('Status: {{status}}', { status: entry.effective_status ?? 'unknown' })
		];
		if (entry.last_error) {
			parts.push($i18n.t('Last error: {{err}}', { err: entry.last_error }));
		}
		if (entry.seconds_until_retry != null && entry.seconds_until_retry > 0) {
			parts.push(
				$i18n.t('Cool-off: {{s}}s remaining', { s: entry.seconds_until_retry })
			);
		}
		if (entry.latency_ms != null) {
			parts.push($i18n.t('Latency: {{ms}}ms', { ms: entry.latency_ms }));
		}
		return parts.join('\n');
	}
</script>

<div class="space-y-2">
	{#if loading}
		<div class="text-xs text-gray-500">{$i18n.t('Loading providers…')}</div>
	{:else if availableUrls.length === 0}
		<div class="text-xs text-gray-500">
			{$i18n.t('No OpenAI-compatible connections configured. Add one in Admin → Settings → Connections first.')}
		</div>
	{/if}

	{#each providers as provider, idx}
		<div class="border border-gray-200 dark:border-gray-700 rounded-md p-2 space-y-1">
			<div class="flex items-center gap-2">
				<span class="text-xs font-medium w-20 shrink-0 text-gray-500">
					{idx === 0
						? $i18n.t('Primary')
						: $i18n.t('Backup #{{n}}', { n: idx })}
				</span>

				<span
					class="w-2 h-2 rounded-full shrink-0 {statusDotClass(provider.connection_url)}"
					title={statusTitle(provider.connection_url)}
				></span>

				<select
					bind:value={provider.connection_url}
					class="flex-1 min-w-0 text-sm bg-transparent outline-none"
					aria-label={$i18n.t('Connection URL')}
				>
					{#if !availableUrls.includes(provider.connection_url) && provider.connection_url}
						<!-- Preserve a URL that is no longer configured so the user
						     can see what's there before they change it. -->
						<option value={provider.connection_url}>{provider.connection_url} ({$i18n.t('missing')})</option>
					{/if}
					{#each availableUrls as url}
						<option value={url}>{url}</option>
					{/each}
				</select>

				<input
					type="text"
					bind:value={provider.model_name}
					placeholder={$i18n.t('Model name (e.g. gpt-4o)')}
					class="flex-1 min-w-0 text-sm bg-transparent outline-none border-b border-gray-300 dark:border-gray-700"
					aria-label={$i18n.t('Model name')}
				/>

				<button
					type="button"
					class="px-1 text-gray-500 hover:text-black dark:hover:text-white disabled:opacity-30"
					on:click={() => move(idx, -1)}
					disabled={idx === 0}
					aria-label={$i18n.t('Move up')}>↑</button
				>
				<button
					type="button"
					class="px-1 text-gray-500 hover:text-black dark:hover:text-white disabled:opacity-30"
					on:click={() => move(idx, 1)}
					disabled={idx === providers.length - 1}
					aria-label={$i18n.t('Move down')}>↓</button
				>
				<button
					type="button"
					class="px-1 text-gray-500 hover:text-red-500"
					on:click={() => removeProvider(idx)}
					aria-label={$i18n.t('Remove')}>×</button
				>
			</div>

			<div class="flex gap-3 text-xs ml-22 text-gray-500">
				<label class="flex items-center gap-1">
					<input
						type="checkbox"
						checked={provider.capabilities.includes('tools')}
						on:change={() => toggleCapability(idx, 'tools')}
					/>
					{$i18n.t('Tools')}
				</label>
				<label class="flex items-center gap-1">
					<input
						type="checkbox"
						checked={provider.capabilities.includes('vision')}
						on:change={() => toggleCapability(idx, 'vision')}
					/>
					{$i18n.t('Vision')}
				</label>
			</div>
		</div>
	{/each}

	<button
		type="button"
		on:click={addProvider}
		disabled={availableUrls.length === 0}
		class="w-full text-sm border border-dashed border-gray-300 dark:border-gray-700 rounded-md p-2 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-850 disabled:opacity-50"
	>
		+ {$i18n.t('Add provider')}
	</button>

	<p class="text-xs text-gray-500">
		{$i18n.t(
			'The first provider is primary. Backups are tried in order on 429/5xx/network errors. Tick a capability to assert the provider supports it — a request that needs tools or vision will skip providers missing them.'
		)}
	</p>
</div>
