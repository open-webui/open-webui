<script lang="ts">
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { toast } from 'svelte-sonner';

	import { showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';

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
	import Mic from '../icons/Mic.svelte';
	import VoiceRecording from '../chat/MessageInput/VoiceRecording.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	import Calendar from '../icons/Calendar.svelte';
	import Users from '../icons/Users.svelte';

	export let id: null | string = null;

	let note = {
		title: '',
		data: {
			content: {
				json: null,
				html: '',
				md: ''
			}
		},
		meta: null,
		access_control: null
	};

	let voiceInput = false;
	let loading = false;

	const init = async () => {
		loading = true;
		const res = await getNoteById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			note = res;
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
</script>

<div class="relative flex-1 w-full h-full flex justify-center">
	{#if loading}
		<div class=" absolute top-0 bottom-0 left-0 right-0 flex">
			<div class="m-auto">
				<Spinner />
			</div>
		</div>
	{:else}
		<div class=" w-full flex flex-col {loading ? 'opacity-20' : ''}">
			<div class="shrink-0 w-full flex justify-between items-center px-4.5 mb-1">
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

			<div
				class="flex gap-1 px-3.5 items-center text-xs font-medium text-gray-500 dark:text-gray-500 mb-4"
			>
				<button class=" flex items-center gap-1 w-fit py-1 px-1.5 rounded-lg">
					<Calendar className="size-3.5" strokeWidth="2" />

					<span>{dayjs(note.created_at / 1000000).calendar()}</span>
				</button>

				<button class=" flex items-center gap-1 w-fit py-1 px-1.5 rounded-lg">
					<Users className="size-3.5" strokeWidth="2" />

					<span> You </span>
				</button>
			</div>

			<div class=" flex-1 w-full h-full overflow-auto px-4.5 pb-5">
				<RichTextInput
					className="input-prose-sm"
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
		class="flex gap-0.5 justify-end w-full {$showSidebar && voiceInput
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		{#if voiceInput}
			<div class="flex-1 w-full">
				<VoiceRecording
					bind:recording={voiceInput}
					className="p-1 w-full max-w-full"
					transcribe={false}
					onCancel={() => {
						voiceInput = false;
					}}
					onConfirm={(data) => {
						console.log(data);
					}}
				/>
			</div>
		{:else}
			<Tooltip content={$i18n.t('Record')}>
				<button
					class="cursor-pointer p-2.5 flex rounded-full border border-gray-50 dark:border-none dark:bg-gray-850 hover:bg-gray-50 dark:hover:bg-gray-800 transition shadow-xl"
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
					<Mic className="size-4.5" />
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
