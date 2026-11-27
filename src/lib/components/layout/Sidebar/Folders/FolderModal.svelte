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
	import FolderMemories from './FolderMemories.svelte';
	import EmojiPicker from '$lib/components/common/EmojiPicker.svelte';
	import Emoji from '$lib/components/common/Emoji.svelte';
	import FolderIcon from '$lib/components/icons/Folder.svelte';
	import SettingsAlt from '$lib/components/icons/SettingsAlt.svelte';
	import Face from '$lib/components/icons/Face.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import XMark from '../icons/XMark.svelte';

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { baseModels, user, config, settings } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import MachineMenu from '$lib/components/chat/MessageInput/MachineMenu.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { writable } from 'svelte/store';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import { getFolderById } from '$lib/apis/folders';
	import { machineIdOf } from '$lib/utils/machines';
	const i18n = getContext<Writable<I18n>>('i18n');

	export let show = false;
	/** Returns true once saved; otherwise the form stays open. */
	export let onSubmit: Function = (e) => {};

	export let folderId = null;
	export let parentId = null;
	export let edit = false;

	let folder: any = null;
	let name = '';
	let meta: { background_image_url: string | null; icon: string; [key: string]: unknown } = {
		background_image_url: null,
		icon: ''
	};
	let data = {
		description: '',
		model_ids: [] as string[],
		machine_id: '',
		working_directory: '',
		system_prompt: '',
		files: []
	};

	let loading = false;
	let selectedTab = 'general';
	let showAccessModal = false;
	let showAdvanced = false;
	let showDirectoryPicker = false;
	let machineModels = [];
	let modelsLoading = false;
	let modelRequest = 0;
	let modelTimer: ReturnType<typeof setTimeout>;

	const loadMachineModels = (visible: boolean, machineId: string, cwd: string) => {
		const request = ++modelRequest;
		clearTimeout(modelTimer);
		machineModels = [];
		modelsLoading = visible && !!machineId;
		if (!modelsLoading) return;

		modelTimer = setTimeout(async () => {
			try {
				const available = await getModels(localStorage.token, false, false, {
					machineId,
					cwd: cwd.trim()
				});
				if (request === modelRequest) machineModels = available;
			} catch (error) {
				if (request === modelRequest) toast.error(`${error}`);
			} finally {
				if (request === modelRequest) modelsLoading = false;
			}
		}, 250);
	};

	// The composer's machine menu picks the folder's default machine.
	const folderMachine = writable<string | null>(null);
	$: folderMachine.set(data.machine_id || null);
	const folderMachineSelection = {
		subscribe: folderMachine.subscribe,
		set: (id: string | null) => {
			if ((id ?? '') === data.machine_id) return;
			data.machine_id = id ?? '';
			data.working_directory = '';
			data.model_ids = data.model_ids.filter((modelId) => !modelId.startsWith('agent:'));
		}
	};

	$: modelMachineId = data.machine_id;
	$: modelDirectory = data.working_directory;
	$: loadMachineModels(show, modelMachineId, modelDirectory);
	$: folderModels = modelMachineId ? machineModels : $baseModels;

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

		const saved = await onSubmit({
			name,
			meta,
			// Sharing saves separately; do not overwrite its mode with the editor's snapshot.
			data: {
				description: data.description.trim(),
				model_ids: data.model_ids,
				machine_id: data.machine_id || null,
				working_directory: data.machine_id ? data.working_directory.trim() || null : null,
				system_prompt: data.system_prompt,
				files: data.files
			},
			parent_id: edit ? undefined : parentId
		});
		if (saved) show = false;
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
			meta = {
				background_image_url: null,
				icon: '',
				...folder.meta
			};
			data = {
				system_prompt: '',
				files: [],
				...folder.data,
				description: folder.data?.description ?? '',
				model_ids: folder.data?.model_ids ?? [],
				machine_id: machineIdOf(folder.data) ?? '',
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
	const tabButtonClass = (active: boolean) =>
		`flex items-center gap-1.5 h-7 px-2 md:w-full shrink-0 rounded-lg text-xs text-left transition-colors duration-75 ${
			active
				? 'font-medium text-base-900 dark:text-base-0 bg-base-50 dark:bg-base-0/[0.04]'
				: 'text-base-600 hover:text-base-700 dark:text-base-400 dark:hover:text-base-300'
		}`;

	$: showPersonalization =
		edit &&
		!!folderId &&
		$config?.features?.enable_memories &&
		($user?.role === 'admin' || ($user?.permissions?.features?.memories ?? true));

	$: if (!show) {
		selectedTab = 'general';
		showAccessModal = false;
		showAdvanced = false;
		showDirectoryPicker = false;
	}

	$: if (!show && !edit) {
		name = '';
		meta = {
			background_image_url: null,
			icon: ''
		};
		data = {
			description: '',
			model_ids: [],
			machine_id: '',
			working_directory: '',
			system_prompt: '',
			files: []
		};
	}
</script>

<Modal
	ariaLabel={edit ? $i18n.t('Edit Folder') : $i18n.t('Create Folder')}
	size={showPersonalization ? 'lg' : 'md'}
	className="bg-base-0 dark:bg-base-900 rounded-3xl {showPersonalization
		? 'flex flex-col md:flex-row overflow-hidden md:h-[36rem] md:min-h-0 max-h-[calc(100dvh-1.5rem)]'
		: ''}"
	bind:show
