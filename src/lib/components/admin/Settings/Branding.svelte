<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { config } from '$lib/stores';
	import { getBackendConfig } from '$lib/apis';
	import { getBrandingConfig, setBrandingConfig } from '$lib/apis/configs';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let saveHandler: () => void;

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	let loading = true;

	let brandingConfig = {
		app_name: '',
		accent_color: '#e3530f',
		accent_color_scale: {},
		logo_url: '',
		logo_dark_url: '',
		favicon_url: '',
		login_background_url: '',
		login_background_color: '',
		presets: [],
		domain_mappings: []
	};

	// Preset editing
	let newPresetName = '';
	let editingPresetIndex = -1;

	// Domain mapping editing
	let newDomain = '';
	let newDomainPreset = '';

	// Color scale generation from a base hex color
	function generateColorScale(hex: string): Record<string, string> {
		const r = parseInt(hex.slice(1, 3), 16);
		const g = parseInt(hex.slice(3, 5), 16);
		const b = parseInt(hex.slice(5, 7), 16);

		function mix(c1: number, c2: number, weight: number): number {
			return Math.round(c1 * weight + c2 * (1 - weight));
		}

		function toHex(r: number, g: number, b: number): string {
			return (
				'#' +
				[r, g, b]
					.map((c) => {
						const hex = Math.max(0, Math.min(255, c)).toString(16);
						return hex.length === 1 ? '0' + hex : hex;
					})
					.join('')
			);
		}

		return {
			'50': toHex(mix(r, 255, 0.05), mix(g, 255, 0.05), mix(b, 255, 0.05)),
			'100': toHex(mix(r, 255, 0.15), mix(g, 255, 0.15), mix(b, 255, 0.15)),
			'200': toHex(mix(r, 255, 0.3), mix(g, 255, 0.3), mix(b, 255, 0.3)),
			'300': toHex(mix(r, 255, 0.5), mix(g, 255, 0.5), mix(b, 255, 0.5)),
			'400': toHex(mix(r, 255, 0.7), mix(g, 255, 0.7), mix(b, 255, 0.7)),
			'500': hex,
			'600': toHex(mix(r, 0, 0.85), mix(g, 0, 0.85), mix(b, 0, 0.85)),
			'700': toHex(mix(r, 0, 0.7), mix(g, 0, 0.7), mix(b, 0, 0.7)),
			'800': toHex(mix(r, 0, 0.55), mix(g, 0, 0.55), mix(b, 0, 0.55)),
			'900': toHex(mix(r, 0, 0.45), mix(g, 0, 0.45), mix(b, 0, 0.45)),
			'950': toHex(mix(r, 0, 0.25), mix(g, 0, 0.25), mix(b, 0, 0.25))
		};
	}

	function handleAccentColorChange() {
		brandingConfig.accent_color_scale = generateColorScale(brandingConfig.accent_color);
	}

	function addPreset() {
		if (!newPresetName.trim()) {
			toast.error($i18n.t('Please enter a preset name'));
			return;
		}
		brandingConfig.presets = [
			...brandingConfig.presets,
			{
				name: newPresetName.trim(),
				accent_color: brandingConfig.accent_color,
				accent_color_scale: { ...brandingConfig.accent_color_scale },
				background_color: '',
				logo_url: '',
				logo_dark_url: '',
				favicon_url: '',
				login_background_url: '',
				login_background_color: '',
				microsoft_client_id: '',
				microsoft_client_secret: '',
				microsoft_tenant_id: ''
			}
		];
		newPresetName = '';
	}

	function loadPreset(index: number) {
		const preset = brandingConfig.presets[index];
		brandingConfig.accent_color = preset.accent_color || '#e3530f';
		brandingConfig.accent_color_scale = preset.accent_color_scale || {};
		brandingConfig.logo_url = preset.logo_url || '';
		brandingConfig.logo_dark_url = preset.logo_dark_url || '';
		brandingConfig.favicon_url = preset.favicon_url || '';
		brandingConfig.login_background_url = preset.login_background_url || '';
		brandingConfig.login_background_color = preset.login_background_color || '';
		toast.success($i18n.t('Preset "{{name}}" loaded', { name: preset.name }));
	}

	function saveToPreset(index: number) {
		brandingConfig.presets[index] = {
			...brandingConfig.presets[index],
			accent_color: brandingConfig.accent_color,
			accent_color_scale: { ...brandingConfig.accent_color_scale },
			logo_url: brandingConfig.logo_url,
			logo_dark_url: brandingConfig.logo_dark_url,
			favicon_url: brandingConfig.favicon_url,
			login_background_url: brandingConfig.login_background_url,
			login_background_color: brandingConfig.login_background_color
		};
		brandingConfig.presets = [...brandingConfig.presets];
		toast.success(
			$i18n.t('Current settings saved to "{{name}}"', {
				name: brandingConfig.presets[index].name
			})
		);
	}

	function removePreset(index: number) {
		const name = brandingConfig.presets[index].name;
		// Also remove any domain mappings that reference this preset
		brandingConfig.domain_mappings = brandingConfig.domain_mappings.filter(
			(m) => m.preset_name !== name
		);
		brandingConfig.presets = brandingConfig.presets.filter((_, i) => i !== index);
	}

	function addDomainMapping() {
		if (!newDomain.trim()) {
			toast.error($i18n.t('Please enter a domain'));
			return;
		}
		if (!newDomainPreset) {
			toast.error($i18n.t('Please select a preset'));
			return;
		}
		brandingConfig.domain_mappings = [
			...brandingConfig.domain_mappings,
			{
				domain: newDomain.trim(),
				preset_name: newDomainPreset
			}
		];
		newDomain = '';
		newDomainPreset = '';
	}

	function removeDomainMapping(index: number) {
		brandingConfig.domain_mappings = brandingConfig.domain_mappings.filter((_, i) => i !== index);
	}

	const saveBrandingHandler = async () => {
		// Auto-generate color scale if not set
		if (
			!brandingConfig.accent_color_scale ||
			Object.keys(brandingConfig.accent_color_scale).length === 0
		) {
			brandingConfig.accent_color_scale = generateColorScale(brandingConfig.accent_color);
		}

		const result = await setBrandingConfig(localStorage.token, brandingConfig);
		if (result) {
			brandingConfig = result;
			await config.set(await getBackendConfig());
			saveHandler();
		}
	};

	onMount(async () => {
		try {
			const result = await getBrandingConfig(localStorage.token);
			if (result) {
				brandingConfig = {
					app_name: result.app_name || '',
					accent_color: result.accent_color || '#e3530f',
					accent_color_scale: result.accent_color_scale || {},
					logo_url: result.logo_url || '',
					logo_dark_url: result.logo_dark_url || '',
					favicon_url: result.favicon_url || '',
					login_background_url: result.login_background_url || '',
					login_background_color: result.login_background_color || '',
					presets: result.presets || [],
					domain_mappings: result.domain_mappings || []
				};
			}
		} catch (e) {
			console.error('Failed to load branding config:', e);
		}
		loading = false;
	});
