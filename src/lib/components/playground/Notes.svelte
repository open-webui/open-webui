<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import RichTextInput from '../common/RichTextInput.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
	import SparklesSolid from '../icons/SparklesSolid.svelte';
	import Mic from '../icons/Mic.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import { toast } from 'svelte-sonner';

	let name = $state('');
	let content = $state('');

	let voiceInput = $state(false);
	const loading = false;
</script>

<div class="relative flex-1 w-full h-full flex justify-center overflow-auto px-5">
	{#if loading}
		<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
			<div class="m-auto">
				<Spinner />
			</div>
		</div>
	{/if}

	<div class=" w-full flex flex-col gap-2" class:opacity-20={loading}>
		<div class="shrink-0 w-full flex justify-between items-center">
			<div class="w-full">
				<input
					class="w-full text-2xl font-medium bg-transparent outline-hidden"
					placeholder={$i18n.t('Title')}
					required
					type="text"
					bind:value={name}
				/>
			</div>
		</div>

		<div class=" flex-1 w-full h-full">
			<RichTextInput
				className="input-prose-sm"
				placeholder={$i18n.t('Write something...')}
				preserveBreaks={true}
				bind:value={content}
			/>
		</div>
	</div>

	<div class="absolute bottom-0 left-0 right-0 p-5 max-w-full flex justify-end">
		<div class="flex gap-0.5 justify-end w-full">
			{#if voiceInput}
				<div class="flex-1 w-full">
					<VoiceRecording
						className="p-1 w-full max-w-full"
						bind:recording={voiceInput}
						on:cancel={() => {
							voiceInput = false;
						}}
						on:confirm={(e) => {
							const { text, filename } = e.detail;

							// url is hostname + /cache/audio/transcription/ + filename
							const url = `${window.location.origin}/cache/audio/transcription/${filename}`;

							// Open in new tab

							if (content.trim() !== '') {
								content = `${content}\n\n${text}\n\nRecording: ${url}\n\n`;
							} else {
								content = `${content}${text}\n\nRecording: ${url}\n\n`;
							}

							voiceInput = false;
						}}
					/>
				</div>
			{:else}
				<Tooltip content={$i18n.t('Voice Input')}>
					<button
						class="cursor-pointer p-2.5 flex rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition shadow-xl"
						onclick={async () => {
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
						type="button"
					>
						<Mic className="size-4" />
					</button>
				</Tooltip>
			{/if}

			<!-- <button
				class="cursor-pointer p-2.5 flex rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition shadow-xl"
			>
				<SparklesSolid className="size-4" />
			</button> -->
		</div>
	</div>
</div>
