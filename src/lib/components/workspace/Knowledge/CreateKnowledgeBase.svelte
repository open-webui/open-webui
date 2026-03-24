<script>
	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { createNewKnowledge, getKnowledgeBases } from '$lib/apis/knowledge';
	import { toast } from 'svelte-sonner';
	import { knowledge, user } from '$lib/stores';
	import AccessControl from '../common/AccessControl.svelte';

	let loading = false;

	let name = '';
	let description = '';
	let accessControl = {};

	const submitHandler = async () => {
		loading = true;

		if (name.trim() === '' || description.trim() === '') {
			toast.error($i18n.t('Please fill in all fields.'));
			name = '';
			description = '';
			loading = false;
			return;
		}

		const res = await createNewKnowledge(
			localStorage.token,
			name,
			description,
			accessControl
		).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			toast.success($i18n.t('Knowledge created successfully.'));
			knowledge.set(await getKnowledgeBases(localStorage.token));
			goto(`/workspace/knowledge/${res.id}`);
		}

		loading = false;
	};
</script>

<div class="w-full min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 p-3 sm:p-6">
	

	<!-- Main Card -->
	<div class="w-full">
		<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
			<!-- Header Section -->
			<div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 px-4 sm:px-8 py-6 sm:py-10 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
					<div class="p-1.5 sm:p-2.5 bg-blue-500/10 dark:bg-blue-500/20 rounded-lg">
						<svg class="w-5 h-5 sm:w-6 sm:h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
						</svg>
					</div>
					<h1 class="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 dark:text-white">
						{$i18n.t('Create a knowledge base')}
					</h1>
				</div>
				<p class="text-xs sm:text-sm text-gray-600 dark:text-gray-400 sm:ml-14">
					Build a centralized repository for your team's information and insights
				</p>
			</div>

			<!-- Form Section -->
			<form
				class="p-4 sm:p-8"
				on:submit|preventDefault={() => {
					submitHandler();
				}}
			>
				<div class="space-y-4 sm:space-y-6">
					<!-- Name Input -->
					<div class="space-y-1.5 sm:space-y-2">
						<label for="name" class="block text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-300">
							{$i18n.t('What are you working on?')}
							<span class="text-red-500">*</span>
						</label>
						<div class="relative">
							<input
								id="name"
							class="w-full rounded-lg sm:rounded-xl py-2 sm:py-3 px-3 sm:px-4 text-xs sm:text-sm bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-all duration-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Name your knowledge base')}
								required
							/>
						</div>
					</div>

					<!-- Description Textarea -->
					<div class="space-y-1.5 sm:space-y-2">
						<label for="description" class="block text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-300">
							{$i18n.t('What are you trying to achieve?')}
							<span class="text-red-500">*</span>
						</label>
						<div class="relative">
							<textarea
								id="description"
							class="w-full resize-none rounded-lg sm:rounded-xl py-2 sm:py-3 px-3 sm:px-4 text-xs sm:text-sm bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 transition-all duration-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none"
							rows="3"
								bind:value={description}
								placeholder={$i18n.t('Describe your knowledge base and objectives')}
								required
							/>
						</div>
					</div>

					<!-- Access Control -->
					<div class="space-y-1.5 sm:space-y-2">
						<label class="block text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-300">
							{$i18n.t('Access Control')}
						</label>
						<div class="p-3 sm:p-4 bg-gray-50 dark:bg-gray-900 border-2 border-gray-200 dark:border-gray-700 rounded-lg sm:rounded-xl overflow-visible">
							<AccessControl
								bind:accessControl
								accessRoles={['read', 'write']}
								allowPublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
							/>
						</div>
					</div>
				</div>

				<!-- Action Buttons -->
				<div class="flex items-center justify-end gap-2 sm:gap-3 mt-6 sm:mt-8 pt-4 sm:pt-6 border-t border-gray-200 dark:border-gray-700">
					<button
						type="button"
						class="px-4 sm:px-5 py-2 sm:py-2.5 text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750 border border-gray-300 dark:border-gray-600 rounded-lg transition-all duration-200 focus:ring-4 focus:ring-gray-200 dark:focus:ring-gray-700"
						on:click={() => {
							goto('/workspace/knowledge');
						}}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="group relative px-4 sm:px-6 py-2 sm:py-3 text-xs sm:text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-600 hover:from-blue-700 hover:to-blue-700 rounded-lg sm:rounded-xl transition-all duration-200 focus:ring-4 focus:ring-blue-500/30 shadow-lg shadow-blue-500/25 flex items-center gap-1.5 sm:gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:from-blue-600 disabled:hover:to-blue-600"
						type="submit"
						disabled={loading}
					>
						<span class="font-semibold">{$i18n.t('Create Knowledge')}</span>
						{#if loading}
							<svg
								class="w-3 h-3 sm:w-4 sm:h-4 animate-spin"
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
							<svg class="w-3 h-3 sm:w-4 sm:h-4 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
							</svg>
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
</div>