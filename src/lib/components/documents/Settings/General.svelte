<script lang="ts">
	import { getDocs } from '$lib/apis/documents';
	import {
		getChunkParams,
		getRAGTemplate,
		scanDocs,
		updateChunkParams,
		updateRAGTemplate
	} from '$lib/apis/rag';
	import { documents } from '$lib/stores';
	import { onMount } from 'svelte';
	import toast from 'svelte-french-toast';

	import Reload from 'svelte-radix/Reload.svelte';
	import { Button } from '$lib/components/ui/button';

	export let saveHandler: Function;

	let loading = false;

	let chunkSize = 0;
	let chunkOverlap = 0;

	let template = '';

	const scanHandler = async () => {
		loading = true;
		const res = await scanDocs(localStorage.token);
		loading = false;

		if (res) {
			await documents.set(await getDocs(localStorage.token));
			toast.success('Scan complete!');
		}
	};

	const submitHandler = async () => {
		const res = await updateChunkParams(localStorage.token, chunkSize, chunkOverlap);
		await updateRAGTemplate(localStorage.token, template);
	};

	onMount(async () => {
		const res = await getChunkParams(localStorage.token);

		if (res) {
			chunkSize = res.chunk_size;
			chunkOverlap = res.chunk_overlap;
		}

		template = await getRAGTemplate(localStorage.token);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
		saveHandler();
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-80">
		<div>
			<div class=" mb-2 text-sm font-medium">General Settings</div>

			<div class="  flex w-full justify-between">
				<div class=" self-center text-xs font-medium">Scan for documents from '/data/docs'</div>

				<Button
					class=" self-center text-xs p-1 px-3 bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded flex flex-row space-x-1 items-center {loading
						? ' cursor-not-allowed'
						: ''}"
					on:click={() => {
						scanHandler();
						console.log('check');
					}}
					type="button"
					disabled={loading}
				>
					{#if !loading}
						<div class="self-center font-medium">Scan</div>

						<!-- <svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-3 h-3"
					>
						<path
							fill-rule="evenodd"
							d="M13.836 2.477a.75.75 0 0 1 .75.75v3.182a.75.75 0 0 1-.75.75h-3.182a.75.75 0 0 1 0-1.5h1.37l-.84-.841a4.5 4.5 0 0 0-7.08.932.75.75 0 0 1-1.3-.75 6 6 0 0 1 9.44-1.242l.842.84V3.227a.75.75 0 0 1 .75-.75Zm-.911 7.5A.75.75 0 0 1 13.199 11a6 6 0 0 1-9.44 1.241l-.84-.84v1.371a.75.75 0 0 1-1.5 0V9.591a.75.75 0 0 1 .75-.75H5.35a.75.75 0 0 1 0 1.5H3.98l.841.841a4.5 4.5 0 0 0 7.08-.932.75.75 0 0 1 1.025-.273Z"
							clip-rule="evenodd"
						/>
					</svg> -->
					{:else if loading}
						<Reload class="mr-2 h-4 w-4 animate-spin" />
						Ingesting Documents
					{/if}
				</Button>
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		<div class=" ">
			<div class=" text-sm font-medium">Chunk Params</div>

			<div class=" flex">
				<div class="  flex w-full justify-between">
					<div class="self-center text-xs font-medium min-w-fit">Chunk Size</div>

					<div class="self-center p-3">
						<input
							class=" w-full rounded py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none border border-gray-100 dark:border-gray-600"
							type="number"
							placeholder="Enter Chunk Size"
							bind:value={chunkSize}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>

				<div class="flex w-full">
					<div class=" self-center text-xs font-medium min-w-fit">Chunk Overlap</div>

					<div class="self-center p-3">
						<input
							class="w-full rounded py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none border border-gray-100 dark:border-gray-600"
							type="number"
							placeholder="Enter Chunk Overlap"
							bind:value={chunkOverlap}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" mb-2.5 text-sm font-medium">RAG Template</div>
				<textarea
					bind:value={template}
					class="w-full rounded p-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none resize-none"
					rows="4"
				/>
			</div>
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
