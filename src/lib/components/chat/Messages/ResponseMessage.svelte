<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';

	import { createEventDispatcher, onDestroy } from 'svelte';
	import { onMount, tick, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType, t } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	const dispatch = createEventDispatcher();

	import {
		createNewFeedback,
		getFeedbackById,
		updateFeedbackById,
		submitMessageFeedback
	} from '$lib/apis/evaluations';
	import { getChatById } from '$lib/apis/chats';
	import { generateTags } from '$lib/apis';

	import {
		audioQueue,
		config,
		models,
		settings,
		temporaryChatEnabled,
		TTSWorker,
		user
	} from '$lib/stores';
	import { synthesizeOpenAISpeech } from '$lib/apis/audio';
	import { imageGenerations } from '$lib/apis/images';
	import {
		copyToClipboard as _copyToClipboard,
		approximateToHumanReadable,
		getMessageContentParts,
		sanitizeResponseContent,
		createMessagesList,
		formatDate,
		removeDetails,
		removeAllDetails
	} from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Skeleton from './Skeleton.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import RateComment from './RateComment.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import WebSearchResults from './ResponseMessage/WebSearchResults.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';

	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Error from './Error.svelte';
	import Citations from './Citations.svelte';
	import CodeExecutions from './CodeExecutions.svelte';
	import ContentRenderer from './ContentRenderer.svelte';
	import { KokoroWorker } from '$lib/workers/KokoroWorker';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import FollowUps from './ResponseMessage/FollowUps.svelte';
	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import RegenerateMenu from './ResponseMessage/RegenerateMenu.svelte';
	import StatusHistory from './ResponseMessage/StatusHistory.svelte';
	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';

	interface MessageType {
		id: string;
		model: string;
		content: string;
		files?: { type: string; url: string }[];
		timestamp: number;
		role: string;
		statusHistory?: {
			done: boolean;
			action: string;
			description: string;
			urls?: string[];
			query?: string;
		}[];
		status?: {
			done: boolean;
			action: string;
			description: string;
			urls?: string[];
			query?: string;
		};
		toolExecutions?: Record<string, {
			status: 'executing' | 'completed';
			message: string;
		}>;
		done: boolean;
		completed?: boolean; // Set to true after chatCompletedHandler is called
		error?: boolean | { content: string };
		sources?: string[];
		code_executions?: {
			uuid: string;
			name: string;
			code: string;
			language?: string;
			result?: {
				error?: string;
				output?: string;
				files?: { name: string; url: string }[];
			};
		}[];
		info?: {
			openai?: boolean;
			prompt_tokens?: number;
			completion_tokens?: number;
			total_tokens?: number;
			eval_count?: number;
			eval_duration?: number;
			prompt_eval_count?: number;
			prompt_eval_duration?: number;
			total_duration?: number;
			load_duration?: number;
			usage?: unknown;
		};
		annotation?: { type: string; rating: number };
		feedback?: 'good' | 'bad' | null;
	}

	export let chatId = '';
	export let history;
	export let messageId;
	export let selectedModels = [];

	let message: MessageType = JSON.parse(JSON.stringify(history.messages[messageId]));
	$: if (history.messages) {
		if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
			message = JSON.parse(JSON.stringify(history.messages[messageId]));
		}
	}

	// Check if any tool is currently executing
	$: isToolExecuting = message?.toolExecutions
		? Object.values(message.toolExecutions).some((t) => t.status === 'executing')
		: false;

	// Get list of executing tools for display
	$: executingTools = message?.toolExecutions
		? Object.entries(message.toolExecutions).filter(([_, t]) => t.status === 'executing')
		: [];

	export let siblings;

	export let setInputText: Function = () => {};
	export let gotoMessage: Function = () => {};
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;

	export let updateChat: Function;
	export let editMessage: Function;
	export let saveMessage: Function;
	export let rateMessage: Function;
	export let actionMessage: Function;
	export let deleteMessage: Function;

	export let submitMessage: Function;
	export let continueResponse: Function;
	export let regenerateResponse: Function;

	export let addMessages: Function;

	export let isLastMessage = true;
	export let readOnly = false;
	export let editCodeBlock = true;
	export let topPadding = false;

	let citationsElement: HTMLDivElement;

	let contentContainerElement: HTMLDivElement;
	let buttonsContainerElement: HTMLDivElement;
	let showDeleteConfirm = false;

	let model = null;
	$: model = $models.find((m) => m.id === message.model);

	let edit = false;
	let editedContent = '';
	let editTextAreaElement: HTMLTextAreaElement;

	let messageIndexEdit = false;

	let speaking = false;
	let speakingIdx: number | undefined;

	let loadingSpeech = false;
	let generatingImage = false;

	let showRateComment = false;

	const copyToClipboard = async (text) => {
		text = removeAllDetails(text);

		if (($config?.ui?.response_watermark ?? '').trim() !== '') {
			text = `${text}\n\n${$config?.ui?.response_watermark}`;
		}

		const res = await _copyToClipboard(text, null, $settings?.copyFormatted ?? false);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};

	const stopAudio = () => {
		try {
			speechSynthesis.cancel();
			$audioQueue.stop();
		} catch {}

		if (speaking) {
			speaking = false;
			speakingIdx = undefined;
		}
	};

	const speak = async () => {
		if (!(message?.content ?? '').trim().length) {
			toast.info($i18n.t('No content to speak'));
			return;
		}

		speaking = true;
		const content = removeAllDetails(message.content);

		if ($config.audio.tts.engine === '') {
			let voices = [];
			const getVoicesLoop = setInterval(() => {
				voices = speechSynthesis.getVoices();
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);

					const voice =
						voices
							?.filter(
								(v) => v.voiceURI === ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
							)
							?.at(0) ?? undefined;

					console.log(voice);

					const speech = new SpeechSynthesisUtterance(content);
					speech.rate = $settings.audio?.tts?.playbackRate ?? 1;

					console.log(speech);

					speech.onend = () => {
						speaking = false;
						if ($settings.conversationMode) {
							document.getElementById('voice-input-button')?.click();
						}
					};

					if (voice) {
						speech.voice = voice;
					}

					speechSynthesis.speak(speech);
				}
			}, 100);
		} else {
			$audioQueue.setId(`${message.id}`);
			$audioQueue.setPlaybackRate($settings.audio?.tts?.playbackRate ?? 1);
			$audioQueue.onStopped = () => {
				speaking = false;
				speakingIdx = undefined;
			};

			loadingSpeech = true;
			const messageContentParts: string[] = getMessageContentParts(
				content,
				$config?.audio?.tts?.split_on ?? 'punctuation'
			);

			if (!messageContentParts.length) {
				console.log('No content to speak');
				toast.info($i18n.t('No content to speak'));

				speaking = false;
				loadingSpeech = false;
				return;
			}

			console.debug('Prepared message content for TTS', messageContentParts);
			if ($settings.audio?.tts?.engine === 'browser-kokoro') {
				if (!$TTSWorker) {
					await TTSWorker.set(
						new KokoroWorker({
							dtype: $settings.audio?.tts?.engineConfig?.dtype ?? 'fp32'
						})
					);

					await $TTSWorker.init();
				}

				for (const [idx, sentence] of messageContentParts.entries()) {
					const url = await $TTSWorker
						.generate({
							text: sentence,
							voice: $settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice
						})
						.catch((error) => {
							console.error(error);
							toast.error(`${error}`);

							speaking = false;
							loadingSpeech = false;
						});

					if (url && speaking) {
						$audioQueue.enqueue(url);
						loadingSpeech = false;
					}
				}
			} else {
				for (const [idx, sentence] of messageContentParts.entries()) {
					const res = await synthesizeOpenAISpeech(
						localStorage.token,
						$settings?.audio?.tts?.defaultVoice === $config.audio.tts.voice
							? ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
							: $config?.audio?.tts?.voice,
						sentence
					).catch((error) => {
						console.error(error);
						toast.error(`${error}`);

						speaking = false;
						loadingSpeech = false;
					});

					if (res && speaking) {
						const blob = await res.blob();
						const url = URL.createObjectURL(blob);

						$audioQueue.enqueue(url);
						loadingSpeech = false;
					}
				}
			}
		}
	};

	let preprocessedDetailsCache = [];

	function preprocessForEditing(content: string): string {
		// Replace <details>...</details> with unique ID placeholder
		const detailsBlocks = [];
		let i = 0;

		content = content.replace(/<details[\s\S]*?<\/details>/gi, (match) => {
			detailsBlocks.push(match);
			return `<details id="__DETAIL_${i++}__"/>`;
		});

		// Store original blocks in the editedContent or globally (see merging later)
		preprocessedDetailsCache = detailsBlocks;

		return content;
	}

	function postprocessAfterEditing(content: string): string {
		const restoredContent = content.replace(
			/<details id="__DETAIL_(\d+)__"\/>/g,
			(_, index) => preprocessedDetailsCache[parseInt(index)] || ''
		);

		return restoredContent;
	}

	const editMessageHandler = async () => {
		edit = true;

		editedContent = preprocessForEditing(message.content);

		await tick();

		editTextAreaElement.style.height = '';
		editTextAreaElement.style.height = `${editTextAreaElement.scrollHeight}px`;
	};

	const editMessageConfirmHandler = async () => {
		const messageContent = postprocessAfterEditing(editedContent ? editedContent : '');
		editMessage(message.id, { content: messageContent }, false);

		edit = false;
		editedContent = '';

		await tick();
	};

	const saveAsCopyHandler = async () => {
		const messageContent = postprocessAfterEditing(editedContent ? editedContent : '');

		editMessage(message.id, { content: messageContent });

		edit = false;
		editedContent = '';

		await tick();
	};

	const cancelEditMessage = async () => {
		edit = false;
		editedContent = '';
		await tick();
	};

	const generateImage = async (message: MessageType) => {
		generatingImage = true;
		const res = await imageGenerations(localStorage.token, message.content).catch((error) => {
			toast.error(`${error}`);
		});
		console.log(res);

		if (res) {
			const files = res.map((image) => ({
				type: 'image',
				url: `${image.url}`
			}));

			saveMessage(message.id, {
				...message,
				files: files
			});
		}

		generatingImage = false;
	};

	let feedbackLoading = false;

	// New simple message feedback handler
	let messageFeedbackLoading = false;
	let feedbackExpanded = false;

	// Reactive declaration - always syncs with message.feedback
	$: currentFeedback = message?.feedback ?? null;

	const handleMessageFeedback = async (rating: 'good' | 'bad') => {
		if (messageFeedbackLoading) return;

		messageFeedbackLoading = true;

		try {
			// If clicking the same rating, toggle it off (set to null)
			const newRating = currentFeedback === rating ? null : rating;

			const result = await submitMessageFeedback(
				localStorage.token,
				chatId,
				message.id,
				newRating
			);

			// Update local state
			currentFeedback = newRating;

			// Update message in history
			const updatedMessage = {
				...message,
				feedback: newRating
			};
			saveMessage(message.id, updatedMessage);

			if (newRating) {
				toast.success($i18n.t('Thank you for your feedback!'));
			}
		} catch (error) {
			console.error('Failed to submit feedback:', error);
			toast.error($i18n.t('Failed to submit feedback'));
		} finally {
			messageFeedbackLoading = false;
		}
	};

	const feedbackHandler = async (rating: number | null = null, details: object | null = null) => {
		feedbackLoading = true;
		console.log('Feedback', rating, details);

		const updatedMessage = {
			...message,
			annotation: {
				...(message?.annotation ?? {}),
				...(rating !== null ? { rating: rating } : {}),
				...(details ? details : {})
			}
		};

		const chat = await getChatById(localStorage.token, chatId).catch((error) => {
			toast.error(`${error}`);
		});
		if (!chat) {
			return;
		}

		const messages = createMessagesList(history, message.id);

		let feedbackItem = {
			type: 'rating',
			data: {
				...(updatedMessage?.annotation ? updatedMessage.annotation : {}),
				model_id: message?.selectedModelId ?? message.model,
				...(history.messages[message.parentId].childrenIds.length > 1
					? {
							sibling_model_ids: history.messages[message.parentId].childrenIds
								.filter((id) => id !== message.id)
								.map((id) => history.messages[id]?.selectedModelId ?? history.messages[id].model)
						}
					: {})
			},
			meta: {
				arena: message ? message.arena : false,
				model_id: message.model,
				message_id: message.id,
				message_index: messages.length,
				chat_id: chatId
			},
			snapshot: {
				chat: chat
			}
		};

		const baseModels = [
			feedbackItem.data.model_id,
			...(feedbackItem.data.sibling_model_ids ?? [])
		].reduce((acc, modelId) => {
			const model = $models.find((m) => m.id === modelId);
			if (model) {
				acc[model.id] = model?.info?.base_model_id ?? null;
			} else {
				// Log or handle cases where corresponding model is not found
				console.warn(`Model with ID ${modelId} not found`);
			}
			return acc;
		}, {});
		feedbackItem.meta.base_models = baseModels;

		let feedback = null;
		if (message?.feedbackId) {
			feedback = await updateFeedbackById(
				localStorage.token,
				message.feedbackId,
				feedbackItem
			).catch((error) => {
				toast.error(`${error}`);
			});
		} else {
			feedback = await createNewFeedback(localStorage.token, feedbackItem).catch((error) => {
				toast.error(`${error}`);
			});

			if (feedback) {
				updatedMessage.feedbackId = feedback.id;
			}
		}

		console.log(updatedMessage);
		saveMessage(message.id, updatedMessage);

		await tick();

		if (!details) {
			showRateComment = true;

			if (!updatedMessage.annotation?.tags && (message?.content ?? '') !== '') {
				// attempt to generate tags
				const tags = await generateTags(localStorage.token, message.model, messages, chatId).catch(
					(error) => {
						console.error(error);
						return [];
					}
				);
				console.log(tags);

				if (tags) {
					updatedMessage.annotation.tags = tags;
					feedbackItem.data.tags = tags;

					saveMessage(message.id, updatedMessage);
					await updateFeedbackById(
						localStorage.token,
						updatedMessage.feedbackId,
						feedbackItem
					).catch((error) => {
						toast.error(`${error}`);
					});
				}
			}
		}

		feedbackLoading = false;
	};

	const deleteMessageHandler = async () => {
		deleteMessage(message.id);
	};

	$: if (!edit) {
		(async () => {
			await tick();
		})();
	}

	const buttonsWheelHandler = (event: WheelEvent) => {
		if (buttonsContainerElement) {
			if (buttonsContainerElement.scrollWidth <= buttonsContainerElement.clientWidth) {
				// If the container is not scrollable, horizontal scroll
				return;
			} else {
				event.preventDefault();

				if (event.deltaY !== 0) {
					// Adjust horizontal scroll position based on vertical scroll
					buttonsContainerElement.scrollLeft += event.deltaY;
				}
			}
		}
	};

	const contentCopyHandler = (e) => {
		if (contentContainerElement) {
			e.preventDefault();
			// Get the selected HTML
			const selection = window.getSelection();
			const range = selection.getRangeAt(0);
			const tempDiv = document.createElement('div');

			// Remove background, color, and font styles
			tempDiv.appendChild(range.cloneContents());

			tempDiv.querySelectorAll('table').forEach((table) => {
				table.style.borderCollapse = 'collapse';
				table.style.width = 'auto';
				table.style.tableLayout = 'auto';
			});

			tempDiv.querySelectorAll('th').forEach((th) => {
				th.style.whiteSpace = 'nowrap';
				th.style.padding = '4px 8px';
			});

			// Put cleaned HTML + plain text into clipboard
			e.clipboardData.setData('text/html', tempDiv.innerHTML);
			e.clipboardData.setData('text/plain', selection.toString());
		}
	};

	onMount(async () => {
		// console.log('ResponseMessage mounted');

		await tick();
		if (buttonsContainerElement) {
			buttonsContainerElement.addEventListener('wheel', buttonsWheelHandler);
		}

		if (contentContainerElement) {
			contentContainerElement.addEventListener('copy', contentCopyHandler);
		}
	});

	onDestroy(() => {
		if (buttonsContainerElement) {
			buttonsContainerElement.removeEventListener('wheel', buttonsWheelHandler);
		}

		if (contentContainerElement) {
			contentContainerElement.removeEventListener('copy', contentCopyHandler);
		}
	});
