<script>
	import { getContext, createEventDispatcher, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import CodeEditor from './CodeEditor.svelte';
	import { goto } from '$app/navigation';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	const dispatch = createEventDispatcher();

	let formElement = null;
	let loading = false;
	let showConfirm = false;

	export let edit = false;
	export let clone = false;

	export let id = '';
	export let name = '';
	export let meta = {
		description: ''
	};
	export let content = '';

	$: if (name && !edit && !clone) {
		id = name.replace(/\s+/g, '_').toLowerCase();
	}

	let codeEditor;

	const saveHandler = async () => {
		loading = true;
		dispatch('save', {
			id,
			name,
			meta,
			content
		});
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
		<form
			bind:this={formElement}
			class=" flex flex-col max-h-[100dvh] h-full"
			on:submit|preventDefault={() => {
				if (edit) {
					submitHandler();
				} else {
					showConfirm = true;
				}
			}}
		>
			<div class="mb-2.5">
				<button
					class="flex space-x-1"
					on:click={() => {
						goto('/workspace/tools');
					}}
					type="button"
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
							class="w-full px-3 py-2 text-sm font-medium disabled:text-gray-300 dark:disabled:text-gray-700 bg-gray-50 dark:bg-gray-850 dark:text-gray-200 rounded-lg outline-none"
							type="text"
							placeholder="Toolkit ID (e.g. my_toolkit)"
							bind:value={id}
							required
							disabled={edit}
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
					<CodeEditor
						bind:value={content}
						bind:this={codeEditor}
						on:save={() => {
							if (formElement) {
								formElement.requestSubmit();
							}
						}}
					/>
				</div>

				<div class="pb-3 flex justify-between">
					<div class="flex-1 pr-3">
						<div class="text-xs text-gray-500 line-clamp-2">
							<span class=" font-semibold dark:text-gray-200">Warning:</span> Tools are a function
							calling system with arbitrary code execution <br />—
							<span class=" font-medium dark:text-gray-400"
								>don't install random tools from sources you don't trust.</span
							>
						</div>
					</div>

					<button
						class="px-3 py-1.5 text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-gray-50 transition rounded-lg"
						type="submit"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</div>
		</form>
	</div>
</div>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		submitHandler();
	}}
>
	<div class="text-sm text-gray-500">
		<div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
			<div>Please carefully review the following warnings:</div>

			<ul class=" mt-1 list-disc pl-4 text-xs">
				<li>Tools have a function calling system that allows arbitrary code execution.</li>
				<li>Do not install tools from sources you do not fully trust.</li>
			</ul>
		</div>

		<div class="my-3">
			I acknowledge that I have read and I understand the implications of my action. I am aware of
			the risks associated with executing arbitrary code and I have verified the trustworthiness of
			the source.
		</div>
	</div>
</ConfirmDialog>
