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

<div class="w-full max-h-full flex justify-center px-4">
	<div class="w-full max-w-4xl">
		<form
			class="flex flex-col w-full"
			on:submit|preventDefault={() => {
				submitHandler();
			}}
		>
			<!-- Main Card -->
			<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
				<!-- Header Section -->
				<div class="bg-gradient-to-r from-orange-50 to-orange-50 dark:from-purple-950/30 dark:to-pink-950/30 px-6 py-5 border-b border-gray-200 dark:border-gray-700">
					<div class="flex items-center gap-3">
						<div class="p-2 bg-purple-500/10 dark:bg-purple-500/20 rounded-lg">
							<svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
							</svg>
						</div>
						<div>
							<h2 class="text-lg font-bold text-gray-900 dark:text-white">
								{edit ? $i18n.t('Edit Prompt') : $i18n.t('Create New Prompt')}
							</h2>
							<p class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
								{$i18n.t('Define a reusable command with custom content')}
							</p>
						</div>
					</div>
				</div>

				<!-- Form Content -->
				<div class="p-6 space-y-6">
					<!-- Title and Command Section -->
					<div class="space-y-4">
						<Tooltip
							content={`${$i18n.t('Only alphanumeric characters and hyphens are allowed')} - ${$i18n.t(
								'Activate this command by typing "/{{COMMAND}}" to chat input.',
								{
									COMMAND: command
								}
							)}`}
							placement="bottom-start"
						>
							<div class="space-y-3">
								<!-- Title Input -->
								<div class="flex items-center justify-between gap-3">
									<div class="flex-1">
										<label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
											{$i18n.t('Prompt Title')}
											<span class="text-red-500">*</span>
										</label>
										<input
											class="text-lg font-semibold w-full bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-all duration-200  outline-none"
											placeholder={$i18n.t('Title')}
											bind:value={title}
											required
										/>
									</div>

									<!-- Access Control Button -->
									<div class="self-end pb-1">
										<button
											class="group relative px-4 py-3 bg-gray-50 hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-800 border-2 border-gray-200 dark:border-gray-700 transition-all duration-200 rounded-xl flex gap-2 items-center "
											type="button"
											on:click={() => {
												showAccessControlModal = true;
											}}
										>
											<LockClosed strokeWidth="2.5" className="size-4 text-gray-600 dark:text-gray-400 group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors" />
											<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
												{$i18n.t('Access')}
											</div>
										</button>
									</div>
								</div>

								<!-- Command Input -->
								<div>
									<label class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
										{$i18n.t('Command')}
										<span class="text-red-500">*</span>
									</label>
									<div class="relative">
										<div class="absolute left-4 top-1/2 -translate-y-1/2 text-purple-600 dark:text-purple-400 font-mono font-semibold text-base pointer-events-none">
											/
										</div>
										<input
											class="w-full bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-xl pl-8 pr-4 py-3 text-sm font-mono text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-all duration-200  focus:ring-purple-500/10 outline-none disabled:opacity-50 disabled:cursor-not-allowed"
											placeholder={$i18n.t('Command')}
											bind:value={command}
											required
											disabled={edit}
										/>
									</div>
									<p class="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
										{$i18n.t('Only alphanumeric characters and hyphens are allowed')}
									</p>
								</div>
							</div>
						</Tooltip>
					</div>

					<!-- Prompt Content Section -->
					<div class="space-y-3">
						<label class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
							{$i18n.t('Prompt Content')}
							<span class="text-red-500">*</span>
						</label>
						
						<div class="relative">
							<Textarea
								className="text-sm w-full bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-all duration-200  outline-none overflow-y-hidden resize-none"
								placeholder={$i18n.t('Write a summary in 50 words that summarizes [topic or keyword].')}
								bind:value={content}
								rows={6}
								required
							/>
						</div>

						<!-- Helper Text -->
						<div class="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 rounded-xl p-4 space-y-2">
							<div class="flex items-start gap-2">
								<svg class="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
								</svg>
								<div class="text-xs text-blue-900 dark:text-blue-200 leading-relaxed">
									<p class="font-medium mb-1">{$i18n.t('Variable Formatting')}</p>
									<p>
										{$i18n.t('Format your variables using brackets like this:')}&nbsp;<code
											class="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded font-mono text-xs"
											>{'{{'}{$i18n.t('variable')}{'}}'}</code
										>
									</p>
									<p class="mt-1.5">
										{$i18n.t('Make sure to enclose them with')}
										<code class="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded font-mono text-xs">{'{{'}</code>
										{$i18n.t('and')}
										<code class="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded font-mono text-xs">{'}}'}</code>
									</p>
								</div>
							</div>
							<div class="flex items-start gap-2 pt-2 border-t border-blue-200 dark:border-blue-900">
								<svg class="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
									<path d="M8 2a1 1 0 000 2h2a1 1 0 100-2H8z" />
									<path d="M3 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v6h-4.586l1.293-1.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L10.414 13H15v3a2 2 0 01-2 2H5a2 2 0 01-2-2V5zM15 11h2a1 1 0 110 2h-2v-2z" />
								</svg>
								<div class="text-xs text-blue-900 dark:text-blue-200 leading-relaxed">
									<p>
										{$i18n.t('Utilize')}<code
											class="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded font-mono text-xs mx-1"
											>{` {{CLIPBOARD}}`}
										</code>{$i18n.t('variable to have them replaced with clipboard content.')}
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>

				<!-- Footer Actions -->
				<div class="bg-gray-50 dark:bg-gray-900 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
					<div class="flex justify-end">
						<button
							class="group relative px-6 py-3 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-600 hover:from-blue-700 hover:to-blue-700 rounded-xl transition-all duration-200 focus:ring-4 focus:ring-blue-500/30 shadow-lg shadow-blue-500/25 min-w-[200px] justify-center flex items-center gap-2"
							type="submit"
							disabled={loading}
						>
							<span class="font-semibold">{$i18n.t('Save & Create')}</span>
							{#if loading}
								<svg
									class="w-4 h-4 animate-spin"
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
							{:else}
								<svg class="w-4 h-4 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
								</svg>
							{/if}
						</button>
					</div>
				</div>
			</div>
		</form>
	</div>
</div>