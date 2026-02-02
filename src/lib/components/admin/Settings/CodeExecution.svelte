<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { getCodeExecutionConfig, setCodeExecutionConfig } from '$lib/apis/configs';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let config = null;

	let engines = ['pyodide', 'jupyter'];

	const submitHandler = async () => {
		const res = await setCodeExecutionConfig(localStorage.token, config);
	};

	onMount(async () => {
		const res = await getCodeExecutionConfig(localStorage.token);

		if (res) {
			config = res;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={async () => {
		await submitHandler();
		saveHandler();
	}}
>
	<div class="space-y-6 overflow-y-scroll scrollbar-hidden h-full px-1">
		{#if config}
			<!-- General Settings Section -->
			<div class="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 space-y-4 border border-gray-200 dark:border-gray-800">
				<div class="flex items-center gap-2">
					<div class="w-1 h-6 bg-blue-500 rounded-full"></div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('General')}</h3>
				</div>

				<div class="space-y-4">
					<div class="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
						<div class="flex flex-col gap-1">
							<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
								{$i18n.t('Enable Code Execution')}
							</span>
							<span class="text-xs text-gray-500 dark:text-gray-400">
								Allow code execution in your environment
							</span>
						</div>
						<Switch bind:state={config.ENABLE_CODE_EXECUTION} />
					</div>

					<div class="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
						<div class="flex flex-col gap-1">
							<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
								{$i18n.t('Code Execution Engine')}
							</span>
							<span class="text-xs text-gray-500 dark:text-gray-400">
								Choose the execution environment
							</span>
						</div>
						<select
							class="bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-medium text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
							bind:value={config.CODE_EXECUTION_ENGINE}
							placeholder={$i18n.t('Select a engine')}
							required
						>
							<option disabled selected value="">{$i18n.t('Select a engine')}</option>
							{#each engines as engine}
								<option value={engine}>{engine}</option>
							{/each}
						</select>
					</div>

					{#if config.CODE_EXECUTION_ENGINE === 'jupyter'}
						<div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 flex gap-2">
							<svg class="w-5 h-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
							</svg>
							<p class="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
								{$i18n.t('Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.')}
							</p>
						</div>

						<div class="space-y-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
							<div class="space-y-2">
								<label class="text-sm font-medium text-gray-900 dark:text-gray-100">
									{$i18n.t('Jupyter URL')}
								</label>
								<input
									class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg placeholder:text-gray-400 dark:placeholder:text-gray-500 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
									type="text"
									placeholder={$i18n.t('Enter Jupyter URL')}
									bind:value={config.CODE_EXECUTION_JUPYTER_URL}
									autocomplete="off"
								/>
							</div>

							<div class="space-y-2">
								<div class="flex items-center justify-between">
									<label class="text-sm font-medium text-gray-900 dark:text-gray-100">
										{$i18n.t('Jupyter Auth')}
									</label>
									<select
										class="bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-medium text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
										bind:value={config.CODE_EXECUTION_JUPYTER_AUTH}
										placeholder={$i18n.t('Select an auth method')}
									>
										<option selected value="">{$i18n.t('None')}</option>
										<option value="token">{$i18n.t('Token')}</option>
										<option value="password">{$i18n.t('Password')}</option>
									</select>
								</div>

								{#if config.CODE_EXECUTION_JUPYTER_AUTH}
									<div>
										{#if config.CODE_EXECUTION_JUPYTER_AUTH === 'password'}
											<SensitiveInput
												type="text"
												placeholder={$i18n.t('Enter Jupyter Password')}
												bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_PASSWORD}
												autocomplete="off"
											/>
										{:else}
											<SensitiveInput
												type="text"
												placeholder={$i18n.t('Enter Jupyter Token')}
												bind:value={config.CODE_EXECUTION_JUPYTER_AUTH_TOKEN}
												autocomplete="off"
											/>
										{/if}
									</div>
								{/if}
							</div>

							<div class="flex items-center justify-between">
								<label class="text-sm font-medium text-gray-900 dark:text-gray-100">
									{$i18n.t('Code Execution Timeout')}
								</label>
								<Tooltip content={$i18n.t('Enter timeout in seconds')}>
									<input
										class="w-24 px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 text-right focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
										type="number"
										bind:value={config.CODE_EXECUTION_JUPYTER_TIMEOUT}
										placeholder={$i18n.t('e.g. 60')}
										autocomplete="off"
									/>
								</Tooltip>
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Code Interpreter Section -->
			<div class="bg-gray-50 dark:bg-gray-900/50 rounded-xl p-5 space-y-4 border border-gray-200 dark:border-gray-800">
				<div class="flex items-center gap-2">
					<div class="w-1 h-6 bg-purple-500 rounded-full"></div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Code Interpreter')}</h3>
				</div>

				<div class="space-y-4">
					<div class="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
						<div class="flex flex-col gap-1">
							<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
								{$i18n.t('Enable Code Interpreter')}
							</span>
							<span class="text-xs text-gray-500 dark:text-gray-400">
								Allow interactive code interpretation
							</span>
						</div>
						<Switch bind:state={config.ENABLE_CODE_INTERPRETER} />
					</div>

					{#if config.ENABLE_CODE_INTERPRETER}
						<div class="flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
							<div class="flex flex-col gap-1">
								<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
									{$i18n.t('Code Interpreter Engine')}
								</span>
								<span class="text-xs text-gray-500 dark:text-gray-400">
									Choose the interpreter environment
								</span>
							</div>
							<select
								class="bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-medium text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
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

						{#if config.CODE_INTERPRETER_ENGINE === 'jupyter'}
							<div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 flex gap-2">
								<svg class="w-5 h-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
								</svg>
								<p class="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
									{$i18n.t('Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.')}
								</p>
							</div>

							<div class="space-y-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
								<div class="space-y-2">
									<label class="text-sm font-medium text-gray-900 dark:text-gray-100">
										{$i18n.t('Jupyter URL')}
									</label>
									<input
										class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg placeholder:text-gray-400 dark:placeholder:text-gray-500 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
										type="text"
										placeholder={$i18n.t('Enter Jupyter URL')}
										bind:value={config.CODE_INTERPRETER_JUPYTER_URL}
										autocomplete="off"
									/>
								</div>

								<div class="space-y-2">
									<div class="flex items-center justify-between">
										<label class="text-sm font-medium text-gray-900 dark:text-gray-100">
											{$i18n.t('Jupyter Auth')}
										</label>
										<select
											class="bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-2 text-sm font-medium text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
											bind:value={config.CODE_INTERPRETER_JUPYTER_AUTH}
											placeholder={$i18n.t('Select an auth method')}
										>
											<option selected value="">{$i18n.t('None')}</option>
											<option value="token">{$i18n.t('Token')}</option>
											<option value="password">{$i18n.t('Password')}</option>
										</select>
									</div>

									{#if config.CODE_INTERPRETER_JUPYTER_AUTH}
										<div>
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
									{/if}
								</div>

								<div class="flex items-center justify-between">
									<label class="text-sm font-medium text-gray-900 dark:text-gray-100">
										{$i18n.t('Code Execution Timeout')}
									</label>
									<Tooltip content={$i18n.t('Enter timeout in seconds')}>
										<input
											class="w-24 px-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-gray-100 text-right focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition"
											type="number"
											bind:value={config.CODE_INTERPRETER_JUPYTER_TIMEOUT}
											placeholder={$i18n.t('e.g. 60')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						{/if}

						<div class="p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
							<div class="space-y-2">
								<label class="text-sm font-medium text-gray-900 dark:text-gray-100">
									{$i18n.t('Code Interpreter Prompt Template')}
								</label>
								<p class="text-xs text-gray-500 dark:text-gray-400">
									{$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
								</p>
								<Tooltip
									content={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
									placement="top-start"
								>
									<Textarea
										bind:value={config.CODE_INTERPRETER_PROMPT_TEMPLATE}
										placeholder={$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
									/>
								</Tooltip>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-4 px-1 border-t border-gray-200 dark:border-gray-800 mt-4">
		<button
			class="px-5 py-2.5 text-sm font-semibold bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white transition-all duration-200 rounded-lg shadow-sm hover:shadow-md active:scale-95"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>