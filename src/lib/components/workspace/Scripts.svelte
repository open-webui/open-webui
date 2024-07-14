<script lang="ts">
	import fileSaver from 'file-saver';
	import { toast } from 'svelte-sonner';
	import { copyToClipboard } from '$lib/utils';
	import { type Writable } from 'svelte/store';
	import { v4 as uuidv4 } from 'uuid';

	const { saveAs } = fileSaver;
	import PyodideWorker from '$lib/workers/pyodide.worker?worker';

	import { type PythonScript } from '$lib/types';
	import { WEBUI_NAME, functions, models } from '$lib/stores';
	import { getContext, tick } from 'svelte';

	import { goto } from '$app/navigation';
	import {
		createNewPyScripts,
		getPyScriptById,
		getPyScripts,
		updatePyScriptById,
		deletePyScriptById
	} from '$lib/apis/scripts';

	import { getModels } from '$lib/apis';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Heart from '../icons/Heart.svelte';
	import FunctionMenu from './Functions/FunctionMenu.svelte';
	import type { i18n as i18nType } from 'i18next';
	import CodeEditor from '../common/CodeEditor.svelte';

	const boilerplate = `# Open WebUI Python Script
def quicksort(arr):
	if len(arr) <= 1:
		return arr
	else:
		pivot = arr[len(arr) // 2]
		left = [x for x in arr if x < pivot]
		middle = [x for x in arr if x == pivot]
		right = [x for x in arr if x > pivot]
		return quicksort(left) + middle + quicksort(right)

# Example usage
arr = [3, 6, 8, 10, 1, 2, 1]
print("Original array:", arr)
sorted_arr = quicksort(arr)
print("Sorted array:", sorted_arr)
`;

	let stdout: string | null = null;
	let stderr: string | null = null;
	let result: string | null = null;
	let executing = false;

	const executePythonAsWorker = async (code: string) => {
		result = null;
		stdout = null;
		stderr = null;

		executing = true;

		let packages = [
			code.includes('requests') ? 'requests' : null,
			code.includes('bs4') ? 'beautifulsoup4' : null,
			code.includes('numpy') ? 'numpy' : null,
			code.includes('pandas') ? 'pandas' : null,
			code.includes('sklearn') ? 'scikit-learn' : null,
			code.includes('scipy') ? 'scipy' : null,
			code.includes('re') ? 'regex' : null,
			code.includes('seaborn') ? 'seaborn' : null
		].filter(Boolean);

		console.log(packages);

		const pyodideWorker = new PyodideWorker();

		pyodideWorker.postMessage({
			id: uuidv4(),
			code: code,
			packages: packages
		});

		setTimeout(() => {
			if (executing) {
				executing = false;
				stderr = 'Execution Time Limit Exceeded';
				pyodideWorker.terminate();
			}
		}, 60000);

		pyodideWorker.onmessage = (event) => {
			console.log('pyodideWorker.onmessage', event);
			const { id, ...data } = event.data;

			console.log(id, data);

			data['stdout'] && (stdout = data['stdout']);
			data['stderr'] && (stderr = data['stderr']);
			data['result'] && (result = data['result']);

			executing = false;
		};

		pyodideWorker.onerror = (event) => {
			console.log('pyodideWorker.onerror', event);
			executing = false;
		};
	};

	const i18n = getContext<Writable<i18nType>>('i18n');

	let scriptImportInputElement: HTMLInputElement;
	let importFiles: FileList | null = null;

	let showConfirm = false;
	let query = '';

	let showManifestModal = false;
	let showValvesModal = false;
	let selectedScript: PythonScript | null = null;
	let creatingNewScript = false;

	let showDeleteConfirm = false;

	function onCreateNewScript() {
		selectedScript = null;
		creatingNewScript = true;
	}

	const deleteHandler = async (s: PythonScript) => {
		const res = await deletePyScriptById(localStorage.token, s.id).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Function deleted successfully'));

			// functions.set(await getFunctions(localStorage.token));
			models.set(await getModels(localStorage.token));
		}
	};
	let functionList: any[] = $functions;

	$: functionList = $functions.filter(
		(f: any) => query === '' || f.name.toLowerCase().includes(query.toLowerCase())
	);
