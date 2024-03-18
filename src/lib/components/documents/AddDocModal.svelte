<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { onMount } from 'svelte';

	import { createNewDoc, getDocs, tagDocByName, updateDocByName } from '$lib/apis/documents';
	import Modal from '../common/Modal.svelte';
	import { documents } from '$lib/stores';
	import TagInput from '../common/Tags/TagInput.svelte';
	import Tags from '../common/Tags.svelte';
	import { addTagById } from '$lib/apis/chats';
	import { uploadDocToVectorDB } from '$lib/apis/rag';
	import { transformFileName } from '$lib/utils';
	import { SUPPORTED_FILE_EXTENSIONS, SUPPORTED_FILE_TYPE } from '$lib/constants';

	export let show = false;
	export let selectedDoc;
	let uploadDocInputElement: HTMLInputElement;
	let inputFiles;
	let tags = [];

	let doc = {
		name: '',
		title: '',
		content: null
	};

	const uploadDoc = async (file) => {
		const res = await uploadDocToVectorDB(localStorage.token, '', file).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			await createNewDoc(
				localStorage.token,
				res.collection_name,
				res.filename,
				transformFileName(res.filename),
				res.filename,
				tags.length > 0
					? {
							tags: tags
					  }
					: null
			).catch((error) => {
				toast.error(error);
				return null;
			});
			await documents.set(await getDocs(localStorage.token));
		}
	};

	const submitHandler = async () => {
		if (inputFiles && inputFiles.length > 0) {
			for (const file of inputFiles) {
				console.log(file, file.name.split('.').at(-1));
				if (
					SUPPORTED_FILE_TYPE.includes(file['type']) ||
					SUPPORTED_FILE_EXTENSIONS.includes(file.name.split('.').at(-1))
				) {
					uploadDoc(file);
				} else {
					toast.error(
						`Unknown File Type '${file['type']}', but accepting and treating as plain text`
					);
					uploadDoc(file);
				}
			}

			inputFiles = null;
			uploadDocInputElement.value = '';
		} else {
			toast.error(`File not found.`);
		}

		show = false;
		documents.set(await getDocs(localStorage.token));
	};

	const addTagHandler = async (tagName) => {
		if (!tags.find((tag) => tag.name === tagName) && tagName !== '') {
			tags = [...tags, { name: tagName }];
		} else {
			console.log('tag already exists');
		}
	};

	const deleteTagHandler = async (tagName) => {
		tags = tags.filter((tag) => tag.name !== tagName);
	};

	onMount(() => {});
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 py-4">
			<div class=" text-lg font-medium self-center">Add Docs</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
		<hr class=" dark:border-gray-800" />

		<div class="flex flex-col md:flex-row w-full px-5 py-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="mb-3 w-full">
						<input
							id="upload-doc-input"
							bind:this={uploadDocInputElement}
							hidden
							bind:files={inputFiles}
							type="file"
							multiple
						/>

						<button
							class="w-full text-sm font-medium py-3 bg-gray-850 hover:bg-gray-800 text-center rounded-xl"
							type="button"
							on:click={() => {
								uploadDocInputElement.click();
							}}
						>
							{#if inputFiles}
								{inputFiles.length > 0 ? `${inputFiles.length}` : ''} document(s) selected.
							{:else}
								Click here to select documents.
							{/if}
						</button>
					</div>

					<div class=" flex flex-col space-y-1.5">
						<div class="flex flex-col w-full">
							<div class=" mb-1.5 text-xs text-gray-500">Tags</div>

							<Tags {tags} addTag={addTagHandler} deleteTag={deleteTagHandler} />
						</div>
					</div>

					<div class="flex justify-end pt-5 text-sm font-medium">
						<button
							class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
							type="submit"
						>
							Save
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
