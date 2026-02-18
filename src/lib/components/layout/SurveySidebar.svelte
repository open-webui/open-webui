<script lang="ts">
	import { page } from '$app/stores';
	import { showSidebar, user, mobile } from '$lib/stores';
	import { getContext } from 'svelte';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getWorkflowState, type WorkflowStateResponse } from '$lib/apis/workflow';
	import { getStepRoute, canAccessStep, getStepLabel, isStepCompleted } from '$lib/utils/workflow';
	import { tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	let workflowState: WorkflowStateResponse | null = null;
	let loadingProgress = true;

	/** Get auth token from user store first, then localStorage. Always use backend as source of truth. */
	function getToken(): string | null {
		return ($user as { token?: string })?.token ?? localStorage.token ?? null;
	}

	async function fetchWorkflowProgress() {
		const token = getToken();
		if (!token) {
			loadingProgress = false;
			return;
		}
		try {
			loadingProgress = true;
			const state = await getWorkflowState(token);
			workflowState = state;
		} catch (error) {
			console.error('Failed to fetch workflow progress:', error);
			workflowState = null;
		} finally {
			loadingProgress = false;
		}
	}

	// Navigation function
	async function goToStep(step: number) {
		console.log('goToStep called with step:', step);

		if (!workflowState) {
			await fetchWorkflowProgress();
		}

		if (!workflowState) {
			toast.error('Workflow state not available. Please try again.');
			return;
		}

		const canAccess = canAccessStep(step, workflowState);
		console.log(
			'canAccessStep result:',
			canAccess,
			'for step:',
			step,
			'workflowState:',
			workflowState
		);

		if (!canAccess) {
			toast.error('This step is not yet available');
			return;
		}

		const route = getStepRoute(step);
		console.log('Navigating to route:', route);
		await goto(route);

		// Refresh state after navigation
		await fetchWorkflowProgress();
	}

	// Get step display info
	function getStepInfo(step: number) {
		if (!workflowState) {
			return {
				route: getStepRoute(step),
				isCurrentStep: false,
				isCompleted: false,
				canAccess: false,
				label: getStepLabel(step)
			};
		}

		const route = getStepRoute(step);
		const currentRoute = $page.url.pathname;
		const isCurrentStep = route === currentRoute || currentRoute.startsWith(route);
		const canAccess = canAccessStep(step, workflowState);
		const isCompleted = isStepCompleted(step, workflowState);

		return {
			route,
			isCurrentStep,
			isCompleted,
			canAccess,
			label: getStepLabel(step)
		};
	}

	onMount(() => {
		fetchWorkflowProgress();
		const onWorkflowUpdate = () => {
			fetchWorkflowProgress();
		};
		window.addEventListener('workflow-updated', onWorkflowUpdate);
		return () => {
			window.removeEventListener('workflow-updated', onWorkflowUpdate);
		};
	});

	// Refresh when route changes
	$: if ($page.url.pathname) {
		fetchWorkflowProgress();
	}
</script>

{#if $showSidebar}
	<div
		class="{$mobile
			? 'fixed z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain'
			: ''} fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			showSidebar.set(!$showSidebar);
		}}
	/>
{/if}

