<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import FailoverProviders from '$lib/components/common/FailoverProviders.svelte';
	import {
		getModelFailoverMap,
		setModelFailoverMap,
		type ModelFailoverEntry
	} from '$lib/apis/configs';

	const i18n: any = getContext('i18n');

	export let show = false;
	// The base model whose failover chain is being edited. Pass the row's
	// `model` object so we can display its name.
	export let model: { id: string; name?: string } | null = null;

	let loading = false;
	let saving = false;

	// Editor state (bound into FailoverProviders.svelte). The base model is
	// the implicit primary; entries here are its ordered backups.
	let providers: ModelFailoverEntry[] = [];

	// Full map cached so we can write back without clobbering other entries.
	let fullMap: Record<string, ModelFailoverEntry[]> = {};

	$: if (show && model?.id) {
		loadMap();
	}

	async function loadMap() {
		loading = true;
		try {
			fullMap = await getModelFailoverMap(localStorage.token);
			providers = (fullMap[model!.id] ?? []).map((p: any) => ({
				model_id: p?.model_id ?? '',
				capabilities: p?.capabilities ?? []
			}));
		} catch (err: any) {
			toast.error(err?.detail ?? `${err}`);
			providers = [];
		} finally {
			loading = false;
		}
	}

	async function save() {
		if (!model?.id) return;
		saving = true;
		try {
			const valid = providers.filter((p) => p.model_id);
			const next = { ...fullMap };
			if (valid.length > 0) {
				next[model.id] = valid;
			} else {
				// Drop the key entirely so absence-of-key stays the canonical
				// "no failover" state.
				delete next[model.id];
			}
			fullMap = await setModelFailoverMap(localStorage.token, next);
			toast.success($i18n.t('Failover saved'));
			show = false;
		} catch (err: any) {
			toast.error(err?.detail ?? `${err}`);
		} finally {
			saving = false;
		}
	}
</script>

<Modal bind:show size="md">
	<div class="text-gray-700 dark:text-gray-100">
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class="text-lg font-medium self-center">
				{$i18n.t('Failover for {{name}}', { name: model?.name ?? model?.id ?? '' })}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
				aria-label={$i18n.t('Close')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="px-5 pb-2">
			<p class="text-xs text-gray-500 dark:text-gray-400 mb-3">
				{$i18n.t(
					'When a chat is sent to {{name}} and the request fails with a network/429/5xx error, the resolver tries the providers below in order. Workspace models with their own failover chain ignore this list.',
					{ name: model?.name ?? model?.id ?? '' }
				)}
			</p>

			{#if loading}
				<div class="flex justify-center py-6">
					<Spinner />
				</div>
			{:else}
				<FailoverProviders bind:providers currentModelId={model?.id ?? null} />
			{/if}
		</div>

		<div class="flex justify-end px-5 pb-4 pt-2 gap-2">
			<button
				class="px-3.5 py-1.5 text-sm font-medium dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white bg-white border border-gray-100 dark:border-gray-800 hover:bg-gray-100 transition rounded-full"
				on:click={() => {
					show = false;
				}}
				disabled={saving}
			>
				{$i18n.t('Cancel')}
			</button>
			<button
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full disabled:opacity-50"
				on:click={save}
				disabled={loading || saving}
			>
				{saving ? $i18n.t('Saving…') : $i18n.t('Save')}
			</button>
		</div>
	</div>
</Modal>
