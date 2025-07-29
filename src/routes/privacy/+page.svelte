<script lang="ts">
	import { goto } from '$app/navigation';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import { getContext } from 'svelte';
	import { changeLanguage } from '$lib/i18n';
	import { get, type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');

	function goBack() {
		goto('/auth');
	}

	function switchLanguage(lang: string) {
		changeLanguage(lang);
	}
</script>

<div class="w-full h-screen dark bg-[#010E1D] p-6 pt-16 overflow-y-auto" dir={$i18n.language === 'ar' ? 'rtl' : 'ltr'}>
	<button
		on:click={goBack}
		class="fixed top-4 left-4 z-10 p-2 text-white hover:text-gray-300 transition-colors md:hidden"
		aria-label="Go back"
	>
		<ChevronLeft className="w-6 h-6" strokeWidth="2" />
	</button>

	<!-- Language Switcher -->
	<div class="fixed top-4 z-10" class:right-4={$i18n.language !== 'ar'} class:left-4={$i18n.language === 'ar'}>
		{#if $i18n.language === 'ar'}
			<button
				on:click={() => switchLanguage('en-US')}
				class="px-3 py-1 text-sm bg-transparent text-white rounded transition-colors shadow-md"
			>
				English
			</button>
		{:else}
			<button
				on:click={() => switchLanguage('ar')}
				class="px-3 py-1 text-sm bg-transparent text-white rounded transition-colors shadow-md"
			>
				العربية
			</button>
		{/if}
	</div>

	<div class="w-full max-w-4xl mx-auto overflow-y-auto">
		<div class="bg-transparent">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
				{$i18n.t('privacy:title')}
			</h1>
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-8 text-justify">
				{$i18n.t('privacy:version')}
			</p>

			<div class="space-y-8">
				<!-- Introduction -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:introduction.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:introduction.content')}
					</p>
				</section>

				<!-- What We Collect -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:what_we_collect.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:what_we_collect.content')}
					</p>
				</section>

				<!-- How We Collect -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:how_we_collect.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:how_we_collect.content')}
					</p>
				</section>

				<!-- How We Use -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:how_we_use.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:how_we_use.content')}
					</p>
				</section>

				<!-- How We Protect -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:how_we_protect.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:how_we_protect.content')}
					</p>
				</section>

				<!-- Data Sharing -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:data_sharing.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:data_sharing.content')}
					</p>
				</section>

				<!-- Data Retention -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:data_retention.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:data_retention.content')}
					</p>
				</section>

				<!-- Breach Notification -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:breach_notification.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:breach_notification.content')}
					</p>
				</section>

				<!-- Cookie Policy -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:cookie_policy.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:cookie_policy.content')}
					</p>
				</section>

				<!-- External Links -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:external_links.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:external_links.content')}
					</p>
				</section>

				<!-- Consent -->
				<section class="border-t pt-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('privacy:consent.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('privacy:consent.content')}
					</p>
				</section>
			</div>
		</div>
	</div>
</div>
