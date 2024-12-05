<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';

	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Mic from '$lib/components/icons/Mic.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import VoiceRecording from '$lib/components/chat/MessageInput/VoiceRecording.svelte';
	export let show = false;

	let name = 'Untitled';
	let content = '';

	let voiceInput = false;
</script>

<Modal size="full" containerClassName="" className="h-full bg-white dark:bg-gray-900" bind:show>
	<div class="absolute top-0 right-0 p-5">
		<button
			class="self-center dark:text-white"
			type="button"
			on:click={() => {
				show = false;
			}}
		>
			<XMark className="size-3.5" />
		</button>
	</div>
	<div class="flex flex-col md:flex-row w-full h-full md:space-x-4 dark:text-gray-200">
		<form
			class="flex flex-col w-full h-full"
			on:submit|preventDefault={() => {
				if (name.trim() === '' || content.trim() === '') {
					toast.error($i18n.t('Please fill in all fields.'));
					name = name.trim();
					content = content.trim();
					return;
				}

				dispatch('submit', {
					name,
					content
				});
				show = false;
				name = '';
				content = '';
			}}
		>
			<div class=" flex-1 w-full h-full flex justify-center overflow-auto px-5 py-4">
				<div class=" max-w-3xl py-2 md:py-10 w-full flex flex-col gap-2">
					<div class="flex-shrink-0 w-full flex justify-between items-center">
						<div class="w-full">
							<input
								class="w-full text-3xl font-semibold bg-transparent outline-none"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Title')}
								required
							/>
						</div>
					</div>

					<div class=" flex-1 w-full h-full">
						<RichTextInput
							bind:value={content}
							placeholder={$i18n.t('Write something...')}
							preserveBreaks={true}
						/>
					</div>
				</div>
			</div>

			<div
				class="flex flex-row items-center justify-end text-sm font-medium flex-shrink-0 mt-1 p-4 gap-1.5"
			>
				<div class="">
					{#if voiceInput}
						<div class=" max-w-full w-64">
							<VoiceRecording
								bind:recording={voiceInput}
								className="p-1"
								on:cancel={() => {
									voiceInput = false;
								}}
								on:confirm={(e) => {
									const { text, filename } = e.detail;
									content = `${content}${text} `;

									voiceInput = false;
								}}
							/>
						</div>
					{:else}
						<Tooltip content={$i18n.t('Voice Input')}>
							<button
								class=" p-2 bg-gray-50 text-gray-700 dark:bg-gray-700 dark:text-white transition rounded-full"
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
											voiceInput = true;
											const tracks = stream.getTracks();
											tracks.forEach((track) => track.stop());
										}
										stream = null;
									} catch {
										toast.error($i18n.t('Permission denied when accessing microphone'));
									}
								}}
							>
								<Mic className="size-5" />
							</button>
						</Tooltip>
					{/if}
				</div>

				<div class=" flex-shrink-0">
					<Tooltip content={$i18n.t('Save')}>
						<button
							class=" px-3.5 py-2 bg-black text-white dark:bg-white dark:text-black transition rounded-full"
							type="submit"
						>
							{$i18n.t('Save')}
						</button>
					</Tooltip>
				</div>
			</div>
		</form>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
