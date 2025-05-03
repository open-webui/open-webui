<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, config, prompts as _prompts, user } from '$lib/stores';

	import { getNotes } from '$lib/apis/notes';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';

	const i18n = getContext('i18n');
	let loaded = false;

	let importFiles = '';
	let query = '';

	let notes = [];
	let selectedNote = null;

	let showDeleteConfirm = false;

	const init = async () => {
		notes = await getNotes(localStorage.token);

		console.log(notes);
	};

	onMount(async () => {
		await init();
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Notes')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete note?')}
		on:confirm={() => {}}
	>
		<div class=" text-sm text-gray-500">
			{$i18n.t('This will delete')} <span class="  font-semibold">{selectedNote.title}</span>.
		</div>
	</DeleteConfirmDialog>

	{#if notes.length > 0}
		<div class="flex flex-col gap-1 my-1.5">
			<!-- <div class="flex justify-between items-center">
			<div class="flex md:self-center text-xl font-medium px-0.5 items-center">
				{$i18n.t('Notes')}
				<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
				<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{notes.length}</span>
			</div>
		</div> -->

			<div class=" flex w-full space-x-2">
				<div class="flex flex-1">
					<div class=" self-center ml-1 mr-3">
						<Search className="size-3.5" />
					</div>
					<input
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Notes')}
					/>
				</div>
			</div>
		</div>

		<div class="mb-5 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
			{#each notes as note}
				<div
					class=" flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition"
				>
					<div class=" flex flex-1 space-x-4 cursor-pointer w-full">
						<a href={`/notes/${note.id}`}>
							<div class=" flex-1 flex items-center gap-2 self-center">
								<div class=" font-semibold line-clamp-1 capitalize">{note.title}</div>
							</div>

							<div class=" text-xs px-0.5">
								<Tooltip
									content={note?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0"
									placement="top-start"
								>
									<div class="shrink-0 text-gray-500">
										{$i18n.t('By {{name}}', {
											name: capitalizeFirstLetter(
												note?.user?.name ?? note?.user?.email ?? $i18n.t('Deleted User')
											)
										})}
									</div>
								</Tooltip>
							</div>
						</a>
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="w-full h-full flex flex-col items-center justify-center">
			<div class="pb-20 text-center">
				<div class=" text-xl font-medium text-gray-400 dark:text-gray-600">
					{$i18n.t('No Notes')}
				</div>

				<div class="mt-1 text-sm text-gray-300 dark:text-gray-700">
					{$i18n.t('Create your first note by clicking on the plus button below.')}
				</div>
			</div>
		</div>
	{/if}

	<div class="absolute bottom-0 left-0 right-0 p-5 max-w-full flex justify-end">
		<div class="flex gap-0.5 justify-end w-full">
			<Tooltip content={$i18n.t('Create Note')}>
				<button
					class="cursor-pointer p-2.5 flex rounded-full bg-gray-50 dark:bg-gray-850 hover:bg-gray-100 dark:hover:bg-gray-800 transition shadow-xl"
					type="button"
					on:click={async () => {}}
				>
					<Plus className="size-4.5" strokeWidth="2.5" />
				</button>
			</Tooltip>

			<!-- <button
				class="cursor-pointer p-2.5 flex rounded-full hover:bg-gray-100 dark:hover:bg-gray-850 transition shadow-xl"
			>
				<SparklesSolid className="size-4" />
			</button> -->
		</div>
	</div>

	<!-- {#if $user?.role === 'admin'}
		<div class=" flex justify-end w-full mb-3">
			<div class="flex space-x-2">
				<input
					id="notes-import-input"
					bind:files={importFiles}
					type="file"
					accept=".md"
					hidden
					on:change={() => {
						console.log(importFiles);

						const reader = new FileReader();
						reader.onload = async (event) => {
							console.log(event.target.result);
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

				<button
					class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
					on:click={() => {
						const notesImportInputElement = document.getElementById('notes-import-input');
						if (notesImportInputElement) {
							notesImportInputElement.click();
						}
					}}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Import Notes')}</div>

					<div class=" self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</button>
			</div>
		</div>
	{/if} -->
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
