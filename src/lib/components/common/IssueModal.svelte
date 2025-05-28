<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import Modal from './Modal.svelte';
	import { user } from '$lib/stores';
	import { createIssue } from '$lib/apis/issues';
	import { toast } from '$lib/utils/toast';

	export let show = false;

	const i18n = getContext('i18n');

	let description = '';
	let stepsToReproduce = '';
	let files: FileList | null = null;
	let loading = false;
	let error = '';
	const MAX_FILES = 3;

	let mounted = false; // Add mounted variable

	onMount(() => {
		mounted = true;
	});

	const resetForm = () => {
		description = '';
		stepsToReproduce = '';
		files = null;
		error = '';
	};

	const handleFileChange = (event: Event) => {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > MAX_FILES) {
			error = $i18n.t('You can only upload up to {{maxCount}} files', {
				maxCount: MAX_FILES
			});
			input.value = ''; // Clear the selection
			files = null;
			return;
		}

		// Validate file types
		if (input.files) {
			const invalidFiles = Array.from(input.files).filter(
				(file) => !file.type.startsWith('image/')
			);
			if (invalidFiles.length > 0) {
				error = $i18n.t('Only image files are allowed.');
				input.value = '';
				files = null;
				return;
			}
		}

		error = '';
		files = input.files;
	};

	const closeModal = () => {
		show = false;
		resetForm(); // Reset immediately instead of with timeout
	};

	$: if (!show && mounted) {
		closeModal();
	}

	const submit = async () => {
		if (loading) return;

		try {
			if (!description || !stepsToReproduce) {
				error = $i18n.t('Please fill out all required fields');
				return;
			}

			loading = true;
			error = '';

			await createIssue(localStorage.token, {
				email: $user?.email || '',
				description,
				stepsToReproduce,
				files
			});

			toast.success($i18n.t('Thank you! Your issue has been submitted successfully.'));
			closeModal();
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Failed to submit issue. Please try again later.'));
		} finally {
			loading = false;
		}
	};

	const fileInputText = (files: FileList | null) => {
		if (!files || files.length === 0) {
			return $i18n.t('No file chosen');
		}
		return Array.from(files)
			.map((f) => f.name)
			.join(', ');
	};
</script>

<Modal bind:show on:close={closeModal} disableClose={loading}>
	<div class="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-700">
		<h3 class="text-2xl font-medium font-primary text-gray-900 dark:text-gray-100">
			{$i18n.t('Issue Form')}
		</h3>
		<button
			on:click={() => !loading && (show = false)}
			class="text-gray-400 {loading
				? 'opacity-50 cursor-not-allowed'
				: 'hover:text-gray-500'} focus:outline-none"
			disabled={loading}
		>
			<span class="sr-only">Close</span>
			<svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M6 18L18 6M6 6l12 12"
				/>
			</svg>
		</button>
	</div>

	<div class="p-4">
		<div class="w-full">
			<p class="text-sm text-gray-600 dark:text-gray-300 mb-4">
				{$i18n.t('Report any problems or bugs you encounter to help us improve the application.')}
			</p>
			<form on:submit|preventDefault={submit} class="space-y-4">
				{#if error}
					<div class="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
						<p>{error}</p>
					</div>
				{/if}
				<div>
					<label for="description" class="text-sm mb-2 block text-gray-900 dark:text-gray-100"
						>{$i18n.t('Description')} *</label
					>
					<textarea
						id="description"
						bind:value={description}
						rows="4"
						required
						placeholder={$i18n.t('Please describe what happened')}
						class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-100 dark:text-gray-300 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-700"
					></textarea>
				</div>

				<div>
					<label for="stepsToReproduce" class="text-sm mb-2 block text-gray-900 dark:text-gray-100"
						>{$i18n.t('Steps to Reproduce')} *</label
					>
					<textarea
						id="stepsToReproduce"
						bind:value={stepsToReproduce}
						rows="4"
						required
						placeholder={$i18n.t('Please list the steps to reproduce this issue')}
						class="w-full resize-none rounded-lg py-2 px-4 text-sm bg-gray-100 dark:text-gray-300 dark:bg-gray-850 border border-gray-200 dark:border-gray-700 outline-none focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-700"
					></textarea>
				</div>
				<div>
					<label for="files" class="text-sm mb-2 block text-gray-900 dark:text-gray-100">
						{$i18n.t('Attach images')} ({$i18n.t('max')}
						{MAX_FILES})
					</label>
					<div class="relative mt-1">
						<input
							type="file"
							id="files"
							on:change={handleFileChange}
							multiple
							accept="image/*"
							aria-label={$i18n.t('Choose files to upload')}
							class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
						/>
						<div class="text-sm text-gray-600 dark:text-gray-400 flex items-center">
							<span
								class="inline-flex items-center px-4 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-300"
							>
								{$i18n.t('Choose Files')}
							</span>
							<span class="ml-3 text-gray-700 dark:text-gray-400">
								{fileInputText(files)}
							</span>
						</div>
					</div>
				</div>

				<div class="flex justify-end space-x-3 pt-4">
					<button
						type="button"
						on:click={closeModal}
						class="text-sm px-4 py-2 transition rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white"
					>
						<div class="self-center font-medium">
							{$i18n.t('Cancel')}
						</div>
					</button>
					<button
						type="submit"
						disabled={loading}
						class="text-sm px-4 py-2 transition rounded-lg {loading
							? 'cursor-not-allowed bg-gray-400 text-white dark:bg-gray-100 dark:text-gray-800'
							: 'bg-gray-900 hover:bg-gray-850 text-white dark:bg-gray-100 dark:hover:bg-white dark:text-gray-800'} flex"
					>
						<div class="self-center font-medium">
							{$i18n.t('Submit')}
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
	</div>
</Modal>
