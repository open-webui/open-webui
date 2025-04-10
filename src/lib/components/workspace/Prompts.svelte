<script lang="ts">
	import { toast } from '$lib/utils/toast';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, prompts as _prompts, user } from '$lib/stores';

	import {
		createNewPrompt,
		deletePromptByCommand,
		getPrompts,
		getPromptList
	} from '$lib/apis/prompts';

	import { getGroups } from '$lib/apis/groups';

	import PromptMenu from './Prompts/PromptMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import { capitalizeFirstLetter, sanitizeResponseContent } from '$lib/utils';

	const i18n = getContext('i18n');
	let promptsImportInputElement: HTMLInputElement;
	let promptsV1ImportInputElement: HTMLInputElement;
	let loaded = false;

	let importFiles = '';
	let importV1Files = '';
	let query = '';

	let prompts = [];
	let groups = [];

	let showDeleteConfirm = false;
	let deletePrompt = null;

	let filteredItems = [];
	$: filteredItems = prompts.filter((p) => query === '' || p.command.includes(query));

	const generateRandomSuffix = () => {
		const characters = 'abcdefghijklmnopqrstuvwxyz0123456789';
		let result = '';
		for (let i = 0; i < 5; i++) {
			result += characters.charAt(Math.floor(Math.random() * characters.length));
		}
		return result;
	};

	const sanitizeCommandString = (inputString) => {
		// Replace any non-alphanumeric characters with hyphens and ensure no consecutive hyphens
		return inputString
			.replace(/[^a-zA-Z0-9-]/g, '-') // Replace special chars with hyphens
			.replace(/-+/g, '-') // Replace consecutive hyphens with a single hyphen
			.replace(/^-|-$/g, ''); // Remove leading/trailing hyphens
	};

	const cloneHandler = async (prompt) => {
		sessionStorage.prompt = JSON.stringify(prompt);
		goto('/workspace/prompts/create');
	};

	const deleteHandler = async (prompt) => {
		const command = prompt.command;
		await deletePromptByCommand(localStorage.token, command);
		await init();
	};

	const init = async () => {
		prompts = await getPromptList(localStorage.token);
		groups = await getGroups(localStorage.token);
		await _prompts.set(await getPrompts(localStorage.token));
	};

	const getPromptGroupName = (prompt) => {
		if (prompt.access_control === null) return null;

		// Check for both read and write group access
		const writeGroupId = prompt.access_control.write.group_ids[0];
		const readGroupId = prompt.access_control.read.group_ids[0];
		const groupId = writeGroupId || readGroupId;

		if (groupId) {
			const group = groups.find((g) => g.id === groupId);
			return group?.name;
		}

		// Return null for private prompts (will show user name instead)
		return null;
	};

	const isGroupPrompt = (prompt) => {
		return (
			prompt.access_control !== null &&
			(prompt.access_control.read.group_ids.length > 0 ||
				prompt.access_control.write.group_ids.length > 0)
		);
	};

	$: getPromptDisplayText = (prompt) => {
		if (prompt.access_control === null) {
			return $i18n.t('Public');
		}

		const groupName = getPromptGroupName(prompt);
		const userName = capitalizeFirstLetter(
			prompt?.user?.name ?? prompt?.user?.email ?? $i18n.t('Deleted User')
		);

		// If it's a group prompt but user didn't create it
		if (groupName && prompt?.user?.id !== $user?.id) {
			return $i18n.t('By {{name}}', { name: groupName });
		}

		// If user created it (with or without group)
		return $i18n.t('By {{name}}', { name: userName });
	};

	onMount(async () => {
		await init();
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Prompts')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete prompt?')}
		on:confirm={() => {
			deleteHandler(deletePrompt);
		}}
	>
		<div class=" text-sm text-gray-500">
			{$i18n.t('This will delete')} <span class="  font-semibold">{deletePrompt.command}</span>.
		</div>
	</DeleteConfirmDialog>

	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center">
				{$i18n.t('Prompts')}
				<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
				<span class="text-lg font-medium text-gray-500 dark:text-gray-300"
					>{filteredItems.length}</span
				>
			</div>
		</div>

		<div class=" flex w-full space-x-2">
			<div class="flex flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Prompts')}
				/>
			</div>

			<div>
				<a
					class=" px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 dark:text-gray-300 dark:hover:text-white transition font-medium text-sm flex items-center space-x-1"
					href="/workspace/prompts/create"
				>
					<Plus className="size-3.5" />
				</a>
			</div>
		</div>
	</div>

	<div class="mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
		{#each filteredItems as prompt}
			<div
				class="flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition"
			>
				<a
					class="flex flex-1 w-full"
					href={$user?.role === 'admin' ||
					prompt?.user?.id === $user?.id ||
					prompt.access_control?.write?.group_ids?.some((id) => groups.find((g) => g.id === id))
						? `/workspace/prompts/edit?command=${encodeURIComponent(prompt.command.replace(/^\//, ''))}`
						: `/workspace/prompts/view?command=${encodeURIComponent(prompt.command.replace(/^\//, ''))}`}
				>
					<div class="flex flex-col flex-1">
						<div class="flex items-center gap-2">
							<div class="font-semibold line-clamp-1 capitalize">{prompt.title}</div>
							<div class="text-xs overflow-hidden text-ellipsis line-clamp-1">
								{prompt.command}
							</div>
						</div>
						<div class="text-xs">
							<Tooltip
								content={prompt.access_control == null
									? $i18n.t('Public')
									: (getPromptGroupName(prompt) ?? prompt?.user?.email ?? $i18n.t('Deleted User'))}
								className="flex shrink-0"
								placement="top-start"
							>
								<div class="shrink-0 text-gray-500">
									{#if prompt.access_control == null}
										{$i18n.t('Public')}
									{:else}
										{getPromptDisplayText(prompt)}
										{#if isGroupPrompt(prompt) && prompt?.user?.id === $user?.id}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 20 20"
												fill="currentColor"
												class="w-4 h-4 inline-block ml-0.5 -mt-0.5"
											>
												<path
													d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 002.07-.654.78.78 0 00.357-.442 3 3 0 00-4.308-3.517 6.484 6.484 0 011.907 3.96 2.32 2.32 0 01-.026.654zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z"
												/>
											</svg>
										{/if}
									{/if}
								</div>
							</Tooltip>
						</div>
					</div>
				</a>
				<div class="flex flex-row gap-0.5 self-center">
					{#if $user?.role === 'admin' || prompt?.user?.id === $user?.id || prompt.access_control?.write?.group_ids?.some( (id) => groups.find((g) => g.id === id) )}
						<a
							class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
							type="button"
							href={`/workspace/prompts/edit?command=${encodeURIComponent(prompt.command.replace(/^\//, ''))}`}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
								/>
							</svg>
						</a>
					{/if}

					<PromptMenu
						cloneHandler={() => {
							cloneHandler(prompt);
						}}
						deleteHandler={async () => {
							deletePrompt = prompt;
							showDeleteConfirm = true;
						}}
						onClose={() => {}}
						canDelete={$user?.role === 'admin' ||
							(prompt?.user?.id === $user?.id &&
								!(prompt.user.role === 'user' && prompt.access_control === null))}
					>
						<button
							class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
							type="button"
						>
							<EllipsisHorizontal className="size-5" />
						</button>
					</PromptMenu>
				</div>
			</div>
		{/each}
	</div>

	<div class=" flex justify-end w-full mb-3">
		<div class="flex space-x-2">
			{#if $user?.role === 'admin'}
				<input
					id="prompts-import-input"
					bind:this={promptsImportInputElement}
					bind:files={importFiles}
					type="file"
					accept=".json"
					hidden
					on:change={() => {
						const reader = new FileReader();
						reader.onload = async (event) => {
							const savedPrompts = JSON.parse(event.target.result);
							for (const prompt of savedPrompts) {
								// Check if the prompt should be private (has access_control)
								const isPrivate = prompt.access_control !== null;

								// Remove potential random suffix from command for imported prompts
								let cleanCommand = prompt.command;
								if (cleanCommand.charAt(0) === '/') {
									cleanCommand = cleanCommand.slice(1);
								}

								// If the command has a random suffix pattern (like -abc12), remove it
								cleanCommand = cleanCommand.replace(/-[a-z0-9]{5}$/, '');

								// Sanitize the command to remove any special characters
								cleanCommand = sanitizeCommandString(cleanCommand);

								// For private prompts, add a new random suffix
								if (isPrivate) {
									cleanCommand = `${cleanCommand}-${generateRandomSuffix()}`;
								}

								await createNewPrompt(localStorage.token, {
									command: cleanCommand,
									title: prompt.title,
									content: prompt.content,
									// Preserve access control settings from the imported prompt
									access_control: prompt.access_control
								}).catch((error) => {
									toast.error(`${error}`);
									return null;
								});
							}

							prompts = await getPromptList(localStorage.token);
							await _prompts.set(await getPrompts(localStorage.token));

							importFiles = [];
							promptsImportInputElement.value = '';
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

				<button
					class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
					on:click={() => {
						promptsImportInputElement.click();
					}}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Import Prompts')}</div>

					<div class=" self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</button>

				<button
					class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
					on:click={async () => {
						// promptsImportInputElement.click();
						let blob = new Blob([JSON.stringify(prompts)], {
							type: 'application/json'
						});
						saveAs(blob, `prompts-export-${Date.now()}.json`);
					}}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Export Prompts')}</div>

					<div class=" self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</button>
			{/if}
		</div>
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
