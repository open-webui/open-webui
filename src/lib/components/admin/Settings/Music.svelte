<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	import { getMusicConfig, updateMusicConfig, type MusicConfig } from '$lib/apis/music';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let saveHandler: () => void;

	let loading = false;
	let saving = false;

	let ENABLE_MUSIC_GENERATION = false;
	let MUSIC_API_BASE_URL = '';
	let MUSIC_API_KEY = '';
	let MUSIC_API_GENERATE_PATH = '/generate';
	let MUSIC_MODEL = '';

	const load = async () => {
		loading = true;
		try {
			const cfg = (await getMusicConfig(localStorage.token)) as MusicConfig;
			ENABLE_MUSIC_GENERATION = Boolean(cfg?.ENABLE_MUSIC_GENERATION);
			MUSIC_API_BASE_URL = cfg?.MUSIC_API_BASE_URL ?? '';
			MUSIC_API_KEY = cfg?.MUSIC_API_KEY ?? '';
			MUSIC_API_GENERATE_PATH = cfg?.MUSIC_API_GENERATE_PATH ?? '/generate';
			MUSIC_MODEL = cfg?.MUSIC_MODEL ?? '';
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			loading = false;
		}
	};

	const save = async () => {
		saving = true;
		try {
			await updateMusicConfig(localStorage.token, {
				ENABLE_MUSIC_GENERATION,
				MUSIC_API_BASE_URL,
				MUSIC_API_KEY,
				MUSIC_API_GENERATE_PATH,
				MUSIC_MODEL
			});

			saveHandler?.();
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			saving = false;
		}
	};

	onMount(() => {
		void load();
	});
</script>

<div class="flex flex-col gap-4 pb-16">
	<div>
		<div class="text-lg font-semibold">{$i18n.t('Music')}</div>
		<div class="text-sm text-gray-500 dark:text-gray-400">
			{$i18n.t('Configure provider endpoint, API key, and default model.')}
		</div>
	</div>

	{#if loading}
		<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
			<Spinner className="size-4" />{$i18n.t('Loading...')}
		</div>
	{:else}
		<div class="flex items-center justify-between gap-4 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
			<div class="flex flex-col">
				<div class="font-medium">{$i18n.t('Enable Music')}</div>
				<div class="text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Allow users to generate music from chat prompts')}
				</div>
			</div>

			<Switch
				state={ENABLE_MUSIC_GENERATION}
				on:change={(e) => {
					ENABLE_MUSIC_GENERATION = e.detail;
				}}
			/>
		</div>

		<div class="flex flex-col gap-2">
			<div class="text-sm font-medium">{$i18n.t('API Base URL')}</div>
			<input
				class="w-full rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-3 py-2 text-sm outline-hidden"
				placeholder="https://example.com"
				bind:value={MUSIC_API_BASE_URL}
			/>
		</div>

		<div class="flex flex-col gap-2">
			<div class="text-sm font-medium">{$i18n.t('Generate Path')}</div>
			<input
				class="w-full rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-3 py-2 text-sm outline-hidden"
				placeholder="/generate"
				bind:value={MUSIC_API_GENERATE_PATH}
			/>
		</div>

		<div class="flex flex-col gap-2">
			<div class="text-sm font-medium">{$i18n.t('API Key')}</div>
			<SensitiveInput bind:value={MUSIC_API_KEY} placeholder={$i18n.t('Enter API key')} />
		</div>

		<div class="flex flex-col gap-2">
			<div class="text-sm font-medium">{$i18n.t('Default Model')}</div>
			<input
				class="w-full rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 px-3 py-2 text-sm outline-hidden"
				placeholder="model-id"
				bind:value={MUSIC_MODEL}
			/>
		</div>

		<div class="flex justify-end">
			<button
				type="button"
				class="px-4 py-2 rounded-xl bg-gray-900 hover:bg-gray-800 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-gray-900 text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed"
				disabled={saving}
				on:click={() => void save()}
			>
				{#if saving}
					<span class="inline-flex items-center gap-2">
						<Spinner className="size-4" />{$i18n.t('Saving...')}
					</span>
				{:else}
					{$i18n.t('Save')}
				{/if}
			</button>
		</div>
	{/if}
</div>

