<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import AccessControl from '../common/AccessControl.svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';

	export let onSubmit: Function;
	export let edit = false;
	export let prompt = null;

	const i18n = getContext('i18n');

	let loading = false;

	let title = '';
	let baseCommand = '';
	let command = '';
	let content = '';

	let accessControl = null;

	const generateRandomSuffix = () => {
		const characters = 'abcdefghijklmnopqrstuvwxyz0123456789';
		let result = '';
		for (let i = 0; i < 5; i++) {
			result += characters.charAt(Math.floor(Math.random() * characters.length));
		}
		return result;
	};

	const generateCommandString = () => {
		if (!edit) {
			// Add random suffix only for private prompts
			if (accessControl !== null) {
				return `${baseCommand}-${generateRandomSuffix()}`;
			}
			// For public prompts, just use the base command
			return baseCommand;
		}
		return command;
	};

	$: if (!edit) {
		baseCommand = title !== '' ? title.replace(/\s+/g, '-').toLowerCase() : '';
		command = baseCommand;
	}

	const submitHandler = async () => {
		loading = true;
		command = generateCommandString();

		// Remove group requirement validation
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

	// Initialize with private access control for non-admin users
	onMount(async () => {
		if (!edit && $user?.role !== 'admin') {
			// Initialize empty access control without any group or user IDs
			// This makes prompts private by default for all non-admin users
			accessControl = {
				read: { group_ids: [], user_ids: [] },
				write: { group_ids: [], user_ids: [] }
			};
		}

		if (prompt) {
			title = prompt.title;
			await tick();

			baseCommand = command =
				prompt.command.at(0) === '/' ? prompt.command.slice(1) : prompt.command;
			content = prompt.content;

			accessControl = prompt?.access_control ?? null;
		}
	});
</script>

<div class="w-full max-h-full">
	<form
		class="flex flex-col max-w-lg mx-auto mt-10 mb-10"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		<div class="w-full flex flex-col justify-center">
			<div class="text-2xl font-medium font-primary mb-2.5">
				{edit ? $i18n.t('Edit prompt') : $i18n.t('Create a prompt')}
			</div>

			<div class="w-full flex flex-col gap-2.5">
				<div class="w-full">
					<div class="text-sm mb-2">{$i18n.t('Title')}</div>
					<div class="w-full mt-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="text"
							bind:value={title}
							placeholder={$i18n.t('Name your prompt')}
							required
						/>
					</div>
				</div>

				<div class="w-full">
					<div class="text-sm mb-2">{$i18n.t('Command')}</div>
					<div class="w-full mt-1">
						<div class="flex items-center w-full rounded-lg bg-gray-50 dark:bg-gray-850">
							<span class="text-gray-500 pl-4">/</span>
							<input
								class="w-full py-2 px-2 text-sm bg-transparent outline-none"
								type="text"
								bind:value={command}
								placeholder={$i18n.t('Command trigger')}
								required
								disabled={edit}
							/>
						</div>
					</div>
				</div>

				<div>
					<div class="text-sm mb-2">{$i18n.t('Prompt Content')}</div>
					<div class="w-full mt-1">
						<textarea
							class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t(
								'Write a summary in 50 words that summarizes [topic or keyword].'
							)}
							bind:value={content}
							rows={4}
							required
						/>
						<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
							ⓘ {$i18n.t('Format your variables using brackets like this:')}
							<span class="text-gray-600 dark:text-gray-300 font-medium"
								>{'{{'}{$i18n.t('variable')}{'}}'}</span
							>
						</div>
					</div>
				</div>
			</div>
		</div>

		<div class="mt-2">
			<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
				<AccessControl bind:accessControl />
			</div>
		</div>

		<div class="flex justify-end mt-2">
			<!-- Move Cancel button here -->
			<button
				class="text-sm px-4 py-2 transition rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white"
				on:click={() => goto('/workspace/prompts')}
				type="button"
			>
				<div class="self-center font-medium">
					{$i18n.t('Cancel')}
				</div>
			</button>
			<button
				class="text-sm px-4 py-2 ml-2 transition rounded-lg {loading
					? 'cursor-not-allowed bg-gray-900 dark:bg-gray-100'
					: 'bg-gray-900 hover:bg-gray-850 text-white dark:bg-gray-100 dark:hover:bg-white dark:text-gray-800'} flex"
				type="submit"
				disabled={loading}
			>
				<div class="self-center font-medium">
					{edit ? $i18n.t('Save Changes') : $i18n.t('Create Prompt')}
				</div>
				{#if loading}
					<div class="ml-1.5 self-center">
						<svg
							class="w-4 h-4"
							viewBox="0 0 24 24"
							fill="currentColor"
							xmlns="http://www.w3.org/2000/svg"
						>
							<style>
								.spinner_ajPY {
									transform-origin: center;
									animation: spinner_AtaB 0.75s infinite linear;
								}
								@keyframes spinner_AtaB {
									100% {
										transform: rotate(360deg);
									}
								}
							</style>
							<path
								d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
								opacity=".25"
							/>
							<path
								d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
								class="spinner_ajPY"
							/>
						</svg>
					</div>
				{/if}
			</button>
		</div>
	</form>
</div>
