<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { getCodeInterpreterConfig, setCodeInterpreterConfig } from '$lib/apis/configs';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let config = null;

	let engines = ['pyodide', 'jupyter'];

	const submitHandler = async () => {
		const res = await setCodeInterpreterConfig(localStorage.token, config);
	};

	onMount(async () => {
		const res = await getCodeInterpreterConfig(localStorage.token);

		if (res) {
			config = res;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		await submitHandler();
		saveHandler();
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		{#if config}
			<div>
				<div class=" mb-1 text-sm font-medium">
					{$i18n.t('Code Interpreter')}
				</div>

				<div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Enable Code Interpreter')}
						</div>

						<Switch bind:state={config.ENABLE_CODE_INTERPRETER} />
					</div>
				</div>

				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Code Interpreter Engine')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
							bind:value={config.CODE_INTERPRETER_ENGINE}
							placeholder={$i18n.t('Select a engine')}
							required
						>
							<option disabled selected value="">{$i18n.t('Select a engine')}</option>
							{#each engines as engine}
								<option value={engine}>{engine}</option>
							{/each}
						</select>
					</div>
				</div>

				{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
					<div class="mt-1 flex flex-col gap-1.5 mb-1 w-full">
						<div class="text-xs font-medium">
							{$i18n.t('Jupyter URL')}
						</div>

						<div class="flex w-full">
							<div class="flex-1">
								<input
									class="w-full text-sm py-0.5 placeholder:text-gray-300 dark:placeholder:text-gray-700 bg-transparent outline-none"
									type="text"
									placeholder={$i18n.t('Enter Jupyter URL')}
									bind:value={config.CODE_INTERPRETER_JUPYTER_URL}
									autocomplete="off"
								/>
							</div>
						</div>
					</div>

					<div class="mt-1 flex gap-2 mb-1 w-full items-center justify-between">
						<div class="text-xs font-medium">
							{$i18n.t('Jupyter Auth')}
						</div>

						<div>
							<select
								class="dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-left"
								bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH}
								placeholder={$i18n.t('Select an auth method')}
							>
								<option selected value="">{$i18n.t('None')}</option>
								<option value="token">{$i18n.t('Token')}</option>
								<option value="password">{$i18n.t('Password')}</option>
							</select>
						</div>
					</div>

					{#if config.CODE_INTERPRETER_JUPYTER_AUTH}
						<div class="flex w-full gap-2">
							<div class="flex-1">
								{#if config.CODE_INTERPRETER_JUPYTER_AUTH === 'password'}
									<SensitiveInput
										type="text"
										placeholder={$i18n.t('Enter Jupyter Password')}
										bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD}
										autocomplete="off"
									/>
								{:else}
									<SensitiveInput
										type="text"
										placeholder={$i18n.t('Enter Jupyter Token')}
										bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN}
										autocomplete="off"
									/>
								{/if}
							</div>
						</div>
					{/if}
				{/if}
			</div>

			<hr class=" dark:border-gray-850 my-2" />

			<div>
				<div class="py-0.5 w-full">
					<div class=" mb-2.5 text-xs font-medium">
						{$i18n.t('Code Interpreter Prompt Template')}
					</div>

					<Tooltip
						content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
						placement="top-start"
					>
						<Textarea
							bind:value={config.CODE_INTERPRETER_PROMPT_TEMPLATE}
							placeholder={$i18n.t(
								'Leave empty to use the default prompt, or enter a custom prompt'
							)}
						/>
					</Tooltip>
				</div>
			</div>
		{/if}
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
