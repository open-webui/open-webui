<script lang="ts">
	import {
		models,
		userModels,
		showSettings,
		settings,
		user,
		mobile,
		config
	} from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Selector from './ModelSelector/Selector.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	import { updateUserSettings } from '$lib/apis/users';
	import {
		listUserModels,
		createUserModel,
		updateUserModel,
		deleteUserModel
	} from '$lib/apis/userModels';

	let showUserModelModal = false;
	let editingCredential = null;
	let form = {
		name: '',
		model_id: '',
		base_url: '',
		api_key: ''
	};
	const i18n = getContext('i18n');

	export let selectedModels = [''];
	export let disabled = false;

	export let showSetDefault = true;

	const saveDefaultModel = async () => {
		const hasEmptyModel = selectedModels.filter((it) => it === '');
		if (hasEmptyModel.length) {
			toast.error($i18n.t('Choose a model before saving...'));
			return;
		}
		settings.set({ ...$settings, models: selectedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });

		toast.success($i18n.t('Default model updated'));
	};

	const pinModelHandler = async (modelId) => {
		let pinnedModels = $settings?.pinnedModels ?? [];

		if (pinnedModels.includes(modelId)) {
			pinnedModels = pinnedModels.filter((id) => id !== modelId);
		} else {
			pinnedModels = [...new Set([...pinnedModels, modelId])];
		}

		settings.set({ ...$settings, pinnedModels: pinnedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	$: if (selectedModels.length > 0 && ($models.length > 0 || $userModels.length > 0)) {
		const allIds = [
			...$models.map((m) => m.id),
			...$userModels.map((m) => m.id)
		];

		const _selectedModels = selectedModels.map((model) => (allIds.includes(model) ? model : ''));

		if (JSON.stringify(_selectedModels) !== JSON.stringify(selectedModels)) {
			selectedModels = _selectedModels;
		}
	}

	const loadUserModels = async () => {
		const res = await listUserModels(localStorage.token).catch((err) => {
			console.error(err);
			return [];
		});
		userModels.set(
			(res ?? []).map((item) => ({
				...item,
				id: `user:${item.id}`, // 前端区分私有模型 ID
				source: 'user'
			}))
		);
	};

	onMount(async () => {
		await loadUserModels();
	});

	const resetForm = () => {
		form = {
			name: '',
			model_id: '',
			base_url: '',
			api_key: ''
		};
		editingCredential = null;
	};

	const submitUserModel = async () => {
		if (!form.model_id || !form.api_key) {
			toast.error($i18n.t('Model ID and API Key are required'));
			return;
		}

		if (editingCredential) {
			const res = await updateUserModel(localStorage.token, editingCredential, form).catch((err) => {
				toast.error(`${err?.detail ?? err}`);
				return null;
			});
			if (res) {
				toast.success($i18n.t('Updated'));
				await loadUserModels();
			}
		} else {
			const res = await createUserModel(localStorage.token, form).catch((err) => {
				toast.error(`${err?.detail ?? err}`);
				return null;
			});
			if (res) {
				toast.success($i18n.t('Added'));
				await loadUserModels();
			}
		}

		resetForm();
		showUserModelModal = false;
	};

	const removeUserModel = async (cred) => {
		console.log("removeUserModel");
		console.log(cred);
		const res = await deleteUserModel(localStorage.token, cred.id.replace('user:', '')).catch((err) => {
			toast.error(`${err?.detail ?? err}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Deleted'));
			await loadUserModels();
		}
	};
</script>


<div class="flex flex-col w-full items-start">
	{#each selectedModels as selectedModel, selectedModelIdx}
		<div class="flex w-full max-w-fit">
			<div class="overflow-hidden w-full">
				<div class="max-w-full {($settings?.highContrastMode ?? false) ? 'm-1' : 'mr-1'}">
					<Selector
						id={`${selectedModelIdx}`}
						placeholder={$i18n.t('Select a model')}
						items={[
							...$models.map((model) => ({
								value: model.id,
								label: model.name,
								model: model,
								source: 'platform'
							})),
							...$userModels.map((model) => ({
								value: model.id,
								label: model.name || model.model_id,
								model: {
									id: model.id,
									name: model.name || model.model_id,
									info: { meta: { description: model.base_url ?? '' } },
									owned_by: 'openai',
									source: 'user'
								},
								source: 'user',
								_credential: model
							}))
						]}
						{pinModelHandler}
						addUserModel={() => {
							resetForm();
							showUserModelModal = true;
						}}
						on:deleteUserModel={(e) => {
							removeUserModel(e.detail);
						}}
						bind:value={selectedModel}
					/>
				</div>
			</div>

			{#if $user?.role === 'admin' || ($user?.permissions?.chat?.multiple_models ?? true)}
				{#if selectedModelIdx === 0}
					<div class="self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]">
						<Tooltip content={$i18n.t('Add Model')}>
							{#if false}
								<button
									class=" "
									{disabled}
									on:click={() => {
										selectedModels = [...selectedModels, ''];
									}}
									aria-label="Add Model"
								>
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-3.5">
										<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
									</svg>
								</button>
							{/if}
						</Tooltip>
					</div>
				{:else}
					<div class="self-center mx-1 disabled:text-gray-600 disabled:hover:text-gray-600 -translate-y-[0.5px]">
						<Tooltip content={$i18n.t('Remove Model')}>
							<button
								{disabled}
								on:click={() => {
									selectedModels.splice(selectedModelIdx, 1);
									selectedModels = selectedModels;
								}}
								aria-label="Remove Model"
							>
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-3">
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
								</svg>
							</button>
						</Tooltip>
					</div>
				{/if}
			{/if}
		</div>
	{/each}

	{#if showUserModelModal}
		<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
			<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-md p-4 space-y-3">
				<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
					{editingCredential ? $i18n.t('Edit My API') : $i18n.t('Add My API')}
				</div>

				<div class="space-y-2 text-sm">
					<div class="flex flex-col gap-1">
						<label class="text-gray-600 dark:text-gray-400">{$i18n.t('Display Name')}</label>
						<input
							class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 outline-none"
							bind:value={form.name}
							placeholder={$i18n.t('Optional')}
						/>
					</div>
					<div class="flex flex-col gap-1">
						<label class="text-gray-600 dark:text-gray-400">{$i18n.t('Model ID')}</label>
						<input
							class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 outline-none"
							bind:value={form.model_id}
							placeholder="gpt-4o / claude-3..."
						/>
					</div>
					<div class="flex flex-col gap-1">
						<label class="text-gray-600 dark:text-gray-400">{$i18n.t('Base URL')}</label>
						<input
							class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 outline-none"
							bind:value={form.base_url}
							placeholder="https://api.openai.com/v1"
						/>
					</div>
						<div class="flex flex-col gap-1">
						<label class="text-gray-600 dark:text-gray-400">API Key</label>
						<input
							type="password"
							class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 outline-none"
							bind:value={form.api_key}
							placeholder="sk-..."
						/>
					</div>
				</div>

				<div class="flex justify-end gap-2">
					<button
						class="px-3 py-2 rounded-lg text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700"
						on:click={() => {
							resetForm();
							showUserModelModal = false;
						}}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="px-3 py-2 rounded-lg text-sm bg-black text-white dark:bg-white dark:text-black"
						on:click={submitUserModel}
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

{#if showSetDefault}
	<div
		class="relative text-left mt-[1px] ml-1 text-[0.7rem] text-gray-600 dark:text-gray-400 font-primary"
	>
		<button on:click={saveDefaultModel}> {$i18n.t('Set as default')}</button>
	</div>
{/if}
