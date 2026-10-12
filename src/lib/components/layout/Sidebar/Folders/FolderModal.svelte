<script lang="ts">
	import { getContext, createEventDispatcher, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '../icons/XMark.svelte';

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { user, config, models } from '$lib/stores';
	import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import { getFolderById } from '$lib/apis/folders';
	const i18n = getContext<Writable<I18n>>('i18n');

	export let show = false;
	export let onSubmit: Function = (e) => {};

	export let folderId = null;
	export let parentId = null;
	export let edit = false;

	let folder = null;
	let name = '';
	let meta = {
		background_image_url: null
	};
	let data = {
		model_ids: [] as string[],
		system_prompt: '',
		files: []
	};

	let loading = false;

	const submitHandler = async () => {
		loading = true;

		if ((data?.files ?? []).some((file) => file.status === 'uploading')) {
			toast.error($i18n.t('Please wait until all files are uploaded.'));
			loading = false;
			return;
		}

		// Check folder max file count limit
		const maxFileCount = $config?.features?.folder_max_file_count ?? '';
		if (maxFileCount && (data?.files ?? []).length > maxFileCount) {
			toast.error(
				$i18n.t('Maximum number of files per folder is {{max}}.', { max: maxFileCount ?? 0 })
			);
			loading = false;
			return;
		}

		await onSubmit({
			name,
			meta,
			data,
			parent_id: edit ? undefined : parentId
		});
		show = false;
		loading = false;
	};

	const init = async () => {
		if (folderId) {
			folder = await getFolderById(localStorage.token, folderId).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			name = folder.name;
			meta = folder.meta || {
				background_image_url: null
			};
			data = {
				system_prompt: '',
				files: [],
				...folder.data,
				model_ids: folder.data?.model_ids ?? []
			};
		}

		focusInput();
	};

	const focusInput = async () => {
		await tick();
		const input = document.getElementById('folder-name') as HTMLInputElement;
		if (input) {
			input.focus();
			input.select();
		}
	};

	$: if (show) {
		init();
	}

	$: if (!show && !edit) {
		name = '';
		meta = {
			background_image_url: null
		};
		data = {
			model_ids: [],
			system_prompt: '',
			files: []
		};
	}
</script>

<Modal size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-4 pt-3 pb-1">
			<div class=" text-sm self-center">
				{#if edit}
					{$i18n.t('Edit Folder')}
				{:else}
					{$i18n.t('Create Folder')}
				{/if}
			</div>
			<button
				aria-label={$i18n.t('Close')}
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="flex flex-col w-full mt-1">
						<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Folder Name')}</div>

						<div class="flex-1">
							<input
								id="folder-name"
								class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Enter folder name')}
								autocomplete="off"
							/>
						</div>
					</div>

					<input
						id="folder-background-image-input"
						type="file"
						hidden
						accept="image/*"
						on:change={(e) => {
							const inputFiles = e.target.files;

							let reader = new FileReader();
							reader.onload = (event) => {
								let originalImageUrl = `${event.target.result}`;
								meta.background_image_url = originalImageUrl;
							};

							if (
								inputFiles &&
								inputFiles.length > 0 &&
								['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(
									inputFiles[0]['type']
								)
							) {
								reader.readAsDataURL(inputFiles[0]);
							} else {
								console.log(`Unsupported File Type '${inputFiles[0]['type']}'.`);

								// clear the input
								e.target.value = '';
							}
						}}
					/>

					<div class="flex justify-between w-full mt-1 items-center">
						<div class="text-xs text-gray-500">{$i18n.t('Folder Background Image')}</div>

						<div class="">
							<button
								aria-labelledby="chat-background-label background-image-url-state"
								class="p-1 px-3 text-xs flex rounded-sm transition"
								on:click={() => {
									if (meta?.background_image_url !== null) {
										meta.background_image_url = null;
									} else {
										const input = document.getElementById('folder-background-image-input');
										if (input) {
											input.click();
										}
									}
								}}
								type="button"
							>
								<span class="ml-2 self-center" id="background-image-url-state"
									>{(meta?.background_image_url ?? null) === null
										? $i18n.t('Upload')
										: $i18n.t('Reset')}</span
								>
							</button>
						</div>
					</div>

					<hr class=" border-gray-50 dark:border-gray-850/30 my-2.5 w-full" />

					<div class="my-1 flex items-center justify-between gap-4">
						<label
							for="model-selector-folder-default-button"
							class="shrink-0 text-xs text-gray-500"
						>
							{$i18n.t('Default Model')}
						</label>
						<div class="flex min-w-0 max-w-[65%] items-center gap-2">
							<div class="min-w-0">
								<ModelSelector
									id="folder-default"
									placeholder={$i18n.t('Use default')}
									items={$models.map((model) => ({
										value: model.id,
										label: model.name,
										model
									}))}
									triggerClassName="text-xs"
									placement="auto"
									align="end"
									selectionOnly
									value={data.model_ids[0] ?? ''}
									bind:values={data.model_ids}
								/>
							</div>
							{#if data.model_ids.length}
								<button
									type="button"
									aria-label={$i18n.t('Reset')}
									class="shrink-0 p-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-200"
									on:click={() => (data.model_ids = [])}
								>
									<XMark className="size-3" />
								</button>
							{/if}
						</div>
					</div>

					{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
						<div class="my-1">
							<div class="mb-2 text-xs text-gray-500">{$i18n.t('System Prompt')}</div>
							<div>
								<Textarea
									className=" text-sm w-full bg-transparent outline-hidden "
									placeholder={$i18n.t(
										'Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.'
									)}
									maxSize={200}
									bind:value={data.system_prompt}
								/>
							</div>
						</div>
					{/if}

					<div class="my-2">
						<Knowledge bind:selectedItems={data.files}>
							<div slot="label">
								<div class="flex w-full justify-between">
									<div class=" text-xs text-gray-500">
										{$i18n.t('Knowledge')}
									</div>
								</div>
							</div>
						</Knowledge>
					</div>

					<div class="flex justify-end pt-3 text-sm font-normal gap-1.5">
						<button
							class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white disabled:cursor-not-allowed"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div class="shrink-0">
									<Spinner className="size-3" />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
