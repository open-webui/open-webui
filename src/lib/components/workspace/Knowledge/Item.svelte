<script lang="ts">
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');
	import { PaneGroup, Pane, PaneResizer } from 'paneforge';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { mobile, showSidebar } from '$lib/stores';

	import { getKnowledgeById } from '$lib/apis/knowledge';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Files from './Files.svelte';
	import AddFilesPlaceholder from '$lib/components/AddFilesPlaceholder.svelte';

	let id = null;
	let knowledge = null;
	let query = '';

	let selectedFileId = null;
	let dragged = false;

	onMount(async () => {
		id = $page.params.id;

		const res = await getKnowledgeById(localStorage.token, id).catch((e) => {
			console.error(e);
		});

		if (res) {
			knowledge = res;
		} else {
			goto('/workspace/knowledge');
		}
	});
</script>

{#if dragged}
	<div
		class="fixed {$showSidebar
			? 'left-0 md:left-[260px] md:w-[calc(100%-260px)]'
			: 'left-0'}  w-full h-full flex z-50 touch-none pointer-events-none"
		id="dropzone"
		role="region"
		aria-label="Drag and Drop Container"
	>
		<div class="absolute w-full h-full backdrop-blur bg-gray-800/40 flex justify-center">
			<div class="m-auto pt-64 flex flex-col justify-center">
				<div class="max-w-md">
					<AddFilesPlaceholder>
						<div class=" mt-2 text-center text-sm dark:text-gray-200 w-full">
							Drop any files here to add to my documents
						</div>
					</AddFilesPlaceholder>
				</div>
			</div>
		</div>
	</div>
{/if}

<div class="flex flex-col w-full max-h-[100dvh] h-full">
	<button
		class="flex space-x-1"
		on:click={() => {
			goto('/workspace/knowledge');
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

	<div class="flex flex-col my-2 flex-1 overflow-auto h-0">
		{#if id && knowledge}
			<div class=" flex w-full mt-1 mb-3.5">
				<div class="flex-1">
					<div class="flex items-center justify-between w-full px-0.5 mb-1">
						<div>
							<input
								type="text"
								class="w-full font-medium text-2xl font-primary bg-transparent outline-none"
								bind:value={knowledge.name}
							/>
						</div>

						<div class=" flex-shrink-0">
							<div>
								<Badge type="success" content="Collection" />
							</div>
						</div>
					</div>

					<div class="flex w-full px-1">
						<input
							type="text"
							class="w-full font-medium text-gray-500 text-sm bg-transparent outline-none"
							bind:value={knowledge.description}
						/>
					</div>
				</div>
			</div>

			<div class="flex flex-row h-0 flex-1 overflow-auto">
				<div
					class=" {!$mobile
						? 'flex-shrink-0'
						: 'flex-1'} p-2.5 w-80 rounded-2xl border border-gray-50 dark:border-gray-850"
				>
					<div class=" flex flex-col w-full space-x-2 rounded-lg h-full">
						<div class="flex px-1">
							<div class=" self-center ml-1 mr-3">
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
								class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
								bind:value={query}
								placeholder={$i18n.t('Search Collection')}
							/>

							<div>
								<Tooltip content={$i18n.t('Add Content')}>
									<button
										class=" px-2 py-2 rounded-xl border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center space-x-1"
										on:click={() => {
											goto('/workspace/knowledge/create');
										}}
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
								</Tooltip>
							</div>
						</div>
						<hr class="my-2 border-gray-50 dark:border-gray-850" />

						<div class="w-full h-full flex">
							{#if (knowledge?.data?.file_ids ?? []).length > 0}
								<Files fileIds={knowledge.data.file_ids} />
							{:else}
								<div class="m-auto text-gray-500 text-xs">No content found</div>
							{/if}
						</div>
					</div>
				</div>

				{#if !$mobile}
					<div class="flex-1 p-1 flex justify-start h-full">
						{#if selectedFileId}
							<textarea />
						{:else}
							<div class="m-auto">
								<AddFilesPlaceholder title={$i18n.t('Select/Add Files')}>
									<div class=" mt-2 text-center text-sm dark:text-gray-200 w-full">
										Select a file to view or drag and drop a file to upload
									</div>
								</AddFilesPlaceholder>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{:else}
			<Spinner />
		{/if}
	</div>
</div>
