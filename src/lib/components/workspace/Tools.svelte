<script>
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import CodeEditor from './Tools/CodeEditor.svelte';

	let loading = false;

	let name = '';

	let codeEditor;

	const submitHandler = async () => {
		loading = true;
		// Call the API to submit the code

		if (codeEditor) {
			codeEditor.submitHandler();
		}
	};
</script>

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<div class=" flex flex-col max-h-[100dvh] h-full">
			<div class="">
				<div class="flex justify-between items-center">
					<div class=" text-lg font-semibold self-center">{$i18n.t('Tools')}</div>
				</div>
			</div>

			<hr class="  dark:border-gray-850 my-2" />

			<div class="flex flex-col flex-1 overflow-auto h-0 rounded-lg">
				<div class="w-full mb-2">
					<!-- Toolkit Name Input -->
					<input
						class="w-full px-3 py-2 text-sm font-medium bg-gray-100 dark:bg-gray-850 dark:text-gray-200 rounded-lg outline-none"
						type="text"
						placeholder="Toolkit Name (e.g. my_toolkit)"
						bind:value={name}
					/>
				</div>

				<div class="mb-2 flex-1 overflow-auto h-0 rounded-lg">
					<CodeEditor bind:this={codeEditor} />
				</div>

				<div class="pb-3 flex justify-end">
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
</div>
