<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';

	import { createEventDispatcher } from 'svelte';
	import { onMount, tick, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType, t } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	const dispatch = createEventDispatcher();

	import { createNewFeedback, getFeedbackById, updateFeedbackById } from '$lib/apis/evaluations';
	import { getChatById } from '$lib/apis/chats';
	import { generateTags } from '$lib/apis';

	import { config, models, settings, temporaryChatEnabled, TTSWorker, user } from '$lib/stores';
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
	import { WEBUI_BASE_URL } from '$lib/constants';

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
	import Copy from '$lib/components/icons/Copy.svelte';
	import VolumeUp from '$lib/components/icons/VolumeUp.svelte';

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
		done: boolean;
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
	}

	export let chatId = '';
	export let history;
	export let messageId;

	let message: MessageType = JSON.parse(JSON.stringify(history.messages[messageId]));
	$: if (history.messages) {
		if (JSON.stringify(message) !== JSON.stringify(history.messages[messageId])) {
			message = JSON.parse(JSON.stringify(history.messages[messageId]));
		}
	}

	export let siblings;

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

	let buttonsContainerElement: HTMLDivElement;
	let showDeleteConfirm = false;

	let model = null;
	$: model = $models.find((m) => m.id === message.model);

	let edit = false;
	let editedContent = '';
	let editTextAreaElement: HTMLTextAreaElement;

	let messageIndexEdit = false;

	let audioParts: Record<number, HTMLAudioElement | null> = {};
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

		const res = await _copyToClipboard(text, $settings?.copyFormatted ?? false);
		if (res) {
			toast.success($i18n.t('Copying to clipboard was successful!'));
		}
	};

	const playAudio = (idx: number) => {
		return new Promise<void>((res) => {
			speakingIdx = idx;
			const audio = audioParts[idx];

			if (!audio) {
				return res();
			}

			audio.play();
			audio.onended = async () => {
				await new Promise((r) => setTimeout(r, 300));

				if (Object.keys(audioParts).length - 1 === idx) {
					speaking = false;
				}

				res();
			};
		});
	};

	const toggleSpeakMessage = async () => {
		if (speaking) {
			try {
				speechSynthesis.cancel();

				if (speakingIdx !== undefined && audioParts[speakingIdx]) {
					audioParts[speakingIdx]!.pause();
					audioParts[speakingIdx]!.currentTime = 0;
				}
			} catch {}

			speaking = false;
			speakingIdx = undefined;
			return;
		}

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

					const speak = new SpeechSynthesisUtterance(content);
					speak.rate = $settings.audio?.tts?.playbackRate ?? 1;

					console.log(speak);

					speak.onend = () => {
						speaking = false;
						if ($settings.conversationMode) {
							document.getElementById('voice-input-button')?.click();
						}
					};

					if (voice) {
						speak.voice = voice;
					}

					speechSynthesis.speak(speak);
				}
			}, 100);
		} else {
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

			audioParts = messageContentParts.reduce(
				(acc, _sentence, idx) => {
					acc[idx] = null;
					return acc;
				},
				{} as typeof audioParts
			);

			let lastPlayedAudioPromise = Promise.resolve(); // Initialize a promise that resolves immediately

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
					const blob = await $TTSWorker
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

					if (blob) {
						const audio = new Audio(blob);
						audio.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;

						audioParts[idx] = audio;
						loadingSpeech = false;
						lastPlayedAudioPromise = lastPlayedAudioPromise.then(() => playAudio(idx));
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

					if (res) {
						const blob = await res.blob();
						const blobUrl = URL.createObjectURL(blob);
						const audio = new Audio(blobUrl);
						audio.playbackRate = $settings.audio?.tts?.playbackRate ?? 1;

						audioParts[idx] = audio;
						loadingSpeech = false;
						lastPlayedAudioPromise = lastPlayedAudioPromise.then(() => playAudio(idx));
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

			if (!updatedMessage.annotation?.tags) {
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

	onMount(async () => {
		// console.log('ResponseMessage mounted');

		await tick();
		if (buttonsContainerElement) {
			console.log(buttonsContainerElement);

			buttonsContainerElement.addEventListener('wheel', function (event) {
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
			});
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
		{#if false}
			<div class={`shrink-0 ltr:mr-3 rtl:ml-3 hidden @lg:flex `}>
				<ProfileImage
					src={model?.info?.meta?.profile_image_url ??
						($i18n.language === 'dg-DG' ? `/doge.png` : `/static/favicon.png`)}
					className={'size-8 assistant-message-profile-image'}
				/>
			</div>
		{/if}

		<div class="flex-auto w-0 pl-1 relative -translate-y-0.5">
			<Name>
				<!-- <Tooltip content={model?.name ?? message.model} placement="top-start">
					<span class="line-clamp-1 text-black dark:text-white">
						{model?.name ?? message.model}
					</span>
				</Tooltip> -->

				{#if message.timestamp}
					<div
						class=" self-center text-xs invisible text-gray-400 font-medium first-letter:capitalize ml-0.5 translate-y-[1px]"
					>
						<Tooltip content={dayjs(message.timestamp * 1000).format('LLLL')}>
							<span class="line-clamp-1">{formatDate(message.timestamp * 1000)}</span>
						</Tooltip>
					</div>
				{/if}
			</Name>

			<div>
				<div class="chat-{message.role} w-full min-w-full markdown-prose">
					<div>
						{#if (message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]).length > 0}
							{@const status = (
								message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]
							).at(-1)}
							{#if !status?.hidden}
								<div class="status-description flex items-center gap-2 py-0.5">
									{#if status?.action === 'web_search' && status?.urls}
										<WebSearchResults {status}>
											<div class="flex flex-col justify-center -space-y-0.5">
												<div
													class="{status?.done === false
														? 'shimmer'
														: ''} text-base line-clamp-1 text-wrap"
												>
													<!-- $i18n.t("Generating search query") -->
													<!-- $i18n.t("No search query generated") -->

													<!-- $i18n.t('Searched {{count}} sites') -->
													{#if status?.description.includes('{{count}}')}
														{$i18n.t(status?.description, {
															count: status?.urls.length
														})}
													{:else if status?.description === 'No search query generated'}
														{$i18n.t('No search query generated')}
													{:else if status?.description === 'Generating search query'}
														{$i18n.t('Generating search query')}
													{:else}
														{status?.description}
													{/if}
												</div>
											</div>
										</WebSearchResults>
									{:else if status?.action === 'knowledge_search'}
										<div class="flex flex-col justify-center -space-y-0.5">
											<div
												class="{status?.done === false
													? 'shimmer'
													: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
											>
												{$i18n.t(`Searching Knowledge for "{{searchQuery}}"`, {
													searchQuery: status.query
												})}
											</div>
										</div>
									{:else}
										<div class="flex flex-col justify-center -space-y-0.5">
											<div
												class="{status?.done === false
													? 'shimmer'
													: ''} text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap"
											>
												<!-- $i18n.t(`Searching "{{searchQuery}}"`) -->
												{#if status?.description.includes('{{searchQuery}}')}
													{$i18n.t(status?.description, {
														searchQuery: status?.query
													})}
												{:else if status?.description === 'No search query generated'}
													{$i18n.t('No search query generated')}
												{:else if status?.description === 'Generating search query'}
													{$i18n.t('Generating search query')}
												{:else if status?.description === 'Searching the web'}
													{$i18n.t('Searching the web...')}
												{:else}
													{status?.description}
												{/if}
											</div>
										</div>
									{/if}
								</div>
							{/if}
						{/if}

						{#if message?.files && message.files?.filter((f) => f.type === 'image').length > 0}
							<div class="my-1 w-full flex overflow-x-auto gap-2 flex-wrap">
								{#each message.files as file}
									<div>
										{#if file.type === 'image'}
											{file}
											<Image src={file.url} alt={message.content} />
										{:else}
											<FileItem
												item={file}
												url={file.url}
												name={file.name}
												type={file.type}
												size={file?.size}
												colorClassName="bg-white dark:bg-gray-850 "
											/>
										{/if}
									</div>
								{/each}
							</div>
						{/if}

						{#if edit === true}
							<div
								class="p-[24px] w-full rounded-[16px] text-[14px] text-typography-titles leading-[24px] bg-light-bg shadow-custom4 dark:border dark:border-[#2D82D2]"
							>
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

								<div class="mt-[20px] flex items-center justify-between">
									<div>
										<button
											id="save-new-message-button"
											class="flex items-center gap-[8px] text-[14px] text-typography-btn-text-secondary font-Inter_SemiBold"
											on:click={() => {
												saveAsCopyHandler();
											}}
										>
											<Copy />{$i18n.t('Copy')}
										</button>
									</div>

									<div class="flex space-x-[12px]">
										<button
											id="close-edit-message-button"
											class="btn-secondary"
											on:click={() => {
												cancelEditMessage();
											}}
										>
											{$i18n.t('Cancel')}
										</button>

										<button
											id="confirm-edit-message-button"
											class="btn-primary"
											on:click={() => {
												editMessageConfirmHandler();
											}}
										>
											{$i18n.t('Save')}
										</button>
									</div>
								</div>
							</div>
						{:else}
							<div
								class="w-full text-[14px] text-typography-titles leading-[24px] flex flex-col relative"
								id="response-content-container"
							>
								{#if message.content === '' && !message.error && (message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]).length === 0}
									<Skeleton />
								{:else if message.content && message.error !== true}
									<!-- always show message contents even if there's an error -->
									<!-- unless message.error === true which is legacy error handling, where the error message is stored in message.content -->
									<ContentRenderer
										id={message.id}
										{history}
										content={message.content}
										sources={message.sources}
										floatingButtons={message?.done && !readOnly}
										save={!readOnly}
										preview={!readOnly}
										{model}
										onTaskClick={async (e) => {
											console.log(e);
										}}
										onSourceClick={async (id, idx) => {
											console.log(id, idx);
											let sourceButton = document.getElementById(`source-${message.id}-${idx}`);
											const sourcesCollapsible = document.getElementById(
												`collapsible-${message.id}`
											);

											if (sourceButton) {
												sourceButton.click();
											} else if (sourcesCollapsible) {
												// Open sources collapsible so we can click the source button
												sourcesCollapsible
													.querySelector('div:first-child')
													.dispatchEvent(new PointerEvent('pointerup', {}));

												// Wait for next frame to ensure DOM updates
												await new Promise((resolve) => {
													requestAnimationFrame(() => {
														requestAnimationFrame(resolve);
													});
												});

												// Try clicking the source button again
												sourceButton = document.getElementById(`source-${message.id}-${idx}`);
												sourceButton && sourceButton.click();
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
									<Citations id={message?.id} sources={message?.sources ?? message?.citations} />
								{/if}

								{#if message.code_executions}
									<CodeExecutions codeExecutions={message.code_executions} />
								{/if}
							</div>
						{/if}
					</div>
				</div>

				{#if !edit}
					<div
						bind:this={buttonsContainerElement}
						class="mt-[24px] flex gap-[2px] justify-start overflow-x-auto buttons text-gray-600 dark:text-gray-500"
					>
						{#if message.done || siblings.length > 1}
							{#if siblings.length > 1}
								<div class="flex self-center min-w-fit" dir="ltr">
									<button
										aria-label={$i18n.t('Previous message')}
										class="self-center p-1 hover:bg-gradient-bg-2 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
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
										<!-- svelte-ignore a11y-no-static-element-interactions -->
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
										class="self-center p-1 hover:bg-gradient-bg-2 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
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
								</div>
							{/if}

							{#if message.done}
								{#if !readOnly}
									{#if $user?.role === 'user' ? ($user?.permissions?.chat?.edit ?? true) : true}
										<Tooltip content={$i18n.t('Edit')} placement="bottom">
											<button
												aria-label={$i18n.t('Edit')}
												class="p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
												on:click={() => {
													editMessageHandler();
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													width="18"
													height="18"
													viewBox="0 0 18 18"
													fill="none"
												>
													<mask
														id="mask0_2146_22832"
														style="mask-type:alpha"
														maskUnits="userSpaceOnUse"
														x="0"
														y="0"
														width="18"
														height="18"
													>
														<rect width="18" height="18" fill="#D9D9D9" />
													</mask>
													<g mask="url(#mask0_2146_22832)">
														<path
															d="M3.44803 15.3469C3.20965 15.3998 3.0044 15.3402 2.83228 15.168C2.66015 14.9959 2.60053 14.7907 2.6534 14.5523L3.28078 11.5407L6.45965 14.7195L3.44803 15.3469ZM6.45965 14.7195L3.28078 11.5407L11.6952 3.12622C11.9538 2.86759 12.274 2.73828 12.6558 2.73828C13.0375 2.73828 13.3577 2.86759 13.6163 3.12622L14.8741 4.38397C15.1327 4.64259 15.262 4.96278 15.262 5.34453C15.262 5.72628 15.1327 6.04647 14.8741 6.30509L6.45965 14.7195ZM12.4972 3.91672L4.8284 11.5782L6.42215 13.1719L14.0836 5.50316C14.1268 5.45991 14.1485 5.40584 14.1485 5.34097C14.1485 5.27597 14.1268 5.22184 14.0836 5.17859L12.8217 3.91672C12.7785 3.87347 12.7243 3.85184 12.6593 3.85184C12.5945 3.85184 12.5404 3.87347 12.4972 3.91672Z"
															fill="#23282E"
														/>
													</g>
												</svg>
											</button>
										</Tooltip>
									{/if}
								{/if}

								<Tooltip content={$i18n.t('Copy')} placement="bottom">
									<button
										aria-label={$i18n.t('Copy')}
										class="{isLastMessage
											? 'visible'
											: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition copy-response-button"
										on:click={() => {
											copyToClipboard(message.content);
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											width="18"
											height="18"
											viewBox="0 0 18 18"
											fill="none"
										>
											<path
												d="M6.79331 13.125C6.41444 13.125 6.09375 12.9938 5.83125 12.7313C5.56875 12.4688 5.4375 12.1481 5.4375 11.7692V3.23081C5.4375 2.85194 5.56875 2.53125 5.83125 2.26875C6.09375 2.00625 6.41444 1.875 6.79331 1.875H13.0817C13.4606 1.875 13.7812 2.00625 14.0438 2.26875C14.3063 2.53125 14.4375 2.85194 14.4375 3.23081V11.7692C14.4375 12.1481 14.3063 12.4688 14.0438 12.7313C13.7812 12.9938 13.4606 13.125 13.0817 13.125H6.79331ZM6.79331 12H13.0817C13.1394 12 13.1923 11.9759 13.2403 11.9278C13.2884 11.8798 13.3125 11.8269 13.3125 11.7692V3.23081C13.3125 3.17306 13.2884 3.12019 13.2403 3.07219C13.1923 3.02406 13.1394 3 13.0817 3H6.79331C6.73556 3 6.68269 3.02406 6.63469 3.07219C6.58656 3.12019 6.5625 3.17306 6.5625 3.23081V11.7692C6.5625 11.8269 6.58656 11.8798 6.63469 11.9278C6.68269 11.9759 6.73556 12 6.79331 12ZM4.16831 15.75C3.78944 15.75 3.46875 15.6188 3.20625 15.3563C2.94375 15.0938 2.8125 14.7731 2.8125 14.3942V4.73081H3.9375V14.3942C3.9375 14.4519 3.96156 14.5048 4.00969 14.5528C4.05769 14.6009 4.11056 14.625 4.16831 14.625H11.5817V15.75H4.16831Z"
												fill="#23282E"
											/>
										</svg>
									</button>
								</Tooltip>

								

								{#if $config?.features.enable_image_generation && ($user?.role === 'admin' || $user?.permissions?.features?.image_generation) && !readOnly}
									<Tooltip content={$i18n.t('Generate Image')} placement="bottom">
										<button
											aria-label={$i18n.t('Generate Image')}
											class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'}  p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
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

								{#if message.usage}
									<Tooltip
										content={message.usage
											? `<pre>${sanitizeResponseContent(
													JSON.stringify(message.usage, null, 2)
														.replace(/"([^(")"]+)":/g, '$1:')
														.slice(1, -1)
														.split('\n')
														.map((line) => line.slice(2))
														.map((line) => (line.endsWith(',') ? line.slice(0, -1) : line))
														.join('\n')
												)}</pre>`
											: ''}
										placement="bottom"
									>
										<button
											aria-hidden="true"
											class=" {isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition whitespace-pre-wrap"
											on:click={() => {
												console.log(message);
											}}
											id="info-{message.id}"
										>
											<svg
												aria-hidden="true"
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2.3"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}

								{#if !readOnly}
									{#if !$temporaryChatEnabled && ($config?.features.enable_message_rating ?? true)}
										<Tooltip content={$i18n.t('Good Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Good Response')}
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg {(
													message?.annotation?.rating ?? ''
												).toString() === '1'
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} dark:hover:text-white hover:text-black transition disabled:cursor-progress disabled:hover:bg-transparent"
												disabled={feedbackLoading}
												on:click={async () => {
													await feedbackHandler(1);
													window.setTimeout(() => {
														document
															.getElementById(`message-feedback-${message.id}`)
															?.scrollIntoView();
													}, 0);
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													width="18"
													height="18"
													viewBox="0 0 18 18"
													fill="none"
												>
													<path
														d="M13.2981 15.3767H5.40862V6.37669L10.3847 1.42969L11.0192 2.06419C11.0971 2.14206 11.1617 2.24519 11.2133 2.37356C11.2646 2.50194 11.2903 2.62288 11.2903 2.73638V2.92669L10.4942 6.37669H15.5192C15.8759 6.37669 16.1911 6.5135 16.4646 6.78713C16.7382 7.06063 16.875 7.37575 16.875 7.7325V8.94394C16.875 9.02181 16.8649 9.10594 16.8446 9.19631C16.8245 9.28669 16.8019 9.37088 16.7769 9.44888L14.6278 14.52C14.5202 14.7604 14.3399 14.9633 14.0871 15.1286C13.8342 15.294 13.5712 15.3767 13.2981 15.3767ZM6.53363 14.2517H13.2981C13.3509 14.2517 13.405 14.2373 13.4603 14.2084C13.5156 14.1795 13.5578 14.1314 13.5866 14.0642L15.75 9.00169V7.7325C15.75 7.66513 15.7284 7.60981 15.6851 7.56656C15.6419 7.52331 15.5866 7.50169 15.5192 7.50169H9.07219L10.0125 3.39113L6.53363 6.85556V14.2517ZM5.40862 6.37669V7.50169H3V14.2517H5.40862V15.3767H1.875V6.37669H5.40862Z"
														fill="#23282E"
													/>
												</svg>
											</button>
										</Tooltip>

										<Tooltip content={$i18n.t('Bad Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Bad Response')}
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg {(
													message?.annotation?.rating ?? ''
												).toString() === '-1'
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} dark:hover:text-white hover:text-black transition disabled:cursor-progress disabled:hover:bg-transparent"
												disabled={feedbackLoading}
												on:click={async () => {
													await feedbackHandler(-1);
													window.setTimeout(() => {
														document
															.getElementById(`message-feedback-${message.id}`)
															?.scrollIntoView();
													}, 0);
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													width="18"
													height="18"
													viewBox="0 0 18 18"
													fill="none"
												>
													<path
														d="M4.70194 2.92969H12.5914V11.9295L7.61531 16.8767L6.98081 16.242C6.90294 16.1641 6.83825 16.061 6.78675 15.9326C6.73537 15.8043 6.70969 15.6834 6.70969 15.57V15.3795L7.50581 11.9295H2.48081C2.12406 11.9295 1.80894 11.7928 1.53544 11.5193C1.26181 11.2456 1.125 10.9305 1.125 10.5739V9.36225C1.125 9.28438 1.13512 9.20025 1.15537 9.10988C1.1755 9.0195 1.19806 8.93538 1.22306 8.8575L3.37219 3.78638C3.47981 3.546 3.66006 3.34313 3.91294 3.17775C4.16581 3.01238 4.42881 2.92969 4.70194 2.92969ZM11.4664 4.05469H4.70194C4.64906 4.05469 4.595 4.06906 4.53975 4.09781C4.48438 4.12669 4.44225 4.17481 4.41338 4.24219L2.25 9.30469V10.5739C2.25 10.6411 2.27163 10.6964 2.31488 10.7396C2.35812 10.783 2.41344 10.8047 2.48081 10.8047H8.92781L7.9875 14.9153L11.4664 11.4508V4.05469ZM12.5914 11.9295V10.8047H15V4.05469H12.5914V2.92969H16.125V11.9295H12.5914Z"
														fill="#23282E"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									{#if false && isLastMessage}
										<Tooltip content={$i18n.t('Continue Response')} placement="bottom">
											<button
												aria-label={$i18n.t('Continue Response')}
												type="button"
												id="continue-response-button"
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
												on:click={() => {
													continueResponse();
												}}
											>
												<svg
													aria-hidden="true"
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
													/>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									{#if $user?.role === 'admin'}
									<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
										<button
											type="button"
											aria-label={$i18n.t('Regenerate')}
											class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
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
												stroke-width="2.3"
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

									{#if siblings.length > 1}
										<Tooltip content={$i18n.t('Delete')} placement="bottom">
											<button
												type="button"
												aria-label={$i18n.t('Delete')}
												id="delete-response-button"
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
												on:click={() => {
													showDeleteConfirm = true;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
													stroke="currentColor"
													aria-hidden="true"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
													/>
												</svg>
											</button>
										</Tooltip>
									{/if}

									{#if isLastMessage}
										{#each model?.actions ?? [] as action}
											<Tooltip content={action.name} placement="bottom">
												<button
													type="button"
													aria-label={action.name}
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
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
								{#if ($user?.role === 'admin' || ($user?.permissions?.chat?.tts ?? true))}
									<Tooltip content={$i18n.t('Read Aloud')} placement="bottom">
										<button
											aria-label={$i18n.t('Read Aloud')}
											id="speak-button-{message.id}"
											class="{isLastMessage
												? 'visible'
												: 'invisible group-hover:visible'} p-1.5 hover:bg-gradient-bg-2 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
											on:click={() => {
												if (!loadingSpeech) {
													toggleSpeakMessage();
												}
											}}
										>
											{#if loadingSpeech}
												<svg
													class=" w-4 h-4"
													fill="currentColor"
													viewBox="0 0 24 24"
													aria-hidden="true"
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
											{:else if speaking}
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													aria-hidden="true"
													stroke-width="2.3"
													stroke="currentColor"
													class="w-4 h-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
													/>
												</svg>
											{:else}
												<VolumeUp/>
											{/if}
										</button>
									</Tooltip>
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

					{#if false && isLastMessage && message.done && !readOnly && (message?.followUps ?? []).length > 0}
						<div class="mt-2.5" in:fade={{ duration: 100 }}>
							<FollowUps
								followUps={message?.followUps}
								onClick={(prompt) => {
									submitMessage(message?.id, prompt);
								}}
							/>
						</div>
					{/if}
				{/if}
			</div>

			{#if message?.done}
				<div aria-live="polite" class="sr-only">
					{message?.content ?? ''}
				</div>
			{/if}
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
