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
	<!-- Back arrow for small devices -->
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
				{$i18n.t('terms:title')}
			</h1>
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-8 text-justify">
				{$i18n.t('terms:version')}
			</p>

			<div class="space-y-8">
				<!-- User Responsibilities -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('terms:user_responsibilities.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('terms:user_responsibilities.content')}
					</p>
				</section>

				<!-- User Rights -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('terms:user_rights.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('terms:user_rights.content')}
					</p>
				</section>

				<!-- Prohibited Activities -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('terms:prohibited_activities.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('terms:prohibited_activities.content')}
					</p>
				</section>

				<!-- Data Access -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('terms:data_access.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('terms:data_access.content')}
					</p>
				</section>

				<!-- Termination -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('terms:termination.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('terms:termination.content')}
					</p>
				</section>

				<!-- Disclaimer -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('terms:disclaimer.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('terms:disclaimer.content')}
					</p>
				</section>

				<!-- Contact -->
				<section>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('terms:contact.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('terms:contact.content')}
					</p>
				</section>

				<!-- Consent -->
				<section class="border-t pt-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">
						{$i18n.t('terms:consent.title')}
					</h2>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed text-justify">
						{$i18n.t('terms:consent.content')}
					</p>
				</section>
			</div>
		</div>
	</div>
</div>
