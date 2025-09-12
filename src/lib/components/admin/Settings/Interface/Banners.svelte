<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { getLanguages } from '$lib/i18n';
	import Sortable from 'sortablejs';
	import { getContext } from 'svelte';
	import { cubicOut } from 'svelte/easing';
	import { slide } from 'svelte/transition';

	const i18n = getContext('i18n');

	export let banners = [];

	let sortable = null;
	let bannerListElement = null;
	let availableLanguages = [];
	let expandedBanners = new Set(); // Track which banners have expanded translation view
	let languageSearchTerms = new Map(); // Track search terms for each banner

	const positionChangeHandler = () => {
		const bannerIdOrder = Array.from(bannerListElement.children).map((child) =>
			child.id.replace('banner-item-', '')
		);

		// Sort the banners array based on the new order
		banners = bannerIdOrder.map((id) => {
			const index = banners.findIndex((banner) => banner.id === id);
			return banners[index];
		});
	};

	const classNames: Record<string, string> = {
		info: 'bg-blue-500/20 text-blue-700 dark:text-blue-200 ',
		success: 'bg-green-500/20 text-green-700 dark:text-green-200',
		warning: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200',
		error: 'bg-red-500/20 text-red-700 dark:text-red-200'
	};

	$: if (banners) {
		init();
		// Initialize translations for all banners
		banners.forEach((banner) => initializeBannerTranslations(banner));
	}

	// Load available languages
	getLanguages().then((languages) => {
		availableLanguages = languages;
	});

	const init = () => {
		if (sortable) {
			sortable.destroy();
		}

		if (bannerListElement) {
			sortable = new Sortable(bannerListElement, {
				animation: 150,
				handle: '.item-handle',
				onUpdate: async (event) => {
					positionChangeHandler();
				}
			});
		}
	};

	const toggleTranslations = (bannerId) => {
		if (expandedBanners.has(bannerId)) {
			expandedBanners.delete(bannerId);
		} else {
			expandedBanners.add(bannerId);
		}
		expandedBanners = expandedBanners;
	};

	const addTranslation = (banner, langCode) => {
		// Don't allow adding current language as it's managed in the main content field
		if (langCode === $i18n.language) {
			return;
		}

		if (!banner.translations) {
			banner.translations = {};
		}
		banner.translations[langCode] = '';
		banners = banners;
	};

	const removeTranslation = (banner, langCode) => {
		if (banner.translations) {
			// Create a new object without the langCode to trigger reactivity
			const { [langCode]: removed, ...remainingTranslations } = banner.translations;
			banner.translations = remainingTranslations;

			// If no translations left, remove the translations property entirely
			if (Object.keys(banner.translations).length === 0) {
				delete banner.translations;
			}

			// Trigger reactivity
			banners = banners;
		}
	};

	// Helper function to get/set current language content
	const initializeBannerTranslations = (banner) => {
		if (!banner.translations) {
			banner.translations = {};
		}

		// If current language content doesn't exist, initialize it with banner.content
		if (!banner.translations[$i18n.language] && banner.content) {
			banner.translations[$i18n.language] = banner.content;
			banner.content = ''; // Clear old content field
			banners = banners; // Trigger reactivity
		}

		// Ensure current language always has an entry
		if (!banner.translations[$i18n.language]) {
			banner.translations[$i18n.language] = '';
		}
	};

	// Reactive statement to ensure proper updates
	$: getFilteredLanguages = (bannerId) => {
		const searchTerm = languageSearchTerms.get(bannerId) || '';
		if (!searchTerm.trim()) return [];

		const currentBanner = banners.find((b) => b.id === bannerId);

		return availableLanguages.filter((lang) => {
			const searchLower = searchTerm.toLowerCase().trim();
			const titleLower = lang.title.toLowerCase();
			const codeLower = lang.code.toLowerCase();

			// Simple and effective matching
			const matchesSearch = titleLower.includes(searchLower) || codeLower.includes(searchLower);
			const notAlreadyAdded =
				!currentBanner?.translations || !currentBanner.translations[lang.code];
			const notCurrentLanguage = lang.code !== $i18n.language;

			return matchesSearch && notAlreadyAdded && notCurrentLanguage;
		});
	};
</script>

