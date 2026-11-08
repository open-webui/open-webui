<script lang="ts">
	import { getContext, createEventDispatcher, onMount, onDestroy, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';

	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import ModelSettingsLabel from '$lib/components/workspace/Models/ModelSettingsLabel.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import FolderShareModal from './FolderShareModal.svelte';
	import XMark from '../icons/XMark.svelte';

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { baseModels, user, config, settings } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import FileNav from '$lib/components/chat/FileNav.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import TerminalSelector from '$lib/components/workspace/Models/TerminalSelector.svelte';

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
		description: '',
		model_ids: [] as string[],
		terminal_id: '',
		working_directory: '',
		system_prompt: '',
		files: []
	};

	let loading = false;
	let showAccessModal = false;
	let showAdvanced = false;
	let showDirectoryPicker = false;
	let terminalModels = [];
	let modelsLoading = false;
	let modelRequest = 0;
	let modelTimer: ReturnType<typeof setTimeout>;

	const loadTerminalModels = (visible: boolean, terminalId: string, cwd: string) => {
		const request = ++modelRequest;
		clearTimeout(modelTimer);
		terminalModels = [];
		modelsLoading = visible && !!terminalId;
		if (!modelsLoading) return;

		modelTimer = setTimeout(async () => {
			try {
				const available = await getModels(
					localStorage.token,
					$config?.features?.enable_direct_integrations
						? ($settings?.directConnections ?? null)
						: null,
					false,
					false,
					{ terminalId, cwd: cwd.trim() }
				);
				if (request === modelRequest) terminalModels = available;
			} catch (error) {
				if (request === modelRequest) toast.error(`${error}`);
			} finally {
				if (request === modelRequest) modelsLoading = false;
			}
		}, 250);
	};

	$: modelTerminalId = data.terminal_id;
	$: modelDirectory = data.working_directory;
	$: loadTerminalModels(show, modelTerminalId, modelDirectory);
	$: folderModels = modelTerminalId ? terminalModels : $baseModels;

	onDestroy(() => {
		clearTimeout(modelTimer);
		modelRequest++;
	});

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
			// Sharing saves separately; do not overwrite its mode with the editor's snapshot.
			data: {
				description: data.description.trim(),
				model_ids: data.model_ids,
				terminal_id: data.terminal_id || null,
				working_directory: data.terminal_id ? data.working_directory.trim() || null : null,
				system_prompt: data.system_prompt,
				files: data.files
			},
			parent_id: edit ? undefined : parentId
		});
		show = false;
		loading = false;
	};

	const init = async () => {
		folder = null;
		if (folderId) {
			folder = await getFolderById(localStorage.token, folderId).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
			if (!folder) return;

			name = folder.name;
			meta = folder.meta || {
				background_image_url: null
			};
			data = {
				system_prompt: '',
				files: [],
				...folder.data,
				description: folder.data?.description ?? '',
				model_ids: folder.data?.model_ids ?? [],
				terminal_id: folder.data?.terminal_id ?? '',
				working_directory: folder.data?.working_directory ?? ''
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
	$: if (!show) {
		showAccessModal = false;
		showAdvanced = false;
		showDirectoryPicker = false;
	}

	$: if (!show && !edit) {
		name = '';
		meta = {
			background_image_url: null
		};
		data = {
			description: '',
			model_ids: [],
			terminal_id: '',
			working_directory: '',
			system_prompt: '',
			files: []
		};
	}
</script>

<Modal ariaLabel={edit ? $i18n.t('Edit Folder') : $i18n.t('Create Folder')} size="md" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-4 pt-3 pb-1">
			<div class=" text-sm self-center">
				{#if edit}
					{$i18n.t('Edit Folder')}
				{:else}
					{$i18n.t('Create Folder')}
				{/if}
			</div>
			<div class="flex items-center gap-1">
				{#if edit && folder && ($user?.role === 'admin' || (folder.user_id === $user?.id && $user?.permissions?.sharing?.folders))}
					<AccessButton disabled={loading} on:click={() => (showAccessModal = true)} />
				{/if}
				<button
					aria-label={$i18n.t('Close')}
					class="self-center rounded-lg py-1 text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 px-0"
					on:click={() => {
						show = false;
					}}
				>
					<XMark className={'size-4'} />
				</button>
			</div>
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
						<label for="folder-name" class="block mb-1 text-xs text-gray-500"
							>{$i18n.t('Folder Name')}</label
						>

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

					<div class="my-2">
						<label for="folder-description" class="mb-1 block text-xs text-gray-500">
							{$i18n.t('Description')}
						</label>
						<Textarea
							id="folder-description"
							ariaLabel={$i18n.t('Description')}
							className="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
							placeholder={$i18n.t('Enter description')}
							maxSize={200}
							bind:value={data.description}
						/>
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
						<div id="folder-background-image-label" class="text-xs text-gray-500">
							{$i18n.t('Folder Background Image')}
						</div>

						<div class="">
							<button
								aria-labelledby="folder-background-image-label folder-background-image-state"
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
								<span class="ml-2 self-center" id="folder-background-image-state"
									>{(meta?.background_image_url ?? null) === null
										? $i18n.t('Upload')
										: $i18n.t('Reset')}</span
								>
							</button>
						</div>
					</div>

					<hr class=" border-gray-50 dark:border-gray-850/30 my-2.5 w-full" />

					<Collapsible
						title={$i18n.t('Advanced')}
						bind:open={showAdvanced}
						buttonClassName="w-full py-1 text-xs font-normal text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100 transition"
					>
						<div slot="content" class="space-y-0.5 pt-1">
							<TerminalSelector
								bind:terminalId={data.terminal_id}
								label={$i18n.t('Default terminal')}
								description={$i18n.t(
									'Select the terminal used by default for new chats in this folder.'
								)}
								onChange={() => {
									data.working_directory = '';
									data.model_ids = data.model_ids.filter((id) => !id.startsWith('agent:'));
								}}
							/>
							{#if data.terminal_id}
								<div
									class="grid grid-cols-[7rem_minmax(0,1fr)] items-start gap-2 px-1 py-1 sm:grid-cols-[8rem_minmax(0,1fr)]"
								>
									<label
										for="folder-working-directory"
										class="block text-xs font-normal text-gray-600 dark:text-gray-400"
									>
										<ModelSettingsLabel
											label={$i18n.t('Working directory')}
											description={$i18n.t(
												'Path on the selected terminal. Applies to new chats only.'
											)}
										/>
									</label>
									<div class="flex min-w-0 items-center gap-2">
										<input
											id="folder-working-directory"
											class="min-w-0 flex-1 bg-transparent text-xs font-normal text-gray-900 outline-hidden placeholder:text-gray-400 dark:text-gray-100 dark:placeholder:text-gray-600"
											bind:value={data.working_directory}
											placeholder={$i18n.t('Use the terminal’s default directory')}
										/>
										<button
											type="button"
											aria-label={$i18n.t('Browse directories')}
											title={$i18n.t('Browse directories')}
											class="shrink-0 text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
											on:click={() => (showDirectoryPicker = true)}
											><FolderOpen className="size-3.5" /></button
										>
									</div>
								</div>
							{/if}

							<div
								class="grid min-h-7 grid-cols-[7rem_minmax(0,1fr)] items-center gap-2 px-1 sm:grid-cols-[8rem_minmax(0,1fr)]"
							>
								<label
									for="model-selector-folder-default-button"
									class="shrink-0 text-xs font-normal text-gray-600 dark:text-gray-400"
								>
									<ModelSettingsLabel
										label={$i18n.t('Default Model')}
										description={$i18n.t(
											'Select the model used by default for new chats in this folder.'
										)}
									/>
								</label>
								<div class="flex min-w-0 items-center justify-between gap-2">
									<div class="min-w-0">
										<ModelSelector
											id="folder-default"
											placeholder={$i18n.t('Use default')}
											disabled={modelsLoading}
											items={folderModels.map((model) => ({
												value: model.id,
												label: model.name,
												model
											}))}
											triggerClassName="text-xs font-normal text-gray-900 dark:text-gray-100"
											placement="auto"
											align="start"
											selectionOnly
											value={data.model_ids[0] ?? ''}
											bind:values={data.model_ids}
										/>
									</div>
									{#if modelsLoading}<Spinner className="size-3" />{/if}
									{#if data.model_ids.length}
										<button
											type="button"
											aria-label={$i18n.t('Reset')}
											class="shrink-0 py-1 text-gray-500 hover:text-gray-700 dark:hover:text-gray-200 px-0"
											on:click={() => (data.model_ids = [])}
										>
											<XMark className="size-3" />
										</button>
									{/if}
								</div>
							</div>

							{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
								<div
									class="grid grid-cols-[7rem_minmax(0,1fr)] items-start gap-2 px-1 py-1 sm:grid-cols-[8rem_minmax(0,1fr)]"
								>
									<label
										for="folder-system-prompt"
										class="block text-xs font-normal text-gray-600 dark:text-gray-400"
									>
										<ModelSettingsLabel
											label={$i18n.t('System Prompt')}
											description={$i18n.t(
												'Set instructions that guide how the model behaves in this folder.'
											)}
										/>
									</label>
									<div>
										<Textarea
											id="folder-system-prompt"
											ariaLabel={$i18n.t('System Prompt')}
											className="w-full resize-none bg-transparent text-xs font-normal text-gray-900 outline-hidden placeholder:text-gray-400 dark:text-gray-100 dark:placeholder:text-gray-600"
											placeholder={$i18n.t(
												'Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.'
											)}
											maxSize={200}
											bind:value={data.system_prompt}
										/>
									</div>
								</div>
							{/if}

							<Knowledge bind:selectedItems={data.files}>
								<ModelSettingsLabel
									slot="label"
									label={$i18n.t('Knowledge')}
									description={$i18n.t(
										'Attach knowledge bases, notes, or files for chats in this folder.'
									)}
								/>
							</Knowledge>
						</div>
					</Collapsible>

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

{#if show && edit && folder && ($user?.role === 'admin' || folder.user_id === $user?.id)}
	<FolderShareModal bind:show={showAccessModal} {folder} />
{/if}

{#if show && showDirectoryPicker && data.terminal_id}
	<Modal bind:show={showDirectoryPicker} ariaLabel={$i18n.t('Choose working directory')} size="md">
		<div class="px-2 py-4">
			<div class="mb-3 flex items-center justify-between px-2 text-sm">
				<span>{$i18n.t('Choose working directory')}</span>
				<button
					type="button"
					aria-label={$i18n.t('Close')}
					class="text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
					on:click={() => (showDirectoryPicker = false)}><XMark className="size-4" /></button
				>
			</div>
			<div class="h-[60dvh] min-h-0">
				<FileNav
					terminalId={data.terminal_id}
					initialDirectory={data.working_directory || null}
					manageFileRequests={false}
					showTerminalDock={false}
					onSelectDirectory={(path) => {
						data.working_directory = path;
						showDirectoryPicker = false;
					}}
				/>
			</div>
		</div>
	</Modal>
{/if}
