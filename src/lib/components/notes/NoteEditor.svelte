<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';

	const i18n = getContext('i18n');

	import { toast } from 'svelte-sonner';

	import { config, settings, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';

	import { compressImage } from '$lib/utils';

	import dayjs from '$lib/dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(calendar);
	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	async function loadLocale(locales) {
		for (const locale of locales) {
			try {
				dayjs.locale(locale);
				break; // Stop after successfully loading the first available locale
			} catch (error) {
				console.error(`Could not load locale '${locale}':`, error);
			}
		}
	}

	// Assuming $i18n.languages is an array of language codes
	$: loadLocale($i18n.languages);

	import { getNoteById, updateNoteById } from '$lib/apis/notes';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Spinner from '../common/Spinner.svelte';
	import MicSolid from '../icons/MicSolid.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	import Calendar from '../icons/Calendar.svelte';
	import Users from '../icons/Users.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { uploadFile } from '$lib/apis/files';
	import Image from '../common/Image.svelte';
	import FileItem from '../common/FileItem.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import RecordMenu from './RecordMenu.svelte';

	export let id: null | string = null;

	let note = {
		title: '',
		data: {
			content: {
				json: null,
				html: '',
				md: ''
			},
			files: null
		},
		meta: null,
		access_control: null
	};

	let files = [];
	let recording = false;
	let displayMediaRecord = false;

	let dragged = false;
	let loading = false;

	const init = async () => {
		loading = true;
		const res = await getNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			note = res;
			files = res.data.files || [];
		} else {
			toast.error($i18n.t('Note not found'));
			goto('/notes');
			return;
		}

		loading = false;
	};

	let debounceTimeout: NodeJS.Timeout | null = null;

	const changeDebounceHandler = () => {
		console.log('debounce');
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(async () => {
			const res = await updateNoteById(localStorage.token, id, {
				...note,
				title: note.title === '' ? $i18n.t('Untitled') : note.title
			}).catch((e) => {
				toast.error(`${e}`);
			});
		}, 200);
	};

	$: if (note) {
		changeDebounceHandler();
	}

	$: if (id) {
		init();
	}

	const uploadFileHandler = async (file) => {
		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: 'uploading',
			size: file.size,
			error: '',
			itemId: tempItemId
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		files = [...files, fileItem];

		try {
			// During the file upload, file content is automatically extracted.
			const uploadedFile = await uploadFile(localStorage.token, file);

			if (uploadedFile) {
				console.log('File upload completed:', {
					id: uploadedFile.id,
					name: fileItem.name,
					collection: uploadedFile?.meta?.collection_name
				});

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
				}

				fileItem.status = 'uploaded';
				fileItem.file = uploadedFile;
				fileItem.id = uploadedFile.id;
				fileItem.collection_name =
					uploadedFile?.meta?.collection_name || uploadedFile?.collection_name;

				fileItem.url = `${WEBUI_API_BASE_URL}/files/${uploadedFile.id}`;

				files = files;
			} else {
				files = files.filter((item) => item?.itemId !== tempItemId);
			}
		} catch (e) {
			toast.error(`${e}`);
			files = files.filter((item) => item?.itemId !== tempItemId);
		}

		if (files.length > 0) {
			note.data.files = files;
		} else {
			note.data.files = null;
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		console.log('Input files handler called with:', inputFiles);
		inputFiles.forEach((file) => {
			console.log('Processing file:', {
				name: file.name,
				type: file.type,
				size: file.size,
				extension: file.name.split('.').at(-1)
			});

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				console.log('File exceeds max size limit:', {
					fileSize: file.size,
					maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
				});
				toast.error(
					$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
						maxSize: $config?.file?.max_size
					})
				);
				return;
			}

			if (
				['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/avif'].includes(file['type'])
			) {
				let reader = new FileReader();
				reader.onload = async (event) => {
					let imageUrl = event.target.result;

					if ($settings?.imageCompression ?? false) {
						const width = $settings?.imageCompressionSize?.width ?? null;
						const height = $settings?.imageCompressionSize?.height ?? null;

						if (width || height) {
							imageUrl = await compressImage(imageUrl, width, height);
						}
					}

					files = [
						...files,
						{
							type: 'image',
							url: `${imageUrl}`
						}
					];
					note.data.files = files;
				};
				reader.readAsDataURL(file);
			} else {
				uploadFileHandler(file);
			}
		});
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being dragged.
		if (e.dataTransfer?.types?.includes('Files')) {
			dragged = true;
		} else {
			dragged = false;
		}
	};

	const onDragLeave = () => {
		dragged = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		console.log(e);

		if (e.dataTransfer?.files) {
			const inputFiles = Array.from(e.dataTransfer?.files);
			if (inputFiles && inputFiles.length > 0) {
				console.log(inputFiles);
				inputFilesHandler(inputFiles);
			}
		}

		dragged = false;
	};

	onMount(async () => {
		await tick();

		const dropzoneElement = document.getElementById('note-editor');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		console.log('destroy');
		const dropzoneElement = document.getElementById('note-editor');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});
