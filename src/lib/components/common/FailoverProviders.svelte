<script lang="ts">
	import { getContext } from 'svelte';
	import { models } from '$lib/stores';

	const i18n: any = getContext('i18n');

	// Ordered list. First entry is the primary provider; subsequent ones are
	// tried in order when earlier ones fail with a retryable error.
	export let providers: Array<{
		model_id: string;
		capabilities: string[];
	}> = [];

	// Exclude the model currently being edited so it can't self-reference,
	// and drop presets / arena / direct entries so the list matches the
	// legacy base-model dropdown.
	export let currentModelId: string | null = null;

	$: availableModels = ($models ?? []).filter(
		(m: any) =>
			(!currentModelId || m.id !== currentModelId) &&
			!m?.preset &&
			m?.owned_by !== 'arena' &&
			!(m?.direct ?? false)
	);

	function modelDisplayName(id: string): string {
		const m = ($models ?? []).find((m: any) => m.id === id);
		return m?.name ?? id;
	}

	function addProvider() {
		providers = [
			...providers,
			{
				model_id: '',
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
</script>

<div class="space-y-1.5">
	{#each providers as provider, idx (idx)}
		<div
			class="rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-850/50 px-3 py-2"
		>
			<div class="flex items-center gap-2">
				<!-- Position label -->
				<div
					class="shrink-0 flex items-center gap-1.5 w-24 text-xs font-medium uppercase tracking-wide {idx ===
					0
						? 'text-gray-700 dark:text-gray-300'
						: 'text-gray-500 dark:text-gray-400'}"
				>
					{#if idx === 0}
						<span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
						{$i18n.t('Primary')}
					{:else}
						<span class="w-1.5 h-1.5 rounded-full bg-amber-400/70"></span>
						{$i18n.t('Backup {{n}}', { n: idx })}
					{/if}
				</div>

				<!-- Model selector -->
				<select
					class="flex-1 min-w-0 text-sm bg-transparent outline-none truncate"
					bind:value={provider.model_id}
					aria-label={$i18n.t('Model')}
				>
					<option value="" class="text-gray-900">{$i18n.t('Select a model')}</option>
					{#if provider.model_id && !availableModels.find((m: any) => m.id === provider.model_id)}
						<!-- Preserve an id that no longer appears in the store
						     (e.g. connection removed) so the user can see it
						     before re-picking. -->
						<option value={provider.model_id} class="text-gray-900">
							{provider.model_id} ({$i18n.t('missing')})
						</option>
					{/if}
					{#each availableModels as m (m.id)}
						<option value={m.id} class="text-gray-900">{m.name}</option>
					{/each}
				</select>

				<!-- Reorder / remove -->
				<div class="flex items-center shrink-0 text-gray-400">
					<button
						type="button"
						class="p-1 hover:text-black dark:hover:text-white disabled:opacity-20 disabled:pointer-events-none"
						on:click={() => move(idx, -1)}
						disabled={idx === 0}
						aria-label={$i18n.t('Move up')}
						title={$i18n.t('Move up')}
					>
						<svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path
								fill-rule="evenodd"
								d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04L10.75 5.612V16.25A.75.75 0 0110 17z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
					<button
						type="button"
						class="p-1 hover:text-black dark:hover:text-white disabled:opacity-20 disabled:pointer-events-none"
						on:click={() => move(idx, 1)}
						disabled={idx === providers.length - 1}
						aria-label={$i18n.t('Move down')}
						title={$i18n.t('Move down')}
					>
						<svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path
								fill-rule="evenodd"
								d="M10 3a.75.75 0 01.75.75v10.638l3.96-4.158a.75.75 0 111.08 1.04l-5.25 5.5a.75.75 0 01-1.08 0l-5.25-5.5a.75.75 0 111.08-1.04l3.96 4.158V3.75A.75.75 0 0110 3z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
					<button
						type="button"
						class="p-1 hover:text-red-500"
						on:click={() => removeProvider(idx)}
						aria-label={$i18n.t('Remove provider')}
						title={$i18n.t('Remove provider')}
					>
						<svg viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path
								d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
							/>
						</svg>
					</button>
				</div>
			</div>

			<!-- Capabilities row -->
			<div class="flex items-center gap-4 mt-1.5 ml-24 text-xs text-gray-500 dark:text-gray-400">
				<span class="text-[10px] uppercase tracking-wide">{$i18n.t('Supports')}</span>
				<label class="flex items-center gap-1 cursor-pointer select-none">
					<input
						type="checkbox"
						class="accent-gray-500"
						checked={provider.capabilities.includes('tools')}
						on:change={() => toggleCapability(idx, 'tools')}
					/>
					{$i18n.t('Tools')}
				</label>
				<label class="flex items-center gap-1 cursor-pointer select-none">
					<input
						type="checkbox"
						class="accent-gray-500"
						checked={provider.capabilities.includes('vision')}
						on:change={() => toggleCapability(idx, 'vision')}
					/>
					{$i18n.t('Vision')}
				</label>
				{#if idx > 0}
					<span class="text-[10px] text-gray-400 dark:text-gray-500">
						{$i18n.t('Leave unticked if unsure — untagged backups are always eligible.')}
					</span>
				{/if}
			</div>
		</div>
	{/each}

	<button
		type="button"
		on:click={addProvider}
		class="w-full text-sm border border-dashed border-gray-300 dark:border-gray-700 rounded-lg py-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-400 dark:hover:border-gray-600 transition"
	>
		+ {$i18n.t(providers.length === 0 ? 'Add primary provider' : 'Add backup provider')}
	</button>

	<p class="text-[11px] leading-relaxed text-gray-400 dark:text-gray-500 pt-1">
		{$i18n.t(
			'The first provider is the primary. Backups are tried in order when the previous one fails with a network, 429, or 5xx error. Capability ticks filter backups out when the request needs tools or vision.'
		)}
	</p>
</div>
