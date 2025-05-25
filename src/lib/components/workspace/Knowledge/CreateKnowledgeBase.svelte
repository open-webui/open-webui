<script lang="ts">
	import { goto } from '$app/navigation';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { createNewKnowledge, getKnowledgeBases, updateKnowledgeById } from '$lib/apis/knowledge';
	import { toast } from 'svelte-sonner';
	import AccessControl from '../common/AccessControl.svelte';
	import BackIcon from '$lib/components/icons/BackIcon.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AccessSelect from '$lib/components/common/AccessSelect.svelte';
	import { transcribeAudio } from '$lib/apis/audio';
	import { blobToFile } from '$lib/utils';
	import { uploadFile } from '$lib/apis/files';
	import { v4 as uuidv4 } from 'uuid';
	import Dropzone from '../Models/Dropzone.svelte';
	import DocumentIcon from '$lib/components/icons/DocumentIcon.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
	import { formatFileSize } from '$lib/utils';
	import dayjs from 'dayjs';

	export let edit = false;
	export let knowledge = null;

	let loading = false;

	let name = '';
	let description = '';
	let accessControl = {};
	let id = null;

	let files = [];

	let initialized = false;

	$: if (knowledge && !initialized) {
		id = knowledge.id;
		name = knowledge.name;
		description = knowledge.description;
		accessControl = knowledge.access_control;
		files = knowledge.files;
		initialized = true;
	}

	const uploadFileHandler = async (file) => {

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			size: file.size,
			status: 'uploading',
			error: '',
			itemId: tempItemId
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		// Check if the file is an audio file and transcribe/convert it to text file
		if (['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/x-m4a'].includes(file['type'])) {
			const res = await transcribeAudio(localStorage.token, file).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				const blob = new Blob([res.text], { type: 'text/plain' });
				file = blobToFile(blob, `${file.name}.txt`);
			}
		}

		try {
			const uploadedFile = await uploadFile(localStorage.token, file).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (uploadedFile) {
				if (uploadedFile?.id) {
					files = [...files, uploadedFile];
				}
			} else {
				toast.error($i18n.t('Failed to upload file.'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const submitHandler = async () => {
		loading = true;

		if (name.trim() === '' || description.trim() === '') {
			toast.error($i18n.t('Please fill in all fields.'));
			name = '';
			description = '';
			loading = false;
			return;
		}

		if (!edit) {
			const res = await createNewKnowledge(
				localStorage.token,
				name,
				description,
				accessControl,
				files
			).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				toast.success($i18n.t('Knowledge created successfully.'));
				goto(`/workspace/knowledge`);
			}
		} else {
			knowledge.data.file_ids = files?.map((item) => item.id);
			knowledge.name = name;
			knowledge.description = description;
			knowledge.access_control = accessControl;
			const res = await updateKnowledgeById(localStorage.token, id, knowledge).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				toast.success($i18n.t('Knowledge updated successfully.'));
				goto(`/workspace/knowledge`);
			}
		}

		loading = false;
	};

	$: totalFileSize = files.reduce((sum, file) => sum + (file.meta?.size ?? 0), 0);
</script>

<div class="w-full max-h-full">
	<div class="py-5 px-4 border-b border-lightGray-400 dark:border-customGray-700">
		<button
			class="flex items-center gap-1"
			on:click={() => {
				goto('/workspace/knowledge');
			}}
		>
			<div class=" self-center">
				<BackIcon />
			</div>
			{#if edit}
				<div class=" self-center font-medium text-sm text-lightGray-100 dark:text-customGray-100">{$i18n.t('Edit Knowledge')}</div>
			{:else}
				<div class=" self-center font-medium text-sm text-lightGray-100 dark:text-customGray-100">{$i18n.t('Create Knowledge')}</div>
			{/if}
		</button>
	</div>
	<div class="flex w-full md:w-[34rem] py-3 px-4">
		<form
			class="w-full flex flex-col bg-lightGray-550 dark:bg-customGray-800 rounded-2xl pt-6 pb-3 px-3"
			on:submit|preventDefault={() => {
				submitHandler();
			}}
		>
			<div class="flex flex-col w-full mb-1.5">
				<div class="mb-1.5">
					<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
						{#if name}
							<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
								{$i18n.t('Name')}
							</div>
						{/if}
						<input
							class={`px-2.5 text-sm ${name ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 dark:text-customGray-100 placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 outline-none`}
							placeholder={$i18n.t('Name')}
							bind:value={name}
							required
						/>
						{#if !name}
							<span
								class="absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-lightGray-100/50 dark:text-customGray-100/50 pointer-events-none select-none"
							>
								{$i18n.t('What are you working on')}
							</span>
						{/if}
					</div>
				</div>
				<div class="mb-1">
					<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
						{#if description}
							<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
								{$i18n.t('Description')}
							</div>
						{/if}
						<Textarea
							className={`px-2.5 py-2.5 text-sm ${description ? 'pt-4' : 'pt-2'} w-full h-20 bg-transparent text-lightGray-100 dark:text-customGray-100 placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 outline-none`}
							placeholder={$i18n.t('Description')}
							bind:value={description}
							rows={4}
							required
						/>
						{#if !description}
							<span
								class="absolute top-6.5 w-45 text-right right-2.5 -translate-y-1/2 text-xs text-lightGray-100/50 dark:text-customGray-100/50 pointer-events-none select-none"
							>
								{$i18n.t('Describe your knowledge base and objectives')}
							</span>
						{/if}
					</div>
				</div>
				<div>
					<div class="w-full flex py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5">
						<div class="w-[17.5rem] text-xs text-lightGray-100 dark:text-customGray-300">
							{$i18n.t('Knowledge base')}
						</div>
						{#if files.length > 0}
							<div class="w-20 text-xs text-lightGray-100 dark:text-customGray-300">{formatFileSize(totalFileSize)}</div>
							<div class="w-20 text-xs text-lightGray-100 dark:text-customGray-300">Added</div>
						{/if}
					</div>
					{#if files.length > 0}
						<ul class="mt-2.5 space-y-1 text-sm mb-5">
							{#each files as file}
								<li
									class="group flex justify-start items-center dark:text-customGray-100 cursor-pointer dark:hover:text-white"
								>
									<div class="flex items-center w-[17.5rem]">
										<DocumentIcon className="mr-2 size-4 shrink-0" />
										<span class="truncate text-sm">{file.meta.name}</span>
									</div>
									<span class="w-20 text-xs">{formatFileSize(file.meta.size)}</span>
									<span class="w-20 text-xs"
										>{dayjs(file.created_at * 1000).format('DD.MM.YYYY')}</span
									>
									<button
										class="opacity-0 group-hover:opacity-100 w-[40px] flex items-center justify-center"
										type="button"
										on:click={() => {
											files = files.filter((f) => f.id !== file.id);
										}}
									>
										<DeleteIcon />
									</button>
								</li>
							{/each}
						</ul>
					{/if}
					<Dropzone {uploadFileHandler} />
				</div>
				<div>
					<div class="py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5">
						<div class="text-xs text-lightGray-100 dark:text-customGray-300">{$i18n.t('Organization')}</div>
					</div>
					<AccessSelect bind:accessControl accessRoles={['read', 'write']} />
				</div>
			</div>

			<div class="flex justify-end mt-2">
				<div>
					<button
						class=" text-xs w-[10.5rem] h-10 px-3 py-2 font-medium transition rounded-lg {loading
							? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-500 text-lightGray-100 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border dark:border-customGray-700'
							: 'bg-lightGray-300 hover:bg-lightGray-500 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border dark:border-customGray-700'} flex justify-center"
						type="submit"
						disabled={loading}
					>
						<div class=" self-center font-medium">{$i18n.t('Save')}</div>

						{#if loading}
							<div class="ml-1.5 self-center">
								<svg
									class=" w-4 h-4"
									viewBox="0 0 24 24"
									fill="currentColor"
									xmlns="http://www.w3.org/2000/svg"
									><style>
										.spinner_ajPY {
											transform-origin: center;
											animation: spinner_AtaB 0.75s infinite linear;
										}
										@keyframes spinner_AtaB {
											100% {
												transform: rotate(360deg);
											}
										}
									</style><path
										d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
										opacity=".25"
									/><path
										d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
										class="spinner_ajPY"
									/></svg
								>
							</div>
						{/if}
					</button>
				</div>
			</div>
		</form>
	</div>
</div>
