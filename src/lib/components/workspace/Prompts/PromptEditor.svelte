<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AccessControl from '../common/AccessControl.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { user } from '$lib/stores';

	export let onSubmit: Function;
	export let edit = false;
	export let prompt = null;

	const i18n = getContext('i18n');

	let loading = false;

	let title = '';
	let command = '';
	let content = '';

	let accessControl = {};

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
				access_control: accessControl
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

			command = prompt.command.at(0) === '/' ? prompt.command.slice(1) : prompt.command;
			content = prompt.content;

			accessControl = prompt?.access_control ?? null;
		}
	});
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessControl
	accessRoles={['read', 'write']}
	allowPublic={$user?.permissions?.sharing?.public_prompts || $user?.role === 'admin'}
/>

<div class="w-full max-h-full">
	<button
		class="flex items-center text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
		on:click={() => {
			window.history.back();
		}}
	>
		<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
		</svg>
		Back
	</button>

	<form
		class="flex flex-col max-w-4xl mx-auto mt-10 mb-10"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div class=" w-full flex flex-col justify-center">

			<div class="w-full flex flex-col gap-2.5">
				<div class="w-full">
					<div class=" text-sm mb-2">{$i18n.t('Title')}</div>
					<div class="w-full mt-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={title}
							placeholder={$i18n.t('Title')}
							required
						/>
					</div>
				</div>

				<div class="w-full">
					<div class=" text-sm mb-2">{$i18n.t('Command')}</div>
					<div class="w-full mt-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							type="text"
							bind:value={command}
							placeholder={$i18n.t('Command')}
							required
							disabled={edit}
						/>
					</div>
				</div>
			</div>
		</div>

		<div class="w-full">
			<div class=" text-sm mb-2">{$i18n.t('Prompt Content')}</div>
			<div class=" w-full mt-1">
				<textarea
					class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
					rows="6"
					bind:value={content}
					placeholder={$i18n.t('Write a summary in 50 words that summarizes [topic or keyword].')}
					required
				/>
			</div>
			
			<div class="text-xs text-gray-400 dark:text-gray-500 mt-2">
				ⓘ {$i18n.t('Format your variables using brackets like this:')}&nbsp;<span
					class=" text-gray-600 dark:text-gray-300 font-medium"
					>{'{{'}{$i18n.t('variable')}{'}}'}</span
				>.
				{$i18n.t('Make sure to enclose them with')}
				<span class=" text-gray-600 dark:text-gray-300 font-medium">{'{{'}</span>
				{$i18n.t('and')}
				<span class=" text-gray-600 dark:text-gray-300 font-medium">{'}}'}</span>.
			</div>

			<div class="text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Utilize')}<span class=" text-gray-600 dark:text-gray-300 font-medium">
					{` {{CLIPBOARD}}`}</span
				>
				{$i18n.t('variable to have them replaced with clipboard content.')}
			</div>
		</div>

		<div class="mt-2">
			<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
				<AccessControl
					bind:accessControl
					accessRoles={['read', 'write']}
					allowPublic={$user?.permissions?.sharing?.public_prompts || $user?.role === 'admin'}
				/>
			</div>
		</div>

		<div class="flex justify-center mt-8 mb-12">
			<button
				class="w-full bg-gray-800 dark:bg-gray-700 text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-900 dark:hover:bg-gray-600 transition-colors {loading ? 'cursor-not-allowed' : ''}"
				type="submit"
				disabled={loading}
			>
				{$i18n.t('Save')}

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
