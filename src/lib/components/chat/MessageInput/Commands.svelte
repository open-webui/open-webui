<script>
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';

	const dispatch = createEventDispatcher();

	import Prompts from './Commands/Prompts.svelte';
	import Documents from './Commands/Documents.svelte';
	import Models from './Commands/Models.svelte';

	import { removeLastWordFromString } from '$lib/utils';
	import { uploadWebToVectorDB, uploadYoutubeTranscriptionToVectorDB } from '$lib/apis/rag';

	export let prompt = '';
	export let files = [];

	let commandElement = null;

	export const selectUp = () => {
		commandElement?.selectUp();
	};

	export const selectDown = () => {
		commandElement?.selectDown();
	};

	let command = '';
	$: command = (prompt?.trim() ?? '').split(' ')?.at(-1) ?? '';

	const uploadWeb = async (url) => {
		console.log(url);

		const doc = {
			type: 'doc',
			name: url,
			collection_name: '',
			status: false,
			url: url,
			error: ''
		};

		try {
			files = [...files, doc];
			const res = await uploadWebToVectorDB(localStorage.token, '', url);

			if (res) {
				doc.status = 'processed';
				doc.collection_name = res.collection_name;
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(e);
		}
	};

	const uploadYoutubeTranscription = async (url) => {
		console.log(url);

		const doc = {
			type: 'doc',
			name: url,
			collection_name: '',
			status: false,
			url: url,
			error: ''
		};

		try {
			files = [...files, doc];
			const res = await uploadYoutubeTranscriptionToVectorDB(localStorage.token, url);

			if (res) {
				doc.status = 'processed';
				doc.collection_name = res.collection_name;
				files = files;
			}
		} catch (e) {
			// Remove the failed doc from the files array
			files = files.filter((f) => f.name !== url);
			toast.error(e);
		}
	};
</script>

{#if ['/', '#', '@'].includes(command?.charAt(0))}
	{#if command?.charAt(0) === '/'}
		<Prompts bind:this={commandElement} bind:prompt bind:files {command} />
	{:else if command?.charAt(0) === '#'}
		<Documents
			bind:this={commandElement}
			bind:prompt
			{command}
			on:youtube={(e) => {
				console.log(e);
				uploadYoutubeTranscription(e.detail);
			}}
			on:url={(e) => {
				console.log(e);
				uploadWeb(e.detail);
			}}
			on:select={(e) => {
				console.log(e);
				files = [
					...files,
					{
						type: e?.detail?.type ?? 'file',
						...e.detail,
						status: 'processed'
					}
				];

				dispatch('select');
			}}
		/>
	{:else if command?.charAt(0) === '@'}
		<Models
			bind:this={commandElement}
			{command}
			on:select={(e) => {
				prompt = removeLastWordFromString(prompt, command);

				dispatch('select', {
					type: 'model',
					data: e.detail
				});
			}}
		/>
	{/if}
{/if}
