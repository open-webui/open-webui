<script>
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import CodeEditor from './CodeEditor.svelte';
	import { goto } from '$app/navigation';

	let loading = false;

	let id = '';
	let name = '';
	let meta = {
		description: ''
	};

	let content = '';

	$: if (name) {
		id = name.replace(/\s+/g, '_').toLowerCase();
	}

	let codeEditor;

	const saveHandler = async () => {
		loading = true;
		// Call the API to save the toolkit
		console.log('saveHandler');
	};

	const submitHandler = async () => {
		if (codeEditor) {
			const res = await codeEditor.formatHandler();

			if (res) {
				console.log('Code formatted successfully');
				saveHandler();
			}
		}
	};
</script>

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<div class=" flex flex-col max-h-[100dvh] h-full">
			<div class="mb-2.5">
				<button
					class="flex space-x-1"
					on:click={() => {
						goto('/workspace/tools');
					}}
				>
					<div class=" self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center font-medium text-sm">{$i18n.t('Back')}</div>
				</button>
			</div>

			<div class="flex flex-col flex-1 overflow-auto h-0 rounded-lg">
				<div class="w-full mb-2 flex flex-col gap-1.5">
					<div class="flex gap-2 w-full">
						<input
							class="w-full px-3 py-2 text-sm font-medium bg-gray-50 dark:bg-gray-850 dark:text-gray-200 rounded-lg outline-none"
							type="text"
							placeholder="Toolkit Name (e.g. My ToolKit)"
							bind:value={name}
							required
						/>

						<input
							class="w-full px-3 py-2 text-sm font-medium bg-gray-50 dark:bg-gray-850 dark:text-gray-200 rounded-lg outline-none"
							type="text"
							placeholder="Toolkit ID (e.g. my_toolkit)"
							bind:value={id}
							required
						/>
					</div>
					<input
						class="w-full px-3 py-2 text-sm font-medium bg-gray-50 dark:bg-gray-850 dark:text-gray-200 rounded-lg outline-none"
						type="text"
						placeholder="Toolkit Description (e.g. A toolkit for performing various operations)"
						bind:value={meta.description}
						required
					/>
				</div>

				<div class="mb-2 flex-1 overflow-auto h-0 rounded-lg">
					<CodeEditor bind:value={content} bind:this={codeEditor} {saveHandler} />
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
