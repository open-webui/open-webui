<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';

	import { config, user, tools as _tools, mobile, knowledge } from '$lib/stores';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import { createPicker } from '$lib/utils/google-drive-picker';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUp from '$lib/components/icons/DocumentArrowUp.svelte';
	import Camera from '$lib/components/icons/Camera.svelte';
	import Note from '$lib/components/icons/Note.svelte';
	import Clip from '$lib/components/icons/Clip.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import Refresh from '$lib/components/icons/Refresh.svelte';
	import Agile from '$lib/components/icons/Agile.svelte';
	import ClockRotateRight from '$lib/components/icons/ClockRotateRight.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import Chats from './InputMenu/Chats.svelte';
	import Files from './InputMenu/Files.svelte';
	import Notes from './InputMenu/Notes.svelte';
	import Knowledge from './InputMenu/Knowledge.svelte';
	import AttachWebpageModal from './AttachWebpageModal.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';

	const i18n = getContext('i18n');

	export let files = [];

	export let selectedModels: string[] = [];
	export let fileUploadCapableModels: string[] = [];

	export let screenCaptureHandler: Function;
	export let uploadFilesHandler: Function;
	export let inputFilesHandler: Function;

	export let uploadGoogleDriveHandler: Function;
	export let uploadOneDriveHandler: Function;

	export let onUpload: Function;
	export let onClose: Function;

	let show = false;
	let tab = '';

	let showAttachWebpageModal = false;

	let fileUploadEnabled = true;
	$: fileUploadEnabled =
		fileUploadCapableModels.length === selectedModels.length &&
		($user?.role === 'admin' || $user?.permissions?.chat?.file_upload);

	let webUploadEnabled = true;
	$: webUploadEnabled = $user?.role === 'admin' || ($user?.permissions?.chat?.web_upload ?? true);

	$: if (!fileUploadEnabled && files.length > 0) {
		files = [];
	}

	const detectMobile = () => {
		const userAgent = navigator.userAgent || navigator.vendor || window.opera;
		return /android|iphone|ipad|ipod|windows phone/i.test(userAgent);
	};

	const handleFileChange = (event) => {
		const inputFiles = Array.from(event.target?.files);
		if (inputFiles && inputFiles.length > 0) {
			console.log(inputFiles);
			inputFilesHandler(inputFiles);
		}
	};

	const onSelect = (item) => {
		if (files.find((f) => f.id === item.id)) {
			return;
		}
		files = [
			...files,
			{
				...item,
				status: 'processed'
			}
		];

		show = false;
	};
</script>

<AttachWebpageModal
	bind:show={showAttachWebpageModal}
	onSubmit={(e) => {
		onUpload(e);
	}}
/>

<!-- Hidden file input used to open the camera on mobile -->
<input
	id="camera-input"
	type="file"
	accept="image/*"
	capture="environment"
	on:change={handleFileChange}
	class="hidden"
/>