</script>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete message?')}
	on:confirm={() => {
		deleteMessageHandler();
	}}
/>

{#key message.id}
	<div
		class=" flex w-full message-{message.id}"
		id="message-{message.id}"
		dir={$settings.chatDirection}
	>
		<!-- <div class={`shrink-0 ltr:mr-3 rtl:ml-3 hidden @lg:flex mt-1 `}>
			<ProfileImage
				src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}`}
				className={'size-8 assistant-message-profile-image'}
			/>
		</div> -->

		<div class="flex-auto w-0 pl-1 relative">
			<Name>
				<!-- <Tooltip content={model?.name ?? message.model} placement="top-start">
					<span id="response-message-model-name" class="line-clamp-1 text-gra-900 dark:text-gray-100">
						{model?.name ?? message.model}
					</span>
				</Tooltip> -->

				<!-- {#if message.timestamp}
					<div
						class="self-center text-xs font-medium first-letter:capitalize ml-0.5 translate-y-[1px] {($settings?.highContrastMode ??
						false)
							? 'dark:text-gray-100 text-gray-900'
							: 'invisible group-hover:visible transition text-gray-400'}"
					>
						<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
							<span class="line-clamp-1"
								>{$i18n.t(formatDate(message.timestamp * 1000), {
									LOCALIZED_TIME: dayjs(message.timestamp * 1000).format('LT'),
									LOCALIZED_DATE: dayjs(message.timestamp * 1000).format('L')
								})}</span
							>
						</Tooltip>
					</div>
				{/if} -->
			</Name>

			<div>
				<div class="chat-{message.role} w-full min-w-full markdown-prose">
					<div>
						{#if model?.info?.meta?.capabilities?.status_updates ?? true}
							<StatusHistory statusHistory={message?.statusHistory} />
						{/if}

						{#if message?.files && message.files?.filter((f) => f.type === 'image').length > 0}
							<div class="my-1 w-full flex overflow-x-auto gap-2 flex-wrap">
								{#each message.files as file}
									<div>
										{#if file.type === 'image'}
											<Image src={file.url} alt={message.content} />
										{:else}
											<FileItem
												item={file}
												url={file.url}
												name={file.name}
												type={file.type}
												size={file?.size}
												small={true}
											/>
										{/if}
									</div>
								{/each}
							</div>
						{/if}

						{#if message?.embeds && message.embeds.length > 0}
							<div class="my-1 w-full flex overflow-x-auto gap-2 flex-wrap">
								{#each message.embeds as embed, idx}
									<div class="my-2 w-full" id={`${message.id}-embeds-${idx}`}>
										<FullHeightIframe
											src={embed}
											allowScripts={true}
											allowForms={true}
											allowSameOrigin={true}
											allowPopups={true}
										/>
									</div>
								{/each}
							</div>
						{/if}

						{#if edit === true}
							<div class="w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-5 py-3 my-2">
								<textarea
									id="message-edit-{message.id}"
									bind:this={editTextAreaElement}
									class=" bg-transparent outline-hidden w-full resize-none"
									bind:value={editedContent}
									on:input={(e) => {
										e.target.style.height = '';
										e.target.style.height = `${e.target.scrollHeight}px`;
									}}
									on:keydown={(e) => {
										if (e.key === 'Escape') {
											document.getElementById('close-edit-message-button')?.click();
										}

										const isCmdOrCtrlPressed = e.metaKey || e.ctrlKey;
										const isEnterPressed = e.key === 'Enter';

										if (isCmdOrCtrlPressed && isEnterPressed) {
											document.getElementById('confirm-edit-message-button')?.click();
										}
									}}
								/>

								<div class=" mt-2 mb-1 flex justify-between text-sm font-medium">
									<div>
										<button
											id="save-new-message-button"
											class="px-3.5 py-1.5 bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 border border-gray-100 dark:border-gray-700 text-gray-700 dark:text-gray-200 transition rounded-3xl"
											on:click={() => {
												saveAsCopyHandler();
											}}
										>
											{$i18n.t('Save As Copy')}
										</button>
									</div>

									<div class="flex space-x-1.5">
										<button
											id="close-edit-message-button"
											class="px-3.5 py-1.5 bg-white dark:bg-gray-900 hover:bg-gray-100 text-gray-800 dark:text-gray-100 transition rounded-3xl"
											on:click={() => {
												cancelEditMessage();
											}}
										>
											{$i18n.t('Cancel')}
										</button>

										<button
											id="confirm-edit-message-button"
											class="px-3.5 py-1.5 bg-gray-900 dark:bg-white hover:bg-gray-850 text-gray-100 dark:text-gray-800 transition rounded-3xl"
											on:click={() => {
												editMessageConfirmHandler();
											}}
										>
											{$i18n.t('Save')}
										</button>
									</div>
								</div>
							</div>
						{/if}

						<!-- Message + Regenerate Button Row -->
						<div class="flex flex-col @md:flex-row @md:items-end gap-2">
							<div
								bind:this={contentContainerElement}
								class="max-w-full @md:max-w-[75%] w-fit flex flex-col relative {edit
									? 'hidden'
									: ''}
								bg-white/50 dark:bg-white/5
								border border-gray-200/30 dark:border-gray-200/20
								backdrop-blur-md
								shadow-[0.25rem_0.25rem_1.25rem_rgba(0,0,0,0.1),inset_0.125rem_0.125rem_0.625rem_rgba(255,255,255,0.05),inset_0.125rem_0.125rem_1rem_rgba(206,212,229,0.12)]
								rounded-[1.25rem] rounded-bl-[0.25rem]
								text-gray-900 dark:text-gray-100
								py-5 px-7"
								id="response-content-container"
							>
								{#if message.content === '' && !message.error && (!message.completed || isToolExecuting) && ((model?.info?.meta?.capabilities?.status_updates ?? true) ? (message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]).length === 0 || (message?.statusHistory?.at(-1)?.hidden ?? false) : true)}
									<Skeleton />
								{:else if message.content === '' && !message.error && message.completed && !isToolExecuting}
									<!-- Edge case: message completed but no content (model error or save issue) -->
									<div class="text-gray-500 dark:text-gray-400 text-sm italic">
										{$i18n.t('No response received. Please try again.')}
									</div>
								{:else if message.content && message.error !== true}
									<!-- always show message contents even if there's an error -->
									<!-- unless message.error === true which is legacy error handling, where the error message is stored in message.content -->
									<ContentRenderer
										id={`${chatId}-${message.id}`}
										messageId={message.id}
										{history}
										{selectedModels}
										content={message.content}
										sources={message.sources}
										floatingButtons={message?.done &&
											!readOnly &&
											($settings?.showFloatingActionButtons ?? true)}
										save={!readOnly}
										preview={!readOnly}
										{editCodeBlock}
										{topPadding}
										done={($settings?.chatFadeStreamingText ?? true)
											? (message?.done ?? false)
											: true}
										{model}
										onTaskClick={async (e) => {
											console.log(e);
										}}
										onSourceClick={async (id) => {
											console.log(id);

											if (citationsElement) {
												citationsElement?.showSourceModal(id);
											}
										}}
										onAddMessages={({ modelId, parentId, messages }) => {
											addMessages({ modelId, parentId, messages });
										}}
										onSave={({ raw, oldContent, newContent }) => {
											history.messages[message.id].content = history.messages[
												message.id
											].content.replace(raw, raw.replace(oldContent, newContent));

											updateChat();
										}}
									/>
								{/if}

								{#if message?.error}
									<Error content={message?.error?.content ?? message.content} />
								{/if}

								{#if (message?.sources || message?.citations) && (model?.info?.meta?.capabilities?.citations ?? true)}
									<Citations
										bind:this={citationsElement}
										id={message?.id}
										sources={message?.sources ?? message?.citations}
										{readOnly}
									/>
								{/if}

								{#if message.code_executions}
									<CodeExecutions codeExecutions={message.code_executions} />
								{/if}

								<!-- Tool Execution Status (shown at bottom of message while generating) -->
								{#if executingTools.length > 0}
									<div class="flex flex-col gap-1 mt-3 w-full">
										{#each executingTools as [toolName, toolInfo]}
											<div
												class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-lg px-3 py-2"
												transition:fade={{ duration: 150 }}
											>
												<Spinner className="size-4" />
												<span>{toolInfo.message}</span>
											</div>
										{/each}
									</div>
								{/if}
							</div>

							<!-- Desktop Buttons Container (PC only) -->
							{#if message.completed && !readOnly && !isToolExecuting}
								<div class="hidden md:flex flex-row items-center gap-1">
									<!-- Regenerate Button (PC) -->
									{#if !currentFeedback && ($user?.role === 'admin' || ($user?.permissions?.chat?.regenerate_response ?? true))}
										<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
											<button
												type="button"
												aria-label={$i18n.t('Regenerate')}
												class="p-1 text-gray-950 dark:text-gray-50 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition regenerate-response-button"
												on:click={() => {
													showRateComment = false;
													regenerateResponse(message);

													(model?.actions ?? []).forEach((action) => {
														dispatch('action', {
															id: action.id,
															event: {
																id: 'regenerate-response',
																data: {
																	messageId: message.id
																}
															}
														});
													});
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
													aria-hidden="true"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}
									<!-- Feedback Status Icon (when feedback exists) -->
									{#if currentFeedback}
										<div class="flex items-center gap-1">
											<!-- Current feedback indicator - click to expand -->
											<button
												type="button"
												class="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition"
												on:click={() => (feedbackExpanded = !feedbackExpanded)}
											>
												{#if currentFeedback === 'good'}
													<svg
														xmlns="http://www.w3.org/2000/svg"
														fill="#34BE89"
														viewBox="0 0 24 24"
														stroke-width="2"
														stroke="#34BE89"
														class="w-4 h-4"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
														/>
													</svg>
												{:else}
													<svg
														xmlns="http://www.w3.org/2000/svg"
														fill="#FF4D6A"
														viewBox="0 0 24 24"
														stroke-width="2"
														stroke="#FF4D6A"
														class="w-4 h-4"
													>
														<path
															stroke-linecap="round"
															stroke-linejoin="round"
															d="M6 18L18 6M6 6l12 12"
														/>
													</svg>
												{/if}
											</button>

											<!-- Expanded feedback options -->
											{#if feedbackExpanded}
												<div
													class="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-full px-1 py-0.5"
												>
													<Tooltip content={$i18n.t('No')} placement="bottom">
														<button
															type="button"
															class="p-0.5 rounded-full transition {currentFeedback === 'bad'
																? 'bg-red-200 dark:bg-red-900/50'
																: 'hover:bg-gray-200 dark:hover:bg-gray-700'}"
															disabled={messageFeedbackLoading}
															on:click={() => handleMessageFeedback('bad')}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																fill={currentFeedback === 'bad' ? '#FF4D6A' : 'none'}
																viewBox="0 0 24 24"
																stroke-width="2"
																stroke="#FF4D6A"
																class="w-4 h-4"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="M6 18L18 6M6 6l12 12"
																/>
															</svg>
														</button>
													</Tooltip>
													<Tooltip content={$i18n.t('Yes')} placement="bottom">
														<button
															type="button"
															class="p-0.5 rounded-full transition {currentFeedback === 'good'
																? 'bg-green-200 dark:bg-green-900/50'
																: 'hover:bg-gray-200 dark:hover:bg-gray-700'}"
															disabled={messageFeedbackLoading}
															on:click={() => handleMessageFeedback('good')}
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																fill={currentFeedback === 'good' ? '#34BE89' : 'none'}
																viewBox="0 0 24 24"
																stroke-width="2"
																stroke="#34BE89"
																class="w-4 h-4"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
																/>
															</svg>
														</button>
													</Tooltip>
													{#if messageFeedbackLoading}
														<Spinner className="size-3" />
													{/if}
												</div>
											{/if}
										</div>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				</div>
				<!-- Feedback Section: 답변이 이해되셨나요? (only when no feedback yet and response is completed) -->
				{#if message.completed && !isToolExecuting && !readOnly && !currentFeedback}
					<div class="flex flex-row items-center gap-2 mt-2.5 w-full justify-start">
						<div class="flex flex-row items-center gap-2">
							<span class="text-caption text-gray-700 dark:text-gray-300">
								{$i18n.t('Did you understand the answer?')}
							</span>
							<Tooltip content={$i18n.t('No')} placement="bottom">
								<button
									type="button"
									aria-label={$i18n.t('No')}
									class="p-0.5 hover:opacity-80 transition disabled:opacity-50"
									disabled={messageFeedbackLoading}
									on:click={() => handleMessageFeedback('bad')}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2"
										stroke="#FF4D6A"
										class="w-5 h-5"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Yes')} placement="bottom">
								<button
									type="button"
									aria-label={$i18n.t('Yes')}
									class="p-0.5 hover:opacity-80 transition disabled:opacity-50"
									disabled={messageFeedbackLoading}
									on:click={() => handleMessageFeedback('good')}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2"
										stroke="#34BE89"
										class="w-5 h-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
							d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
										/>
									</svg>
								</button>
							</Tooltip>
							{#if messageFeedbackLoading}
								<Spinner className="size-4" />
							{/if}
						</div>
						
						<!-- Regenerate Button (Mobile only) -->
						<div class="md:hidden">
							{#if $user?.role === 'admin' || ($user?.permissions?.chat?.regenerate_response ?? true)}
								<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
									<button
										type="button"
										aria-label={$i18n.t('Regenerate')}
										class="p-1 text-gray-950 dark:text-gray-50 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg transition regenerate-response-button"
										on:click={() => {
											showRateComment = false;
											regenerateResponse(message);

											(model?.actions ?? []).forEach((action) => {
												dispatch('action', {
													id: action.id,
													event: {
														id: 'regenerate-response',
														data: {
															messageId: message.id
														}
													}
												});
											});
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="2"
											aria-hidden="true"
											stroke="currentColor"
							class="w-4 h-4"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
											/>
										</svg>
									</button>
								</Tooltip>
							{/if}
						</div>
					</div>
				{/if}

				{#if !edit}
					<div
						bind:this={buttonsContainerElement}
						class="flex justify-start overflow-x-auto buttons text-gray-600 dark:text-gray-500 mt-0.5"
					>
						{#if message.done || siblings.length > 1}
							{#if siblings.length > 1}
								<!-- <div class="flex self-center min-w-fit" dir="ltr">
									<button
										aria-label={$i18n.t('Previous message')}
										class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
										on:click={() => {
											showPreviousMessage(message);
										}}
									>
										<svg
											aria-hidden="true"
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke="currentColor"
											stroke-width="2.5"
											class="size-3.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 19.5 8.25 12l7.5-7.5"
											/>
										</svg>
									</button>

									{#if messageIndexEdit}
										<div
											class="text-sm flex justify-center font-semibold self-center dark:text-gray-100 min-w-fit"
										>
											<input
												id="message-index-input-{message.id}"
												type="number"
												value={siblings.indexOf(message.id) + 1}
												min="1"
												max={siblings.length}
												on:focus={(e) => {
													e.target.select();
												}}
												on:blur={(e) => {
													gotoMessage(message, e.target.value - 1);
													messageIndexEdit = false;
												}}
												on:keydown={(e) => {
													if (e.key === 'Enter') {
														gotoMessage(message, e.target.value - 1);
														messageIndexEdit = false;
													}
												}}
												class="bg-transparent font-semibold self-center dark:text-gray-100 min-w-fit outline-hidden"
											/>/{siblings.length}
										</div>
									{:else}
										
										<div
											class="text-sm tracking-widest font-semibold self-center dark:text-gray-100 min-w-fit"
											on:dblclick={async () => {
												messageIndexEdit = true;

												await tick();
												const input = document.getElementById(`message-index-input-${message.id}`);
												if (input) {
													input.focus();
													input.select();
												}
											}}
										>
											{siblings.indexOf(message.id) + 1}/{siblings.length}
										</div>
									{/if}

									<button
										class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
										on:click={() => {
											showNextMessage(message);
										}}
										aria-label={$i18n.t('Next message')}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											aria-hidden="true"
											viewBox="0 0 24 24"
											stroke="currentColor"
											stroke-width="2.5"
											class="size-3.5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="m8.25 4.5 7.5 7.5-7.5 7.5"
											/>
										</svg>
									</button>
								</div> -->
							{/if}

							{#if message.done}
								{#if $config?.features.enable_image_generation && ($user?.role === 'admin' || $user?.permissions?.features?.image_generation) && !readOnly}
									<Tooltip content={$i18n.t('Generate Image')} placement="bottom">
										<button
											aria-label={$i18n.t('Generate Image')}
											class="{isLastMessage || ($settings?.highContrastMode ?? false)
												? 'visible'
												: 'invisible group-hover:visible'}  p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
											on:click={() => {
												if (!generatingImage) {
													generateImage(message);
												}
											}}
										>
											{#if generatingImage}
												<svg
													aria-hidden="true"
													class=" w-4 h-4"
													fill="currentColor"
													viewBox="0 0 24 24"
													xmlns="http://www.w3.org/2000/svg"
												>
													<style>
														.spinner_S1WN {
															animation: spinner_MGfb 0.8s linear infinite;
															animation-delay: -0.8s;
														}

														.spinner_Km9P {
															animation-delay: -0.65s;
														}

														.spinner_JApP {
															animation-delay: -0.5s;
														}

														@keyframes spinner_MGfb {
															93.75%,
															100% {
																opacity: 0.2;
															}
														}
													</style>
													<circle class="spinner_S1WN" cx="4" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_Km9P" cx="12" cy="12" r="3" />
													<circle class="spinner_S1WN spinner_JApP" cx="20" cy="12" r="3" />
												</svg>
											{:else}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													aria-hidden="true"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
													/>
												</svg>
											{/if}
										</button>
									</Tooltip>
								{/if}

								{#if !readOnly}
									{#if isLastMessage}
										{#each model?.actions ?? [] as action}
											<Tooltip content={action.name} placement="bottom">
												<button
													type="button"
													aria-label={action.name}
													class="{isLastMessage || ($settings?.highContrastMode ?? false)
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
													on:click={() => {
														actionMessage(action.id, message);
													}}
												>
													{#if action?.icon}
														<div class="size-4">
															<img
																src={action.icon}
																class="w-4 h-4 {action.icon.includes('svg')
																	? 'dark:invert-[80%]'
																	: ''}"
																style="fill: currentColor;"
																alt={action.name}
															/>
														</div>
													{:else}
														<Sparkles strokeWidth="2.1" className="size-4" />
													{/if}
												</button>
											</Tooltip>
										{/each}
									{/if}
								{/if}
							{/if}
						{/if}
					</div>

					{#if message.done && showRateComment}
						<RateComment
							bind:message
							bind:show={showRateComment}
							on:save={async (e) => {
								await feedbackHandler(null, {
									...e.detail
								});
							}}
						/>
					{/if}

					{#if (isLastMessage || ($settings?.keepFollowUpPrompts ?? false)) && message.done && !readOnly && (message?.followUps ?? []).length > 0}
						<div class="mt-2.5" in:fade={{ duration: 100 }}>
							<FollowUps
								followUps={message?.followUps}
								onClick={(prompt) => {
									if ($settings?.insertFollowUpPrompt ?? false) {
										// Insert the follow-up prompt into the input box
										setInputText(prompt);
									} else {
										// Submit the follow-up prompt directly
										submitMessage(message?.id, prompt);
									}
								}}
							/>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/key}

<style>
	.buttons::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.buttons {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
