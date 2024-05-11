<script lang="ts">
	import { fnCaller, fnStore } from '$lib/apis/functions';
	import type { i18n as i18nType, t } from 'i18next';
	import { getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';

	const i18n: Writable<i18nType> = getContext('i18n');
	let selectedFnName: string | undefined = Object.keys($fnStore.fns)[0];
	$: selectedFn = selectedFnName
		? {
				...$fnStore.schema[selectedFnName],
				...$fnStore.fns[selectedFnName]
		  }
		: undefined;

	const createFunction = async () => {
		// find an unused name
		let i = 1;
		let name = `newFunction${i}`;
		while (Object.keys($fnStore.fns).includes(name)) {
			i++;
			name = `newFunction${i}`;
		}
		$fnStore.fns[name] = {
			fn: `// define your tool's code here\nconst run: Tool = ({}) => {\n    console.log("ran!");\n    return "";\n}\n\n// expose our tool to the LLM\nrun;`,
			createdAt: new Date().getTime(),
			enabled: true
		};
		$fnStore.schema[name] = {
			description: 'A new function',
			params: {
				param1: {
					type: 'string',
					description: 'A new parameter',
					required: true,
					createdAt: new Date().getTime()
				}
			}
		};
		$fnStore = { ...$fnStore };
		await tick();
		selectedFnName = name;
	};

	const deleteFunction = async () => {
		if (typeof selectedFnName === 'undefined') return;
		// delete the current item, then select the item before it
		const keys = Object.keys($fnStore.fns);
		const index = keys.indexOf(selectedFnName);
		console.log(selectedFnName, index, keys, keys[index - 1]);
		delete $fnStore.fns[selectedFnName];
		delete $fnStore.schema[selectedFnName];
		$fnStore = { ...$fnStore };
		await tick();
		const newKeys = Object.keys($fnStore.fns);
		selectedFnName = newKeys[index] || newKeys[index - 1] || undefined;
	};

	const renameFunction = (name: string) => {
		// if the name is in use, don't rename
		if (Object.keys($fnStore.fns).includes(name) || typeof selectedFnName === 'undefined' || !name)
			return;
		$fnStore.fns[name] = $fnStore.fns[selectedFnName];
		$fnStore.schema[name] = $fnStore.schema[selectedFnName];
		delete $fnStore.fns[selectedFnName];
		delete $fnStore.schema[selectedFnName];
		$fnStore = { ...$fnStore };
		selectedFnName = name;
	};

	const updateDescription = (description: string) => {
		if (typeof selectedFnName === 'undefined') return;
		$fnStore.schema[selectedFnName].description = description;
		$fnStore = { ...$fnStore };
	};

	const updateParam = (
		param: Partial<{
			description: string;
			type: string;
			required: boolean;
			createdAt: number;
		}>,
		paramName: string
	) => {
		if (typeof selectedFnName === 'undefined') return;
		$fnStore.schema[selectedFnName].params[paramName] = {
			...$fnStore.schema[selectedFnName].params[paramName],
			...(param as any)
		};
		$fnStore = { ...$fnStore };
	};

	let container: HTMLDivElement;

	const renameParam = (oldName: string, newName: string) => {
		if (typeof selectedFnName === 'undefined') return;
		// if it exists, dont
		if (Object.keys($fnStore.schema[selectedFnName].params).includes(newName)) return;
		$fnStore.schema[selectedFnName].params[newName] =
			$fnStore.schema[selectedFnName].params[oldName];
		delete $fnStore.schema[selectedFnName].params[oldName];
		$fnStore = { ...$fnStore };
	};

	const createParameter = async () => {
		if (typeof selectedFnName === 'undefined') return;
		let i = 1;
		let name = `param${i}`;
		while (Object.keys($fnStore.schema[selectedFnName].params).includes(name)) {
			i++;
			name = `param${i}`;
		}
		$fnStore.schema[selectedFnName].params[name] = {
			type: 'string',
			description: 'A new parameter',
			required: true,
			createdAt: new Date().getTime()
		};
		$fnStore = { ...$fnStore };
		await tick();
		container.scrollTop = container.scrollHeight;
	};
</script>

<div class="flex flex-col h-full justify-between text-sm overflow-y-auto max-h-[400px]">
	<div bind:this={container} class="flex justify-between h-full flex-col pr-1.5 overflow-y-scroll">
		<div class="space-y-2">
			<div class="text-sm font-medium">{$i18n.t('Edit Functions')}</div>
			<div class="flex justify-between mt-1">
				<div class="self-center text-xs font-medium">
					{$i18n.t(
						Object.keys($fnStore.fns).length > 0
							? 'Choose a function to edit'
							: 'Create a function to edit'
					)}
				</div>
				<div class="flex items-center gap-2">
					{#if Object.keys($fnStore.fns).length > 0}
						<select
							bind:value={selectedFnName}
							class="dark:bg-gray-900 w-fit pr-8 rounded py-2 px-2 text-xs bg-transparent outline-none text-right"
							placeholder={$i18n.t('Choose a function to edit')}
						>
							{#each Object.keys($fnStore.fns) as key}
								<option value={key}>{key}</option>
							{/each}
						</select>
					{/if}
					<div>
						<div class="flex w-full justify-end">
							<div aria-label="Add Function" class="flex">
								<button
									on:click={createFunction}
									class="p-2 flex gap-2 items-center bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
									><svg
										class="w-4 h-4"
										viewBox="0 0 24 24"
										fill="none"
										xmlns="http://www.w3.org/2000/svg"
									>
										<g id="Edit / Add_Plus">
											<path
												id="Vector"
												d="M6 12H12M12 12H18M12 12V18M12 12V6"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											/>
										</g>
									</svg></button
								>
							</div>
						</div>
					</div>
					{#if typeof selectedFnName !== 'undefined' && typeof selectedFn !== 'undefined'}
						<div>
							<div class="flex w-full justify-end">
								<div aria-label="Add Function" class="flex">
									<button
										on:click={deleteFunction}
										class="p-2 flex gap-2 items-center bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
										><svg
											class="w-4 h-4"
											viewBox="0 0 24 24"
											fill="none"
											xmlns="http://www.w3.org/2000/svg"
										>
											<path
												d="M10 12V17"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											/>
											<path
												d="M14 12V17"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											/>
											<path
												d="M4 7H20"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											/>
											<path
												d="M6 10V18C6 19.6569 7.34315 21 9 21H15C16.6569 21 18 19.6569 18 18V10"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											/>
											<path
												d="M9 5C9 3.89543 9.89543 3 11 3H13C14.1046 3 15 3.89543 15 5V7H9V5Z"
												stroke="currentColor"
												stroke-width="2"
												stroke-linecap="round"
												stroke-linejoin="round"
											/>
										</svg></button
									>
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
			{#if typeof selectedFnName !== 'undefined' && typeof selectedFn !== 'undefined' && selectedFn?.params}
				<div>
					<div class="mb-2 text-sm font-medium">{$i18n.t('Function name')}</div>
					<div class="flex w-full">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="text"
							value={selectedFnName}
							placeholder={selectedFnName}
							on:input={(e) => {
								if (e.target instanceof HTMLInputElement) {
									renameFunction(e.target.value);
								}
							}}
						/>
					</div>
					<!-- <div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
					To access the available model names for downloading, <a
						class="text-gray-500 dark:text-gray-300 font-medium underline"
						href="https://ollama.com/library"
						target="_blank">click here.</a
					>
				</div> -->
				</div>
				<div class="!mb-4">
					<div class="mb-2 text-sm font-medium">{$i18n.t('Function description')}</div>
					<div class="flex w-full">
						<textarea
							class="w-full rounded-lg py-2 px-4 resize-none h-28 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							value={selectedFn.description}
							on:input={(e) => {
								if (e.target instanceof HTMLTextAreaElement) {
									updateDescription(e.target.value);
								}
							}}
						/>
					</div>
					<!-- <div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
					To access the available model names for downloading, <a
						class="text-gray-500 dark:text-gray-300 font-medium underline"
						href="https://ollama.com/library"
						target="_blank">click here.</a
					>
				</div> -->
				</div>
				<table class="w-full border-spacing-x-4 border-spacing-y-1 border-separate -ml-4">
					<tr class="text-left whitespace-nowrap overflow-hidden text-ellipsis">
						<th>{$i18n.t('Parameter')}</th>
						<th>{$i18n.t('Type')}</th>
						<th>{$i18n.t('Description')}</th>
						<th>{$i18n.t('Required')}</th>
					</tr>
					{#each Object.entries(selectedFn.params).sort((a, b) => {
						return a[1].createdAt - b[1].createdAt;
					}) as [key, value]}
						<tr>
							<td>
								<input
									class="w-16 bg-transparent border-none outline-none"
									type="text"
									value={key}
									on:change={(e) => {
										if (e.target instanceof HTMLInputElement) {
											renameParam(key, e.target.value);
										}
									}}
								/>
							</td>
							<td>
								<select
									class="dark:bg-gray-900 w-fit pr-8 rounded py-2 text-xs bg-transparent outline-none text-left"
									placeholder="Choose a function to edit"
									value={value.type}
									on:change={(e) => {
										if (e.target instanceof HTMLSelectElement) {
											updateParam(
												{
													type: e.target.value
												},
												key
											);
										}
									}}
								>
									<option>string</option>
									<option>number</option>
									<option>boolean</option>
									<option>object</option>
									<option>array</option>
									<option>function</option>
								</select>
							</td>
							<td>
								<input
									class="bg-transparent border-none outline-none w-32"
									type="text"
									value={value.description}
									on:change={(e) => {
										if (e.target instanceof HTMLInputElement) {
											updateParam(
												{
													description: e.target.value
												},
												key
											);
										}
									}}
								/>
							</td>
							<td>
								<input
									type="checkbox"
									checked={value.required}
									on:change={(e) => {
										if (e.target instanceof HTMLInputElement) {
											updateParam(
												{
													required: e.target.checked
												},
												key
											);
										}
									}}
								/>
							</td>
							<td class="flex justify-end w-full">
								<button
									on:click={() => {
										if (typeof selectedFnName === 'undefined') return;
										delete $fnStore.schema[selectedFnName].params[key];
										$fnStore = { ...$fnStore };
									}}
									class="p-2 flex gap-2 items-center bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								>
									<svg
										class="w-4 h-4"
										viewBox="0 0 24 24"
										fill="none"
										xmlns="http://www.w3.org/2000/svg"
									>
										<path
											d="M10 12V17"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										/>
										<path
											d="M14 12V17"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										/>
										<path
											d="M4 7H20"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										/>
										<path
											d="M6 10V18C6 19.6569 7.34315 21 9 21H15C16.6569 21 18 19.6569 18 18V10"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										/>
										<path
											d="M9 5C9 3.89543 9.89543 3 11 3H13C14.1046 3 15 3.89543 15 5V7H9V5Z"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										/>
									</svg>
								</button>
							</td>
						</tr>
					{/each}
				</table>
				<div class="!mt-0 flex gap-4">
					<button
						on:click={createParameter}
						class="p-2 px-4 flex gap-2 items-center bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition {Object.keys(
							selectedFn.params
						).length === 0 && 'mt-[38px]'}">{$i18n.t('Create parameter')}</button
					>
					<a
						href="/editor/{selectedFnName}"
						class="p-2 px-4 flex gap-2 items-center bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition {Object.keys(
							selectedFn.params
						).length === 0 && 'mt-[38px]'}">{$i18n.t('Enter code editor')}</a
					>
				</div>
			{/if}
		</div>
	</div>
</div>
