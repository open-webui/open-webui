<script context="module">
	export async function downloadOpenWebUiLog() {
		let error = null;

		const res = await fetch('/ollama/api/opu-openwebui-log', {
			method: 'GET',
			headers: {}
		})
			.then(async (response) => {
				if (!response.ok) {
					throw await response.json();
				}
				return response.blob();
			})
			.then((blob) => {
				const url = window.URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `open-webui${new Date().toISOString()}.log`;
				document.body.appendChild(a);
				a.click();
				window.URL.revokeObjectURL(url);
			})
			.catch((err) => {
				console.error(err);
				error = err.detail;
				return null;
			});

		if (error) {
			console.error('Error Download OPU Open-WebUi log failed:', error);
			throw error;
		}
	}

	export async function downloadFlaskLog() {
		let error = null;

		const res = await fetch('/ollama/api/opu-flask-log', {
			method: 'GET',
			headers: {}
		})
			.then(async (response) => {
				if (!response.ok) {
					throw await response.json();
				}
				return response.blob();
			})
			.then((blob) => {
				const url = window.URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `flask${new Date().toISOString()}.log`;
				document.body.appendChild(a);
				a.click();
				window.URL.revokeObjectURL(url);
			})
			.catch((err) => {
				console.error(err);
				error = err.detail;
				return null;
			});

		if (error) {
			console.error('Error Download OPU flask log failed:', error);
			throw error;
		}
	}

	export async function restartOpu() {
		isRestarting.set(true);
		try {
			const response = await fetch('/ollama/api/restartopu', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ target: 'opu' })
			});
			if (!response.ok) throw new Error('Restart failed');
			return response;
		} catch (error) {
			console.error('Error restarting OPU:', error);
			return null;
		} finally {
			isRestarting.set(false);
		}
	}
	export async function healthCheckOpu() {
		try {
			const response = await fetch('/ollama/api/healthcheckopu', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ target: 'opu' })
			});
			if (!response.ok) throw new Error('Health check failed');
			const data = await response.json(); // ✅ Parse JSON
			return data; // 🔁 Return the parsed object!
		} catch (error) {
			console.error('Error Health Check of OPU:', error);
			return null;
		}
	}
	export async function systemInfoOpu() {
		try {
			const response = await fetch('/ollama/api/systeminfoopu', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ target: 'opu' })
			});
			if (!response.ok) throw new Error('System info failed');
			const data = await response.json(); // ✅ Parse JSON
			return data; // 🔁 Return the parsed object!
		} catch (error) {
			console.error('Error System Info of OPU:', error);
			return null;
		}
	}
	export async function abortTaskOpu() {
		isAborting.set(true);
		try {
			const response = await fetch('/ollama/api/aborttaskopu', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ target: 'opu' })
			});
			if (!response.ok) throw new Error('System info failed');
			const data = await response.json(); // ✅ Parse JSON
			return data; // 🔁 Return the parsed object!
		} catch (error) {
			console.error('Error System Info of OPU:', error);
			return null;
		} finally {
			isAborting.set(false);
		}
	}
</script>

<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import AdvancedParams from '../Settings/Advanced/AdvancedParams.svelte';
	import Valves from '$lib/components/chat/Controls/Valves.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import { user, settings, isRestarting, isAborting } from '$lib/stores';
	export let models = [];
	export let chatFiles = [];
	export let params = {};

	onMount(async () => {
		params = { ...params, ...$settings.params };
		params.stop = $settings?.params?.stop ? ($settings?.params?.stop ?? []).join(',') : null;
	});

	let showValves = false;
	let showAbortJobConfirmDialog = false;
</script>

<ConfirmDialog
	bind:show={showAbortJobConfirmDialog}
	title={$i18n.t('Abort Job Message')}
	message={$i18n.t('Are you sure you want to abort this job?')}
	onConfirm={async () => {
		const res = await abortTaskOpu();
		if (res) toast.success($i18n.t(`Task aborted on OPU.`));
		else toast.error($i18n.t(`Something went wrong while aborting task on OPU.`));
	}}
