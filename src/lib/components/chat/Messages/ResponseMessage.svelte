<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { marked } from 'marked';
	import tippy from 'tippy.js';
	import auto_render from 'katex/dist/contrib/auto-render.mjs';
	import 'katex/dist/katex.min.css';
	import mermaid from 'mermaid';

	import { fade } from 'svelte/transition';
	import { createEventDispatcher } from 'svelte';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	const dispatch = createEventDispatcher();

	import { config, models, settings } from '$lib/stores';
	import { synthesizeOpenAISpeech } from '$lib/apis/audio';
	import { imageGenerations } from '$lib/apis/images';
	import {
		approximateToHumanReadable,
		extractSentences,
		revertSanitizedResponseContent,
		sanitizeResponseContent
	} from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Skeleton from './Skeleton.svelte';
	import CodeBlock from './CodeBlock.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import RateComment from './RateComment.svelte';
	import CitationsModal from '$lib/components/chat/Messages/CitationsModal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import WebSearchResults from './ResponseMessage/WebSearchResults.svelte';

	export let message;
	export let siblings;

	export let isLastMessage = true;

	export let readOnly = false;

	export let updateChatMessages: Function;
	export let confirmEditResponseMessage: Function;
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;
	export let rateMessage: Function;

	export let copyToClipboard: Function;
	export let continueGeneration: Function;
	export let regenerateResponse: Function;

	let model = null;
	$: model = $models.find((m) => m.id === message.model);

	let edit = false;
	let editedContent = '';
	let editTextAreaElement: HTMLTextAreaElement;
	let tooltipInstance = null;

	let sentencesAudio = {};
	let speaking = null;
	let speakingIdx = null;

	let loadingSpeech = false;
	let generatingImage = false;

	let showRateComment = false;
	let showCitationModal = false;

	let selectedCitation = null;

	$: tokens = marked.lexer(sanitizeResponseContent(message?.content));

	const renderer = new marked.Renderer();

	// For code blocks with simple backticks
	renderer.codespan = (code) => {
		return `<code>${code.replaceAll('&amp;', '&')}</code>`;
	};

	// Open all links in a new tab/window (from https://github.com/markedjs/marked/issues/655#issuecomment-383226346)
	const origLinkRenderer = renderer.link;
	renderer.link = (href, title, text) => {
		const html = origLinkRenderer.call(renderer, href, title, text);
		return html.replace(/^<a /, '<a target="_blank" rel="nofollow" ');
	};

	const { extensions, ...defaults } = marked.getDefaults() as marked.MarkedOptions & {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		extensions: any;
	};

	$: if (message) {
		renderStyling();
	}

	const renderStyling = async () => {
		await tick();

		if (tooltipInstance) {
			tooltipInstance[0]?.destroy();
		}

		renderLatex();

		if (message.info) {
			let tooltipContent = '';
			if (message.info.openai) {
				tooltipContent = `prompt_tokens: ${message.info.prompt_tokens ?? 'N/A'}<br/>
													completion_tokens: ${message.info.completion_tokens ?? 'N/A'}<br/>
													total_tokens: ${message.info.total_tokens ?? 'N/A'}`;
			} else {
				tooltipContent = `response_token/s: ${
					`${
						Math.round(
							((message.info.eval_count ?? 0) / (message.info.eval_duration / 1000000000)) * 100
						) / 100
					} tokens` ?? 'N/A'
				}<br/>
					prompt_token/s: ${
						Math.round(
							((message.info.prompt_eval_count ?? 0) /
								(message.info.prompt_eval_duration / 1000000000)) *
								100
						) / 100 ?? 'N/A'
					} tokens<br/>
                    total_duration: ${
											Math.round(((message.info.total_duration ?? 0) / 1000000) * 100) / 100 ??
											'N/A'
										}ms<br/>
                    load_duration: ${
											Math.round(((message.info.load_duration ?? 0) / 1000000) * 100) / 100 ?? 'N/A'
										}ms<br/>
                    prompt_eval_count: ${message.info.prompt_eval_count ?? 'N/A'}<br/>
                    prompt_eval_duration: ${
											Math.round(((message.info.prompt_eval_duration ?? 0) / 1000000) * 100) /
												100 ?? 'N/A'
										}ms<br/>
                    eval_count: ${message.info.eval_count ?? 'N/A'}<br/>
                    eval_duration: ${
											Math.round(((message.info.eval_duration ?? 0) / 1000000) * 100) / 100 ?? 'N/A'
										}ms<br/>
                    approximate_total: ${approximateToHumanReadable(message.info.total_duration)}`;
			}
			tooltipInstance = tippy(`#info-${message.id}`, {
				content: `<span class="text-xs" id="tooltip-${message.id}">${tooltipContent}</span>`,
				allowHTML: true
			});
		}
	};

	const renderLatex = () => {
		let chatMessageElements = document
			.getElementById(`message-${message.id}`)
			?.getElementsByClassName('chat-assistant');

		if (chatMessageElements) {
			for (const element of chatMessageElements) {
				auto_render(element, {
					// customised options
					// • auto-render specific keys, e.g.:
					delimiters: [
						{ left: '$$', right: '$$', display: false },
						{ left: '$ ', right: ' $', display: false },
						{ left: '\\(', right: '\\)', display: false },
						{ left: '\\[', right: '\\]', display: false },
						{ left: '[ ', right: ' ]', display: false }
					],
					// • rendering keys, e.g.:
					throwOnError: false
				});
			}
		}
	};

	const playAudio = (idx) => {
		return new Promise((res) => {
			speakingIdx = idx;
			const audio = sentencesAudio[idx];
			audio.play();
			audio.onended = async (e) => {
				await new Promise((r) => setTimeout(r, 300));

				if (Object.keys(sentencesAudio).length - 1 === idx) {
					speaking = null;

					if ($settings.conversationMode) {
						document.getElementById('voice-input-button')?.click();
					}
				}

				res(e);
			};
		});
	};

	const toggleSpeakMessage = async () => {
		if (speaking) {
			try {
				speechSynthesis.cancel();

				sentencesAudio[speakingIdx].pause();
				sentencesAudio[speakingIdx].currentTime = 0;
			} catch {}

			speaking = null;
			speakingIdx = null;
		} else {
			if ((message?.content ?? '').trim() !== '') {
				speaking = true;

				if ($config.audio.tts.engine === 'openai') {
					loadingSpeech = true;

					const sentences = extractSentences(message.content).reduce((mergedTexts, currentText) => {
						const lastIndex = mergedTexts.length - 1;
						if (lastIndex >= 0) {
							const previousText = mergedTexts[lastIndex];
							const wordCount = previousText.split(/\s+/).length;
							if (wordCount < 2) {
								mergedTexts[lastIndex] = previousText + ' ' + currentText;
							} else {
								mergedTexts.push(currentText);
							}
						} else {
							mergedTexts.push(currentText);
						}
						return mergedTexts;
					}, []);

					console.log(sentences);

					sentencesAudio = sentences.reduce((a, e, i, arr) => {
						a[i] = null;
						return a;
					}, {});

					let lastPlayedAudioPromise = Promise.resolve(); // Initialize a promise that resolves immediately

					for (const [idx, sentence] of sentences.entries()) {
						const res = await synthesizeOpenAISpeech(
							localStorage.token,
							$settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice,
							sentence
						).catch((error) => {
							toast.error(error);

							speaking = null;
							loadingSpeech = false;

							return null;
						});

						if (res) {
							const blob = await res.blob();
							const blobUrl = URL.createObjectURL(blob);
							const audio = new Audio(blobUrl);
							sentencesAudio[idx] = audio;
							loadingSpeech = false;
							lastPlayedAudioPromise = lastPlayedAudioPromise.then(() => playAudio(idx));
						}
					}
				} else {
					let voices = [];
					const getVoicesLoop = setInterval(async () => {
						voices = await speechSynthesis.getVoices();
						if (voices.length > 0) {
							clearInterval(getVoicesLoop);

							const voice =
								voices
									?.filter(
										(v) =>
											v.voiceURI === ($settings?.audio?.tts?.voice ?? $config?.audio?.tts?.voice)
									)
									?.at(0) ?? undefined;

							console.log(voice);

							const speak = new SpeechSynthesisUtterance(message.content);

							console.log(speak);

							speak.onend = () => {
								speaking = null;
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
				}
			} else {
				toast.error('No content to speak');
			}
		}
	};

	const editMessageHandler = async () => {
		edit = true;
		editedContent = message.content;

		await tick();

		editTextAreaElement.style.height = '';
		editTextAreaElement.style.height = `${editTextAreaElement.scrollHeight}px`;
	};

	const editMessageConfirmHandler = async () => {
		if (editedContent === '') {
			editedContent = ' ';
		}

		confirmEditResponseMessage(message.id, editedContent);

		edit = false;
		editedContent = '';

		await tick();
		renderStyling();
	};

	const cancelEditMessage = async () => {
		edit = false;
		editedContent = '';
		await tick();
		renderStyling();
	};

	const generateImage = async (message) => {
		generatingImage = true;
		const res = await imageGenerations(localStorage.token, message.content).catch((error) => {
			toast.error(error);
		});
		console.log(res);

		if (res) {
			message.files = res.map((image) => ({
				type: 'image',
				url: `${image.url}`
			}));

			dispatch('save', message);
		}

		generatingImage = false;
	};

	$: if (!edit) {
		(async () => {
			await tick();
			renderStyling();

			await mermaid.run({
				querySelector: '.mermaid'
			});
		})();
	}

	onMount(async () => {
		await tick();
		renderStyling();

		await mermaid.run({
			querySelector: '.mermaid'
		});
	});
</script>

<CitationsModal bind:show={showCitationModal} citation={selectedCitation} />

{#key message.id}
	<div
		class=" flex w-full message-{message.id}"
		id="message-{message.id}"
		dir={$settings.chatDirection}
	>
		<ProfileImage
			src={model?.info?.meta?.profile_image_url ??
				($i18n.language === 'dg-DG' ? `/doge.png` : `${WEBUI_BASE_URL}/static/favicon.png`)}
		/>

		<div class="w-full overflow-hidden pl-1">
			<Name>
				{model?.name ?? message.model}

				{#if message.timestamp}
					<span
						class=" self-center invisible group-hover:visible text-gray-400 text-xs font-medium uppercase"
					>
						{dayjs(message.timestamp * 1000).format($i18n.t('h:mm a'))}
					</span>
				{/if}
			</Name>

			{#if (message?.files ?? []).filter((f) => f.type === 'image').length > 0}
				<div class="my-2.5 w-full flex overflow-x-auto gap-2 flex-wrap">
					{#each message.files as file}
						<div>
							{#if file.type === 'image'}
								<Image src={file.url} />
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			<div
				class="prose chat-{message.role} w-full max-w-full dark:prose-invert prose-headings:my-0 prose-headings:-mb-4 prose-p:m-0 prose-p:-mb-6 prose-pre:my-0 prose-table:my-0 prose-blockquote:my-0 prose-img:my-0 prose-ul:-my-4 prose-ol:-my-4 prose-li:-my-3 prose-ul:-mb-6 prose-ol:-mb-8 prose-ol:p-0 prose-li:-mb-4 whitespace-pre-line"
			>
				<div>
					{#if (message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]).length > 0}
						{@const status = (
							message?.statusHistory ?? [...(message?.status ? [message?.status] : [])]
						).at(-1)}
						<div class="flex items-center gap-2 pt-1 pb-1">
							{#if status.done === false}
								<div class="">
									<Spinner className="size-4" />
								</div>
							{/if}

							{#if status?.action === 'web_search' && status?.urls}
								<WebSearchResults {status}>
									<div class="flex flex-col justify-center -space-y-0.5">
										<div class="text-base line-clamp-1 text-wrap">
											{status?.description}
										</div>
									</div>
								</WebSearchResults>
							{:else}
								<div class="flex flex-col justify-center -space-y-0.5">
									<div class=" text-gray-500 dark:text-gray-500 text-base line-clamp-1 text-wrap">
										{status?.description}
									</div>
								</div>
							{/if}
						</div>
					{/if}

					{#if edit === true}
						<div class="w-full bg-gray-50 dark:bg-gray-800 rounded-3xl px-5 py-3 my-2">
							<textarea
								id="message-edit-{message.id}"
								bind:this={editTextAreaElement}
								class=" bg-transparent outline-none w-full resize-none"
								bind:value={editedContent}
								on:input={(e) => {
									e.target.style.height = '';
									e.target.style.height = `${e.target.scrollHeight}px`;
								}}
							/>

							<div class=" mt-2 mb-1 flex justify-end space-x-1.5 text-sm font-medium">
								<button
									id="close-edit-message-button"
									class="px-4 py-2 bg-white hover:bg-gray-100 text-gray-800 transition rounded-3xl"
									on:click={() => {
										cancelEditMessage();
									}}
								>
									{$i18n.t('Cancel')}
								</button>

								<button
									id="save-edit-message-button"
									class=" px-4 py-2 bg-gray-900 hover:bg-gray-850 text-gray-100 transition rounded-3xl"
									on:click={() => {
										editMessageConfirmHandler();
									}}
								>
									{$i18n.t('Save')}
								</button>
							</div>
						</div>
					{:else}
						<div class="w-full">
							{#if message.content === '' && !message.error}
								<Skeleton />
							{:else if message.content && message.error !== true}
								<!-- always show message contents even if there's an error -->
								<!-- unless message.error === true which is legacy error handling, where the error message is stored in message.content -->
								{#each tokens as token, tokenIdx}
									{#if token.type === 'code'}
										{#if token.lang === 'mermaid'}
											<pre class="mermaid">{revertSanitizedResponseContent(token.text)}</pre>
										{:else}
											<CodeBlock
												id={`${message.id}-${tokenIdx}`}
												lang={token?.lang ?? ''}
												code={revertSanitizedResponseContent(token?.text ?? '')}
											/>
										{/if}
									{:else}
										{@html marked.parse(token.raw, {
											...defaults,
											gfm: true,
											breaks: true,
											renderer
										})}
									{/if}
								{/each}
							{/if}

							{#if message.error}
								<div
									class="flex mt-2 mb-4 space-x-2 border px-4 py-3 border-red-800 bg-red-800/30 font-medium rounded-lg"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-5 h-5 self-center"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
										/>
									</svg>

									<div class=" self-center">
										{message?.error?.content ?? message.content}
									</div>
								</div>
							{/if}

							{#if message.citations}
								<div class="mt-1 mb-2 w-full flex gap-1 items-center flex-wrap">
									{#each message.citations.reduce((acc, citation) => {
										citation.document.forEach((document, index) => {
											const metadata = citation.metadata?.[index];
											const id = metadata?.source ?? 'N/A';
											let source = citation?.source;
											// Check if ID looks like a URL
											if (id.startsWith('http://') || id.startsWith('https://')) {
												source = { name: id };
											}

											const existingSource = acc.find((item) => item.id === id);

											if (existingSource) {
												existingSource.document.push(document);
												existingSource.metadata.push(metadata);
											} else {
												acc.push( { id: id, source: source, document: [document], metadata: metadata ? [metadata] : [] } );
											}
										});
										return acc;
									}, []) as citation, idx}
										<div class="flex gap-1 text-xs font-semibold">
											<button
												class="flex dark:text-gray-300 py-1 px-1 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-xl"
												on:click={() => {
													showCitationModal = true;
													selectedCitation = citation;
												}}
											>
												<div class="bg-white dark:bg-gray-700 rounded-full size-4">
													{idx + 1}
												</div>
												<div class="flex-1 mx-2 line-clamp-1">
													{citation.source.name}
												</div>
											</button>
										</div>
									{/each}
								</div>
							{/if}

							{#if message.done || siblings.length > 1}
								<div
									class=" flex justify-start overflow-x-auto buttons text-gray-600 dark:text-gray-500"
								>
									{#if siblings.length > 1}
										<div class="flex self-center min-w-fit" dir="ltr">
											<button
												class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
												on:click={() => {
													showPreviousMessage(message);
												}}
											>
												<svg
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

											<div
												class="text-sm tracking-widest font-semibold self-center dark:text-gray-100 min-w-fit"
											>
												{siblings.indexOf(message.id) + 1}/{siblings.length}
											</div>

											<button
												class="self-center p-1 hover:bg-black/5 dark:hover:bg-white/5 dark:hover:text-white hover:text-black rounded-md transition"
												on:click={() => {
													showNextMessage(message);
												}}
											>
												<svg
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
														d="m8.25 4.5 7.5 7.5-7.5 7.5"
													/>
												</svg>
											</button>
										</div>
									{/if}

									{#if message.done}
										{#if !readOnly}
											<Tooltip content={$i18n.t('Edit')} placement="bottom">
												<button
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
													on:click={() => {
														editMessageHandler();
													}}
												>
													<svg
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
															d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
														/>
													</svg>
												</button>
											</Tooltip>
										{/if}

										<Tooltip content={$i18n.t('Copy')} placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition copy-response-button"
												on:click={() => {
													copyToClipboard(message.content);
												}}
											>
												<svg
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
														d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"
													/>
												</svg>
											</button>
										</Tooltip>

										<Tooltip content={$i18n.t('Read Aloud')} placement="bottom">
											<button
												id="speak-button-{message.id}"
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
												on:click={() => {
													if (!loadingSpeech) {
														toggleSpeakMessage(message);
													}
												}}
											>
												{#if loadingSpeech}
													<svg
														class=" w-4 h-4"
														fill="currentColor"
														viewBox="0 0 24 24"
														xmlns="http://www.w3.org/2000/svg"
														><style>
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
														</style><circle class="spinner_S1WN" cx="4" cy="12" r="3" /><circle
															class="spinner_S1WN spinner_Km9P"
															cx="12"
															cy="12"
															r="3"
														/><circle
															class="spinner_S1WN spinner_JApP"
															cx="20"
															cy="12"
															r="3"
														/></svg
													>
												{:else if speaking}
													<svg
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
															d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
														/>
													</svg>
												{:else}
													<svg
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
															d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z"
														/>
													</svg>
												{/if}
											</button>
										</Tooltip>

										{#if $config?.features.enable_image_generation && !readOnly}
											<Tooltip content={$i18n.t('Generate Image')} placement="bottom">
												<button
													class="{isLastMessage
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
															class=" w-4 h-4"
															fill="currentColor"
															viewBox="0 0 24 24"
															xmlns="http://www.w3.org/2000/svg"
															><style>
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
															</style><circle class="spinner_S1WN" cx="4" cy="12" r="3" /><circle
																class="spinner_S1WN spinner_Km9P"
																cx="12"
																cy="12"
																r="3"
															/><circle
																class="spinner_S1WN spinner_JApP"
																cx="20"
																cy="12"
																r="3"
															/></svg
														>
													{:else}
														<svg
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
																d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
															/>
														</svg>
													{/if}
												</button>
											</Tooltip>
										{/if}

										{#if message.info}
											<Tooltip content={$i18n.t('Generation Info')} placement="bottom">
												<button
													class=" {isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition whitespace-pre-wrap"
													on:click={() => {
														console.log(message);
													}}
													id="info-{message.id}"
												>
													<svg
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
											<Tooltip content={$i18n.t('Good Response')} placement="bottom">
												<button
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg {(message
														?.annotation?.rating ?? null) === 1
														? 'bg-gray-100 dark:bg-gray-800'
														: ''} dark:hover:text-white hover:text-black transition"
													on:click={() => {
														rateMessage(message.id, 1);
														showRateComment = true;

														window.setTimeout(() => {
															document
																.getElementById(`message-feedback-${message.id}`)
																?.scrollIntoView();
														}, 0);
													}}
												>
													<svg
														stroke="currentColor"
														fill="none"
														stroke-width="2.3"
														viewBox="0 0 24 24"
														stroke-linecap="round"
														stroke-linejoin="round"
														class="w-4 h-4"
														xmlns="http://www.w3.org/2000/svg"
														><path
															d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"
														/></svg
													>
												</button>
											</Tooltip>

											<Tooltip content={$i18n.t('Bad Response')} placement="bottom">
												<button
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg {(message
														?.annotation?.rating ?? null) === -1
														? 'bg-gray-100 dark:bg-gray-800'
														: ''} dark:hover:text-white hover:text-black transition"
													on:click={() => {
														rateMessage(message.id, -1);
														showRateComment = true;
														window.setTimeout(() => {
															document
																.getElementById(`message-feedback-${message.id}`)
																?.scrollIntoView();
														}, 0);
													}}
												>
													<svg
														stroke="currentColor"
														fill="none"
														stroke-width="2.3"
														viewBox="0 0 24 24"
														stroke-linecap="round"
														stroke-linejoin="round"
														class="w-4 h-4"
														xmlns="http://www.w3.org/2000/svg"
														><path
															d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"
														/></svg
													>
												</button>
											</Tooltip>
										{/if}

										{#if isLastMessage && !readOnly}
											<Tooltip content={$i18n.t('Continue Response')} placement="bottom">
												<button
													type="button"
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
													on:click={() => {
														continueGeneration();
													}}
												>
													<svg
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

											<Tooltip content={$i18n.t('Regenerate')} placement="bottom">
												<button
													type="button"
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition regenerate-response-button"
													on:click={() => {
														showRateComment = false;
														regenerateResponse(message);
													}}
												>
													<svg
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
															d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
														/>
													</svg>
												</button>
											</Tooltip>
										{/if}
									{/if}
								</div>
							{/if}

							{#if message.done && showRateComment}
								<RateComment
									messageId={message.id}
									bind:show={showRateComment}
									bind:message
									on:submit={() => {
										updateChatMessages();
									}}
								/>
							{/if}
						</div>
					{/if}
				</div>
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
