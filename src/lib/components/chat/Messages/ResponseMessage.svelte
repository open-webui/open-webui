<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { marked } from 'marked';
	import tippy from 'tippy.js';
	import auto_render from 'katex/dist/contrib/auto-render.mjs';
	import 'katex/dist/katex.min.css';

	import { fade } from 'svelte/transition';
	import { createEventDispatcher } from 'svelte';
	import { onMount, tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	const dispatch = createEventDispatcher();

	import { config, settings } from '$lib/stores';
	import { synthesizeOpenAISpeech } from '$lib/apis/openai';
	import { imageGenerations } from '$lib/apis/images';
	import { extractSentences } from '$lib/utils';

	import Name from './Name.svelte';
	import ProfileImage from './ProfileImage.svelte';
	import Skeleton from './Skeleton.svelte';
	import CodeBlock from './CodeBlock.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let modelfiles = [];
	export let message;
	export let siblings;

	export let isLastMessage = true;

	export let confirmEditResponseMessage: Function;
	export let showPreviousMessage: Function;
	export let showNextMessage: Function;
	export let rateMessage: Function;

	export let copyToClipboard: Function;
	export let continueGeneration: Function;
	export let regenerateResponse: Function;

	let edit = false;
	let editedContent = '';
	let editTextAreaElement: HTMLTextAreaElement;
	let tooltipInstance = null;

	let sentencesAudio = {};
	let speaking = null;
	let speakingIdx = null;

	let loadingSpeech = false;
	let generatingImage = false;

	$: tokens = marked.lexer(message.content);

	const renderer = new marked.Renderer();

	// For code blocks with simple backticks
	renderer.codespan = (code) => {
		return `<code>${code.replaceAll('&amp;', '&')}</code>`;
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
			tooltipInstance = tippy(`#info-${message.id}`, {
				content: `<span class="text-xs" id="tooltip-${message.id}">response_token/s: ${
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
										}ms</span>`,
				allowHTML: true
			});
		}
	};

	const renderLatex = () => {
		let chatMessageElements = document.getElementsByClassName('chat-assistant');
		// let lastChatMessageElement = chatMessageElements[chatMessageElements.length - 1];

		for (const element of chatMessageElements) {
			auto_render(element, {
				// customised options
				// • auto-render specific keys, e.g.:
				delimiters: [
					{ left: '$$', right: '$$', display: false },
					{ left: '$', right: '$', display: false },
					{ left: '\\(', right: '\\)', display: false },
					{ left: '\\[', right: '\\]', display: false },
					{ left: '[ ', right: ' ]', display: false }
				],
				// • rendering keys, e.g.:
				throwOnError: false
			});
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
			speechSynthesis.cancel();

			sentencesAudio[speakingIdx].pause();
			sentencesAudio[speakingIdx].currentTime = 0;

			speaking = null;
			speakingIdx = null;
		} else {
			speaking = true;

			if ($settings?.audio?.TTSEngine === 'openai') {
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
						$settings?.audio?.speaker,
						sentence
					).catch((error) => {
						toast.error(error);
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
							voices?.filter((v) => v.name === $settings?.audio?.speaker)?.at(0) ?? undefined;

						const speak = new SpeechSynthesisUtterance(message.content);

						speak.onend = () => {
							speaking = null;
							if ($settings.conversationMode) {
								document.getElementById('voice-input-button')?.click();
							}
						};
						speak.voice = voice;
						speechSynthesis.speak(speak);
					}
				}, 100);
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

	onMount(async () => {
		await tick();
		renderStyling();
	});
</script>

{#key message.id}
	<div class=" flex w-full message-{message.id}">
		<ProfileImage
			src={modelfiles[message.model]?.imageUrl ?? `${WEBUI_BASE_URL}/static/favicon.png`}
		/>

		<div class="w-full overflow-hidden">
			<Name>
				{#if message.model in modelfiles}
					{modelfiles[message.model]?.title}
				{:else}
					{message.model ? ` ${message.model}` : ''}
				{/if}

				{#if message.timestamp}
					<span class=" invisible group-hover:visible text-gray-400 text-xs font-medium">
						{dayjs(message.timestamp * 1000).format($i18n.t('DD/MM/YYYY HH:mm'))}
					</span>
				{/if}
			</Name>

			{#if message.content === ''}
				<Skeleton />
			{:else}
				{#if message.files}
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
					class="prose chat-{message.role} w-full max-w-full dark:prose-invert prose-headings:my-0 prose-p:m-0 prose-p:-mb-6 prose-pre:my-0 prose-table:my-0 prose-blockquote:my-0 prose-img:my-0 prose-ul:-my-4 prose-ol:-my-4 prose-li:-my-3 prose-ul:-mb-6 prose-ol:-mb-8 prose-ol:p-0 prose-li:-mb-4 whitespace-pre-line"
				>
					<div>
						{#if edit === true}
							<div class=" w-full">
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

								<div class=" mt-2 mb-1 flex justify-center space-x-2 text-sm font-medium">
									<button
										class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded-lg"
										on:click={() => {
											editMessageConfirmHandler();
										}}
									>
										{$i18n.t('Save')}
									</button>

									<button
										class=" px-4 py-2 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-100 transition outline outline-1 outline-gray-200 dark:outline-gray-600 rounded-lg"
										on:click={() => {
											cancelEditMessage();
										}}
									>
										{$i18n.t('Cancel')}
									</button>
								</div>
							</div>
						{:else}
							<div class="w-full">
								{#if message?.error === true}
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
											{message.content}
										</div>
									</div>
								{:else}
									{#each tokens as token}
										{#if token.type === 'code'}
											<!-- {token.text} -->
											<CodeBlock lang={token.lang} code={token.text} />
										{:else}
											{@html marked.parse(token.raw, {
												...defaults,
												gfm: true,
												breaks: true,
												renderer
											})}
										{/if}
									{/each}
									<!-- {@html marked(message.content.replaceAll('\\', '\\\\'))} -->
								{/if}

								{#if message.done}
									<div
										class=" flex justify-start space-x-1 overflow-x-auto buttons text-gray-700 dark:text-gray-500"
									>
										{#if siblings.length > 1}
											<div class="flex self-center min-w-fit -mt-1">
												<button
													class="self-center dark:hover:text-white hover:text-black transition"
													on:click={() => {
														showPreviousMessage(message);
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="w-4 h-4"
													>
														<path
															fill-rule="evenodd"
															d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z"
															clip-rule="evenodd"
														/>
													</svg>
												</button>

												<div class="text-xs font-bold self-center min-w-fit dark:text-gray-100">
													{siblings.indexOf(message.id) + 1} / {siblings.length}
												</div>

												<button
													class="self-center dark:hover:text-white hover:text-black transition"
													on:click={() => {
														showNextMessage(message);
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="w-4 h-4"
													>
														<path
															fill-rule="evenodd"
															d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
															clip-rule="evenodd"
														/>
													</svg>
												</button>
											</div>
										{/if}

										<Tooltip content="Edit" placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1 rounded dark:hover:text-white hover:text-black transition"
												on:click={() => {
													editMessageHandler();
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
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

										<Tooltip content="Copy" placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1 rounded dark:hover:text-white hover:text-black transition copy-response-button"
												on:click={() => {
													copyToClipboard(message.content);
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="2"
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

										<Tooltip content="Good Response" placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1 rounded {message.rating === 1
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} dark:hover:text-white hover:text-black transition"
												on:click={() => {
													rateMessage(message.id, 1);
												}}
											>
												<svg
													stroke="currentColor"
													fill="none"
													stroke-width="2"
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

										<Tooltip content="Bad Response" placement="bottom">
											<button
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1 rounded {message.rating === -1
													? 'bg-gray-100 dark:bg-gray-800'
													: ''} dark:hover:text-white hover:text-black transition"
												on:click={() => {
													rateMessage(message.id, -1);
												}}
											>
												<svg
													stroke="currentColor"
													fill="none"
													stroke-width="2"
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

										<Tooltip content="Read Aloud" placement="bottom">
											<button
												id="speak-button-{message.id}"
												class="{isLastMessage
													? 'visible'
													: 'invisible group-hover:visible'} p-1 rounded dark:hover:text-white hover:text-black transition"
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
														stroke-width="2"
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
														stroke-width="2"
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

										{#if $config.images}
											<Tooltip content="Generate Image" placement="bottom">
												<button
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1 rounded dark:hover:text-white hover:text-black transition"
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
															stroke-width="2"
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
											<Tooltip content="Generation Info" placement="bottom">
												<button
													class=" {isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1 rounded dark:hover:text-white hover:text-black transition whitespace-pre-wrap"
													on:click={() => {
														console.log(message);
													}}
													id="info-{message.id}"
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														fill="none"
														viewBox="0 0 24 24"
														stroke-width="2"
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

										{#if isLastMessage}
											<Tooltip content="Continue Response" placement="bottom">
												<button
													type="button"
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1 rounded dark:hover:text-white hover:text-black transition regenerate-response-button"
													on:click={() => {
														continueGeneration();
													}}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														fill="none"
														viewBox="0 0 24 24"
														stroke-width="2"
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

											<Tooltip content="Regenerate" placement="bottom">
												<button
													type="button"
													class="{isLastMessage
														? 'visible'
														: 'invisible group-hover:visible'} p-1 rounded dark:hover:text-white hover:text-black transition regenerate-response-button"
													on:click={regenerateResponse}
												>
													<svg
														xmlns="http://www.w3.org/2000/svg"
														fill="none"
														viewBox="0 0 24 24"
														stroke-width="2"
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
								{/if}
							</div>
						{/if}
					</div>
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