{#if !$mobile && !$showSidebar}
	<div
		class="pt-[7px] pb-2 px-2 flex flex-col justify-between text-black dark:text-white hover:bg-gray-50/30 dark:hover:bg-gray-950/30 h-full z-10 transition-all border-e-[0.5px] border-gray-50 dark:border-gray-850/30"
		id="survey-sidebar"
	>
		<button
			class="flex items-center justify-center w-8 h-8 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition"
			on:click={() => {
				showSidebar.set(true);
			}}
			aria-label="Show Sidebar"
		>
			<svg
				class="w-5 h-5"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
				xmlns="http://www.w3.org/2000/svg"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M4 6h16M4 12h16M4 18h16"
				></path>
			</svg>
		</button>
	</div>
{/if}

{#if $showSidebar}
	<nav
		class="flex flex-col justify-between text-black dark:text-white bg-white dark:bg-gray-900 border-e border-gray-200 dark:border-gray-800 h-full z-50 transition-all {$mobile
			? 'fixed w-[260px]'
			: 'relative'} {$showSidebar ? 'w-[260px]' : 'w-0'} overflow-hidden"
		id="survey-sidebar-nav"
	>
		<div class="flex flex-col flex-1 overflow-y-auto">
			<!-- Header -->
			<div
				class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800"
			>
				<div class="flex items-center gap-2">
					<h2 class="text-lg font-semibold">Child-AI Survey</h2>
				</div>
				{#if $mobile}
					<button
						class="flex items-center justify-center w-8 h-8 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 transition"
						on:click={() => {
							// Defer to avoid re-entrant updates during Svelte render/teardown
							setTimeout(() => showSidebar.set(false), 0);
						}}
						aria-label="Hide Sidebar"
					>
						<svg
							class="w-5 h-5"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							></path>
						</svg>
					</button>
				{/if}
			</div>

			<!-- Navigation Items -->
			<div class="flex-1 p-4">
				<div class="space-y-2">
					<!-- Assignment Progress -->
					{#if !loadingProgress && workflowState}
						{@const step0 = getStepInfo(0)}
						{@const step1 = getStepInfo(1)}
						{@const step2 = getStepInfo(2)}
						{@const step3 = getStepInfo(3)}
						{@const step4 = getStepInfo(4)}
						{@const onInstructionsPage = $page.url.pathname.startsWith('/assignment-instructions')}
						{@const step1Clickable = step1.canAccess && (!onInstructionsPage || step1.isCompleted)}
						<div class="mb-6">
							<div
								class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3"
							>
								{$i18n.t('Assignment Progress')}
							</div>
							<div class="space-y-2">
								<!-- Step 0: Assignment Instructions -->
								<button
									data-step="0"
									disabled={!step0.canAccess}
									on:click|preventDefault|stopPropagation={() => {
										if (step0.canAccess) {
											goToStep(0);
										} else {
											toast.error('This step is not yet available');
										}
									}}
									class="flex items-center gap-2 w-full px-3 py-2 rounded-xl transition {step0.isCurrentStep
										? 'bg-blue-100 dark:bg-blue-900'
										: step0.canAccess
											? 'hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer'
											: 'opacity-50 cursor-not-allowed'}"
									aria-label="Navigate to {step0.label}"
									aria-disabled={!step0.canAccess}
								>
									<div
										class="size-5 rounded-full flex items-center justify-center flex-shrink-0 {step0.isCompleted
											? 'bg-green-500'
											: step0.isCurrentStep
												? 'bg-blue-500'
												: 'bg-gray-300 dark:bg-gray-600'}"
									>
										{#if step0.isCompleted}
											<svg
												class="size-3 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 13l4 4L19 7"
												></path>
											</svg>
										{:else}
											<span class="text-xs font-bold text-white">0</span>
										{/if}
									</div>
									<span class="text-sm text-gray-700 dark:text-gray-300 text-left">
										{$i18n.t('Assignment Instructions')}
									</span>
								</button>

								<!-- Step 1: Child Profile (not clickable while on assignment-instructions) -->
								<button
									data-step="1"
									disabled={!step1Clickable}
									on:click|preventDefault|stopPropagation={() => {
										if (step1Clickable) {
											goToStep(1);
										} else {
											toast.error('This step is not yet available');
										}
									}}
									class="flex items-center gap-2 w-full px-3 py-2 rounded-xl transition {step1.isCurrentStep
										? 'bg-blue-100 dark:bg-blue-900'
										: step1Clickable
											? 'hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer'
											: 'opacity-50 cursor-not-allowed'}"
									aria-label="Navigate to {step1.label}"
									aria-disabled={!step1Clickable}
								>
									<div
										class="size-5 rounded-full flex items-center justify-center flex-shrink-0 {step1.isCompleted
											? 'bg-green-500'
											: step1.isCurrentStep
												? 'bg-blue-500'
												: 'bg-gray-300 dark:bg-gray-600'}"
									>
										{#if step1.isCompleted}
											<svg
												class="size-3 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 13l4 4L19 7"
												></path>
											</svg>
										{:else}
											<span class="text-xs font-bold text-white">1</span>
										{/if}
									</div>
									<span class="text-sm text-gray-700 dark:text-gray-300 text-left">
										{$i18n.t('Child Profile')}
									</span>
								</button>

								<!-- Step 2: Scenario Review (Moderation) -->
								<button
									data-step="2"
									disabled={!step2.canAccess}
									on:click|preventDefault|stopPropagation={() => {
										if (step2.canAccess) {
											goToStep(2);
										} else {
											toast.error('This step is not yet available');
										}
									}}
									class="flex items-center gap-2 w-full px-3 py-2 rounded-xl transition {step2.isCurrentStep
										? 'bg-blue-100 dark:bg-blue-900'
										: step2.canAccess
											? 'hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer'
											: 'opacity-50 cursor-not-allowed'}"
									aria-label="Navigate to {step2.label}"
									aria-disabled={!step2.canAccess}
								>
									<div
										class="size-5 rounded-full flex items-center justify-center flex-shrink-0 {step2.isCompleted
											? 'bg-green-500'
											: (workflowState?.progress_by_section?.moderation_completed_count ?? 0) > 0
												? 'bg-yellow-500'
												: step2.isCurrentStep
													? 'bg-blue-500'
													: 'bg-gray-300 dark:bg-gray-600'}"
									>
										{#if step2.isCompleted}
											<svg
												class="size-3 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 13l4 4L19 7"
												></path>
											</svg>
										{:else if (workflowState?.progress_by_section?.moderation_completed_count ?? 0) > 0}
											<span class="text-xs font-bold text-white">2</span>
										{:else}
											<span class="text-xs font-bold text-white">2</span>
										{/if}
									</div>
									<span class="text-sm text-gray-700 dark:text-gray-300 text-left">
										{$i18n.t('Scenario Review')}
									</span>
								</button>

								<!-- Step 3: Exit Survey -->
								<button
									data-step="3"
									disabled={!step3.canAccess}
									on:click|preventDefault|stopPropagation={() => {
										if (step3.canAccess) {
											goToStep(3);
										} else {
											toast.error('This step is not yet available');
										}
									}}
									class="flex items-center gap-2 w-full px-3 py-2 rounded-xl transition {step3.isCurrentStep
										? 'bg-blue-100 dark:bg-blue-900'
										: step3.canAccess
											? 'hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer'
											: 'opacity-50 cursor-not-allowed'}"
									aria-label="Navigate to {step3.label}"
									aria-disabled={!step3.canAccess}
								>
									<div
										class="size-5 rounded-full flex items-center justify-center flex-shrink-0 {step3.isCompleted
											? 'bg-green-500'
											: step3.isCurrentStep
												? 'bg-blue-500'
												: 'bg-gray-300 dark:bg-gray-600'}"
									>
										{#if step3.isCompleted}
											<svg
												class="size-3 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 13l4 4L19 7"
												></path>
											</svg>
										{:else}
											<span class="text-xs font-bold text-white">3</span>
										{/if}
									</div>
									<span class="text-sm text-gray-700 dark:text-gray-300 text-left">
										{$i18n.t('Exit Survey')}
									</span>
								</button>

								<!-- Step 4: Completion -->
								<button
									data-step="4"
									disabled={!step4.canAccess}
									on:click|preventDefault|stopPropagation={() => {
										if (step4.canAccess) {
											goToStep(4);
										} else {
											toast.error('This step is not yet available');
										}
									}}
									class="flex items-center gap-2 w-full px-3 py-2 rounded-xl transition {step4.isCurrentStep
										? 'bg-blue-100 dark:bg-blue-900'
										: step4.canAccess
											? 'hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer'
											: 'opacity-50 cursor-not-allowed'}"
									aria-label="Navigate to {step4.label}"
									aria-disabled={!step4.canAccess}
								>
									<div
										class="size-5 rounded-full flex items-center justify-center flex-shrink-0 {step4.isCompleted
											? 'bg-green-500'
											: step4.isCurrentStep
												? 'bg-blue-500'
												: 'bg-gray-300 dark:bg-gray-600'}"
									>
										{#if step4.isCompleted}
											<svg
												class="size-3 text-white"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M5 13l4 4L19 7"
												></path>
											</svg>
										{:else}
											<span class="text-xs font-bold text-white">4</span>
										{/if}
									</div>
									<span class="text-sm text-gray-700 dark:text-gray-300 text-left">
										{$i18n.t('Completion')}
									</span>
								</button>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<!-- User Menu -->
		{#if $user}
			<div class="p-4 border-t border-gray-200 dark:border-gray-800">
				<UserMenu
					show={false}
					role={$user?.role || ''}
					profile={true}
					help={false}
					showActiveUsers={false}
				>
					<div
						class="flex items-center rounded-2xl py-2 px-1.5 w-full hover:bg-gray-100/50 dark:hover:bg-gray-900/50 transition"
					>
						<div class="self-center mr-3 relative">
							<img
								src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
								class="size-7 object-cover rounded-full"
								alt={$i18n.t('Open User Profile Menu')}
								aria-label={$i18n.t('Open User Profile Menu')}
							/>
						</div>
						<div class="self-center font-medium">{$user?.name}</div>
					</div>
				</UserMenu>
			</div>
		{/if}
	</nav>
{/if}