<div class="flex flex-col gap-3 {banners?.length > 0 ? 'mt-2' : ''}" bind:this={bannerListElement}>
	{#each banners as banner, bannerIdx (banner.id)}
		<div
			class="flex flex-col rounded-lg border border-gray-200 bg-white shadow-sm transition-shadow duration-200 hover:shadow-md dark:border-gray-700 dark:bg-gray-900"
			id="banner-item-{banner.id}"
		>
			<!-- Banner Content Row: Refactored for consistency -->
			<div class="flex items-center gap-4 px-4 py-3">
				<!-- 1. Handle -->
				<div class="flex-shrink-0 text-gray-400">
					<EllipsisVertical className="size-5 cursor-move item-handle" />
				</div>

				<!-- 2. Main Content (takes up remaining space) -->
				<div class="flex min-w-0 flex-1 items-center gap-4">
					<!-- Type Selector -->
					<div class="flex flex-shrink-0 items-center gap-3">
						<div
							class="h-4 w-4 flex-shrink-0 rounded-full {classNames[banner.type]
								? classNames[banner.type].split(' ')[0]
								: 'bg-gray-300 dark:bg-gray-600'} shadow-sm"
						></div>
						<select
							class="w-auto min-w-20 rounded-md border border-gray-200 bg-gray-50 px-2 py-1 pr-6 text-xs font-medium capitalize text-gray-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300"
							bind:value={banner.type}
							required
						>
							{#if banner.type == ''}
								<option value="" selected disabled class="text-gray-900 dark:text-gray-200"
									>{$i18n.t('Type')}</option
								>
							{/if}
							<option value="info" class="text-gray-900 dark:text-gray-200"
								>{$i18n.t('Info')}</option
							>
							<option value="warning" class="text-gray-900 dark:text-gray-200"
								>{$i18n.t('Warning')}</option
							>
							<option value="error" class="text-gray-900 dark:text-gray-200"
								>{$i18n.t('Error')}</option
							>
							<option value="success" class="text-gray-900 dark:text-gray-200"
								>{$i18n.t('Success')}</option
							>
						</select>
					</div>

					<!-- Current Language Content -->
					<div class="min-w-0 flex-1">
						<Textarea
							className="w-full resize-none border-0 bg-transparent p-0 text-sm outline-none focus:ring-0"
							placeholder={$i18n.t('Content for') +
								' ' +
								($i18n.language === 'en-US'
									? 'English'
									: availableLanguages.find((l) => l.code === $i18n.language)?.title ||
										$i18n.language)}
							bind:value={banner.translations[$i18n.language]}
							maxSize={100}
						/>
					</div>
				</div>

				<!-- 3. Actions (all grouped together) -->
				<div class="flex flex-shrink-0 items-center gap-2">
					<Tooltip content={$i18n.t('Translations')} className="flex h-fit items-center">
						<button
							type="button"
							class="flex items-center gap-1 rounded-md p-1.5 text-xs font-medium text-gray-500 transition-colors hover:bg-blue-100 hover:text-blue-700 dark:text-gray-400 dark:hover:bg-blue-900/30 dark:hover:text-blue-300"
							on:click={() => toggleTranslations(banner.id)}
							aria-expanded={expandedBanners.has(banner.id)}
							aria-controls="translations-section-{banner.id}"
						>
							<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
								/>
							</svg>
						</button>
					</Tooltip>
					<Tooltip content={$i18n.t('Remember Dismissal')} className="flex h-fit items-center">
						<Switch bind:state={banner.dismissible} />
					</Tooltip>
					<div class="mx-1 h-5 w-px bg-gray-200 dark:bg-gray-700"></div>
					<Tooltip content={$i18n.t('Remove Banner')} className="flex h-fit items-center">
						<button
							type="button"
							class="rounded-md p-1.5 text-gray-500 transition-colors hover:bg-red-100 hover:text-red-600 dark:text-gray-400 dark:hover:bg-red-900/30 dark:hover:text-red-400"
							aria-label={$i18n.t('Remove Banner')}
							on:click={() => {
								banners.splice(bannerIdx, 1);
								banners = banners;
							}}
						>
							<XMark className={'size-4'} />
						</button>
					</Tooltip>
				</div>
			</div>

			<!-- Translations Section: Full Width Below -->
			{#if expandedBanners.has(banner.id)}
				<div
					class="overflow-hidden"
					transition:slide={{ duration: 300, easing: cubicOut }}
					id="translations-section-{banner.id}"
				>
					<div
						class="border-t border-gray-200 bg-gradient-to-br from-gray-50 to-gray-100 p-4 shadow-inner dark:border-gray-700 dark:from-gray-800 dark:to-gray-900"
					>
						<!-- Header -->
						<div class="mb-4 flex items-center gap-2">
							<svg
								class="h-4 w-4 text-gray-600 dark:text-gray-400"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
								/>
							</svg>
							<span class="text-sm font-semibold tracking-wide text-gray-700 dark:text-gray-300">
								{$i18n.t('Translations')}
							</span>
							<div class="ml-2 h-px flex-1 bg-gray-200 dark:bg-gray-600"></div>
						</div>

						<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
							<!-- Left Column: Existing Translations -->
							<div class="space-y-2">
								<div class="flex items-center gap-1">
									<h4
										class="text-xs font-medium uppercase tracking-wide text-gray-600 dark:text-gray-400"
									>
										Current
									</h4>
									{#if banner.translations && Object.keys(banner.translations).filter((code) => code !== $i18n.language).length > 0}
										<span
											class="rounded-full bg-blue-100 px-1.5 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
										>
											{Object.keys(banner.translations).filter((code) => code !== $i18n.language)
												.length}
										</span>
									{/if}
								</div>

								{#if banner.translations && Object.keys(banner.translations).filter((code) => code !== $i18n.language).length > 0}
									<div class="space-y-1">
										{#each Object.entries(banner.translations).filter(([langCode]) => langCode !== $i18n.language) as [langCode, translation]}
											<div
												class="group rounded border border-gray-200 bg-white p-2 shadow-sm transition-all duration-200 hover:shadow dark:border-gray-700 dark:bg-gray-900"
											>
												<div class="flex items-start gap-2">
													<div class="flex min-w-16 flex-col pt-2">
														<span
															class="text-xs font-medium leading-tight text-gray-700 dark:text-gray-300"
														>
															{availableLanguages.find((l) => l.code === langCode)?.title ||
																langCode}
														</span>
														<span class="font-mono text-xs text-gray-500 dark:text-gray-400">
															{langCode}
														</span>
													</div>
													<div class="flex-1">
														<!-- UPDATED TEXTAREA -->
														<Textarea
															className="w-full resize-none border-b border-gray-200 bg-transparent px-1 py-1.5 text-xs focus:border-blue-500 focus:outline-none focus:ring-0 dark:border-gray-600 dark:focus:border-blue-400"
															placeholder={$i18n.t('Translation')}
															bind:value={banner.translations[langCode]}
															maxSize={100}
														/>
													</div>
													<button
														type="button"
														class="mt-1 rounded p-0.5 text-xs text-gray-400 opacity-0 transition-all duration-200 group-hover:opacity-100 hover:bg-red-50 hover:text-red-500 dark:text-gray-500 dark:hover:bg-red-900/20 dark:hover:text-red-400"
														on:click={() => removeTranslation(banner, langCode)}
														title={$i18n.t('Remove')}
													>
														<svg
															class="h-3 w-3"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M6 18L18 6M6 6l12 12"
															/>
														</svg>
													</button>
												</div>
											</div>
										{/each}
									</div>
								{:else}
									<!-- ... No changes here ... -->
								{/if}
							</div>

							<!-- Right Column: Add Language Search -->
							<div class="space-y-2">
								<div class="flex items-center gap-1">
									<h4
										class="text-xs font-medium uppercase tracking-wide text-gray-600 dark:text-gray-400"
									>
										Add
									</h4>
									<svg
										class="h-3 w-3 text-gray-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 6v6m0 0v6m0-6h6m-6 0H6"
										/>
									</svg>
								</div>

								<div class="relative">
									<svg
										class="absolute left-2 top-1/2 h-3 w-3 -translate-y-1/2 transform text-gray-400"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
										/>
									</svg>
									<input
										type="text"
										placeholder="Search languages..."
										class="w-full rounded border border-gray-200 bg-white py-1.5 pl-7 pr-3 text-xs text-gray-700 transition-all duration-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-300"
										value={languageSearchTerms.get(banner.id) || ''}
										on:input={(e) => {
											languageSearchTerms.set(banner.id, e.target.value);
											languageSearchTerms = languageSearchTerms;
										}}
									/>
								</div>

								<!-- Search Results / Popular Languages -->
								<div
									class="rounded border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900"
								>
									{#if languageSearchTerms.get(banner.id) && languageSearchTerms
											.get(banner.id)
											.trim()}
										{#if getFilteredLanguages(banner.id).length > 0}
											<div class="p-1.5">
												<div class="mb-1 px-1 text-xs text-gray-500 dark:text-gray-400">
													{getFilteredLanguages(banner.id).length} found
												</div>
												<div class="max-h-32 space-y-0.5 overflow-y-auto">
													{#each getFilteredLanguages(banner.id).slice(0, 6) as lang (lang.code)}
														<button
															type="button"
															class="group flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-xs text-gray-700 transition-all duration-200 hover:bg-blue-50 hover:text-blue-700 dark:text-gray-300 dark:hover:bg-blue-900/20 dark:hover:text-blue-300"
															on:click={() => {
																addTranslation(banner, lang.code);
																languageSearchTerms.set(banner.id, '');
																languageSearchTerms = languageSearchTerms;
															}}
														>
															<span class="truncate">{lang.title}</span>
															<span
																class="ml-1 font-mono text-xs text-gray-400 group-hover:text-blue-500"
																>{lang.code}</span
															>
														</button>
													{/each}
												</div>
											</div>
										{:else}
											<div class="p-4 text-center">
												<svg
													class="mx-auto mb-1 h-5 w-5 text-gray-300 dark:text-gray-600"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
													/>
												</svg>
												<p class="text-xs text-gray-500 dark:text-gray-400">No matches</p>
											</div>
										{/if}
									{:else}
										<div class="p-4 text-center">
											<svg
												class="mx-auto mb-2 h-6 w-6 text-gray-300 dark:text-gray-600"
												fill="none"
												stroke="currentColor"
												viewBox="0 0 24 24"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="2"
													d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
												/>
											</svg>
											<p class="text-xs text-gray-500 dark:text-gray-400 mb-1">
												Start typing to search
											</p>
											<p class="text-xs text-gray-400 dark:text-gray-500">
												Find languages to add translations
											</p>
										</div>
									{/if}
								</div>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	{/each}
</div>
