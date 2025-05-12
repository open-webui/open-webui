<script>
	import { slide } from 'svelte/transition';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
	let expanded = false;

	function toggleFooter() {
		window._paq?.push(['trackEvent', 'Footer', 'Toggle']);
		expanded = !expanded;
	}
</script>

<footer class="fr-footer" role="contentinfo" id="footer-7361">
	<div class="fr-container">
		<div class="fr-footer__header">
			<div class="fr-footer__brand">
				<a href="/" title="Retour à l'accueil du site" class="logo-link">
					<p class="fr-logo">Gouvernement</p>
				</a>
			</div>
			<button
				class="fr-btn fr-btn--secondary fr-btn--sm fr-footer__expand-btn"
				on:click={toggleFooter}
				aria-expanded={expanded}
				aria-controls="footer-content"
			>
				{#if expanded}
					{$i18n.t('Reduce information')}
				{:else}
					{$i18n.t('More information')}
				{/if}
			</button>
		</div>

		{#if expanded}
			<div class="fr-footer__body" transition:slide={{ duration: 300 }} id="footer-content">
				<div class="fr-">
					<div class="align-left">
						<div class="footer-links-column">
							<ul class="fr-footer__content-list">
								<li class="fr-footer__content-item">
									<a
										class="fr-footer__content-link"
										target="_blank"
										rel="noopener external"
										title="info.gouv.fr - nouvelle fenêtre"
										href="https://info.gouv.fr">info.gouv.fr</a
									>
								</li>
								<li class="fr-footer__content-item">
									<a
										class="fr-footer__content-link"
										target="_blank"
										rel="noopener external"
										title="service-public.fr - nouvelle fenêtre"
										href="https://service-public.fr">service-public.fr</a
									>
								</li>
								<li class="fr-footer__content-item">
									<a
										class="fr-footer__content-link"
										target="_blank"
										rel="noopener external"
										title="legifrance.gouv.fr - nouvelle fenêtre"
										href="https://legifrance.gouv.fr">legifrance.gouv.fr</a
									>
								</li>
								<li class="fr-footer__content-item">
									<a
										class="fr-footer__content-link"
										target="_blank"
										rel="noopener external"
										title="data.gouv.fr - nouvelle fenêtre"
										href="https://data.gouv.fr">data.gouv.fr</a
									>
								</li>
							</ul>
						</div>

						<div class="footer-links-column">
							<ul class="fr-footer__bottom-list">
								<li class="fr-footer__bottom-item">
									<a class="fr-footer__bottom-link" href="#">{$i18n.t('Site map')}</a>
								</li>
								<li class="fr-footer__bottom-item">
									<a class="fr-footer__bottom-link" href="#"
										>{$i18n.t('Accessibility: not compliant')}</a
									>
								</li>
								<li class="fr-footer__bottom-item">
									<a class="fr-footer__bottom-link" href="#">{$i18n.t('Legal notice')}</a>
								</li>
								<li class="fr-footer__bottom-item">
									<a class="fr-footer__bottom-link" href="/privacy">{$i18n.t('Personal data')}</a>
								</li>
								<li class="fr-footer__bottom-item">
									<a class="fr-footer__bottom-link" href="/terms">{$i18n.t('Terms of use')}</a>
								</li>
							</ul>
						</div>

						<div class="fr-footer__bottom-copy">
							<p>
								{$i18n.t(
									'Except where otherwise noted, content on this site is licensed under the'
								)}
								<a
									href="https://github.com/etalab/licence-ouverte/blob/master/LO.md"
									target="_blank"
									rel="noopener external"
									title="Licence etalab - nouvelle fenêtre">licence etalab-2.0</a
								>
							</p>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
</footer>

<style>
	.fr-footer {
		padding: 0.5rem 0;
		position: relative;
		z-index: 1;
		width: 100%;
	}

	.fr-footer__header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		min-height: 2rem;
		position: relative;
		z-index: 1;
		width: 100%;
	}

	.fr-logo {
		margin: 0;
		line-height: 1.2;
	}

	.fr-footer__body {
		padding-top: 1rem;
		border-top: 1px solid var(--border-default-grey, #ddd);
		margin-top: 0.5rem;
		width: 100%;
	}
</style>