</script>

{#if !loading}
	<form
		class="flex flex-col h-full justify-between space-y-3 text-sm"
		on:submit|preventDefault={() => {
			saveBrandingHandler();
		}}
	>
		<div class="overflow-y-scroll scrollbar-hidden h-full pr-1.5">
			<!-- ═══════════════════════════════════════════ -->
			<!-- IDENTITY -->
			<!-- ═══════════════════════════════════════════ -->
			<div class="mb-4">
				<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Identity')}</div>
				<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="mb-3">
					<div class="mb-1 text-xs font-medium">{$i18n.t('App Name')}</div>
					<input
						class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
						bind:value={brandingConfig.app_name}
						placeholder={$i18n.t('Leave empty to use default')}
					/>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('Overrides the app name shown in the UI and browser tab')}
					</div>
				</div>
			</div>

			<!-- ═══════════════════════════════════════════ -->
			<!-- ACCENT COLOR -->
			<!-- ═══════════════════════════════════════════ -->
			<div class="mb-4">
				<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Accent Color')}</div>
				<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="mb-3 flex items-center gap-3">
					<div class="relative">
						<input
							type="color"
							class="w-12 h-10 rounded-lg cursor-pointer border-2 border-gray-200 dark:border-gray-700"
							bind:value={brandingConfig.accent_color}
							on:input={handleAccentColorChange}
						/>
					</div>
					<div class="flex-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden font-mono"
							bind:value={brandingConfig.accent_color}
							on:input={handleAccentColorChange}
							placeholder="#e3530f"
						/>
					</div>
					<button
						type="button"
						class="px-3 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
						on:click={() => {
							brandingConfig.accent_color = '#e3530f';
							handleAccentColorChange();
						}}
					>
						{$i18n.t('Reset')}
					</button>
				</div>

				<!-- Color scale preview -->
				{#if brandingConfig.accent_color_scale && Object.keys(brandingConfig.accent_color_scale).length > 0}
					<div class="mb-3">
						<div class="mb-1.5 text-xs font-medium text-gray-500">
							{$i18n.t('Generated Color Scale')}
						</div>
						<div class="flex rounded-lg overflow-hidden h-8">
							{#each ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950'] as shade}
								<Tooltip content="{shade}: {brandingConfig.accent_color_scale[shade] || ''}">
									<div
										class="flex-1 h-8 transition-all"
										style="background-color: {brandingConfig.accent_color_scale[shade] || '#ccc'}"
									/>
								</Tooltip>
							{/each}
						</div>
					</div>
				{/if}

				<button
					type="button"
					class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
					on:click={handleAccentColorChange}
				>
					{$i18n.t('Regenerate color scale from accent color')}
				</button>
			</div>

			<!-- ═══════════════════════════════════════════ -->
			<!-- LOGOS & ASSETS -->
			<!-- ═══════════════════════════════════════════ -->
			<div class="mb-4">
				<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Logos & Assets')}</div>
				<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
					<div>
						<div class="mb-1 text-xs font-medium">{$i18n.t('Logo URL (Light)')}</div>
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							bind:value={brandingConfig.logo_url}
							placeholder="https://example.com/logo.png"
						/>
						{#if brandingConfig.logo_url}
							<div
								class="mt-2 p-3 rounded-lg bg-white border border-gray-200 flex items-center justify-center"
							>
								<img
									src={brandingConfig.logo_url}
									alt="Logo preview"
									class="max-h-12 max-w-full object-contain"
								/>
							</div>
						{/if}
					</div>

					<div>
						<div class="mb-1 text-xs font-medium">{$i18n.t('Logo URL (Dark)')}</div>
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							bind:value={brandingConfig.logo_dark_url}
							placeholder="https://example.com/logo-dark.png"
						/>
						{#if brandingConfig.logo_dark_url}
							<div
								class="mt-2 p-3 rounded-lg bg-gray-900 border border-gray-700 flex items-center justify-center"
							>
								<img
									src={brandingConfig.logo_dark_url}
									alt="Dark logo preview"
									class="max-h-12 max-w-full object-contain"
								/>
							</div>
						{/if}
					</div>
				</div>

				<div class="mb-3">
					<div class="mb-1 text-xs font-medium">{$i18n.t('Favicon URL')}</div>
					<input
						class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
						bind:value={brandingConfig.favicon_url}
						placeholder="https://example.com/favicon.png"
					/>
					<div class="text-xs text-gray-500 mt-1">
						{$i18n.t('Recommended: 32x32 or 64x64 PNG')}
					</div>
				</div>
			</div>

			<!-- ═══════════════════════════════════════════ -->
			<!-- LOGIN PAGE -->
			<!-- ═══════════════════════════════════════════ -->
			<div class="mb-4">
				<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Login Page')}</div>
				<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
					<div>
						<div class="mb-1 text-xs font-medium">{$i18n.t('Background Image URL')}</div>
						<input
							class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
							bind:value={brandingConfig.login_background_url}
							placeholder="https://example.com/bg.jpg"
						/>
					</div>

					<div>
						<div class="mb-1 text-xs font-medium">{$i18n.t('Background Color')}</div>
						<div class="flex items-center gap-2">
							<input
								type="color"
								class="w-10 h-10 rounded-lg cursor-pointer border-2 border-gray-200 dark:border-gray-700"
								bind:value={brandingConfig.login_background_color}
							/>
							<input
								class="flex-1 rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden font-mono"
								bind:value={brandingConfig.login_background_color}
								placeholder="#1a2744"
							/>
						</div>
					</div>
				</div>

				<!-- Login page preview -->
				{#if brandingConfig.login_background_color || brandingConfig.login_background_url}
					<div class="mb-3">
						<div class="mb-1.5 text-xs font-medium text-gray-500">
							{$i18n.t('Preview')}
						</div>
						<div
							class="rounded-lg h-24 border border-gray-200 dark:border-gray-700 flex items-center justify-center overflow-hidden"
							style="background-color: {brandingConfig.login_background_color ||
								'transparent'}; {brandingConfig.login_background_url
								? `background-image: url(${brandingConfig.login_background_url}); background-size: cover; background-position: center;`
								: ''}"
						>
							<div
								class="text-xs font-medium px-3 py-1.5 rounded-full"
								style="background-color: {brandingConfig.accent_color}; color: white;"
							>
								{$i18n.t('Sign In')}
							</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- ═══════════════════════════════════════════ -->
			<!-- THEME PRESETS -->
			<!-- ═══════════════════════════════════════════ -->
			<div class="mb-4">
				<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Theme Presets')}</div>
				<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="text-xs text-gray-500 mb-3">
					{$i18n.t(
						'Save and load named theme configurations. Presets can be mapped to domains for automatic theming.'
					)}
				</div>

				<!-- Existing presets -->
				{#if brandingConfig.presets.length > 0}
					<div class="space-y-2 mb-3">
						{#each brandingConfig.presets as preset, index}
							<div
								class="rounded-lg bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800"
							>
								<div class="flex items-center gap-2 p-3">
									<!-- Color swatch -->
									<div
										class="w-8 h-8 rounded-md shrink-0 border border-gray-200 dark:border-gray-700"
										style="background: linear-gradient(135deg, {preset.accent_color ||
											'#e3530f'} 50%, {preset.background_color ||
											preset.login_background_color ||
											'#1a2744'} 50%)"
									/>

									<div class="flex-1 min-w-0">
										{#if editingPresetIndex === index}
											<input
												class="w-full rounded py-1 px-2 text-sm bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700"
												bind:value={preset.name}
												on:blur={() => {
													editingPresetIndex = -1;
													brandingConfig.presets = [...brandingConfig.presets];
												}}
												on:keydown={(e) => {
													if (e.key === 'Enter') {
														editingPresetIndex = -1;
														brandingConfig.presets = [...brandingConfig.presets];
													}
												}}
											/>
										{:else}
											<button
												type="button"
												class="text-sm font-medium truncate text-left w-full hover:text-gray-600 dark:hover:text-gray-300"
												on:click={() => {
													editingPresetIndex = index;
												}}
											>
												{preset.name}
											</button>
										{/if}
										<div class="text-[10px] text-gray-400 font-mono mt-0.5">
											{preset.accent_color || '#e3530f'}
											{#if preset.login_background_color}
												&middot; bg: {preset.login_background_color}
											{/if}
											{#if preset.microsoft_client_id}
												&middot; <span class="text-blue-500">MS OAuth</span>
											{/if}
										</div>
									</div>

									<div class="flex items-center gap-1 shrink-0">
										<Tooltip content={$i18n.t('Load this preset')}>
											<button
												type="button"
												class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
												on:click={() => loadPreset(index)}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path
														d="M3 10a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM8.5 10a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0ZM15.5 8.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3Z"
													/>
												</svg>
											</button>
										</Tooltip>

										<Tooltip content={$i18n.t('Save current settings to this preset')}>
											<button
												type="button"
												class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
												on:click={() => saveToPreset(index)}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path
														d="M13.75 7h-3v5.296l1.943-2.048a.75.75 0 0 1 1.114 1.004l-3.25 3.5a.75.75 0 0 1-1.114 0l-3.25-3.5a.75.75 0 1 1 1.114-1.004L9.25 12.296V7h-3a.75.75 0 0 1 0-1.5h7.5a.75.75 0 0 1 0 1.5Z"
													/>
													<path d="M4.25 15a.75.75 0 0 0 0 1.5h11.5a.75.75 0 0 0 0-1.5H4.25Z" />
												</svg>
											</button>
										</Tooltip>

										<Tooltip content={$i18n.t('Delete preset')}>
											<button
												type="button"
												class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition text-gray-400 hover:text-red-600 dark:hover:text-red-400"
												on:click={() => removePreset(index)}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													viewBox="0 0 20 20"
													fill="currentColor"
													class="w-4 h-4"
												>
													<path
														fill-rule="evenodd"
														d="M8.75 1A2.75 2.75 0 0 0 6 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 1 0 .23 1.482l.149-.022 1.005 11.36A2.75 2.75 0 0 0 7.76 20h4.48a2.75 2.75 0 0 0 2.742-2.53l1.005-11.36.149.022a.75.75 0 1 0 .23-1.482A41.03 41.03 0 0 0 14 4.193V3.75A2.75 2.75 0 0 0 11.25 1h-2.5ZM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4ZM8.58 7.72a.75.75 0 0 0-1.5.06l.3 7.5a.75.75 0 1 0 1.5-.06l-.3-7.5Zm4.34.06a.75.75 0 1 0-1.5-.06l-.3 7.5a.75.75 0 1 0 1.5.06l.3-7.5Z"
														clip-rule="evenodd"
													/>
												</svg>
											</button>
										</Tooltip>
									</div>
								</div>

								<!-- Logos & Assets (collapsible) -->
								<details class="border-t border-gray-100 dark:border-gray-800">
									<summary
										class="px-3 py-2 text-xs font-medium text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 cursor-pointer select-none flex items-center gap-1"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-3.5 h-3.5"
										>
											<path
												fill-rule="evenodd"
												d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z"
												clip-rule="evenodd"
											/>
										</svg>
										{$i18n.t('Logos & Assets')}
										{#if preset.logo_url || preset.favicon_url}
											<span class="ml-1 text-[10px] text-green-600 dark:text-green-400"
												>Configured</span
											>
										{/if}
									</summary>
									<div class="px-3 pb-3 space-y-2">
										<div class="text-[10px] text-gray-400 mb-2">
											{$i18n.t(
												'Configure logos and assets for this preset. These will be used when a domain is mapped to this preset.'
											)}
										</div>
										<div class="grid grid-cols-2 gap-2">
											<div>
												<div class="text-[10px] font-medium text-gray-500 mb-0.5">
													{$i18n.t('Logo (Light)')}
												</div>
												<input
													class="w-full rounded py-1.5 px-2.5 text-xs bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700"
													bind:value={preset.logo_url}
													placeholder="https://..."
												/>
											</div>
											<div>
												<div class="text-[10px] font-medium text-gray-500 mb-0.5">
													{$i18n.t('Logo (Dark)')}
												</div>
												<input
													class="w-full rounded py-1.5 px-2.5 text-xs bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700"
													bind:value={preset.logo_dark_url}
													placeholder="https://..."
												/>
											</div>
										</div>
										<div>
											<div class="text-[10px] font-medium text-gray-500 mb-0.5">
												{$i18n.t('Favicon')}
											</div>
											<input
												class="w-full rounded py-1.5 px-2.5 text-xs bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700"
												bind:value={preset.favicon_url}
												placeholder="https://..."
											/>
										</div>
										<div class="grid grid-cols-2 gap-2">
											<div>
												<div class="text-[10px] font-medium text-gray-500 mb-0.5">
													{$i18n.t('Login Background')}
												</div>
												<input
													class="w-full rounded py-1.5 px-2.5 text-xs bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700"
													bind:value={preset.login_background_url}
													placeholder="https://..."
												/>
											</div>
											<div>
												<div class="text-[10px] font-medium text-gray-500 mb-0.5">
													{$i18n.t('Login BG Color')}
												</div>
												<div class="flex gap-1">
													<input
														type="color"
														class="w-8 h-7 rounded cursor-pointer border border-gray-200 dark:border-gray-700"
														bind:value={preset.login_background_color}
													/>
													<input
														class="flex-1 rounded py-1.5 px-2.5 text-xs bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700 font-mono"
														bind:value={preset.login_background_color}
														placeholder="#1a2744"
													/>
												</div>
											</div>
										</div>
										{#if preset.logo_url || preset.logo_dark_url}
											<div class="flex gap-2 mt-2">
												{#if preset.logo_url}
													<div
														class="flex-1 p-2 rounded bg-white border border-gray-200 flex items-center justify-center"
													>
														<img
															src={preset.logo_url}
															alt="Light logo"
															class="max-h-8 max-w-full object-contain"
														/>
													</div>
												{/if}
												{#if preset.logo_dark_url}
													<div
														class="flex-1 p-2 rounded bg-gray-900 border border-gray-700 flex items-center justify-center"
													>
														<img
															src={preset.logo_dark_url}
															alt="Dark logo"
															class="max-h-8 max-w-full object-contain"
														/>
													</div>
												{/if}
											</div>
										{/if}
									</div>
								</details>

								<!-- Microsoft OAuth Settings (collapsible) -->
								<details class="border-t border-gray-100 dark:border-gray-800">
									<summary
										class="px-3 py-2 text-xs font-medium text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 cursor-pointer select-none flex items-center gap-1"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-3.5 h-3.5"
										>
											<path
												fill-rule="evenodd"
												d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z"
												clip-rule="evenodd"
											/>
										</svg>
										{$i18n.t('Microsoft OAuth (SSO)')}
										{#if preset.microsoft_client_id}
											<span class="ml-1 text-[10px] text-green-600 dark:text-green-400"
												>Configured</span
											>
										{/if}
									</summary>
									<div class="px-3 pb-3 space-y-2">
										<div class="text-[10px] text-gray-400 mb-2">
											{$i18n.t(
												'Configure domain-specific Microsoft OAuth for this preset. When a domain is mapped to this preset, these credentials will be used instead of the global OAuth settings.'
											)}
										</div>
										<div>
											<div class="text-[10px] font-medium text-gray-500 mb-0.5">
												{$i18n.t('Client ID')}
											</div>
											<input
												class="w-full rounded py-1.5 px-2.5 text-xs bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700 font-mono"
												bind:value={preset.microsoft_client_id}
												placeholder="00000000-0000-0000-0000-000000000000"
											/>
										</div>
										<div>
											<div class="text-[10px] font-medium text-gray-500 mb-0.5">
												{$i18n.t('Client Secret')}
											</div>
											<input
												type="password"
												class="w-full rounded py-1.5 px-2.5 text-xs bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700 font-mono"
												bind:value={preset.microsoft_client_secret}
												placeholder="••••••••••••••••"
											/>
										</div>
										<div>
											<div class="text-[10px] font-medium text-gray-500 mb-0.5">
												{$i18n.t('Tenant ID')}
											</div>
											<input
												class="w-full rounded py-1.5 px-2.5 text-xs bg-white dark:bg-gray-800 outline-hidden border border-gray-200 dark:border-gray-700 font-mono"
												bind:value={preset.microsoft_tenant_id}
												placeholder="00000000-0000-0000-0000-000000000000"
											/>
										</div>
									</div>
								</details>
							</div>
						{/each}
					</div>
				{/if}

				<!-- Add new preset -->
				<div class="flex items-center gap-2">
					<input
						class="flex-1 rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
						bind:value={newPresetName}
						placeholder={$i18n.t('New preset name...')}
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								addPreset();
							}
						}}
					/>
					<button
						type="button"
						class="px-3 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition font-medium"
						on:click={addPreset}
					>
						{$i18n.t('Add Preset')}
					</button>
				</div>
			</div>

			<!-- ═══════════════════════════════════════════ -->
			<!-- DOMAIN MAPPING -->
			<!-- ═══════════════════════════════════════════ -->
			<div class="mb-4">
				<div class="mt-0.5 mb-2.5 text-base font-medium">{$i18n.t('Domain Theming')}</div>
				<hr class="border-gray-100/30 dark:border-gray-850/30 my-2" />

				<div class="text-xs text-gray-500 mb-3">
					{$i18n.t(
						'Map domains to theme presets. When users access the app via a mapped domain, the corresponding preset theme will be applied automatically.'
					)}
				</div>

				<!-- Existing mappings -->
				{#if brandingConfig.domain_mappings.length > 0}
					<div class="space-y-2 mb-3">
						{#each brandingConfig.domain_mappings as mapping, index}
							<div
								class="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800"
							>
								<div class="flex-1 min-w-0">
									<div class="text-sm font-mono font-medium truncate">{mapping.domain}</div>
								</div>

								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-4 h-4 text-gray-400 shrink-0"
								>
									<path
										fill-rule="evenodd"
										d="M3 10a.75.75 0 0 1 .75-.75h10.638L10.23 5.29a.75.75 0 1 1 1.04-1.08l5.5 5.25a.75.75 0 0 1 0 1.08l-5.5 5.25a.75.75 0 1 1-1.04-1.08l4.158-3.96H3.75A.75.75 0 0 1 3 10Z"
										clip-rule="evenodd"
									/>
								</svg>

								<div class="shrink-0">
									<span
										class="text-xs font-medium px-2 py-1 rounded-full bg-gray-200 dark:bg-gray-700"
									>
										{mapping.preset_name}
									</span>
								</div>

								<button
									type="button"
									class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition text-gray-400 hover:text-red-600 dark:hover:text-red-400 shrink-0"
									on:click={() => removeDomainMapping(index)}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z"
										/>
									</svg>
								</button>
							</div>
						{/each}
					</div>
				{/if}

				<!-- Add new mapping -->
				<div class="flex items-center gap-2">
					<input
						class="flex-1 rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
						bind:value={newDomain}
						placeholder={$i18n.t('chat.fiwealth.com')}
						on:keydown={(e) => {
							if (e.key === 'Enter') {
								e.preventDefault();
								addDomainMapping();
							}
						}}
					/>
					<select
						class="rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
						bind:value={newDomainPreset}
					>
						<option value="" disabled selected>{$i18n.t('Select preset...')}</option>
						{#each brandingConfig.presets as preset}
							<option value={preset.name}>{preset.name}</option>
						{/each}
					</select>
					<button
						type="button"
						class="px-3 py-2 text-xs rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition font-medium shrink-0"
						on:click={addDomainMapping}
					>
						{$i18n.t('Add')}
					</button>
				</div>
			</div>
		</div>

		<div class="flex justify-end text-sm font-medium">
			<button
				class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
				type="submit"
			>
				{$i18n.t('Save')}
			</button>
		</div>
	</form>
{:else}
	<div class="h-full w-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
