<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { theme } from '$lib/stores';
	import { resolveTheme } from '$lib/utils/theme';

	const i18n = getContext('i18n');

	let providers = [];
	let loading = false;
	let showEditModal = false;
	let editingProvider = null;

	// Form fields for editing
	let formId = '';
	let formName = '';
	let formLogoUrl = '';
	let formLogoLightUrl = '';
	let formLogoDarkUrl = '';
	let formPatterns = '';
	let formModelPatterns = '';
	let formPriority = 50;
	let formIsActive = true;

	// JSON editor state
	let jsonValidationError = '';
	let jsonLineCount = 1;
	let jsonTextareaElement = null;
	let lineNumbersElement = null;

	// Sync scroll between textarea and line numbers
	const syncScroll = () => {
		if (jsonTextareaElement && lineNumbersElement) {
			lineNumbersElement.scrollTop = jsonTextareaElement.scrollTop;
		}
	};

	// Reactive JSON validation
	$: {
		if (formModelPatterns.trim()) {
			try {
				const parsed = JSON.parse(formModelPatterns);
				if (!Array.isArray(parsed)) {
					jsonValidationError = 'Must be a JSON array';
				} else {
					jsonValidationError = '';
				}
			} catch (error) {
				jsonValidationError = error.message;
			}
		} else {
			jsonValidationError = '';
		}
		// Update line count
		jsonLineCount = formModelPatterns.split('\n').length;
	}

	onMount(async () => {
		await loadProviders();
	});

	const loadProviders = async () => {
		loading = true;
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/providers/`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!res.ok) {
				throw new Error(await res.text());
			}

			providers = await res.json();
		} catch (error) {
			toast.error($i18n.t('Failed to load providers'));
		} finally {
			loading = false;
		}
	};

	const openEditModal = (provider = null) => {
		if (provider) {
			// Edit existing provider
			editingProvider = provider;
			formId = provider.id;
			formName = provider.name;
			formLogoUrl = provider.logo_url || '';
			formLogoLightUrl = provider.logo_light_url || '';
			formLogoDarkUrl = provider.logo_dark_url || '';
			formPatterns = provider.model_id_patterns.join(', ');

			// Handle model_patterns - it might be a string or already parsed
			if (provider.model_patterns) {
				if (typeof provider.model_patterns === 'string') {
					formModelPatterns = provider.model_patterns;
				} else {
					formModelPatterns = JSON.stringify(provider.model_patterns, null, 2);
				}
			} else {
				formModelPatterns = '';
			}

			formPriority = provider.priority;
			formIsActive = provider.is_active;
		} else {
			// Create new provider
			editingProvider = null;
			formId = '';
			formName = '';
			formLogoUrl = '';
			formLogoLightUrl = '';
			formLogoDarkUrl = '';
			formPatterns = '';
			formModelPatterns = '';
			formPriority = 50;
			formIsActive = true;
		}
		showEditModal = true;
	};

	const closeEditModal = () => {
		showEditModal = false;
		editingProvider = null;
	};

	const saveProvider = async () => {
		const patterns = formPatterns
			.split(',')
			.map((p) => p.trim())
			.filter((p) => p.length > 0);

		let modelPatterns = null;
		if (formModelPatterns.trim()) {
			try {
				modelPatterns = JSON.parse(formModelPatterns);
				// Validate it's an array
				if (!Array.isArray(modelPatterns)) {
					toast.error($i18n.t('Model patterns must be a JSON array'));
					return;
				}
			} catch (error) {
				toast.error($i18n.t('Invalid JSON') + ': ' + error.message);
				return;
			}
		}

		const providerData = {
			id: formId,
			name: formName,
			logo_url: formLogoUrl || null,
			logo_light_url: formLogoLightUrl || null,
			logo_dark_url: formLogoDarkUrl || null,
			model_id_patterns: patterns,
			model_patterns: modelPatterns,
			priority: formPriority,
			is_active: formIsActive
		};

		try {
			const endpoint = editingProvider
				? `${WEBUI_API_BASE_URL}/providers/${editingProvider.id}/update`
				: `${WEBUI_API_BASE_URL}/providers/create`;

			const res = await fetch(endpoint, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(providerData)
			});

			if (!res.ok) {
				const error = await res.json();
				throw new Error(error.detail || 'Failed to save provider');
			}

			toast.success($i18n.t(editingProvider ? 'Provider updated' : 'Provider created'));
			closeEditModal();
			await loadProviders();
		} catch (error) {
			toast.error(error.message);
		}
	};

	const deleteProvider = async (providerId: string) => {
		if (!confirm($i18n.t('Are you sure you want to delete this provider?'))) {
			return;
		}

		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/providers/${providerId}/delete`, {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!res.ok) {
				throw new Error(await res.text());
			}

			toast.success($i18n.t('Provider deleted'));
			await loadProviders();
		} catch (error) {
			toast.error($i18n.t('Failed to delete provider'));
		}
	};
</script>

