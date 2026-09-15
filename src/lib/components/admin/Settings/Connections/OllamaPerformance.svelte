<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { OLLAMA_API_BASE_URL } from '$lib/constants';

	let loading = true;
	let saving = false;
	let diagnosticsLoading = false;
	let keepModelsLoaded = true;
	let flashAttention = true;
	let numParallel = 2;
	let diagnostics: any = null;

	const headers = () => ({
		Accept: 'application/json',
		'Content-Type': 'application/json',
		Authorization: `Bearer ${localStorage.token}`
	});

	const loadConfig = async () => {
		loading = true;
		try {
			const response = await fetch(`${OLLAMA_API_BASE_URL}/performance`, { headers: headers() });
			if (!response.ok) throw await response.json();
			const data = await response.json();
			keepModelsLoaded = data.KEEP_MODELS_LOADED ?? true;
			flashAttention = data.OLLAMA_FLASH_ATTENTION ?? true;
			numParallel = data.OLLAMA_NUM_PARALLEL ?? 2;
		} catch (error) {
			console.error(error);
			toast.error('Failed to load Ollama performance settings');
		} finally {
			loading = false;
		}
	};

	const saveConfig = async () => {
		saving = true;
		try {
			const response = await fetch(`${OLLAMA_API_BASE_URL}/performance/update`, {
				method: 'POST',
				headers: headers(),
				body: JSON.stringify({
					OLLAMA_KEEP_ALIVE: keepModelsLoaded ? '-1' : '5m',
					OLLAMA_FLASH_ATTENTION: flashAttention,
					OLLAMA_NUM_PARALLEL: Number(numParallel)
				})
			});
			if (!response.ok) throw await response.json();
			toast.success('Ollama performance settings saved');
			await refreshDiagnostics();
		} catch (error) {
			console.error(error);
			toast.error('Failed to save Ollama performance settings');
		} finally {
			saving = false;
		}
	};

	const refreshDiagnostics = async () => {
		diagnosticsLoading = true;
		try {
			const response = await fetch(`${OLLAMA_API_BASE_URL}/performance/diagnostics`, {
				headers: headers()
			});
			if (!response.ok) throw await response.json();
			diagnostics = await response.json();
		} catch (error) {
			console.error(error);
			diagnostics = null;
			toast.error('Failed to load Ollama diagnostics');
		} finally {
			diagnosticsLoading = false;
		}
	};

	onMount(async () => {
		await loadConfig();
		await refreshDiagnostics();
	});
</script>

<div class="mt-4 border-t border-gray-100 pt-4 dark:border-white/10">
	<div class="mb-3 flex items-center justify-between gap-3">
		<div>
			<div class="text-sm font-medium text-gray-900 dark:text-gray-100">Model performance</div>
			<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
				Optimize local Ollama responsiveness and inspect loaded runners.
			</div>
		</div>
		<button
			class="rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs transition hover:bg-gray-50 disabled:opacity-50 dark:border-white/10 dark:hover:bg-white/5"
			disabled={diagnosticsLoading}
			on:click={refreshDiagnostics}
		>
			{diagnosticsLoading ? 'Checking…' : 'Refresh diagnostics'}
		</button>
	</div>

	{#if loading}
		<div class="py-3 text-xs text-gray-500">Loading performance settings…</div>
	{:else}
		<div class="space-y-3">
			<label class="flex items-start justify-between gap-4 rounded-xl border border-gray-100 p-3 dark:border-white/[0.06]">
				<div>
					<div class="text-sm text-gray-800 dark:text-gray-200">Keep models loaded in memory</div>
					<div class="mt-0.5 text-xs text-gray-500">Faster responses, higher RAM/VRAM usage. Enabled uses keep_alive = -1; disabled uses 5m.</div>
				</div>
				<input class="mt-1" type="checkbox" bind:checked={keepModelsLoaded} />
			</label>

			<label class="flex items-start justify-between gap-4 rounded-xl border border-gray-100 p-3 dark:border-white/[0.06]">
				<div>
					<div class="text-sm text-gray-800 dark:text-gray-200">Flash Attention</div>
					<div class="mt-0.5 text-xs text-gray-500">Recommended on supported modern GPUs such as NVIDIA Ampere+ and AMD RDNA2+. Ollama server restart required.</div>
				</div>
				<input class="mt-1" type="checkbox" bind:checked={flashAttention} />
			</label>

			<label class="block rounded-xl border border-gray-100 p-3 dark:border-white/[0.06]">
				<div class="flex items-center justify-between gap-4">
					<div>
						<div class="text-sm text-gray-800 dark:text-gray-200">Parallel requests</div>
						<div class="mt-0.5 text-xs text-gray-500">Recommended: 2–4. Higher values consume more VRAM/RAM and can cause OOM errors. Ollama server restart required.</div>
					</div>
					<input
						class="h-8 w-20 rounded-lg border border-gray-200 bg-transparent px-2 text-sm dark:border-white/10"
						type="number"
						min="1"
						max="16"
						bind:value={numParallel}
					/>
				</div>
			</label>

			<button
				class="w-full rounded-xl bg-gray-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-black disabled:opacity-50 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-100"
				disabled={saving || numParallel < 1 || numParallel > 16}
				on:click={saveConfig}
			>
				{saving ? 'Saving…' : 'Save performance settings'}
			</button>
		</div>
	{/if}

	{#if diagnostics}
		<div class="mt-4 rounded-xl bg-gray-50 p-3 dark:bg-white/[0.03]">
			<div class="mb-2 text-xs font-medium text-gray-700 dark:text-gray-300">Loaded-model diagnostics</div>
			{#if diagnostics.warning}
				<div class="mb-2 rounded-lg bg-amber-50 px-2.5 py-2 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">
					{diagnostics.warning}
				</div>
			{/if}
			{#if diagnostics.models?.length}
				<div class="space-y-1.5">
					{#each diagnostics.models as model}
						<div class="flex items-center justify-between gap-3 text-xs">
							<span class="min-w-0 truncate text-gray-700 dark:text-gray-300">{model.model}</span>
							<span class:model-safe={model.keep_alive_forever} class="shrink-0 text-gray-500">
								Until: {model.until ?? 'Unknown'}
							</span>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-xs text-gray-500">No Ollama models are currently loaded.</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.model-safe {
		color: rgb(22 163 74);
	}
</style>
