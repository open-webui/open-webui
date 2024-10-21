<script lang="ts">
	import { getBackendConfig, getModelFilterConfig, updateModelFilterConfig } from '$lib/apis';
	import { getSignUpEnabledStatus, toggleSignUpEnabledStatus } from '$lib/apis/auths';
	import { getUserPermissions, updateUserPermissions } from '$lib/apis/users';

	import { onMount, getContext } from 'svelte';
	import { models, config } from '$lib/stores';
	import Switch from '$lib/components/common/Switch.svelte';
	import { setDefaultModels } from '$lib/apis/configs';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let defaultModelId = '';

	let whitelistEnabled = false;
	let whitelistModels = [''];
	let permissions = {
		chat: {
			deletion: true,
			edit: true,
			temporary: true
		}
	};

	let chatDeletion = true;
	let chatEdit = true;
	let chatTemporary = true;

	onMount(async () => {
		permissions = await getUserPermissions(localStorage.token);

		chatDeletion = permissions?.chat?.deletion ?? true;
		chatEdit = permissions?.chat?.editing ?? true;
		chatTemporary = permissions?.chat?.temporary ?? true;

		const res = await getModelFilterConfig(localStorage.token);
		if (res) {
			whitelistEnabled = res.enabled;
			whitelistModels = res.models.length > 0 ? res.models : [''];
		}

		defaultModelId = $config.default_models ? $config?.default_models.split(',')[0] : '';
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		// console.log('submit');

		await setDefaultModels(localStorage.token, defaultModelId);
		await updateUserPermissions(localStorage.token, {
			chat: {
				deletion: chatDeletion,
				editing: chatEdit,
				temporary: chatTemporary
			}
		});
		await updateModelFilterConfig(localStorage.token, whitelistEnabled, whitelistModels);
		saveHandler();

		await config.set(await getBackendConfig());
	}}
>
	<div class=" space-y-3 overflow-y-scroll max-h-full">
		<div>
			<div class=" mb-2 text-sm font-medium">{$i18n.t('User Permissions')}</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Deletion')}</div>

				<Switch bind:state={chatDeletion} />
			</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">{$i18n.t('Allow Chat Editing')}</div>

				<Switch bind:state={chatEdit} />
			</div>

			<div class="  flex w-full justify-between my-2 pr-2">
				<div class=" self-center text-xs font-medium">{$i18n.t('Allow Temporary Chat')}</div>

				<Switch bind:state={chatTemporary} />
			</div>
		</div>

		<hr class=" dark:border-gray-850 my-2" />

		<div class="mt-2 space-y-3">
			<div>
				<div class="mb-2">
					<div class="flex justify-between items-center text-xs">
						<div class=" text-sm font-medium">{$i18n.t('Manage Models')}</div>
					</div>
				</div>
				<div class=" space-y-1 mb-3">
					<div class="mb-2">
						<div class="flex justify-between items-center text-xs">
							<div class=" text-xs font-medium">{$i18n.t('Default Model')}</div>
						</div>
					</div>

					<div class="flex-1 mr-2">
						<select
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={defaultModelId}
							placeholder="Select a model"
						>
							<option value="" disabled selected>{$i18n.t('Select a model')}</option>
							{#each $models.filter((model) => model.id) as model}
								<option value={model.id} class="bg-gray-100 dark:bg-gray-700">{model.name}</option>
							{/each}
						</select>
					</div>
				</div>

				<div class=" space-y-1">
					<div class="mb-2">
						<div class="flex justify-between items-center text-xs my-3 pr-2">
							<div class=" text-xs font-medium">{$i18n.t('Model Whitelisting')}</div>

							<Switch bind:state={whitelistEnabled} />
						</div>
					</div>

					{#if whitelistEnabled}
						<div>
							<div class=" space-y-1.5">
								{#each whitelistModels as modelId, modelIdx}
									<div class="flex w-full">
										<div class="flex-1 mr-2">
											<select
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
												bind:value={modelId}
												placeholder="Select a model"
											>
												<option value="" disabled selected>{$i18n.t('Select a model')}</option>
												{#each $models.filter((model) => model.id) as model}
													<option value={model.id} class="bg-gray-100 dark:bg-gray-700"
														>{model.name}</option
													>
												{/each}
											</select>
										</div>

										{#if modelIdx === 0}
											<button
												class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-900 dark:text-white rounded-lg transition"
												type="button"
												on:click={() => {
													if (whitelistModels.at(-1) !== '') {
														whitelistModels = [...whitelistModels, ''];
													}
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path
														d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
													/>
												</svg>
											</button>
										{:else}
											<button
												class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-900 dark:text-white rounded-lg transition"
												type="button"
												on:click={() => {
													whitelistModels.splice(modelIdx, 1);
													whitelistModels = whitelistModels;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 16 16"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path d="M3.75 7.25a.75.75 0 0 0 0 1.5h8.5a.75.75 0 0 0 0-1.5h-8.5Z" />
												</svg>
											</button>
										{/if}
									</div>
								{/each}
							</div>

							<div class="flex justify-end items-center text-xs mt-1.5 text-right">
								<div class=" text-xs font-medium">
									{whitelistModels.length}
									{$i18n.t('Model(s) Whitelisted')}
								</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