>
	{#if showPersonalization}
		<nav
			class="shrink-0 min-w-0 md:min-h-0 flex flex-col border-b md:border-b-0 md:border-r border-base-100/30 dark:border-base-0/[0.02] md:w-[12rem]"
		>
			<div class="flex items-center gap-1 m-1 md:mb-0 shrink-0">
				<button
					class="flex flex-1 items-center gap-1.5 h-7 px-2 rounded-lg text-xs text-base-600 dark:text-base-500 hover:text-base-700 dark:hover:text-base-300 transition-colors duration-75"
					type="button"
					on:click={() => {
						show = false;
					}}
				>
					<ChevronLeft className="size-3" strokeWidth="2" />
					<span>{$i18n.t('Back')}</span>
				</button>
			</div>
			<div
				role="tablist"
				aria-label={$i18n.t('Edit Folder')}
				class="tabs scrollbar-none flex min-w-0 overflow-x-auto md:flex-col p-1 gap-px"
			>
				<button
					role="tab"
					aria-selected={selectedTab === 'general'}
					class={tabButtonClass(selectedTab === 'general')}
					on:click={() => (selectedTab = 'general')}
				>
					<SettingsAlt className="size-3.5" strokeWidth="2" />
					<span>{$i18n.t('General')}</span>
				</button>
				<button
					role="tab"
					aria-selected={selectedTab === 'personalization'}
					class={tabButtonClass(selectedTab === 'personalization')}
					on:click={() => (selectedTab = 'personalization')}
				>
					<Face className="size-3.5" strokeWidth="2" />
					<span>{$i18n.t('settings.personal.personalization.title')}</span>
				</button>
			</div>
		</nav>
	{/if}

	<div class={showPersonalization ? 'flex-1 min-w-0 min-h-0 flex flex-col' : ''}>
		<div class=" flex shrink-0 justify-between dark:text-base-300 px-4 pt-3 pb-1">
			<div class=" text-sm self-center">
				{#if showPersonalization}
					{selectedTab === 'personalization'
						? $i18n.t('settings.personal.personalization.title')
						: $i18n.t('General')}
				{:else if edit}
					{$i18n.t('Edit Folder')}
				{:else}
					{$i18n.t('Create Folder')}
				{/if}
			</div>
			<div class="flex items-center gap-1">
				{#if edit && folder && selectedTab === 'general' && ($user?.role === 'admin' || (folder.user_id === $user?.id && $user?.permissions?.sharing?.folders))}
					<AccessButton disabled={loading} on:click={() => (showAccessModal = true)} />
				{/if}
				{#if !showPersonalization}
					<button
						aria-label={$i18n.t('Close')}
						class="self-center rounded-lg py-1 text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200 px-0"
						on:click={() => {
							show = false;
						}}
					>
						<XMark className={'size-4'} />
					</button>
				{/if}
			</div>
		</div>

		{#if showPersonalization && folder && selectedTab === 'personalization'}
			<div class="flex-1 min-h-0 overflow-y-auto px-4 pb-4 dark:text-base-200">
				<FolderMemories {folder} />
			</div>
		{/if}

		<div
			class="flex flex-col md:flex-row w-full px-4 md:space-x-4 dark:text-base-200 {showPersonalization
				? 'flex-1 min-h-0 overflow-y-auto'
				: ''}"
			class:hidden={selectedTab !== 'general'}
		>
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					id="folder-form"
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="flex flex-col w-full mt-1">
						<label for="folder-name" class="block mb-1 text-xs text-base-500"
							>{$i18n.t('Folder Name')}</label
						>

						<div class="flex items-center gap-2">
							<EmojiPicker
								side="bottom"
								selected={meta.icon || null}
								onSubmit={(icon: string | null) => {
									meta = { ...meta, icon: icon ?? '' };
								}}
							>
								<button
									type="button"
									class="flex size-7 shrink-0 items-center justify-center rounded-full text-base-500 hover:bg-base-50/40 dark:text-base-400 dark:hover:bg-base-800/40"
									aria-label={$i18n.t('Change folder icon')}
									title={$i18n.t('Change folder icon')}
									disabled={loading}
								>
									{#if meta.icon}
										<Emoji shortCode={meta.icon} className="size-4" />
									{:else}
										<FolderIcon className="size-4" />
									{/if}
								</button>
							</EmojiPicker>
							<input
								id="folder-name"
								class="min-w-0 flex-1 text-sm bg-transparent placeholder:text-base-300 dark:placeholder:text-base-700 outline-hidden"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Enter folder name')}
								autocomplete="off"
							/>
						</div>
					</div>

					<div class="my-2">
						<label for="folder-description" class="mb-1 block text-xs text-base-500">
							{$i18n.t('Description')}
						</label>
						<Textarea
							id="folder-description"
							ariaLabel={$i18n.t('Description')}
							className="w-full text-sm bg-transparent placeholder:text-base-300 dark:placeholder:text-base-700 outline-hidden"
							placeholder={$i18n.t('Enter description')}
							maxSize={200}
							bind:value={data.description}
						/>
					</div>

					{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
						<div class="my-2">
							<label for="folder-system-prompt" class="mb-1 block text-xs text-base-500">
								{$i18n.t('System Prompt')}
							</label>
							<Textarea
								id="folder-system-prompt"
								ariaLabel={$i18n.t('System Prompt')}
								className="w-full text-sm bg-transparent placeholder:text-base-300 dark:placeholder:text-base-700 outline-hidden"
								placeholder={$i18n.t(
									'Write your model system prompt content here\ne.g.) You are Mario from Super Mario Bros, acting as an assistant.'
								)}
								maxSize={200}
								bind:value={data.system_prompt}
							/>
						</div>
					{/if}

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
						<div id="folder-background-image-label" class="text-xs text-base-500">
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

					<hr class=" border-base-50 dark:border-base-850/30 my-2.5 w-full" />

					<Collapsible
						title={$i18n.t('Advanced')}
						bind:open={showAdvanced}
						buttonClassName="w-full py-1 text-xs font-normal text-base-600 hover:text-base-900 dark:text-base-400 dark:hover:text-base-100 transition"
					>
						<div slot="content" class="space-y-0.5 pt-1">
							<div
								class="grid min-h-7 grid-cols-[7rem_minmax(0,1fr)] items-center gap-2 px-1 text-xs font-normal text-base-600 dark:text-base-400 sm:grid-cols-[8rem_minmax(0,1fr)]"
							>
								<ModelSettingsLabel
									label={$i18n.t('Machine')}
									description={$i18n.t(
										'Chats, files and terminals in this folder run on this machine.'
									)}
								/>
								<div class="flex min-w-0">
									<MachineMenu
										selectedMachineId={folderMachineSelection}
										onSelect={folderMachineSelection.set}
										showDirectory={false}
									>
										{#snippet trigger(selected: string | null, label: string)}
											<button
												type="button"
												class="flex w-fit max-w-full min-w-0 items-center gap-1 bg-transparent px-0.5 text-left text-xs font-normal text-base-900 dark:text-base-100"
											>
												<span class="sr-only">{$i18n.t('Machine')}: </span>
												<span class="truncate">{selected ? label : $i18n.t('None')}</span>
												<ChevronDown className="size-3 shrink-0" />
											</button>
										{/snippet}
									</MachineMenu>
								</div>
							</div>
							{#if data.machine_id}
								<div
									class="grid grid-cols-[7rem_minmax(0,1fr)] items-start gap-2 px-1 py-1 sm:grid-cols-[8rem_minmax(0,1fr)]"
								>
									<label
										for="folder-working-directory"
										class="block text-xs font-normal text-base-600 dark:text-base-400"
									>
										<ModelSettingsLabel
											label={$i18n.t('Working directory')}
											description={$i18n.t(
												'Path on the selected machine. Chats, files and terminals in this folder start here.'
											)}
										/>
									</label>
									<div class="flex min-w-0 items-center gap-2">
										<input
											id="folder-working-directory"
											class="min-w-0 flex-1 bg-transparent text-xs font-normal text-base-900 outline-hidden placeholder:text-base-400 dark:text-base-100 dark:placeholder:text-base-600"
											bind:value={data.working_directory}
											placeholder={$i18n.t('Use the machine’s default directory')}
										/>
										<button
											type="button"
											aria-label={$i18n.t('Browse directories')}
											title={$i18n.t('Browse directories')}
											class="shrink-0 text-base-500 hover:text-base-900 dark:hover:text-base-100"
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
									class="shrink-0 text-xs font-normal text-base-600 dark:text-base-400"
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
											triggerClassName="text-xs font-normal text-base-900 dark:text-base-100"
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
											class="shrink-0 py-1 text-base-500 hover:text-base-700 dark:hover:text-base-200 px-0"
											on:click={() => (data.model_ids = [])}
										>
											<XMark className="size-3" />
										</button>
									{/if}
								</div>
							</div>

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
				</form>
			</div>
		</div>

		<div
			class="flex shrink-0 justify-end gap-1.5 px-4 pt-3 pb-4 text-sm font-normal"
			class:hidden={selectedTab !== 'general'}
		>
			<button
				class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0 disabled:cursor-not-allowed"
				type="submit"
				form="folder-form"
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
	</div>
</Modal>

{#if show && edit && folder && ($user?.role === 'admin' || folder.user_id === $user?.id)}
	<FolderShareModal bind:show={showAccessModal} {folder} />
{/if}

{#if show && showDirectoryPicker && data.machine_id}
	<Modal bind:show={showDirectoryPicker} ariaLabel={$i18n.t('Choose working directory')} size="md">
		<div class="px-2 py-4">
			<div class="mb-3 flex items-center justify-between px-2 text-sm">
				<span>{$i18n.t('Choose working directory')}</span>
				<button
					type="button"
					aria-label={$i18n.t('Close')}
					class="text-base-500 hover:text-base-900 dark:hover:text-base-100"
					on:click={() => (showDirectoryPicker = false)}><XMark className="size-4" /></button
				>
			</div>
			<div class="h-[60dvh] min-h-0">
				{#await import('$lib/components/chat/FileNav.svelte') then { default: FileNav }}
					<FileNav
						machineId={data.machine_id}
						initialDirectory={data.working_directory || null}
						manageFileRequests={false}
						showTerminalDock={false}
						onSelectDirectory={(path) => {
							data.working_directory = path;
							showDirectoryPicker = false;
						}}
					/>
				{/await}
			</div>
		</div>
	</Modal>
{/if}
