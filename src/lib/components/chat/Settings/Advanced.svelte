<script lang="ts">
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import AdvancedParams from './Advanced/AdvancedParams.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let saveSettings: Function;

	// Advanced
	let requestFormat = '';
	let keepAlive = null;

	let params = {
		// Advanced
		seed: 0,
		temperature: '',
		frequency_penalty: '',
		repeat_last_n: '',
		mirostat: '',
		mirostat_eta: '',
		mirostat_tau: '',
		top_k: '',
		top_p: '',
		stop: '',
		tfs_z: '',
		num_ctx: '',
		max_tokens: ''
	};

	const toggleRequestFormat = async () => {
		if (requestFormat === '') {
			requestFormat = 'json';
		} else {
			requestFormat = '';
		}

		saveSettings({ requestFormat: requestFormat !== '' ? requestFormat : undefined });
	};

	onMount(() => {
		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');

		requestFormat = settings.requestFormat ?? '';
		keepAlive = settings.keepAlive ?? null;

		params.seed = settings.seed ?? 0;
		params.temperature = settings.temperature ?? '';
		params.frequency_penalty = settings.frequency_penalty ?? '';
		params.top_k = settings.top_k ?? '';
		params.top_p = settings.top_p ?? '';
		params.num_ctx = settings.num_ctx ?? '';
		params = { ...params, ...settings.params };
		params.stop = (settings?.params?.stop ?? []).join(',');
	});
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-80">
		<div class=" text-sm font-medium">{$i18n.t('Parameters')}</div>

		<AdvancedParams bind:params />
		<hr class=" dark:border-gray-700" />

		<div class=" py-1 w-full justify-between">
			<div class="flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Keep Alive')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					type="button"
					on:click={() => {
						keepAlive = keepAlive === null ? '5m' : null;
					}}
				>
					{#if keepAlive === null}
						<span class="ml-2 self-center">{$i18n.t('Default')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Custom')}</span>
					{/if}
				</button>
			</div>

			{#if keepAlive !== null}
				<div class="flex mt-1 space-x-2">
					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						type="text"
						placeholder={$i18n.t("e.g. '30s','10m'. Valid time units are 's', 'm', 'h'.")}
						bind:value={keepAlive}
					/>
				</div>
			{/if}
		</div>

		<div>
			<div class=" py-1 flex w-full justify-between">
				<div class=" self-center text-sm font-medium">{$i18n.t('Request Mode')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleRequestFormat();
					}}
				>
					{#if requestFormat === ''}
						<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
					{:else if requestFormat === 'json'}
						<!-- <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            class="w-4 h-4 self-center"
                        >
                            <path
                                d="M10 2a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 2zM10 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 15zM10 7a3 3 0 100 6 3 3 0 000-6zM15.657 5.404a.75.75 0 10-1.06-1.06l-1.061 1.06a.75.75 0 001.06 1.06l1.06-1.06zM6.464 14.596a.75.75 0 10-1.06-1.06l-1.06 1.06a.75.75 0 001.06 1.06l1.06-1.06zM18 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 0118 10zM5 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 015 10zM14.596 15.657a.75.75 0 001.06-1.06l-1.06-1.061a.75.75 0 10-1.06 1.06l1.06 1.06zM5.404 6.464a.75.75 0 001.06-1.06l-1.06-1.06a.75.75 0 10-1.061 1.06l1.06 1.06z"
                            />
                        </svg> -->
						<span class="ml-2 self-center">{$i18n.t('JSON')}</span>
					{/if}
				</button>
			</div>
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			on:click={() => {
				saveSettings({
					params: {
						seed: (params.seed !== 0 ? params.seed : undefined) ?? undefined,
						stop: params.stop !== '' ? params.stop.split(',').filter((e) => e) : undefined,
						temperature: params.temperature !== '' ? params.temperature : undefined,
						frequency_penalty:
							params.frequency_penalty !== '' ? params.frequency_penalty : undefined,
						repeat_last_n: params.repeat_last_n !== '' ? params.repeat_last_n : undefined,
						mirostat: params.mirostat !== '' ? params.mirostat : undefined,
						mirostat_eta: params.mirostat_eta !== '' ? params.mirostat_eta : undefined,
						mirostat_tau: params.mirostat_tau !== '' ? params.mirostat_tau : undefined,
						top_k: params.top_k !== '' ? params.top_k : undefined,
						top_p: params.top_p !== '' ? params.top_p : undefined,
						tfs_z: params.tfs_z !== '' ? params.tfs_z : undefined,
						num_ctx: params.num_ctx !== '' ? params.num_ctx : undefined,
						max_tokens: params.max_tokens !== '' ? params.max_tokens : undefined
					},
					keepAlive: keepAlive ? (isNaN(keepAlive) ? keepAlive : parseInt(keepAlive)) : undefined
				});

				dispatch('save');
			}}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</div>
