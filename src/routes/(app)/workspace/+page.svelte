<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext } from 'svelte';

	import { WEBUI_NAME, modelfiles, settings, showSidebar, user } from '$lib/stores';
	import { createModel, deleteModel } from '$lib/apis/ollama';
	import {
		createNewModelfile,
		deleteModelfileByTagName,
		getModelfiles
	} from '$lib/apis/modelfiles';
	import { goto } from '$app/navigation';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Modelfiles from '$lib/components/workspace/Modelfiles.svelte';
	import Prompts from '$lib/components/workspace/Prompts.svelte';
	import Documents from '$lib/components/workspace/Documents.svelte';
	import Playground from '$lib/components/workspace/Playground.svelte';

	const i18n = getContext('i18n');

	let tab = '';

	let localModelfiles = [];
	let importFiles;
	let modelfilesImportInputElement: HTMLInputElement;

	const deleteModelHandler = async (tagName) => {
		let success = null;

		success = await deleteModel(localStorage.token, tagName).catch((err) => {
			toast.error(err);
			return null;
		});

		if (success) {
			toast.success($i18n.t(`Deleted {{tagName}}`, { tagName }));
		}

		return success;
	};

	const deleteModelfile = async (tagName) => {
		await deleteModelHandler(tagName);
		await deleteModelfileByTagName(localStorage.token, tagName);
		await modelfiles.set(await getModelfiles(localStorage.token));
	};

	const shareModelfile = async (modelfile) => {
		toast.success($i18n.t('Redirecting you to OpenWebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/modelfiles/create`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(JSON.stringify(modelfile), '*');
				}
			},
			false
		);
	};

	const saveModelfiles = async (modelfiles) => {
		let blob = new Blob([JSON.stringify(modelfiles)], {
			type: 'application/json'
		});
		saveAs(blob, `modelfiles-export-${Date.now()}.json`);
	};

	onMount(() => {
		localModelfiles = JSON.parse(localStorage.getItem('modelfiles') ?? '[]');

		if (localModelfiles) {
			console.log(localModelfiles);
		}
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Workspace')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<div class="min-h-screen max-h-[100dvh] w-full flex justify-center dark:text-white">
	<div class=" flex flex-col justify-between w-full overflow-y-auto">
		<div class=" mx-auto w-full h-full">
			<div class="w-full h-full">
				<div class=" flex flex-col justify-center">
					<div class=" px-4 pt-3 mb-1.5">
						<div class=" flex items-center">
							<div
								class="{$showSidebar
									? 'md:hidden'
									: ''} mr-1 self-start flex flex-none items-center"
							>
								<button
									id="sidebar-toggle-button"
									class="cursor-pointer p-2 flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition"
									on:click={() => {
										showSidebar.set(!$showSidebar);
									}}
								>
									<div class=" m-auto self-center">
										<MenuLines />
									</div>
								</button>
							</div>
							<div class="flex items-center text-xl font-semibold">{$i18n.t('Workspace')}</div>
						</div>
					</div>

					<div class="px-4 mb-1">
						<div
							class="flex scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-xl bg-transparent/10 p-1"
						>
							<button
								class="min-w-fit rounded-lg p-1.5 px-3 {tab === ''
									? 'bg-gray-50 dark:bg-gray-850'
									: ''} transition"
								type="button"
								on:click={() => {
									tab = '';
								}}>Modelfiles</button
							>

							<button
								class="min-w-fit rounded-lg p-1.5 px-3 {tab === 'prompts'
									? 'bg-gray-50 dark:bg-gray-850'
									: ''} transition"
								type="button"
								on:click={() => {
									tab = 'prompts';
								}}>Prompts</button
							>

							<button
								class="min-w-fit rounded-lg p-1.5 px-3 {tab === 'documents'
									? 'bg-gray-50 dark:bg-gray-850'
									: ''} transition"
								type="button"
								on:click={() => {
									tab = 'documents';
								}}>Documents</button
							>

							<button
								class="min-w-fit rounded-lg p-1.5 px-3 {tab === 'playground'
									? 'bg-gray-50 dark:bg-gray-850'
									: ''} transition"
								type="button"
								on:click={() => {
									tab = 'playground';
								}}>Playground</button
							>
						</div>
					</div>

					<hr class=" my-2 dark:border-gray-850" />

					<div class=" py-1 px-5 min-h-full">
						{#if tab === ''}
							<Modelfiles />
						{:else if tab === 'prompts'}
							<Prompts />
						{:else if tab === 'documents'}
							<Documents />
						{:else if tab === 'playground'}
							<Playground />
						{/if}
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