<Dropdown
	bind:show
	visualViewportAware
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="w-70 max-h-72 overflow-hidden transition">
			{#if tab === ''}
				<div
					class="max-h-72 overflow-y-auto overflow-x-hidden scrollbar-thin"
					in:fly={{ x: -20, duration: 150 }}
				>
					{#if $config?.features?.enable_notes ?? false}
						<Tooltip
							content={fileUploadCapableModels.length !== selectedModels.length
								? $i18n.t('Model(s) do not support file upload')
								: !fileUploadEnabled
									? $i18n.t('You do not have permission to upload files.')
									: ''}
							className="w-full"
						>
							<button
								class="flex gap-2 w-full items-center h-[1.6875rem] px-2 text-[13px] font-normal select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40 rounded-xl {!fileUploadEnabled
									? 'opacity-50'
									: ''}"
								on:click={() => {
									tab = 'notes';
								}}
							>
								<PageEdit />

								<div class="flex items-center w-full justify-between">
									<div class=" line-clamp-1">
										{$i18n.t('Attach Notes')}
									</div>

									<div class="text-gray-500">
										<ChevronRight />
									</div>
								</div>
							</button>
						</Tooltip>
					{/if}

					<Tooltip
						content={fileUploadCapableModels.length !== selectedModels.length
							? $i18n.t('Model(s) do not support file upload')
							: !fileUploadEnabled
								? $i18n.t('You do not have permission to upload files.')
								: ''}
						className="w-full"
					>
						<button
							class="flex gap-2 w-full items-center h-[1.6875rem] px-2 text-[13px] font-normal cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40 rounded-xl {!fileUploadEnabled
								? 'opacity-50'
								: ''}"
							on:click={() => {
								tab = 'chats';
							}}
						>
							<ClockRotateRight />

							<div class="flex items-center w-full justify-between">
								<div class=" line-clamp-1">
									{$i18n.t('Reference Chats')}
								</div>

								<div class="text-gray-500">
									<ChevronRight />
								</div>
							</div>
						</button>
					</Tooltip>
				</div>
			{:else if tab === 'knowledge'}
				<div class="flex max-h-72 flex-col overflow-hidden" in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full shrink-0 justify-between gap-2 items-center h-[1.6875rem] px-2 text-[13px] font-normal select-none cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Knowledge')}
							</div>
						</div>
					</button>

					<Knowledge {onSelect} />
				</div>
			{:else if tab === 'notes'}
				<div class="flex max-h-72 flex-col overflow-hidden" in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full shrink-0 justify-between gap-2 items-center h-[1.6875rem] px-2 text-[13px] font-normal select-none cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Notes')}
							</div>
						</div>
					</button>

					<Notes {onSelect} />
				</div>
			{:else if tab === 'files'}
				<div class="flex max-h-72 flex-col overflow-hidden" in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full shrink-0 justify-between gap-2 items-center h-[1.6875rem] px-2 text-[13px] font-normal select-none cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Files')}
							</div>
						</div>
					</button>

					<Files {onSelect} />
				</div>
			{:else if tab === 'chats'}
				<div class="flex max-h-72 flex-col overflow-hidden" in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full shrink-0 justify-between gap-2 items-center h-[1.6875rem] px-2 text-[13px] font-normal select-none cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Chats')}
							</div>
						</div>
					</button>

					<Chats {onSelect} />
				</div>
			{:else if tab === 'microsoft_onedrive'}
				<div in:fly={{ x: 20, duration: 150 }}>
					<button
						class="flex w-full justify-between gap-2 items-center h-[1.6875rem] px-2 text-[13px] font-normal select-none cursor-pointer rounded-xl hover:bg-gray-50/40 dark:hover:bg-gray-800/40"
						on:click={() => {
							tab = '';
						}}
					>
						<ChevronLeft />

						<div class="flex items-center w-full justify-between">
							<div>
								{$i18n.t('Microsoft OneDrive')}
							</div>
						</div>
					</button>

					{#if $config?.features?.enable_onedrive_personal}
						<button
							class="flex w-full gap-2 items-center h-[1.6875rem] px-2 text-[13px] font-normal select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40 rounded-xl text-left"
							type="button"
							on:click={() => {
								uploadOneDriveHandler('personal');
								show = false;
							}}
						>
							<div class="flex flex-col">
								<div class="line-clamp-1">{$i18n.t('Microsoft OneDrive (personal)')}</div>
							</div>
						</button>
					{/if}

					{#if $config?.features?.enable_onedrive_business}
						<button
							class="flex w-full gap-2 items-center h-[1.6875rem] px-2 text-[13px] font-normal select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40 rounded-xl text-left"
							type="button"
							on:click={() => {
								uploadOneDriveHandler('organizations');
								show = false;
							}}
						>
							<div class="line-clamp-1">
								{$i18n.t('Microsoft OneDrive (work/school)')}
							</div>
						</button>
					{/if}
				</div>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
