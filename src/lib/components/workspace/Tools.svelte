<script>
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import CodeEditor from './Tools/CodeEditor.svelte';

	let loading = false;

	const submitHandler = async () => {
		loading = true;
		// Call the API to submit the code
	};
</script>

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<div class=" flex flex-col max-h-[100dvh] h-full">
			<div class="mb-2.5 flex-1 overflow-auto h-0 rounded-lg">
				<CodeEditor />
			</div>
			<div class="pb-3">
				<button
					class="px-3 py-1.5 text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-gray-50 transition rounded-lg"
					on:click={() => {
						submitHandler();
					}}
				>
					{$i18n.t('Save')}
				</button>
			</div>
		</div>
	</div>
</div>
