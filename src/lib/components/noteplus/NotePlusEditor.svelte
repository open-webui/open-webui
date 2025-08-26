<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { v4 as uuidv4 } from 'uuid';
	import heic2any from 'heic2any';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;
	
	import TurndownService from 'turndown';
	import { gfm } from '@joplin/turndown-plugin-gfm';
	
	const turndownService = new TurndownService({
		headingStyle: 'atx',
		hr: '---',
		codeBlockStyle: 'fenced'
	});
	turndownService.escape = (string) => string;
	turndownService.use(gfm);

	import jsPDF from 'jspdf';
	import html2canvas from 'html2canvas-pro';

	const i18n = getContext('i18n');

	import { marked } from 'marked';
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';

	import dayjs from '$lib/dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(calendar);
	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { compressImage, copyToClipboard, splitStream } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { uploadFile } from '$lib/apis/files';
	import { chatCompletion, generateOpenAIChatCompletion } from '$lib/apis/openai';

	import {
		config,
		mobile,
		models,
		settings,
		showSidebar,
		socket,
		user,
		WEBUI_NAME
	} from '$lib/stores';

	// import NotePanel from '$lib/components/notes/NotePanel.svelte';

	import Controls from '$lib/components/noteplus/NotePlusEditor/Controls.svelte';
	import Chat from '$lib/components/noteplus/NotePlusEditor/Chat.svelte';

	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';

	async function loadLocale(locales) {
		for (const locale of locales) {
			try {
				dayjs.locale(locale);
				break;
			} catch (error) {
				console.error(`Could not load locale '${locale}':`, error);
			}
		}
	}

	$: loadLocale($i18n.languages);

	import { 
		deleteNotePlusById, 
		getNotePlusById, 
		updateNotePlusById, 
		generateNotePlusTitle, 
		generateNotePlusCategory 
	} from '$lib/apis/noteplus';

	import RichTextInput from '../common/RichTextInput.svelte';
	import Spinner from '../common/Spinner.svelte';
	import MicSolid from '../icons/MicSolid.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ChatBubbleOval from '../icons/ChatBubbleOval.svelte';

	import Calendar from '../icons/Calendar.svelte';
	import Users from '../icons/Users.svelte';

	import Image from '../common/Image.svelte';
	import FileItem from '../common/FileItem.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import RecordMenu from '../notes/RecordMenu.svelte';
	import NotePlusMenu from './NotesPlus/NotePlusMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
	import SparklesSolid from '../icons/SparklesSolid.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Bars3BottomLeft from '../icons/Bars3BottomLeft.svelte';
	import ArrowUturnLeft from '../icons/ArrowUturnLeft.svelte';
	import ArrowUturnRight from '../icons/ArrowUturnRight.svelte';
	import Sidebar from '../icons/Sidebar.svelte';
	import ArrowRight from '../icons/ArrowRight.svelte';
	import Cog6 from '../icons/Cog6.svelte';
	import AiMenu from './AIMenu.svelte';
	import AdjustmentsHorizontalOutline from '../icons/AdjustmentsHorizontalOutline.svelte';
	import Folder from '../icons/Folder.svelte';

	export let id: null | string = null;

	let editor = null;
	let note = null;

	const newNote = {
		title: '',
		data: {
			content: {
				json: {},
				html: '',
				md: ''
			},
			versions: [],
			files: null
		},
		category_major: 'General',
		category_middle: 'Notes',
		category_minor: 'Default',
		meta: null,
		access_control: {}
	};

	let files = [];
	let messages = [];

	let wordCount = 0;
	let charCount = 0;

	let versionIdx = null;
	let selectedModelId = null;

	let recording = false;
	let displayMediaRecord = false;

	let showPanel = false;
	let selectedPanel = 'chat';

	let selectedContent = null;

	let showDeleteConfirm = false;
	let showAccessControlModal = false;

	let ignoreBlur = false;
	let titleInputFocused = false;
	let titleGenerating = false;
	let categoryGenerating = false;

	let dragged = false;
	let loading = false;

	let editing = false;
	let streaming = false;

	let stopResponseFlag = false;

	let inputElement = null;

	// Category fields
	let showCategoryInput = false;

	const getWordCount = (text) => {
		text = text.trim();
		return text === '' ? 0 : text.split(/\s+/).length;
	};

	const getCharCount = (text) => {
		return text.length;
	};

	const countTokens = (text) => {
		return getCharCount(text) / 4;
	};

	const changeDebounceHandler = async () => {
		console.log('changeDebounceHandler');
		console.log(note);
		changeDebounceTimer && clearTimeout(changeDebounceTimer);
		changeDebounceTimer = setTimeout(async () => {
			saveHandler();
		}, 500);
	};

	let changeDebounceTimer = null;

	const getWords = () => {
		if (note?.data?.content?.md) {
			wordCount = getWordCount(note.data.content.md);
			charCount = getCharCount(note.data.content.md);
		} else {
			wordCount = 0;
			charCount = 0;
		}
	};

	const saveHandler = async () => {
		changeDebounceTimer && clearTimeout(changeDebounceTimer);

		// Get content from editor if available, otherwise use existing note data
		let content, contentHTML, contentJSON;
		
		if (editor) {
			contentHTML = editor.getHTML();
			contentJSON = editor.getJSON();
			// Convert HTML to Markdown using TurndownService
			content = turndownService.turndown(contentHTML);
		} else {
			// Use existing note data
			content = note.data?.content?.md || '';
			contentHTML = note.data?.content?.html || '';
			contentJSON = note.data?.content?.json || {};
		}

		if (id) {
			try {
				const res = await updateNotePlusById(localStorage.token, id, {
					title: note.title || '',
					data: {
						...note.data,
						content: {
							json: contentJSON,
							html: contentHTML,
							md: content
						}
					},
					category_major: note.category_major || 'General',
					category_middle: note.category_middle || 'Notes',
					category_minor: note.category_minor || 'Default',
					meta: note.meta,
					access_control: note.access_control
				});
				
				if (res) {
					console.log('Note saved successfully:', res.id);
					// Dispatch event for category tree refresh
					window.dispatchEvent(new CustomEvent('noteplus:updated'));
				}
			} catch (error) {
				console.error('Error saving note:', error);
				toast.error('Failed to save note');
			}
		}

		getWords();
	};

	const generateTitleHandler = async () => {
		const content = note.data.content.md;

		if (!content || content.trim() === '') {
			toast.error($i18n.t('Please add some content first'));
			return;
		}

		if (!selectedModelId || selectedModelId === '') {
			toast.error($i18n.t('Model not selected'));
			return;
		}

		titleGenerating = true;

		try {
			const DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE = `### Task:
Generate a concise, 3-5 word title with an emoji summarizing the content in the content's primary language.
### Guidelines:
- The title should clearly represent the main theme or subject of the content.
- Keep the title focused on the content rather than instructions.
- Choose an emoji that best represents the overall theme.
- Only output the title without quotes or additional explanation.
- If unsure about the primary language, use English.
### Content:
{{CONTENT}}`;

			const prompt = DEFAULT_TITLE_GENERATION_PROMPT_TEMPLATE.replace('{{CONTENT}}', content);

			const res = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					model: selectedModelId,
					messages: [
						{
							role: 'user',
							content: prompt
						}
					],
					stream: false
				},
				`${WEBUI_BASE_URL}/api`
			);
			
			if (res) {
				console.log('Title generation response:', res);
				const generatedTitle = res?.choices?.[0]?.message?.content || '';
				
				if (generatedTitle) {
					note.title = generatedTitle.trim();
				} else {
					toast.error($i18n.t('Failed to generate title'));
				}
			}
		} catch (error) {
			console.error('Title generation error:', error);
			toast.error($i18n.t('Failed to generate title'));
		} finally {
			titleGenerating = false;
			await tick();
			changeDebounceHandler();
		}
	};

	const generateCategoryHandler = async () => {
		const content = note.data.content.md;
		const title = note.title;

		if (!content || content.trim() === '') {
			toast.error($i18n.t('Please add some content first'));
			return;
		}

		if (!selectedModelId || selectedModelId === '') {
			toast.error($i18n.t('Model not selected'));
			return;
		}

		categoryGenerating = true;

		try {
			const DEFAULT_CATEGORY_GENERATION_PROMPT_TEMPLATE = `### Task:
Categorize the following note content into a 3-level hierarchy.
### Guidelines:
- Major category: High-level domain (e.g., Technology, Business, Personal, Education, Health)
- Middle category: Specific area within the domain (e.g., Programming, Marketing, Journal, Course, Fitness)
- Minor category: Detailed classification (e.g., Python, SEO, Daily, Mathematics, Workout)
- Output format: Return ONLY a JSON object with this exact structure:
{
  "major": "category name",
  "middle": "category name",
  "minor": "category name"
}
- Use English for category names.
### Title:
{{TITLE}}
### Content:
{{CONTENT}}`;

			const prompt = DEFAULT_CATEGORY_GENERATION_PROMPT_TEMPLATE
				.replace('{{TITLE}}', title || 'Untitled')
				.replace('{{CONTENT}}', content);

			const res = await generateOpenAIChatCompletion(
				localStorage.token,
				{
					model: selectedModelId,
					messages: [
						{
							role: 'user',
							content: prompt
						}
					],
					stream: false
				},
				`${WEBUI_BASE_URL}/api`
			);
			
			if (res) {
				console.log('Category generation response:', res);
				
				// Try to parse JSON response
				let categoryData;
				const responseContent = res?.choices?.[0]?.message?.content || '';
				
				try {
					// Extract JSON from the response
					const jsonMatch = responseContent.match(/\{[\s\S]*\}/);
					if (jsonMatch) {
						categoryData = JSON.parse(jsonMatch[0]);
					}
				} catch (jsonError) {
					// If JSON parsing fails, try pipe-separated format
					console.log('JSON parsing failed, trying pipe-separated format');
					if (responseContent.includes('|')) {
						const categories = responseContent.split('|');
						categoryData = {
							major: categories[0]?.trim() || 'General',
							middle: categories[1]?.trim() || 'Notes',
							minor: categories[2]?.trim() || 'Default'
						};
					}
				}

				if (categoryData) {
					note.category_major = categoryData.major || 'General';
					note.category_middle = categoryData.middle || 'Notes';
					note.category_minor = categoryData.minor || 'Default';
				} else {
					// Fallback to default categories
					note.category_major = 'General';
					note.category_middle = 'Notes';
					note.category_minor = 'Default';
					toast.error($i18n.t('Failed to parse category data, using defaults'));
				}
			}
		} catch (error) {
			console.error('Category generation error:', error);
			toast.error($i18n.t('Failed to generate categories'));
		} finally {
			categoryGenerating = false;
			await tick();
			changeDebounceHandler();
		}
	};

	const stopResponseHandler = async () => {
		stopResponseFlag = true;
		console.log('stopResponse', stopResponseFlag);
	};

	async function enhanceNoteHandler() {
		if (!selectedModelId || selectedModelId === '') {
			toast.error($i18n.t('Please select a model'));
			return;
		}

		const model = $models
			.filter((model) => model.id === selectedModelId && !(model?.info?.meta?.hidden ?? false))
			.find((model) => model.id === selectedModelId);

		if (!model) {
			selectedModelId = '';
			return;
		}

		editing = true;
		await enhanceCompletionHandler(model);
		editing = false;
	}

	const enhanceCompletionHandler = async (model) => {
		stopResponseFlag = false;
		let enhancedContent = {
			json: null,
			html: '',
			md: ''
		};

		const systemPrompt = `Enhance existing notes using additional context provided from audio transcription or uploaded file content in the content's primary language. Your task is to make the notes more useful and comprehensive by incorporating relevant information from the provided context.

Input will be provided within <notes> and <context> XML tags, providing a structure for the existing notes and context respectively.

# Output Format

Provide the enhanced notes in markdown format. Use markdown syntax for headings, lists, task lists ([ ]) where tasks or checklists are strongly implied, and emphasis to improve clarity and presentation. Ensure that all integrated content from the context is accurately reflected. Return only the markdown formatted note.
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
				if (done || stopResponseFlag) {
					if (stopResponseFlag) {
						controller.abort('User: Stop Response');
					}

					editing = false;
					streaming = false;
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

										// Update editor with new content
										if (editor) {
											editor.commands.setContent(enhancedContent.html);
										}
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
	}

	const downloadHandler = async (type) => {
		console.log('downloadHandler', type);
		if (type === 'md') {
			const blob = new Blob([note.data.content.md], { type: 'text/markdown' });
			saveAs(blob, `${note.title}.md`);
		} else if (type === 'txt') {
			const blob = new Blob([note.data.content.md], { type: 'text/plain' });
			saveAs(blob, `${note.title}.txt`);
		} else if (type === 'pdf') {
			await downloadPdf(note);
		}
	};

	const downloadPdf = async (note) => {
		try {
			const virtualWidth = 1024;
			const virtualHeight = 1400;

			const html = note.data?.content?.html ?? '';
			let node;
			if (html instanceof HTMLElement) {
				node = html;
			} else {
				node = document.createElement('div');
				node.innerHTML = html;
				document.body.appendChild(node);
			}

			const canvas = await html2canvas(node, {
				useCORS: true,
				scale: 2,
				width: virtualWidth,
				windowWidth: virtualWidth,
				windowHeight: virtualHeight
			});

			if (!(html instanceof HTMLElement)) {
				document.body.removeChild(node);
			}

			const imgData = canvas.toDataURL('image/png');

			const pdf = new jsPDF('p', 'mm', 'a4');
			const imgWidth = 210;
			const pageHeight = 297;

			const imgHeight = (canvas.height * imgWidth) / canvas.width;
			let heightLeft = imgHeight;
			let position = 0;

			pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
			heightLeft -= pageHeight;

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

	const deleteNoteHandler = async (noteId) => {
		const res = await deleteNotePlusById(localStorage.token, noteId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			// Dispatch event for category tree refresh
			window.dispatchEvent(new CustomEvent('noteplus:deleted'));
			goto('/noteplus');
		}
	};

	const onDragOver = (e) => {
		e.preventDefault();
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
			const inputFiles = e.dataTransfer?.files;

			if (inputFiles && inputFiles.length > 0) {
				const _files = [];
				for (const file of inputFiles) {
					console.log(file, file.name.split('.').at(-1));
					if (['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(file['type'])) {
						// Handle image files
						let reader = new FileReader();
						reader.onload = (event) => {
							files = [
								...files,
								{
									type: 'image',
									url: `${event.target.result}`
								}
							];
						};
						reader.readAsDataURL(file);
					} else {
						// Handle other file types
						toast.error($i18n.t(`File type not supported: {{type}}`, { type: file['type'] }));
					}
				}
				files = [...files, ..._files];
			}
		}

		dragged = false;
	};

	onDestroy(() => {
		const dropzoneElement = document.getElementById('note-editor');

		if (dropzoneElement) {
			dropzoneElement?.removeEventListener('dragover', onDragOver);
			dropzoneElement?.removeEventListener('drop', onDrop);
			dropzoneElement?.removeEventListener('dragleave', onDragLeave);
		}
	});

	const loadNote = async (noteId) => {
		if (!noteId) {
			note = JSON.parse(JSON.stringify(newNote));
			selectedModelId = $models?.find((m) => m?.id === $settings?.models?.[0] ?? '')?.id ?? '';
		} else {
			loading = true;
			try {
				note = await getNotePlusById(localStorage.token, noteId);

				if (note) {
					files = note.data?.files ?? [];
					console.log('Loaded note:', note);

					versionIdx = null;
					selectedModelId = note?.meta?.selectedModelId ?? $models?.[0]?.id ?? '';
					getWords();
				} else {
					goto('/noteplus');
				}
			} catch (error) {
				console.error('Error loading note:', error);
				toast.error('Failed to load note');
				goto('/noteplus');
			} finally {
				loading = false;
			}
		}
	};

	onMount(async () => {
		const dropzoneElement = document.getElementById('note-editor');

		dropzoneElement?.addEventListener('dragover', onDragOver);
		dropzoneElement?.addEventListener('drop', onDrop);
		dropzoneElement?.addEventListener('dragleave', onDragLeave);

		await loadNote(id);
	});

	// React to id prop changes
	$: if (id !== undefined) {
		loadNote(id);
	}

	$: if (note) {
		console.log('note', note);
	}
</script>

<svelte:head>
	<title>
		{note?.title
			? `${note?.title.length > 30 ? `${note?.title.slice(0, 30)}...` : note?.title} • ${$WEBUI_NAME}`
			: `${$WEBUI_NAME}`}
	</title>
</svelte:head>

{#if note}
	<AccessControlModal
		bind:show={showAccessControlModal}
		bind:accessControl={note.access_control}
		accessRoles={['read', 'write']}
		onChange={() => {
			changeDebounceHandler();
		}}
	/>
{/if}

<FilesOverlay show={dragged} />

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete note?')}
	on:confirm={() => {
		if (note?.id) {
			deleteNoteHandler(note.id);
		}
		showDeleteConfirm = false;
	}}
>
	<div class=" text-sm text-gray-500">
		{$i18n.t('This will delete')} <span class="  font-semibold">{note?.title || ''}</span>.
	</div>
</DeleteConfirmDialog>

<PaneGroup direction="horizontal" class="w-full h-full">
	<Pane defaultSize={70} minSize={30} class="h-full flex flex-col w-full relative">
		<div class="relative flex-1 w-full h-full flex justify-center pt-[11px]" id="note-editor">
			{#if loading}
				<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
					<div class="m-auto">
						<Spinner className="size-5" />
					</div>
				</div>
			{:else if note}
				<div class=" w-full flex flex-col {loading ? 'opacity-20' : ''}">
					<div class="shrink-0 w-full flex justify-between items-center px-3.5 mb-1.5">
						<div class="w-full flex items-center">
							{#if $mobile}
								<div
									class="{$showSidebar
										? 'md:hidden pl-0.5'
										: ''} flex flex-none items-center pr-1 -translate-x-1"
								>
									<Tooltip
										content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
									>
										<button
											id="sidebar-toggle-button"
											class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
											on:click={() => {
												showSidebar.set(!$showSidebar);
											}}
										>
											<div class=" self-center p-1.5">
												<Sidebar />
											</div>
										</button>
									</Tooltip>
								</div>
							{/if}

							<input
								class="w-full text-2xl font-medium bg-transparent outline-hidden"
								type="text"
								bind:value={note.title}
								placeholder={titleGenerating ? $i18n.t('Generating...') : $i18n.t('Title')}
								disabled={(note?.user_id !== $user?.id && $user?.role !== 'admin') ||
									titleGenerating}
								required
								on:input={changeDebounceHandler}
								on:focus={() => {
									titleInputFocused = true;
								}}
								on:blur={(e) => {
									if (ignoreBlur) {
										ignoreBlur = false;
										return;
									}

									titleInputFocused = false;
									changeDebounceHandler();
								}}
							/>

							{#if titleInputFocused && !titleGenerating}
								<div
									class="flex self-center items-center space-x-1.5 z-10 translate-y-[0.5px] -translate-x-[0.5px] pl-2"
								>
									<Tooltip content={$i18n.t('Generate')}>
										<button
											class=" self-center dark:hover:text-white transition"
											id="generate-title-button"
											disabled={(note?.user_id !== $user?.id && $user?.role !== 'admin') ||
												titleGenerating}
											on:mouseenter={() => {
												ignoreBlur = true;
											}}
											on:click={(e) => {
												e.preventDefault();
												e.stopImmediatePropagation();
												e.stopPropagation();

												generateTitleHandler();
												titleInputFocused = false;
											}}
										>
											<Sparkles strokeWidth="2" />
										</button>
									</Tooltip>
								</div>
							{/if}

							<div class="flex items-center gap-0.5 translate-x-1">
								{#if editor}
									<div>
										<div class="flex items-center gap-0.5 self-center min-w-fit" dir="ltr">
											<button
												class="self-center p-1 hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black rounded-md transition disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
												on:click={() => {
													editor.chain().focus().undo().run();
												}}
												disabled={!editor?.can?.().undo?.()}
											>
												<ArrowUturnLeft className="size-4" />
											</button>

											<button
												class="self-center p-1 hover:enabled:bg-black/5 dark:hover:enabled:bg-white/5 dark:hover:enabled:text-white hover:enabled:text-black rounded-md transition disabled:cursor-not-allowed disabled:text-gray-500 disabled:hover:text-gray-500"
												on:click={() => {
													editor.chain().focus().redo().run();
												}}
												disabled={!editor?.can?.().redo?.()}
											>
												<ArrowUturnRight className="size-4" />
											</button>
										</div>
									</div>
								{/if}

								<!-- AI Menu -->
								<AiMenu
									onGenerateTitle={generateTitleHandler}
									onGenerateCategory={generateCategoryHandler}
									onEnhance={enhanceNoteHandler}
									onChat={() => {
										if (showPanel && selectedPanel === 'chat') {
											showPanel = false;
										} else {
											if (!showPanel) {
												showPanel = true;
											}
											selectedPanel = 'chat';
										}
									}}
								>
									<Tooltip placement="top" content={$i18n.t('AI Features')} className="cursor-pointer">
										<button
											class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
											disabled={!selectedModelId || (titleGenerating || categoryGenerating)}
										>
											{#if titleGenerating || categoryGenerating}
												<Spinner className="size-4" />
											{:else}
												<Sparkles className="size-4" />
											{/if}
										</button>
									</Tooltip>
								</AiMenu>

								<Tooltip placement="top" content={$i18n.t('Categories')} className="cursor-pointer">
									<button
										class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
										on:click={() => {
											showCategoryInput = !showCategoryInput;
										}}
									>
										<Folder />
									</button>
								</Tooltip>

								<Tooltip placement="top" content={$i18n.t('Chat')} className="cursor-pointer">
									<button
										class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
										on:click={() => {
											if (showPanel && selectedPanel === 'chat') {
												showPanel = false;
											} else {
												if (!showPanel) {
													showPanel = true;
												}
												selectedPanel = 'chat';
											}
										}}
									>
										<ChatBubbleOval />
									</button>
								</Tooltip>

								<Tooltip placement="top" content={$i18n.t('Controls')} className="cursor-pointer">
									<button
										class="p-1.5 bg-transparent hover:bg-white/5 transition rounded-lg"
										on:click={() => {
											if (showPanel && selectedPanel === 'settings') {
												showPanel = false;
											} else {
												if (!showPanel) {
													showPanel = true;
												}
												selectedPanel = 'settings';
											}
										}}
									>
										<AdjustmentsHorizontalOutline />
									</button>
								</Tooltip>

								<NotePlusMenu
									onDownload={(type) => {
										downloadHandler(type);
									}}
									onCopyLink={async () => {
										const baseUrl = window.location.origin;
										const res = await copyToClipboard(`${baseUrl}/noteplus/${note.id}`);

										if (res) {
											toast.success($i18n.t('Copied link to clipboard'));
										} else {
											toast.error($i18n.t('Failed to copy link'));
										}
									}}
									onDelete={() => {
										showDeleteConfirm = true;
									}}
								>
									<button
										class=" self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-lg"
										type="button"
									>
										<EllipsisHorizontal />
									</button>
								</NotePlusMenu>
							</div>
						</div>
					</div>

					<!-- Category inputs -->
					{#if showCategoryInput}
						<div class="shrink-0 w-full px-3.5 mb-2">
							<div class="flex items-center gap-2">
								<span class="text-xs text-gray-500">{$i18n.t('Categories')}:</span>
								<input
									class="px-2 py-1 text-sm bg-gray-100 dark:bg-gray-800 rounded outline-none"
									type="text"
									bind:value={note.category_major}
									placeholder={$i18n.t('Major')}
									on:input={changeDebounceHandler}
								/>
								<span class="text-gray-400">/</span>
								<input
									class="px-2 py-1 text-sm bg-gray-100 dark:bg-gray-800 rounded outline-none"
									type="text"
									bind:value={note.category_middle}
									placeholder={$i18n.t('Middle')}
									on:input={changeDebounceHandler}
								/>
								<span class="text-gray-400">/</span>
								<input
									class="px-2 py-1 text-sm bg-gray-100 dark:bg-gray-800 rounded outline-none"
									type="text"
									bind:value={note.category_minor}
									placeholder={$i18n.t('Minor')}
									on:input={changeDebounceHandler}
								/>
								
								{#if !categoryGenerating}
									<Tooltip content={$i18n.t('Auto Categorize')}>
										<button
											class="p-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition"
											disabled={!selectedModelId || categoryGenerating}
											on:click={(e) => {
												e.preventDefault();
												generateCategoryHandler();
											}}
										>
											<Sparkles className="size-4" />
										</button>
									</Tooltip>
								{:else}
									<Spinner className="size-4" />
								{/if}
							</div>
						</div>
					{/if}

					<div class="flex-1 px-3.5 pb-3.5 overflow-y-auto">
						{#if note}
							<RichTextInput
								bind:this={editor}
								bind:editor
								id={`noteplus-${id}`}
								json={true}
								bind:value={note.data.content.json}
								html={note.data?.content?.html}
								placeholder={$i18n.t('Write your note here...')}
								{files}
								editable={versionIdx === null && !editing}
								onChange={(content) => {
									note.data.content.html = content.html;
									note.data.content.md = content.md;
									
									if (editor) {
										wordCount = editor.storage.characterCount.words();
										charCount = editor.storage.characterCount.characters();
									}
									
									changeDebounceHandler();
								}}
								className="prose-sm prose-neutral dark:prose-invert max-w-full"
							/>
						{/if}
					</div>

					<div class="shrink-0 px-3.5 py-2 border-t border-gray-200 dark:border-gray-800 flex justify-between items-center text-xs text-gray-500">
						<div class="flex items-center gap-4">
							<span>{wordCount} {$i18n.t('words')}</span>
							<span>{charCount} {$i18n.t('characters')}</span>
						</div>
						<div>
							{#if note?.updated_at}
								{$i18n.t('Last updated')}: {dayjs(note.updated_at / 1000000).fromNow()}
							{/if}
						</div>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- Floating AI Button at Bottom Right -->
		<div class="absolute z-20 bottom-0 right-0 p-3.5 max-w-full w-full flex">
			<div class="flex gap-1 w-full min-w-full justify-end">
				{#if recording}
					<div class="flex-1 w-full">
						<VoiceRecording
							bind:recording
							className="p-1 w-full max-w-full"
							transcribe={false}
							displayMedia={displayMediaRecord}
							echoCancellation={false}
							noiseSuppression={false}
							onCancel={() => {
								recording = false;
								displayMediaRecord = false;
							}}
							onConfirm={(data) => {
								if (data?.file) {
									// Handle file upload if needed
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
									// Handle audio file upload
								}
							};
						}}
					>
						<Tooltip content={$i18n.t('Record')} placement="top">
							<div
								class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 bg-white dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
							>
								<MicSolid className="size-4.5" />
							</div>
						</Tooltip>
					</RecordMenu>

					<div
						class="cursor-pointer flex gap-0.5 rounded-full border border-gray-50 dark:border-gray-850 dark:bg-gray-850 transition shadow-xl"
					>
						<Tooltip content={$i18n.t('AI')} placement="top">
							{#if editing || streaming}
								<button
									class="p-2 flex justify-center items-center hover:bg-gray-50 dark:hover:bg-gray-800 rounded-full transition shrink-0"
									on:click={() => {
										stopResponseFlag = true;
									}}
									type="button"
								>
									<Spinner className="size-5" />
								</button>
							{:else}
								<AiMenu
									onGenerateTitle={generateTitleHandler}
									onGenerateCategory={generateCategoryHandler}
									onEnhance={enhanceNoteHandler}
									onChat={() => {
										if (showPanel && selectedPanel === 'chat') {
											showPanel = false;
										} else {
											if (!showPanel) {
												showPanel = true;
											}
											selectedPanel = 'chat';
										}
									}}
								>
									<div
										class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 bg-white dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
									>
										<SparklesSolid className="size-4.5" />
									</div>
								</AiMenu>
							{/if}
						</Tooltip>
					</div>
				{/if}
			</div>
		</div>
	</Pane>

	{#if showPanel}
		<PaneResizer class="relative">
			<div
				class="z-10 absolute -left-[0.1rem] top-[50%] text-gray-400 transition rounded-full bg-gray-50 dark:bg-gray-850"
			>
				<ArrowRight className="size-[0.7rem] rotate-180" strokeWidth="4" />
			</div>
		</PaneResizer>

		<Pane defaultSize={30} minSize={20} maxSize={50} class="h-full flex flex-col">
			{#if selectedPanel === 'chat'}
				<Chat
					bind:messages
					bind:stopResponseFlag
					bind:files
					{selectedModelId}
					{selectedContent}
					{editor}
					{note}
					onInsert={(content) => {
						if (editor && content) {
							const selection = editor.view.state.selection;
							editor.commands.insertContentAt(selection.anchor, content);
						}
					}}
					on:select={(e) => {
						if (e.detail !== '') {
							selectedContent = e.detail;
						}
					}}
					{streaming}
				/>
			{:else if selectedPanel === 'settings'}
				<Controls
					on:select={(e) => {
						selectedModelId = e.detail;
						changeDebounceHandler();
					}}
					{selectedModelId}
				/>
			{/if}
		</Pane>
	{/if}
</PaneGroup>