<script lang="ts">
	import { goto } from '$app/navigation';
	import { createNewWorkflow, updateWorkflowById, getWorkflows } from '$lib/apis/workflows';
	import { workflows } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let workflow = null; // null for create, workflow object for edit
	export let onSubmit: Function;

	let mounted = false;
	let loading = false;

	// Form data
	let name = '';
	let apiAddress = '';
	let apiKey = '';

	$: isEdit = workflow !== null;
	$: pageTitle = isEdit ? $i18n.t('Edit Workflow') : $i18n.t('Create Workflow');
	$: buttonText = isEdit ? $i18n.t('Update Workflow') : $i18n.t('Save');

	const saveHandler = async (data: any) => {
		console.log(isEdit ? 'Updating workflow:' : 'Creating workflow:', data);

		let res;
		if (isEdit) {
			res = await updateWorkflowById(localStorage.token, workflow.id, {
				name: data.name,
				api_address: data.api_address,
				api_key: data.api_key
			}).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		} else {
			res = await createNewWorkflow(localStorage.token, {
				id: data.id,
				name: data.name,
				api_address: data.api_address,
				api_key: data.api_key
			}).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		}

		if (res) {
			toast.success(isEdit ? $i18n.t('Workflow updated successfully') : $i18n.t('Workflow created successfully'));
			workflows.set(await getWorkflows(localStorage.token) as any);

			await goto('/workspace/workflows');
		}
	};

	const submitHandler = async () => {
		loading = true;

		if (!name.trim()) {
			toast.error($i18n.t('Name is required'));
			loading = false;
			return;
		}

		if (!apiAddress.trim()) {
			toast.error($i18n.t('API Address is required'));
			loading = false;
			return;
		}

		if (!apiKey.trim()) {
			toast.error($i18n.t('API Key is required'));
			loading = false;
			return;
		}

		// Generate ID from name (only for create)
		const id = isEdit ? workflow.id : name.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');

		await saveHandler({
			id,
			name: name.trim(),
			api_address: apiAddress.trim(),
			api_key: apiKey.trim()
		});

		loading = false;
	};

	onMount(() => {
		// Populate form with existing data if editing
		if (workflow) {
			name = workflow.name || '';
			apiAddress = workflow.api_address || '';
			apiKey = workflow.api_key || '';
		}
		
		mounted = true;
	});
</script>

<svelte:head>
	<title>
		{pageTitle} | {$i18n.t('Workflows')}
	</title>
</svelte:head>

{#if mounted}
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
					<!-- Name Field -->
					<div class="w-full">
						<div class=" text-sm mb-2">{$i18n.t('Name')}</div>
						<div class="w-full mt-1">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Enter workflow name')}
								required
							/>
						</div>
					</div>

					<!-- API Address Field -->
					<div class="w-full">
						<div class=" text-sm mb-2">{$i18n.t('API Address')}</div>
						<div class="w-full mt-1">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="url"
								bind:value={apiAddress}
								placeholder="https://api.example.com/v1"
								required
							/>
						</div>
					</div>

					<!-- API Key Field -->
					<div class="w-full">
						<div class=" text-sm mb-2">{$i18n.t('API Key')}</div>
						<div class="w-full mt-1">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								type="password"
								bind:value={apiKey}
								placeholder="sk-1234567890abcdef"
								required
							/>
						</div>
					</div>
				</div>
			</div>

			<div class="flex justify-center mt-8 mb-12">
				<button
					class="w-full bg-gray-800 dark:bg-gray-700 text-white py-3 px-4 rounded-lg font-medium hover:bg-gray-900 dark:hover:bg-gray-600 transition-colors {loading ? 'cursor-not-allowed' : ''}"
					type="submit"
					disabled={loading}
				>
					{buttonText}

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
								/>
							</svg>
						</div>
					{/if}
				</button>
			</div>
		</form>
	</div>
{:else}
	<div class="flex items-center justify-center py-12">
		<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
	</div>
{/if}
