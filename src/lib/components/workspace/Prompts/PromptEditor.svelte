<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AccessControl from '../common/AccessControl.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import BackIcon from '$lib/components/icons/BackIcon.svelte';
	import TagSelect from '$lib/components/common/TagSelect.svelte';
	import AccessSelect from '$lib/components/common/AccessSelect.svelte';
	import { getUserTagsForPrompts } from '$lib/apis/prompts'

	export let onSubmit: Function;
	export let edit = false;
	export let prompt = null;

	const i18n = getContext('i18n');

	let loading = false;

	let userTags = [];
	const getTags = async () => {
		userTags = await getUserTagsForPrompts(localStorage.token);
	}

	onMount(async () => {
		await getTags();
	})

	let title = '';
	let command = '';
	let content = '';
	let description = '';
	let meta = {
			tags: []
		};

	let accessControl = null;

	let showAccessControlModal = false;

	$: if (!edit) {
		command = title !== '' ? `${title.replace(/\s+/g, '-').toLowerCase()}` : '';
	}

	const submitHandler = async () => {
		loading = true;

		if (validateCommandString(command)) {
			await onSubmit({
				title,
				command,
				content,
				description,
				access_control: accessControl,
				meta
			});
		} else {
			toast.error(
				$i18n.t('Only alphanumeric characters and hyphens are allowed in the command string.')
			);
		}

		loading = false;
	};

	const validateCommandString = (inputString) => {
		// Regular expression to match only alphanumeric characters and hyphen
		const regex = /^[a-zA-Z0-9-]+$/;

		// Test the input string against the regular expression
		return regex.test(inputString);
	};

	onMount(async () => {
		if (prompt) {
			title = prompt.title;
			await tick();
			console.log(prompt)
			command = prompt.command.at(0) === '/' ? prompt.command.slice(1) : prompt.command;
			content = prompt.content;
			description = prompt.description;
			meta = prompt.meta ? prompt.meta : {
				tags: []
			}

			accessControl = prompt?.access_control ?? null;
		}
	});
	onMount(() => {
		const stored = localStorage.getItem('newPromptDraft');
		if (stored) {
			content = stored;
			localStorage.removeItem('newPromptDraft'); 
		}
	});

	$:console.log(command, 'command')
</script>

<div class="flex flex-col">
	<div class="py-[22px] px-[15px] border-b border-lightGray-400 dark:border-customGray-700 ">
		<button class="flex items-center gap-1" on:click={() => history.back()}>
			<BackIcon />
			<div class="flex items-center text-lightGray-100 dark:text-customGray-100 md:self-center text-sm-plus font-medium leading-none px-0.5">
				{$i18n.t('Create prompt')}
			</div>
		</button>
	</div>

	<div class="flex justify-center w-full md:w-[34rem] py-3 px-4">
		<form
			class="flex flex-col bg-lightGray-550 dark:bg-customGray-800 rounded-2xl pt-6 pb-3 px-3"
			on:submit|preventDefault={() => {
				submitHandler();
			}}
		>
			<div class="flex flex-col w-full mb-1.5">
				<div class="flex-1">
					<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
						{#if title}
							<div class="text-xs absolute left-2 top-1 text-lightGray-100/50 dark:text-customGray-100/50">{$i18n.t('Title')}</div>
						{/if}
						<input
							class={`px-2.5 text-sm ${title ? "pt-2" : "pt-0"} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none`}
							placeholder={$i18n.t('Title')}
							bind:value={title}
							required
						/>
						{#if !title}
							<span
							class="absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-lightGray-100/50 dark:text-customGray-100/50 pointer-events-none select-none"
							>
							{$i18n.t('E.g. Paraphrase')}
							</span>
						{/if}
					</div>
				</div>

				<div class="hidden gap-0.5 items-center text-xs text-gray-500">
					<div class="">/</div>
					<input
						class=" w-full bg-transparent outline-none"
						placeholder={$i18n.t('Command')}
						bind:value={command}
						required
						disabled={edit}
					/>
				</div>
			</div>
				
			<div class="mb-1.5">
				<TagSelect bind:selected={meta.tags} {userTags} placeholder="Add category..." />
			</div>

			<div class="mb-1.5">
				<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
					{#if description}
						<div class="text-xs absolute left-2 top-1 text-lightGray-100/50 dark:text-customGray-100/50">{$i18n.t('Description')}</div>
					{/if}
					<input
						class={`px-2.5 text-sm ${description ? "pt-2" : "pt-0"} w-full text-lightGray-100 placeholder:text-lightGray-100 h-12 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
						placeholder={$i18n.t('Description')}
						bind:value={description}
						required
					/>
				</div>
			</div>
			<div class="mb-1">
				<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
					{#if content}
						<div class="text-xs absolute left-2 top-1 text-lightGray-100/50 dark:text-customGray-100/50">{$i18n.t('Prompt Content')}</div>
					{/if}
					<Textarea
						className={`px-2.5 py-2 text-sm ${content ? "pt-4" : "pt-2"} w-full text-lightGray-100 placeholder:text-lightGray-100 h-20 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
						placeholder={$i18n.t('Prompt Content')}
						bind:value={content}
						rows={4}
						required
					/>
					{#if !content}
						<span
						class="absolute top-[26px] w-[180px] text-lightGray-100/50 text-right right-2.5 -translate-y-1/2 text-xs dark:text-customGray-100/50 pointer-events-none select-none"
						>
							{$i18n.t('Write a summary that summarizes [topic or keyword].')}
						</span>
					{/if}
				</div>
			</div>
			<div class="mb-2.5">
				<div class="text-xs text-lightGray-100/50 dark:text-white/50">
					ⓘ {$i18n.t('Format your variables using brackets like this:')}&nbsp;<span
						class=" text-lightGray-100/50 dark:text-white/50 font-medium"
						>{'['}{$i18n.t('variable')}{']'}</span
					>.
					{$i18n.t('Make sure to enclose them with')}
					<span class=" text-lightGray-100/50 dark:text-white/50 font-medium">{"'['"}</span>
					{$i18n.t('and')}
					<span class=" text-lightGray-100/50 dark:text-white/50 font-medium">{"']'"}</span>.
				</div>

				<div class="text-xs text-lightGray-100/50 dark:text-white/50">
					{$i18n.t('Utilize')}<span class=" text-lightGray-100/50 dark:text-white/50 font-medium">
						{` {{CLIPBOARD}}`}</span
					>
					{$i18n.t('variable to have them replaced with clipboard content.')}
				</div>
			</div>

			<div>
				<AccessSelect bind:accessControl accessRoles={['read', 'write']} />
			</div>

			<div class="mt-2.5 mb-1 flex justify-end">
				<button
					class=" text-xs w-[168px] h-12 px-3 py-2 transition rounded-lg {loading
					? ' cursor-not-allowed bg-lightGray-300 hover:bg-lightGray-500 text-lightGray-100 dark:bg-customGray-950 dark:hover:bg-customGray-950 dark:text-white border border-lightGray-400 dark:border-customGray-700'
					: 'bg-lightGray-300 hover:bg-lightGray-500 text-lightGray-100 dark:bg-customGray-900 dark:hover:bg-customGray-950 dark:text-customGray-200 border border-lightGray-400 dark:border-customGray-700'} flex justify-center"
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
		</form>
	</div>
</div>