/>

<div class=" dark:text-white">
	<div class=" flex items-center justify-between dark:text-gray-100 mb-2">
		<div class=" text-lg font-medium self-center font-primary">{$i18n.t('Chat Controls')}</div>
		<button
			class="self-center"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark className="size-3.5" />
		</button>
	</div>

	{#if $user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)}
		<div class=" dark:text-gray-200 text-sm font-primary py-0.5 px-0.5">
			{#if chatFiles.length > 0}
				<Collapsible title={$i18n.t('Files')} open={true} buttonClassName="w-full">
					<div class="flex flex-col gap-1 mt-1.5" slot="content">
						{#each chatFiles as file, fileIdx}
							<FileItem
								className="w-full"
								item={file}
								edit={true}
								url={file?.url ? file.url : null}
								name={file.name}
								type={file.type}
								size={file?.size}
								dismissible={true}
								on:dismiss={() => {
									// Remove the file from the chatFiles array

									chatFiles.splice(fileIdx, 1);
									chatFiles = chatFiles;
								}}
								on:click={() => {
									console.log(file);
								}}
							/>
						{/each}
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}

			<Collapsible bind:open={showValves} title={$i18n.t('Valves')} buttonClassName="w-full">
				<div class="text-sm" slot="content">
					<Valves show={showValves} />
				</div>
			</Collapsible>

			{#if $user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true)}
				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />

				<Collapsible title={$i18n.t('System Prompt')} open={true} buttonClassName="w-full">
					<div class="" slot="content">
						<textarea
							bind:value={params.system}
							class="w-full text-xs outline-hidden resize-vertical {$settings.highContrastMode
								? 'border-2 border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 p-2.5'
								: 'py-1.5 bg-transparent'}"
							rows="4"
							placeholder={$i18n.t('Enter system prompt')}
						/>
					</div>
				</Collapsible>
			{/if}

			{#if ($user?.role === 'admin' || ($user?.permissions.chat?.controls ?? true)) && (params.target === 'cpu' || params.target === 'opu')}
				<hr class="border-gray-50 dark:border-gray-850 my-3" />
				<div class="mt-2 space-y-3 pr-1.5">
					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">{$i18n.t('Abort Job')}</div>
						<button
							disabled={$isAborting}
							class={'w-auto text-sm px-2 py-1 rounded-md transition-colors duration-200' +
								($settings.highContrastMode
									? ' border-2 border-gray-300 dark : border-gray-700 bg-gray-50 dark:bg-gray-850 text-gray-900 dark:text-gray-100 ' +
										($isAborting
											? 'opacity-50 cursor-not-allowed'
											: 'hover:bg-blue-100 dark:hover:bg-blue-900')
									: ' bg-blue-600 text-white ' +
										($isAborting
											? 'opacity-50 cursor-not-allowed'
											: 'hover:bg-blue-700 dark:bg-blue-600'))}
							on:click={() => {
								showAbortJobConfirmDialog = true; //Pop up confirmation dialog and instantiate restart once confirmed
							}}
							>{$isAborting ? $i18n.t('Job being aborted...') : $i18n.t('Abort Job Now')}
						</button>
					</div>
				</div>
			{/if}
			{#if $user?.role === 'admin' || ($user?.permissions.chat?.params ?? true)}
				<Collapsible title={$i18n.t('Advanced Params')} open={true} buttonClassName="w-full">
					<div class="text-sm mt-1.5" slot="content">
						<div>
							<AdvancedParams admin={$user?.role === 'admin'} custom={true} bind:params />
						</div>
					</div>
				</Collapsible>

				<hr class="my-2 border-gray-50 dark:border-gray-700/10" />
			{/if}
		</div>
	{/if}
</div>
