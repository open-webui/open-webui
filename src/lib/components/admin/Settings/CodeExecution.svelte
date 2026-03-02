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
	<div class="space-y-5 overflow-y-scroll scrollbar-hidden h-full px-1">
		{#if config}
			<!-- General Settings Section -->
			<div class="bg-gradient-to-b from-gray-50/50 to-transparent dark:from-gray-800/20 dark:to-transparent rounded-xl p-5 border border-gray-200/60 dark:border-gray-700/30">
				<div class="mb-4 flex items-center gap-2">
					<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
					<h3 class="text-base font-medium text-gray-800 dark:text-gray-200">
						{$i18n.t('General')}
					</h3>
				</div>

				<div class="space-y-3">
					<div class="flex items-center justify-between p-4 bg-white dark:bg-gray-800/50 rounded-lg border border-gray-200/80 dark:border-gray-700/50 shadow-xs">
						<div class="flex flex-col gap-1">
							<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
								{$i18n.t('Enable Code Execution')}
							</span>
							<span class="text-xs text-gray-600 dark:text-gray-400">
								Allow code execution in your environment
							</span>
						</div>
						<Switch bind:state={config.ENABLE_CODE_EXECUTION} />
					</div>

					<div class="flex items-center justify-between p-4 bg-white dark:bg-gray-800/50 rounded-lg border border-gray-200/80 dark:border-gray-700/50 shadow-sm">
						<div class="flex flex-col gap-1 flex-1 mr-4">
							<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
								{$i18n.t('Code Execution Engine')}
							</span>
							<span class="text-xs text-gray-600 dark:text-gray-400">
								Choose the execution environment
							</span>
						</div>
						<select
							class="bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 rounded-lg px-3 py-2 text-sm font-medium text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20 focus:border-transparent outline-none transition-colors"
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
						<div class="bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-300 dark:border-amber-700/50 rounded-lg p-4 flex gap-3 shadow-sm">
							<svg class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
							</svg>
							<p class="text-xs text-amber-900 dark:text-amber-200 leading-relaxed font-medium">
								⚠️ {$i18n.t('Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.')}
							</p>
						</div>

						<div class="space-y-4 p-4 bg-white dark:bg-gray-800/50 rounded-lg border border-gray-200/80 dark:border-gray-700/50 shadow-sm">
							<div class="space-y-2">
								<label class="text-sm font-medium text-gray-700 dark:text-gray-300 block">
									{$i18n.t('Jupyter URL')}
								</label>
								<input
									class="w-full px-3.5 py-2.5 text-sm bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 rounded-lg placeholder:text-gray-500 dark:placeholder:text-gray-400 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20 focus:border-transparent outline-none transition-colors"
									type="text"
									placeholder={$i18n.t('Enter Jupyter URL')}
									bind:value={config.CODE_EXECUTION_JUPYTER_URL}
									autocomplete="off"
								/>
							</div>

							<div class="space-y-2">
								<div class="flex items-center justify-between">
									<label class="text-sm font-medium text-gray-700 dark:text-gray-300">
										{$i18n.t('Jupyter Auth')}
									</label>
									<select
										class="bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 rounded-lg px-3 py-2 text-sm font-medium text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20 focus:border-transparent outline-none transition-colors"
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

							<div class="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700/50">
								<label class="text-sm font-medium text-gray-700 dark:text-gray-300">
									{$i18n.t('Code Execution Timeout')}
								</label>
								<Tooltip content={$i18n.t('Enter timeout in seconds')}>
									<input
										class="w-28 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 rounded-lg text-gray-800 dark:text-gray-200 text-right focus:ring-2 focus:ring-orange-500/20 dark:focus:ring-orange-400/20 focus:border-transparent outline-none transition-colors font-medium"
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
			<div class="bg-gradient-to-b from-gray-50/50 to-transparent dark:from-gray-800/20 dark:to-transparent rounded-xl p-5 border border-gray-200/60 dark:border-gray-700/30">
				<div class="mb-4 flex items-center gap-2">
					<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
					<h3 class="text-base font-medium text-gray-800 dark:text-gray-200">
						{$i18n.t('Code Interpreter')}
					</h3>
				</div>

				<div class="space-y-3">
					<div class="flex items-center justify-between p-4 bg-white dark:bg-gray-800/50 rounded-lg border border-gray-200/80 dark:border-gray-700/50 shadow-sm">
						<div class="flex flex-col gap-1">
							<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
								{$i18n.t('Enable Code Interpreter')}
							</span>
							<span class="text-xs text-gray-600 dark:text-gray-400">
								Allow interactive code interpretation
							</span>
						</div>
						<Switch bind:state={config.ENABLE_CODE_INTERPRETER} />
					</div>

					{#if config.ENABLE_CODE_INTERPRETER}
						<div class="flex items-center justify-between p-4 bg-white dark:bg-gray-800/50 rounded-lg border border-gray-200/80 dark:border-gray-700/50 shadow-sm">
							<div class="flex flex-col gap-1 flex-1 mr-4">
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
									{$i18n.t('Code Interpreter Engine')}
								</span>
								<span class="text-xs text-gray-600 dark:text-gray-400">
									Choose the interpreter environment
								</span>
							</div>
							<select
								class="bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 rounded-lg px-3 py-2 text-sm font-medium text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 focus:border-transparent outline-none transition-colors"
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
							<div class="bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-300 dark:border-amber-700/50 rounded-lg p-4 flex gap-3 shadow-sm">
								<svg class="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
								</svg>
								<p class="text-xs text-amber-900 dark:text-amber-200 leading-relaxed font-medium">
									⚠️ {$i18n.t('Warning: Jupyter execution enables arbitrary code execution, posing severe security risks—proceed with extreme caution.')}
								</p>
							</div>

							<div class="space-y-4 p-4 bg-white dark:bg-gray-800/50 rounded-lg border border-gray-200/80 dark:border-gray-700/50 shadow-sm">
								<div class="space-y-2">
									<label class="text-sm font-medium text-gray-700 dark:text-gray-300 block">
										{$i18n.t('Jupyter URL')}
									</label>
									<input
										class="w-full px-3.5 py-2.5 text-sm bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 rounded-lg placeholder:text-gray-500 dark:placeholder:text-gray-400 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 focus:border-transparent outline-none transition-colors"
										type="text"
										placeholder={$i18n.t('Enter Jupyter URL')}
										bind:value={config.CODE_INTERPRETER_JUPYTER_URL}
										autocomplete="off"
									/>
								</div>

								<div class="space-y-2">
									<div class="flex items-center justify-between">
										<label class="text-sm font-medium text-gray-700 dark:text-gray-300">
											{$i18n.t('Jupyter Auth')}
										</label>
										<select
											class="bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 rounded-lg px-3 py-2 text-sm font-medium text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 focus:border-transparent outline-none transition-colors"
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

								<div class="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700/50">
									<label class="text-sm font-medium text-gray-700 dark:text-gray-300">
										{$i18n.t('Code Execution Timeout')}
									</label>
									<Tooltip content={$i18n.t('Enter timeout in seconds')}>
										<input
											class="w-28 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 border border-gray-300/50 dark:border-gray-600/50 rounded-lg text-gray-800 dark:text-gray-200 text-right focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 focus:border-transparent outline-none transition-colors font-medium"
											type="number"
											bind:value={config.CODE_INTERPRETER_JUPYTER_TIMEOUT}
											placeholder={$i18n.t('e.g. 60')}
											autocomplete="off"
										/>
									</Tooltip>
								</div>
							</div>
						{/if}

						<div class="p-4 bg-white dark:bg-gray-800/50 rounded-lg border border-gray-200/80 dark:border-gray-700/50 shadow-sm">
							<div class="space-y-3">
								<div>
									<label class="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">
										{$i18n.t('Code Interpreter Prompt Template')}
									</label>
									<p class="text-xs text-gray-600 dark:text-gray-400 mb-2">
										{$i18n.t('Leave empty to use the default prompt, or enter a custom prompt')}
									</p>
								</div>
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

	<div class="flex justify-end pt-4 px-1 border-t border-gray-200 dark:border-gray-700/50 mt-4">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>