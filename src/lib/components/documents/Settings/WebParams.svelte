<script lang="ts">
	import { getRAGConfig, updateRAGConfig } from '$lib/apis/rag';

	import { documents, models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let webLoaderSSLVerification = true;

	let youtubeLanguage = 'en';
	let youtubeTranslation = null;

	const submitHandler = async () => {
		const res = await updateRAGConfig(localStorage.token, {
			web_loader_ssl_verification: webLoaderSSLVerification,
			youtube: {
				language: youtubeLanguage.split(',').map((lang) => lang.trim()),
				translation: youtubeTranslation
			}
		});
	};

	onMount(async () => {
		const res = await getRAGConfig(localStorage.token);

		if (res) {
			webLoaderSSLVerification = res.web_loader_ssl_verification;
			youtubeLanguage = res.youtube.language.join(',');
			youtubeTranslation = res.youtube.translation;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
		saveHandler();
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll h-full max-h-[22rem]">
		<div>
			<div class=" mb-1 text-sm font-medium">
				{$i18n.t('Web Loader Settings')}
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Bypass SSL verification for Websites')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							webLoaderSSLVerification = !webLoaderSSLVerification;
							submitHandler();
						}}
						type="button"
					>
						{#if webLoaderSSLVerification === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>

			<div class=" mt-2 mb-1 text-sm font-medium">
				{$i18n.t('Youtube Loader Settings')}
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" w-20 text-xs font-medium self-center">{$i18n.t('Language')}</div>
					<div class=" flex-1 self-center">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="text"
							placeholder={$i18n.t('Enter language codes')}
							bind:value={youtubeLanguage}
							autocomplete="off"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
