<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	export let onSubmit: Function = () => {};
	export let show = false;

	let name = '';
	let description = '';
	let userIds = [];

	let loading = false;

	const submitHandler = async () => {
		loading = true;

		const group = {
			name,
			description
		};

		await onSubmit(group);

		loading = false;
		show = false;

		name = '';
		description = '';
		userIds = [];
	};

	onMount(() => {
		console.log('mounted');
	});
</script>

<Modal size="sm" bind:show>
	<div class="bg-white dark:bg-gray-900 rounded-xl">
		<!-- Header -->
		<div class="flex items-center justify-between px-6 py-5 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center gap-3">
				<div class="p-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-blue-600 dark:text-blue-400">
						<path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
					</svg>
				</div>
				<div>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Add User Group')}
					</h2>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						Create a new group to organize users
					</p>
				</div>
			</div>
			<button
				class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5 text-gray-500 dark:text-gray-400"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<!-- Form Content -->
		<form
			class="p-6"
			on:submit={(e) => {
				e.preventDefault();
				submitHandler();
			}}
		>
			<div class="space-y-5">
				<!-- Name Field -->
				<div class="space-y-2">
					<label for="group-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Name')}
						<span class="text-red-500">*</span>
					</label>
					<div class="relative">
						<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-400">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z" />
								<path stroke-linecap="round" stroke-linejoin="round" d="M6 6h.008v.008H6V6z" />
							</svg>
						</div>
						<input
							id="group-name"
							class="w-full pl-10 pr-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
							type="text"
							bind:value={name}
							placeholder={$i18n.t('Enter group name')}
							autocomplete="off"
							required
						/>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400">
						Choose a descriptive name for your group
					</p>
				</div>

				<!-- Description Field -->
				<div class="space-y-2">
					<label for="group-description" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						{$i18n.t('Description')}
					</label>
					<div class="relative">
						<Textarea
							id="group-description"
							className="w-full px-4 py-2.5 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all resize-none"
							rows={3}
							bind:value={description}
							placeholder={$i18n.t('Describe the purpose of this group (optional)')}
						/>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400">
						Add details about who should be in this group
					</p>
				</div>
			</div>

			<!-- Footer Actions -->
			<div class="flex items-center justify-end gap-3 mt-6 pt-5 border-t border-gray-200 dark:border-gray-700">
				<button
					type="button"
					class="px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
					on:click={() => {
						show = false;
					}}
					disabled={loading}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-6 py-2.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white rounded-lg transition-colors shadow-sm flex items-center gap-2 {loading
						? 'opacity-50 cursor-not-allowed'
						: ''}"
					type="submit"
					disabled={loading}
				>
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
						{$i18n.t('Creating...')}
					{:else}
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
						</svg>
						{$i18n.t('Create')}
					{/if}
				</button>
			</div>
		</form>
	</div>
</Modal>