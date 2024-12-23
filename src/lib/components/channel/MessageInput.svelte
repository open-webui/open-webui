<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { tick, getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { mobile, settings } from '$lib/stores';

	import Tooltip from '../common/Tooltip.svelte';
	import RichTextInput from '../common/RichTextInput.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';

	export let placeholder = $i18n.t('Send a Message');
	export let transparentBackground = false;

	let recording = false;

	let content = '';

	export let onSubmit: Function;

	let submitHandler = async () => {
		if (content === '') {
			return;
		}

		onSubmit({
			content
		});

		content = '';
		await tick();

		const chatInputElement = document.getElementById('chat-input');
		chatInputElement?.focus();
	};
</script>

<div class="{transparentBackground ? 'bg-transparent' : 'bg-white dark:bg-gray-900'} ">
	<div class="max-w-6xl px-2.5 mx-auto inset-x-0">
		<div class="">
			{#if recording}
				<VoiceRecording
					bind:recording
					on:cancel={async () => {
						recording = false;

						await tick();
						document.getElementById('chat-input')?.focus();
					}}
					on:confirm={async (e) => {
						const { text, filename } = e.detail;
						content = `${content}${text} `;
						recording = false;

						await tick();
						document.getElementById('chat-input')?.focus();
					}}
				/>
			{:else}
				<form
					class="w-full flex gap-1.5"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div
						class="flex-1 flex flex-col relative w-full rounded-3xl px-1 bg-gray-50 dark:bg-gray-400/5 dark:text-gray-100"
						dir={$settings?.chatDirection ?? 'LTR'}
					>
						<div class=" flex">
							<div class="ml-1 self-end mb-1.5 flex space-x-1">
								<button
									class="bg-transparent hover:bg-white/80 text-gray-800 dark:text-white dark:hover:bg-gray-800 transition rounded-full p-2 outline-none focus:outline-none"
									type="button"
									aria-label="More"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="size-5"
									>
										<path
											d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
										/>
									</svg>
								</button>
							</div>

							{#if $settings?.richTextInput ?? true}
								<div
									class="scrollbar-hidden text-left bg-transparent dark:text-gray-100 outline-none w-full py-2.5 px-1 rounded-xl resize-none h-fit max-h-80 overflow-auto"
								>
									<RichTextInput
										bind:value={content}
										id="chat-input"
										messageInput={true}
										shiftEnter={!$mobile ||
											!(
												'ontouchstart' in window ||
												navigator.maxTouchPoints > 0 ||
												navigator.msMaxTouchPoints > 0
											)}
										{placeholder}
										largeTextAsFile={$settings?.largeTextAsFile ?? false}
										on:keydown={async (e) => {
											e = e.detail.event;
											const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac
											if (
												!$mobile ||
												!(
													'ontouchstart' in window ||
													navigator.maxTouchPoints > 0 ||
													navigator.msMaxTouchPoints > 0
												)
											) {
												// Prevent Enter key from creating a new line
												// Uses keyCode '13' for Enter key for chinese/japanese keyboards
												if (e.keyCode === 13 && !e.shiftKey) {
													e.preventDefault();
												}

												// Submit the content when Enter key is pressed
												if (content !== '' && e.keyCode === 13 && !e.shiftKey) {
													submitHandler();
												}
											}

											if (e.key === 'Escape') {
												console.log('Escape');
											}
										}}
										on:paste={async (e) => {
											e = e.detail.event;
											console.log(e);
										}}
									/>
								</div>
							{:else}
								<textarea
									id="chat-input"
									class="scrollbar-hidden bg-transparent dark:text-gray-100 outline-none w-full py-3 px-1 rounded-xl resize-none h-[48px]"
									{placeholder}
									bind:value={content}
									on:keydown={async (e) => {
										e = e.detail.event;
										const isCtrlPressed = e.ctrlKey || e.metaKey; // metaKey is for Cmd key on Mac
										if (
											!$mobile ||
											!(
												'ontouchstart' in window ||
												navigator.maxTouchPoints > 0 ||
												navigator.msMaxTouchPoints > 0
											)
										) {
											// Prevent Enter key from creating a new line
											// Uses keyCode '13' for Enter key for chinese/japanese keyboards
											if (e.keyCode === 13 && !e.shiftKey) {
												e.preventDefault();
											}

											// Submit the content when Enter key is pressed
											if (content !== '' && e.keyCode === 13 && !e.shiftKey) {
												submitHandler();
											}
										}

										if (e.key === 'Escape') {
											console.log('Escape');
										}
									}}
									rows="1"
									on:input={async (e) => {
										e.target.style.height = '';
										e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
									}}
									on:focus={async (e) => {
										e.target.style.height = '';
										e.target.style.height = Math.min(e.target.scrollHeight, 320) + 'px';
									}}
								/>
							{/if}

							<div class="self-end mb-1.5 flex space-x-1 mr-1">
								{#if content === ''}
									<Tooltip content={$i18n.t('Record voice')}>
										<button
											id="voice-input-button"
											class=" text-gray-600 dark:text-gray-300 hover:text-gray-700 dark:hover:text-gray-200 transition rounded-full p-1.5 mr-0.5 self-center"
											type="button"
											on:click={async () => {
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
											aria-label="Voice Input"
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="w-5 h-5 translate-y-[0.5px]"
											>
												<path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
												<path
													d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}

								<div class=" flex items-center">
									<div class=" flex items-center">
										<Tooltip content={$i18n.t('Send message')}>
											<button
												id="send-message-button"
												class="{content !== ''
													? 'bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 '
													: 'text-white bg-gray-200 dark:text-gray-900 dark:bg-gray-700 disabled'} transition rounded-full p-1.5 self-center"
												type="submit"
												disabled={content === ''}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="size-6"
												>
													<path
														fill-rule="evenodd"
														d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
														clip-rule="evenodd"
													/>
												</svg>
											</button>
										</Tooltip>
									</div>
								</div>
							</div>
						</div>
					</div>
				</form>
			{/if}
		</div>
	</div>
</div>
