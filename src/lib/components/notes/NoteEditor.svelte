<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import jsPDF from 'jspdf';
	import html2canvas from 'html2canvas-pro';

	const i18n = getContext('i18n');

	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';

	import { config, models, settings, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';

	import { compressImage, copyToClipboard, splitStream } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { uploadFile } from '$lib/apis/files';

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

	import { deleteNoteById, getNoteById, updateNoteById } from '$lib/apis/notes';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Spinner from '../common/Spinner.svelte';
	import MicSolid from '../icons/MicSolid.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Calendar from '../icons/Calendar.svelte';
	import Users from '../icons/Users.svelte';

	import Image from '../common/Image.svelte';
	import FileItem from '../common/FileItem.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import RecordMenu from './RecordMenu.svelte';
	import NoteMenu from './Notes/NoteMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
	import SparklesSolid from '../icons/SparklesSolid.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Bars3BottomLeft from '../icons/Bars3BottomLeft.svelte';
	import ArrowUturnLeft from '../icons/ArrowUturnLeft.svelte';
	import ArrowUturnRight from '../icons/ArrowUturnRight.svelte';
	import Sidebar from '../common/Sidebar.svelte';
	import ArrowRight from '../icons/ArrowRight.svelte';
	import Cog6 from '../icons/Cog6.svelte';
	import { chatCompletion } from '$lib/apis/openai';

	export let id: null | string = null;

	let note = null;

	const newNote = {
		title: '',
		data: {
			content: {
				json: null,
				html: '',
				md: ''
			},
			versions: [],
			files: null
		},
		meta: null,
		access_control: null
	};

	let files = [];

	let versionIdx = null;
	let selectedModelId = null;

	let recording = false;
	let displayMediaRecord = false;

	let showSettings = false;
	let showDeleteConfirm = false;

	let dragged = false;
	let loading = false;

	let enhancing = false;
	let streaming = false;

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
			goto('/');
			return;
		}

		loading = false;
	};

	let debounceTimeout: NodeJS.Timeout | null = null;

	const changeDebounceHandler = () => {
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(async () => {
			if (!note || enhancing || versionIdx !== null) {
				return;
			}

			console.log('Saving note:', note);

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

	function areContentsEqual(a, b) {
		return JSON.stringify(a) === JSON.stringify(b);
	}

	function insertNoteVersion(note) {
		const current = {
			json: note.data.content.json,
			html: note.data.content.html,
			md: note.data.content.md
		};
		const lastVersion = note.data.versions?.at(-1);

		if (!lastVersion || !areContentsEqual(lastVersion, current)) {
			note.data.versions = (note.data.versions ?? []).concat(current);
			return true;
		}
		return false;
	}

	async function enhanceNoteHandler() {
		if (selectedModelId === '') {
			toast.error($i18n.t('Please select a model.'));
			return;
		}

		const model = $models
			.filter((model) => model.id === selectedModelId && !(model?.info?.meta?.hidden ?? false))
			.find((model) => model.id === selectedModelId);

		if (!model) {
			selectedModelId = '';
			return;
		}

		enhancing = true;

		insertNoteVersion(note);
		await enhanceCompletionHandler(model);

		enhancing = false;
		versionIdx = null;
	}

	function setContentByVersion(versionIdx) {
		if (!note.data.versions?.length) return;
		let idx = versionIdx;

		if (idx === null) idx = note.data.versions.length - 1; // latest
		const v = note.data.versions[idx];

		note.data.content.json = v.json;
		note.data.content.html = v.html;
		note.data.content.md = v.md;

		if (versionIdx === null) {
			const lastVersion = note.data.versions.at(-1);
			const currentContent = note.data.content;

			if (areContentsEqual(lastVersion, currentContent)) {
				// remove the last version
				note.data.versions = note.data.versions.slice(0, -1);
			}
		}
	}

	// Navigation
	function versionNavigateHandler(direction) {
		if (!note.data.versions || note.data.versions.length === 0) return;

		if (versionIdx === null) {
			// Get latest snapshots
			const lastVersion = note.data.versions.at(-1);
			const currentContent = note.data.content;

			if (!areContentsEqual(lastVersion, currentContent)) {
				// If the current content is different from the last version, insert a new version
				insertNoteVersion(note);
				versionIdx = note.data.versions.length - 1;
			} else {
				versionIdx = note.data.versions.length;
			}
		}

		if (direction === 'prev') {
			if (versionIdx > 0) versionIdx -= 1;
		} else if (direction === 'next') {
			if (versionIdx < note.data.versions.length - 1) versionIdx += 1;
			else versionIdx = null; // Reset to latest

			if (versionIdx === note.data.versions.length - 1) {
				// If we reach the latest version, reset to null
				versionIdx = null;
			}
		}

		setContentByVersion(versionIdx);
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

	const downloadHandler = async (type) => {
		console.log('downloadHandler', type);
		if (type === 'md') {
			const blob = new Blob([note.data.content.md], { type: 'text/markdown' });
			saveAs(blob, `${note.title}.md`);
		} else if (type === 'pdf') {
			await downloadPdf(note);
		}
	};

	const downloadPdf = async (note) => {
		try {
			// Define a fixed virtual screen size
			const virtualWidth = 1024; // Fixed width (adjust as needed)
			const virtualHeight = 1400; // Fixed height (adjust as needed)

			// STEP 1. Get a DOM node to render
			const html = note.data?.content?.html ?? '';
			let node;
			if (html instanceof HTMLElement) {
				node = html;
			} else {
				// If it's HTML string, render to a temporary hidden element
				node = document.createElement('div');
				node.innerHTML = html;
				document.body.appendChild(node);
			}

			// Render to canvas with predefined width
			const canvas = await html2canvas(node, {
				useCORS: true,
				scale: 2, // Keep at 1x to avoid unexpected enlargements
				width: virtualWidth, // Set fixed virtual screen width
				windowWidth: virtualWidth, // Ensure consistent rendering
				windowHeight: virtualHeight
			});

			// Remove hidden node if needed
			if (!(html instanceof HTMLElement)) {
				document.body.removeChild(node);
			}

			const imgData = canvas.toDataURL('image/png');

			// A4 page settings
			const pdf = new jsPDF('p', 'mm', 'a4');
			const imgWidth = 210; // A4 width in mm
			const pageHeight = 297; // A4 height in mm

			// Maintain aspect ratio
			const imgHeight = (canvas.height * imgWidth) / canvas.width;
			let heightLeft = imgHeight;
			let position = 0;

			pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
			heightLeft -= pageHeight;

			// Handle additional pages
			while (heightLeft > 0) {
				position -= pageHeight;
				pdf.addPage();

				pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
				heightLeft -= pageHeight;
			}

			pdf.save(`${note.title}.pdf`);
		} catch (error) {
			console.error('Error generating PDF', error);

			toast.error(`${error}`);
		}
	};

	const deleteNoteHandler = async (id) => {
		const res = await deleteNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Note deleted successfully'));
			goto('/notes');
		} else {
			toast.error($i18n.t('Failed to delete note'));
		}
	};

	const scrollToBottom = () => {
		const element = document.getElementById('note-content-container');

		if (element) {
			element.scrollTop = element?.scrollHeight;
		}
	};

	const enhanceCompletionHandler = async (model) => {
		let enhancedContent = {
			json: null,
			html: '',
			md: ''
		};

		const systemPrompt = `Enhance existing notes using additional context provided from audio transcription or uploaded file content. Your task is to make the notes more useful and comprehensive by incorporating relevant information from the provided context.

Input will be provided within <notes> and <context> XML tags, providing a structure for the existing notes and context respectively.

# Output Format

Provide the enhanced notes in markdown format. Use markdown syntax for headings, lists, and emphasis to improve clarity and presentation. Ensure that all integrated content from the context is accurately reflected. Return only the markdown formatted note.
`;

		const [res, controller] = await chatCompletion(
			localStorage.token,
			{
				model: model.id,
				stream: true,
				messages: [
					{
						role: 'system',
						content: systemPrompt
					},
					{
						role: 'user',
						content:
							`<notes>${note.data.content.md}</notes>` +
							(files && files.length > 0
								? `\n<context>${files.map((file) => `${file.name}: ${file?.file?.data?.content ?? 'Could not extract content'}\n`).join('')}</context>`
								: '')
					}
				]
			},
			`${WEBUI_BASE_URL}/api`
		);

		await tick();

		streaming = true;

		if (res && res.ok) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done) {
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								console.log(line);
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if (data.choices && data.choices.length > 0) {
									const choice = data.choices[0];
									if (choice.delta && choice.delta.content) {
										enhancedContent.md += choice.delta.content;
										enhancedContent.html = marked.parse(enhancedContent.md);

										note.data.content.md = enhancedContent.md;
										note.data.content.html = enhancedContent.html;
										note.data.content.json = null;

										scrollToBottom();
									}
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}
			}
		}

		streaming = false;
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

		if ($settings?.models) {
			selectedModelId = $settings?.models[0];
		} else if ($config?.default_models) {
			selectedModelId = $config?.default_models.split(',')[0];
		} else {
			selectedModelId = '';
		}

		if (selectedModelId) {
			const model = $models
				.filter((model) => model.id === selectedModelId && !(model?.info?.meta?.hidden ?? false))
				.find((model) => model.id === selectedModelId);

			if (!model) {
				selectedModelId = '';
			}
		}

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

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete note?')}
	on:confirm={() => {
		deleteNoteHandler(note.id);
		showDeleteConfirm = false;
	}}
>
	<div class=" text-sm text-gray-500">
		{$i18n.t('This will delete')} <span class="  font-semibold">{note.title}</span>.
	</div>
</DeleteConfirmDialog>

<div class="relative flex-1 w-full h-full flex justify-center" id="note-editor">
	<Sidebar bind:show={showSettings} className=" bg-white dark:bg-gray-900" width="300px">
		<div class="flex flex-col px-5 py-3 text-sm">
			<div class="flex justify-between items-center mb-2">
				<div class=" font-medium text-base">Settings</div>

				<div class=" translate-x-1.5">
					<button
						class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
						on:click={() => {
							showSettings = !showSettings;
						}}
					>
						<ArrowRight className="size-3" strokeWidth="2.5" />
					</button>
				</div>
			</div>

			<div class="mt-1">
				<div>
					<div class=" text-xs font-medium mb-1">Model</div>

					<div class="w-full">
						<select
							class="w-full bg-transparent text-sm outline-hidden"
							bind:value={selectedModelId}
						>
							<option value="" class="bg-gray-50 dark:bg-gray-700" disabled>
								{$i18n.t('Select a model')}
							</option>
							{#each $models.filter((model) => !(model?.info?.meta?.hidden ?? false)) as model}
								<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
							{/each}
						</select>
					</div>
				</div>
			</div>
		</div>
	</Sidebar>

	{#if loading}
		<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
			<div class="m-auto">
				<Spinner />
			</div>
		</div>
	{:else}
		<div class=" w-full flex flex-col {loading ? 'opacity-20' : ''}">
			<div class="shrink-0 w-full flex justify-between items-center px-4.5 mb-1.5">
				<div class="w-full flex items-center">
					<input
						class="w-full text-2xl font-medium bg-transparent outline-hidden"
						type="text"
						bind:value={note.title}
						placeholder={$i18n.t('Title')}
						required
					/>

					<div class="flex items-center gap-2 translate-x-1">
						{#if note.data?.versions?.length > 0}
							<div>
								<div class="flex items-center gap-0.5 self-center min-w-fit" dir="ltr">
									<button
										class="self-center p-1 hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black rounded-md transition disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
										on:click={() => {
											versionNavigateHandler('prev');
										}}
										disabled={(versionIdx === null && note.data.versions.length === 0) ||
											versionIdx === 0}
									>
										<ArrowUturnLeft className="size-4" />
									</button>

									<button
										class="self-center p-1 hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black rounded-md transition disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
										on:click={() => {
											versionNavigateHandler('next');
										}}
										disabled={versionIdx >= note.data.versions.length || versionIdx === null}
									>
										<ArrowUturnRight className="size-4" />
									</button>
								</div>
							</div>
						{/if}

						<NoteMenu
							onDownload={(type) => {
								downloadHandler(type);
							}}
							onCopyToClipboard={async () => {
								const res = await copyToClipboard(note.data.content.md).catch((error) => {
									toast.error(`${error}`);
									return null;
								});

								if (res) {
									toast.success($i18n.t('Copied to clipboard'));
								}
							}}
							onDelete={() => {
								showDeleteConfirm = true;
							}}
						>
							<EllipsisHorizontal className="size-5" />
						</NoteMenu>

						<button
							class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
							on:click={() => {
								showSettings = !showSettings;
							}}
						>
							<Cog6 />
						</button>
					</div>
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

			<div
				class=" flex-1 w-full h-full overflow-auto px-4 pb-20 relative"
				id="note-content-container"
			>
				{#if enhancing}
					<div
						class="w-full h-full fixed top-0 left-0 {streaming
							? ''
							: ' backdrop-blur-xs  bg-white/10 dark:bg-gray-900/10'} flex items-center justify-center z-10 cursor-not-allowed"
					></div>
				{/if}

				{#if files && files.length > 0}
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
					html={note.data?.content?.html}
					json={true}
					editable={versionIdx === null && !enhancing}
					onChange={(content) => {
						note.data.content.html = content.html;
						note.data.content.md = content.md;
					}}
				/>
			</div>
		</div>
	{/if}
</div>

<div
	class="absolute z-20 bottom-0 right-0 p-5 max-w-full {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} w-full flex justify-end"
>
	<div class="flex gap-1 justify-between w-full max-w-full">
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
				onUpload={async () => {
					const input = document.createElement('input');
					input.type = 'file';
					input.accept = 'audio/*';
					input.multiple = false;
					input.click();

					input.onchange = async (e) => {
						const files = e.target.files;

						if (files && files.length > 0) {
							await uploadFileHandler(files[0]);
						}
					};
				}}
			>
				<Tooltip content={$i18n.t('Record')} placement="top">
					<button
						class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 bg-white dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
						type="button"
					>
						<MicSolid className="size-4.5" />
					</button>
				</Tooltip>
			</RecordMenu>

			<div
				class="cursor-pointer flex gap-0.5 rounded-full border border-gray-50 dark:border-gray-850 dark:bg-gray-850 transition shadow-xl"
			>
				<!-- <Tooltip content={$i18n.t('My Notes')} placement="top">
					<button
						class="p-2 size-8.5 flex justify-center items-center {selectedVersion === 'note'
							? 'bg-gray-100 dark:bg-gray-800 '
							: ' hover:bg-gray-50 dark:hover:bg-gray-800'}  rounded-full transition shrink-0"
						type="button"
						on:click={() => {
							selectedVersion = 'note';
							versionToggleHandler();
						}}
					>
						<Bars3BottomLeft />
					</button>
				</Tooltip> -->

				<Tooltip content={$i18n.t('Enhance')} placement="top">
					<button
						class="{enhancing
							? 'p-2'
							: 'p-2.5'} flex justify-center items-center hover:bg-gray-50 dark:hover:bg-gray-800 rounded-full transition shrink-0"
						on:click={() => {
							enhanceNoteHandler();
						}}
						disabled={enhancing}
						type="button"
					>
						{#if enhancing}
							<Spinner className="size-5" />
						{:else}
							<SparklesSolid />
						{/if}
					</button>
				</Tooltip>
			</div>
		{/if}
	</div>
</div>