<div class="flex flex-col h-full text-sm">
	<div class="flex justify-between items-center mb-3">
		<div class="text-sm font-medium">{$i18n.t('Model Providers')}</div>
		<button
			class="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition"
			on:click={() => openEditModal(null)}
		>
			{$i18n.t('Add Provider')}
		</button>
	</div>

	<div class="text-xs text-gray-500 dark:text-gray-400 mb-3">
		{$i18n.t(
			'Configure automatic logo assignment for model providers. Models matching the patterns will automatically receive the provider logo unless manually overridden.'
		)}
	</div>

	<div class="flex-1 overflow-y-auto pr-1.5">
		{#if loading}
			<div class="flex justify-center py-8">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-white" />
			</div>
		{:else if providers.length === 0}
			<div class="text-center py-8 text-gray-500 dark:text-gray-400">
				{$i18n.t('No providers configured')}
			</div>
		{:else}
			<div class="space-y-2">
				{#each providers as provider (provider.id)}
					<div
						class="border dark:border-gray-800 rounded-lg p-3 flex items-start gap-3 hover:bg-gray-50 dark:hover:bg-gray-900 transition"
					>
						<div class="shrink-0 pt-1">
							{#if provider.logo_url || provider.logo_light_url || provider.logo_dark_url}
								{#key $theme}
									{@const logoUrl = resolveTheme($theme) === 'dark' && provider.logo_dark_url ? provider.logo_dark_url : (resolveTheme($theme) === 'light' && provider.logo_light_url ? provider.logo_light_url : provider.logo_url)}
									<img
										src={logoUrl}
										alt={provider.name}
										class="w-10 h-10 rounded-full object-cover"
										on:error={(e) => {
											// Fallback to initials if image fails to load
											e.target.style.display = 'none';
										}}
									/>
								{/key}
							{:else}
								<div
									class="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs font-medium"
								>
									{provider.name.substring(0, 2).toUpperCase()}
								</div>
							{/if}
						</div>

						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<div class="font-semibold">{provider.name}</div>
								{#if !provider.is_active}
									<span
										class="text-xs px-2 py-0.5 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded"
									>
										{$i18n.t('Inactive')}
									</span>
								{/if}
							</div>
							<div class="text-xs text-gray-600 dark:text-gray-400 mt-1">
								<div>
									<span class="font-medium">{$i18n.t('ID')}:</span>
									{provider.id}
								</div>
								<div>
									<span class="font-medium">{$i18n.t('Priority')}:</span>
									{provider.priority}
								</div>
								{#if provider.model_id_patterns.length > 0}
									<div class="mt-1">
										<span class="font-medium">{$i18n.t('Patterns')}:</span>
										<span class="font-mono text-xs">
											{provider.model_id_patterns.join(', ')}
										</span>
									</div>
								{/if}
							</div>
						</div>

						<div class="flex gap-2 shrink-0">
							<button
								class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded transition"
								on:click={() => openEditModal(provider)}
							>
								{$i18n.t('Edit')}
							</button>
							<button
								class="px-2 py-1 text-xs bg-red-100 hover:bg-red-200 dark:bg-red-900/20 dark:hover:bg-red-900/40 text-red-600 dark:text-red-400 rounded transition"
								on:click={() => deleteProvider(provider.id)}
							>
								{$i18n.t('Delete')}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>

{#if showEditModal}
	<div
		class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
		on:click={closeEditModal}
		on:keydown={(e) => e.key === 'Escape' && closeEditModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
			on:click|stopPropagation
			role="dialog"
			aria-modal="true"
		>
			<div class="p-6">
				<h2 class="text-lg font-semibold mb-4">
					{editingProvider ? $i18n.t('Edit Provider') : $i18n.t('Add Provider')}
				</h2>

				{#key editingProvider?.id || 'new'}
				<form
					on:submit|preventDefault={saveProvider}
					class="space-y-4"
				>
					<div>
						<label class="block text-sm font-medium mb-1">
							{$i18n.t('Provider ID')}
							<span class="text-red-500">*</span>
						</label>
						<input
							type="text"
							bind:value={formId}
							disabled={editingProvider !== null}
							required
							placeholder="openai"
							class="w-full px-3 py-2 border dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
						/>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							{$i18n.t('Unique identifier (lowercase, no spaces)')}
						</p>
					</div>

					<div>
						<label class="block text-sm font-medium mb-1">
							{$i18n.t('Provider Name')}
							<span class="text-red-500">*</span>
						</label>
						<input
							type="text"
							bind:value={formName}
							required
							placeholder="OpenAI"
							class="w-full px-3 py-2 border dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
						/>
					</div>

					<div>
						<label class="block text-sm font-medium mb-1">
							{$i18n.t('Logo URL (default)')}
						</label>
						<input
							type="text"
							bind:value={formLogoUrl}
							placeholder="/providers/{formId || 'provider'}.png"
							class="w-full px-3 py-2 border dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
						/>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							{$i18n.t('Path from /static/ directory, external URL, or base64 data URL. Supports PNG, SVG, JPG.')}
						</p>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium mb-1">
								{$i18n.t('Light Theme Logo')}
							</label>
							<input
								type="text"
								bind:value={formLogoLightUrl}
								placeholder="/providers/{formId || 'provider'}-light.png"
								class="w-full px-3 py-2 border dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
							/>
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('Optional: Override for light theme')}
							</p>
						</div>

						<div>
							<label class="block text-sm font-medium mb-1">
								{$i18n.t('Dark Theme Logo')}
							</label>
							<input
								type="text"
								bind:value={formLogoDarkUrl}
								placeholder="/providers/{formId || 'provider'}-dark.png"
								class="w-full px-3 py-2 border dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
							/>
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('Optional: Override for dark theme')}
							</p>
						</div>
					</div>

					<div>
						<label class="block text-sm font-medium mb-1">
							{$i18n.t('Model ID Patterns')}
						</label>
						<input
							type="text"
							bind:value={formPatterns}
							placeholder="^gpt-, ^o1-, ^text-davinci"
							class="w-full px-3 py-2 border dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 font-mono text-sm"
						/>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							{$i18n.t('Comma-separated regex patterns (e.g., ^gpt-, ^claude-)')}
						</p>
					</div>

					<div>
						<label class="block text-sm font-medium mb-1">
							{$i18n.t('Model-Specific Logos')} <span class="text-gray-500 text-xs font-normal">({$i18n.t('Optional')})</span>
						</label>

						<!-- JSON Editor with line numbers -->
						<div class="json-editor-container flex border {jsonValidationError ? 'border-red-500 dark:border-red-500' : 'border-gray-300 dark:border-gray-700'} rounded-lg bg-white dark:bg-gray-800 overflow-hidden resize-y min-h-[12rem]" style="resize: vertical;">
							<!-- Line numbers (scrolls with textarea) -->
							<div
								bind:this={lineNumbersElement}
								class="w-10 bg-gray-100 dark:bg-gray-900 border-r border-gray-300 dark:border-gray-700 select-none shrink-0"
								style="overflow-y: scroll; overflow-x: hidden; scrollbar-width: none; -ms-overflow-style: none;"
							>
								<style>
									.json-editor-container::-webkit-scrollbar,
									div::-webkit-scrollbar {
										display: none;
									}
								</style>
								<div class="py-2 px-2 text-right text-xs text-gray-500 dark:text-gray-500 font-mono leading-[1.5rem] pointer-events-none">
									{#each Array(Math.max(jsonLineCount, 8)) as _, i}
										<div>{i + 1}</div>
									{/each}
								</div>
							</div>

							<!-- Textarea -->
							<textarea
								bind:value={formModelPatterns}
								bind:this={jsonTextareaElement}
								on:scroll={syncScroll}
								placeholder={`[\n  {\n    "name": "model-name",\n    "patterns": ["^pattern1-", "^pattern2:"],\n    "logo_url": "/providers/models/model-light.svg",\n    "logo_light_url": "/providers/models/model-light.svg",\n    "logo_dark_url": "/providers/models/model-dark.svg"\n  }\n]`}
								rows="8"
								class="flex-1 px-3 py-2 bg-transparent font-mono text-xs focus:outline-none"
								style="line-height: 1.5rem; resize: none;"
								spellcheck="false"
								autocomplete="off"
							></textarea>
						</div>

						<!-- Validation feedback -->
						{#if jsonValidationError}
							<p class="text-xs text-red-600 dark:text-red-400 mt-1 font-mono">
								<span class="font-semibold">JSON Error:</span> {jsonValidationError}
							</p>
						{:else if formModelPatterns.trim()}
							<p class="text-xs text-green-600 dark:text-green-400 mt-1">
								✓ Valid JSON
							</p>
						{/if}

						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							{$i18n.t('JSON array of model-specific logo overrides. Leave empty to use provider logo for all models.')}
						</p>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium mb-1">
								{$i18n.t('Priority')}
							</label>
							<input
								type="number"
								bind:value={formPriority}
								min="0"
								max="1000"
								class="w-full px-3 py-2 border dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
							/>
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('0-1000, default 50. Higher priority checked first for overlapping patterns.')}
							</p>
						</div>

						<div>
							<label class="block text-sm font-medium mb-1">
								{$i18n.t('Status')}
							</label>
							<div class="flex items-center h-10">
								<label class="flex items-center cursor-pointer">
									<input
										type="checkbox"
										bind:checked={formIsActive}
										class="mr-2"
									/>
									<span>{$i18n.t('Active')}</span>
								</label>
							</div>
						</div>
					</div>

					<div class="flex justify-end gap-2 pt-4 border-t dark:border-gray-700">
						<button
							type="button"
							on:click={closeEditModal}
							class="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition"
						>
							{$i18n.t('Cancel')}
						</button>
						<button
							type="submit"
							class="px-4 py-2 text-sm bg-black hover:bg-gray-900 dark:bg-white dark:hover:bg-gray-100 text-white dark:text-black rounded-lg transition"
						>
							{$i18n.t('Save')}
						</button>
					</div>
				</form>
			{/key}
			</div>
		</div>
	</div>
{/if}