</script>

<svelte:head>
	<title>
		{$i18n.t('Python Scripts')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<div class=" h-full flex flex-col">
	<!-- Panel Title -->
	<div class="mb-3 flex justify-between items-center">
		<div class="text-lg font-semibold self-center">{$i18n.t('Python Scripts')}</div>
	</div>

	<div class="flex flex-1">
		<div class="border-r border-gray-600 pr-2">
			<div class="flex w-80 space-x-2">
				<div class="flex flex-1">
					<div class="self-center ml-1 mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<input
						class="w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Scripts')}
					/>
				</div>

				<div>
					<button
						class="px-2 py-2 rounded-xl border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center space-x-1"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
							/>
						</svg>
					</button>
				</div>
			</div>
			<hr class="w-80 dark:border-gray-850 my-2.5" />

			<div class="my-3 mb-5">
				{#each functionList as func}
					<div
						class="flex space-x-4 cursor-pointer w-80 px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl"
					>
						<button
							class="flex flex-1 space-x-3.5 cursor-pointer w-80"
							on:click={() => {
								onCreateNewScript();
							}}
						>
							<div class="flex items-center text-left">
								<div class="flex-1 self-center pl-1">
									<div class="font-semibold flex items-center gap-1.5">
										<div
											class="text-xs font-bold px-1 rounded uppercase line-clamp-1 bg-gray-500/20 text-gray-700 dark:text-gray-200"
										>
											{func.type}
										</div>

										{#if func?.meta?.manifest?.version}
											<div
												class="text-xs font-bold px-1 rounded line-clamp-1 bg-gray-500/20 text-gray-700 dark:text-gray-200"
											>
												v{func?.meta?.manifest?.version ?? ''}
											</div>
										{/if}

										<div class="line-clamp-1">
											{func.name}
										</div>
									</div>

									<div class="flex gap-1.5 px-1">
										<div class="text-gray-500 text-xs font-medium flex-shrink-0">{func.id}</div>
										<div class="text-xs overflow-hidden text-ellipsis line-clamp-1">
											{func.meta.description}
										</div>
									</div>
								</div>
							</div>
						</button>
						<div class="flex flex-row gap-0.5 self-center">
							<FunctionMenu
								{func}
								editHandler={() => {}}
								shareHandler={() => {}}
								cloneHandler={() => {}}
								exportHandler={() => {}}
								deleteHandler={async () => {
									selectedScript = func;
									showDeleteConfirm = true;
								}}
								toggleGlobalHandler={() => {}}
								onClose={() => {}}
							>
								<button
									class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									type="button"
								>
									<EllipsisHorizontal className="size-5" />
								</button>
							</FunctionMenu>
						</div>
					</div>
				{/each}
			</div>
		</div>
		<div class="ml-2 flex-1 h-full flex flex-col">
			{#if selectedScript || creatingNewScript}
				<!-- Operation Panel -->
				<div class="mb-4">
					<div class="flex justify-between items-center">
						<div class="font-semibold self-center">
							{selectedScript ? $i18n.t('Edit Python Script') : $i18n.t('Create Python Script')}
						</div>
						<div class=" flex space-x-2">
							<button
								class="px-2 py-1 rounded-md border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center space-x-1"
								on:click={() => {
									onCreateNewScript();
								}}
							>
								Cancel
							</button>
							<button
								class="px-2 py-1 rounded-md border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center space-x-1"
								on:click={() => {
									onCreateNewScript();
								}}
							>
								Create
							</button>
						</div>
					</div>
					<!-- inputs for name and description -->
					<div class="flex flex-col gap-2 mt-2">
						<div class="flex w-full items-center">
							<label for="name" class="text-sm text-gray-500 dark:text-gray-400 mr-4 w-20">
								{$i18n.t('Name')}
							</label>
							<input
								class="flex-1 px-3 py-2 text-sm font-medium bg-gray-50 dark:bg-gray-850 dark:text-gray-200 rounded-lg outline-none"
								type="text"
								id="name"
								placeholder="Script Name (e.g. quicksort.py)"
								required
							/>
						</div>
						<div class="flex w-full items-center">
							<label for="description" class="text-sm text-gray-500 dark:text-gray-400 mr-4 w-20">
								{$i18n.t('Description')}
							</label>
							<input
								class="flex-1 px-3 py-2 text-sm font-medium bg-gray-50 dark:bg-gray-850 dark:text-gray-200 rounded-lg outline-none"
								type="text"
								id="description"
								placeholder="Description of the script (e.g. Sorts an array using quicksort)"
								required
							/>
						</div>
					</div>
				</div>

				<!-- Code Editor -->
				<div class="rounded-t-lg bg-white px-2">
					<div class="flex justify-between items-center text-sm text-gray-600">
						<div class="font-semibold self-center">{$i18n.t('Python Script')}</div>
						<div class="flex space-x-2">
							<button class=" text-blue-700" on:click={async () => {
								try {
									await copyToClipboard(boilerplate);
									toast.success($i18n.t('Copied to clipboard'));
								} catch (error) {
									console.log(error)
									toast.error($i18n.t('Failed to copy the code to clipboard'));
								}
							}}>Copy</button>
							<button class=" text-blue-700" on:click={() => {
								executePythonAsWorker(boilerplate);
							}}>Run</button>
						</div>
					</div>
				</div>
				<div class="flex-1 max-h-[720px] min-h-0 flex flex-col">
					<CodeEditor value={boilerplate} />
				</div>
				{#if executing}
					<div class="bg-[#202123] text-white px-4 py-4 rounded-b-lg">
						<div class=" text-gray-500 text-xs mb-1">STDOUT/STDERR</div>
						<div class="text-sm">Running...</div>
					</div>
				{:else if stdout || stderr || result}
					<div class="bg-[#202123] text-white px-4 py-4 rounded-b-lg">
						<div class=" text-gray-500 text-xs mb-1">STDOUT/STDERR</div>
						<pre class="text-sm">{stdout || stderr || result}</pre>
					</div>
				{/if}

			{:else}
				<div class="flex items-center justify-center h-full">
					<button
						class="px-2 py-2 rounded-xl border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center space-x-1"
						on:click={() => {
							onCreateNewScript();
						}}
					>
						Create new script
					</button>
				</div>
			{/if}
		</div>
	</div>
</div>

<input
	id="documents-import-input"
	bind:this={scriptImportInputElement}
	bind:files={importFiles}
	type="file"
	accept=".py"
	hidden
	on:change={() => {
		console.log(importFiles);
		showConfirm = true;
	}}
/>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete the python script?')}
	on:confirm={() => {
		// deleteHandler(selectedScript);
	}}
>
	<div class="text-sm text-gray-500">
		{$i18n.t('This will delete')} <span class=" font-semibold">{selectedScript?.name}</span>.
	</div>
</DeleteConfirmDialog>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		const reader = new FileReader();
		reader.onload = async (event) => {
			// const _functions = JSON.parse(event.target.result);
			// console.log(_functions);

			// for (const func of _functions) {
			// 	const res = await createNewFunction(localStorage.token, func).catch((error) => {
			// 		toast.error(error);
			// 		return null;
			// 	});
			// }

			toast.success($i18n.t('Functions imported successfully'));
			// functions.set(await getFunctions(localStorage.token));
			models.set(await getModels(localStorage.token));
		};
		if (importFiles) {
			reader.readAsText(importFiles[0]);
		}
	}}
>
	<div class="text-sm text-gray-500">
		<div class="bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
			<div>Please carefully review the following warnings:</div>

			<ul class="mt-1 list-disc pl-4 text-xs">
				<li>Functions allow arbitrary code execution.</li>
				<li>Do not install functions from sources you do not fully trust.</li>
			</ul>
		</div>

		<div class="my-3">
			I acknowledge that I have read and I understand the implications of my action. I am aware of
			the risks associated with executing arbitrary code and I have verified the trustworthiness of
			the source.
		</div>
	</div>
</ConfirmDialog>
