<script lang="ts">
	import { getDocs } from '$lib/apis/documents';
	import { scanDocs } from '$lib/apis/rag';
	import { documents } from '$lib/stores';
	import { onMount } from 'svelte';

	export let saveHandler: Function;
	const scanHandler = async () => {
		const res = await scanDocs(localStorage.token);

		if (res) {
			await documents.set(await getDocs(localStorage.token));
		}
	};

	onMount(async () => {});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		// console.log('submit');
		saveHandler();
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-80">
		<div>
			<div class=" mb-2 text-sm font-medium">General Settings</div>

			<div class="  flex w-full justify-between">
				<div class=" self-center text-xs font-medium">Scan for documents from '/data/docs'</div>

				<button
					class=" self-center text-xs p-1 px-3 bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded flex flex-row space-x-1 items-center"
					on:click={() => {
						scanHandler();
						console.log('check');
					}}
					type="button"
				>
					<div class="self-center">Scan</div>

					<svg
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
					</svg>
				</button>
			</div>
		</div>
	</div>

	<!-- <div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
			type="submit"
		>
			Save
		</button>
	</div> -->
</form>
