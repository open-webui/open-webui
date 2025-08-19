<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import ModelVerifier from './ModelVerifier.svelte';
	import MessagesVerifier from './MessagesVerifier.svelte';
	import type { Message } from '$lib/types';

	export let history: {
		messages: Record<string, Message>,
		currentId: string | null;
	};
	export let token: string;
	export let selectedModels: string[];
	export let expanded = false;

	const dispatch = createEventDispatcher();

	let showModelVerifier = false;
	let modelVerificationStatus: any = null;

	// Function to toggle the verifier panel
	const toggleVerifier = () => {
		expanded = !expanded;
		dispatch('toggle', { expanded });
	};

	// Function to open model verifier
	const openModelVerifier = () => {
		showModelVerifier = true;
	};

	// Function to close model verifier
	const closeModelVerifier = () => {
		showModelVerifier = false;
	};
</script>

<div class="relative">
	<!-- Toggle Button -->
	{#if !expanded}
		<button
			on:click={toggleVerifier}
			class="fixed right-3 top-12 z-50 bg-green-500 hover:bg-green-600 text-white rounded-full p-2 shadow-lg transition-all duration-200"
			title="Toggle Verification Panel"
		>
			<svg
				class="w-4 h-4"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
			</svg>
		</button>
	{/if}

	<!-- Verifier Panel -->
	{#if expanded}
		<div
			class="fixed right-0 top-10 bottom-0 w-80 bg-white dark:bg-gray-800 shadow-xl border-l border-gray-200 dark:border-gray-700 z-40"
		>
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white">AI Chat Verification</h2>
				<button
					on:click={toggleVerifier}
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div class="h-full flex flex-col">
				<!-- Model Verification Section -->
				<div class="flex-shrink-0 border-b border-gray-200 dark:border-gray-700">
					<div class="p-4">
						<h2 class="text-md font-medium text-gray-900 dark:text-white mb-3">Model Verification</h2>
						
						<!-- Hidden ModelVerifier for automatic verification -->
						<ModelVerifier 
							model={selectedModels[0]} 
							{token} 
							show={false} 
							autoVerify={expanded && !!selectedModels[0]}
							on:statusUpdate={(e) => modelVerificationStatus = e.detail}
						/>
						
						{#if modelVerificationStatus?.loading}
							<!-- Loading State -->
							<div class="flex items-center justify-center py-4">
								<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
								<span class="ml-3 text-sm text-gray-600 dark:text-gray-400">Verifying confidentiality...</span>
							</div>
						{:else if modelVerificationStatus?.error}
							<!-- Error State -->
							<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 mb-3">
								<div class="flex items-center">
									<svg class="w-4 h-4 text-red-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
									</svg>
									<span class="text-red-800 dark:text-red-200 text-sm">{modelVerificationStatus.error}</span>
								</div>
							</div>
							<button
								on:click={() => modelVerificationStatus = null}
								disabled={!selectedModels[0]}
								class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white text-sm font-medium rounded-md transition-colors"
							>
								Retry Verification
							</button>
						{:else if modelVerificationStatus?.isVerified}
							<!-- Success State -->
							<div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3 mb-3">
								<div class="flex items-center mb-2">
									<svg class="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
									</svg>
									<span class="text-green-700 dark:text-green-300 text-sm font-medium">Your chat is confidential.</span>
								</div>
								
								<!-- Attestation Sponsors -->
								<div class="text-center mb-2">
									<p class="text-xs text-gray-600 dark:text-gray-400 mb-2">Attested by</p>
									<div class="flex items-center justify-center space-x-4">
										<!-- NVIDIA Logo -->
										<div class="flex items-center space-x-2">
											<img src="/assets/images/nvidia.svg" alt="NVIDIA" class="w-16 h-6" />
										</div>
										<span class="text-gray-400 text-xs">and</span>
										<!-- Intel Logo -->
										<div class="flex items-center space-x-2">
											<img src="/assets/images/intel.svg" alt="Intel" class="w-12 h-6" />
										</div>
									</div>
								</div>
								
								<!-- Description -->
								<p class="text-xs text-gray-600 dark:text-gray-400">
									This automated verification tool lets you independently confirm that the model is running in the TEE (Trusted Execution Environment).
								</p>
							</div>
							
							<!-- View Details Button -->
							<button
								on:click={openModelVerifier}
								class="w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-sm font-medium rounded-md transition-colors"
							>
								View Verification Details
							</button>
						{:else}
							<!-- No Data State -->
							<div class="flex items-center justify-center py-4">
								<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
								<span class="ml-3 text-sm text-gray-600 dark:text-gray-400">Verifying confidentiality...</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Messages Verification Section -->
				<div class="flex-1 overflow-hidden">
					<div class="h-full flex flex-col">
						<div class="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700">
							<h2 class="text-md font-medium text-gray-900 dark:text-white">Messages Verification</h2>
						</div>
						<div class="flex-1 overflow-y-auto">
							<MessagesVerifier {history} {token} />
						</div>
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Model Verifier Modal -->
	<ModelVerifier
		model={selectedModels[0]}
		{token}
		bind:show={showModelVerifier}
		on:close={closeModelVerifier}
	/>
</div>