</script>

<FilesOverlay show={dragged} />

<div class="relative flex-1 w-full h-full flex justify-center" id="note-editor">
	{#if loading}
		<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
			<div class="m-auto">
				<Spinner />
			</div>
		</div>
	{:else}
		<div class=" w-full flex flex-col {loading ? 'opacity-20' : ''}">
			<div class="shrink-0 w-full flex justify-between items-center px-4.5 pt-1 mb-1.5">
				<div class="w-full">
					<input
						class="w-full text-2xl font-medium bg-transparent outline-hidden"
						type="text"
						bind:value={note.title}
						placeholder={$i18n.t('Title')}
						required
					/>
				</div>
			</div>

			<div class=" mb-2.5 px-3.5">
				<div class="flex gap-1 items-center text-xs font-medium text-gray-500 dark:text-gray-500">
					<button class=" flex items-center gap-1 w-fit py-1 px-1.5 rounded-lg">
						<Calendar className="size-3.5" strokeWidth="2" />

						<span>{dayjs(note.created_at / 1000000).calendar()}</span>
					</button>

					<button class=" flex items-center gap-1 w-fit py-1 px-1.5 rounded-lg">
						<Users className="size-3.5" strokeWidth="2" />

						<span> You </span>
					</button>
				</div>
			</div>

			<div class=" flex-1 w-full h-full overflow-auto px-4 pb-5">
				{#if files}
					<div class="mb-3.5 mt-1.5 w-full flex gap-1 flex-wrap z-40">
						{#each files as file, fileIdx}
							<div class="w-fit">
								{#if file.type === 'image'}
									<Image
										src={file.url}
										imageClassName=" max-h-96 rounded-lg"
										dismissible={true}
										onDismiss={() => {
											files = files.filter((item, idx) => idx !== fileIdx);
											note.data.files = files.length > 0 ? files : null;
										}}
									/>
								{:else}
									<FileItem
										item={file}
										dismissible={true}
										url={file.url}
										name={file.name}
										type={file.type}
										size={file?.size}
										loading={file.status === 'uploading'}
										colorClassName="bg-white dark:bg-gray-850 "
										on:dismiss={() => {
											files = files.filter((item) => item?.id !== file.id);
											note.data.files = files.length > 0 ? files : null;
										}}
									/>
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				<RichTextInput
					className="input-prose-sm px-0.5"
					bind:value={note.data.content.json}
					placeholder={$i18n.t('Write something...')}
					json={true}
					onChange={(content) => {
						note.data.html = content.html;
						note.data.md = content.md;
					}}
				/>
			</div>
		</div>
	{/if}
</div>

<div class="absolute bottom-0 right-0 p-5 max-w-full flex justify-end">
	<div
		class="flex gap-0.5 justify-end w-full {$showSidebar && recording
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		{#if recording}
			<div class="flex-1 w-full">
				<VoiceRecording
					bind:recording
					className="p-1 w-full max-w-full"
					transcribe={false}
					displayMedia={displayMediaRecord}
					onCancel={() => {
						recording = false;
						displayMediaRecord = false;
					}}
					onConfirm={(data) => {
						if (data?.file) {
							uploadFileHandler(data?.file);
						}

						recording = false;
						displayMediaRecord = false;
					}}
				/>
			</div>
		{:else}
			<RecordMenu
				onRecord={async () => {
					displayMediaRecord = false;

					try {
						let stream = await navigator.mediaDevices
							.getUserMedia({ audio: true })
							.catch(function (err) {
								toast.error(
									$i18n.t(`Permission denied when accessing microphone: {{error}}`, {
										error: err
									})
								);
								return null;
							});

						if (stream) {
							recording = true;
							const tracks = stream.getTracks();
							tracks.forEach((track) => track.stop());
						}
						stream = null;
					} catch {
						toast.error($i18n.t('Permission denied when accessing microphone'));
					}
				}}
				onCaptureAudio={async () => {
					displayMediaRecord = true;

					recording = true;
				}}
			>
				<button
					class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
					type="button"
				>
					<MicSolid className="size-4.5" />
				</button>
			</RecordMenu>
		{/if}
	</div>
</div>
