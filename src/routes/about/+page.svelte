<script lang="ts">
	import { t } from '$lib/landing/translations';
	import { APP_NAME } from '$lib/constants';
</script>

<div class="flex flex-col gap-8 p-4 md:p-8 max-w-4xl mx-auto text-[var(--foreground)]">
	<h1 class="text-4xl font-bold">{$t('about.title')} {APP_NAME}</h1>

	<div class="prose dark:prose-invert max-w-none">
		<p class="text-lg">
			{APP_NAME} {$t('about.description')}
		</p>

		<h2 class="text-2xl font-bold mt-8 mb-4">{$t('about.mission.title')}</h2>
		<p>
			{$t('about.mission.description')}
		</p>

		<h2 class="text-2xl font-bold mt-8 mb-4">{$t('about.features.title')} {APP_NAME} {$t('about.features.different')}</h2>

		<h3 class="text-xl font-semibold mt-6 mb-3">{$t('about.features.legalFocus')}</h3>
		<ul class="list-disc pl-6">
			<li>{$t('about.features.legalFocus.1')}</li>
			<li>{$t('about.features.legalFocus.2')}</li>
			<li>{$t('about.features.legalFocus.3')}</li>
			<li>{$t('about.features.legalFocus.4')}</li>
		</ul>

		<h3 class="text-xl font-semibold mt-6 mb-3">{$t('about.features.documentHandling')}</h3>
		<ul class="list-disc pl-6">
			<li>{$t('about.features.documentHandling.1')}</li>
			<li>{$t('about.features.documentHandling.2')}</li>
			<li>{$t('about.features.documentHandling.3')}</li>
			<li>{$t('about.features.documentHandling.4')}</li>
		</ul>

		<h3 class="text-xl font-semibold mt-6 mb-3">{$t('about.features.professional')}</h3>
		<ul class="list-disc pl-6">
			<li>{$t('about.features.professional.1')}</li>
			<li>{$t('about.features.professional.2')}</li>
			<li>{$t('about.features.professional.3')}</li>
			<li>{$t('about.features.professional.4')}</li>
		</ul>

		<h3 class="text-xl font-semibold mt-6 mb-3">{$t('about.features.technical')}</h3>
		<ul class="list-disc pl-6">
			<li>{$t('about.features.technical.1')}</li>
			<li>{$t('about.features.technical.2')}</li>
			<li>{$t('about.features.technical.3')}</li>
			<li>{$t('about.features.technical.4')}</li>
		</ul>

		<h2 class="text-2xl font-bold mt-8 mb-4">{$t('about.bestPractices.title')} {APP_NAME}</h2>
		<ol class="list-decimal pl-6">
			<li>{$t('about.bestPractices.1')}</li>
			<li>{$t('about.bestPractices.2')}</li>
			<li>{$t('about.bestPractices.3')}</li>
			<li>{$t('about.bestPractices.4')}</li>
		</ol>

		<h2 class="text-2xl font-bold mt-8 mb-4">{$t('about.commitment.title')}</h2>
		<ul class="list-disc pl-6">
			<li>{$t('about.commitment.1')}</li>
			<li>{$t('about.commitment.2')}</li>
			<li>{$t('about.commitment.3')}</li>
			<li>{$t('about.commitment.4')}</li>
		</ul>

		<h2 class="text-2xl font-bold mt-8 mb-4">{$t('about.contact.title')}</h2>
		<p>{$t('about.contact.description')}:</p>
		<ul class="list-disc pl-6">
			<li>Email: <a href="mailto:contact@cicero.chat" class="text-blue-500 hover:underline">contact@cicero.chat</a></li>
			<li>Website: <a href="https://www.cicero.chat" class="text-blue-500 hover:underline">https://www.cicero.chat</a></li>
		</ul>

		<div class="mt-12 pt-8 border-t border-[var(--border)]">
			<p class="text-sm text-[var(--muted)]">
				{2024} {APP_NAME} {$t('footer.rights')}
			</p>
		</div>
	</div>
</div>
