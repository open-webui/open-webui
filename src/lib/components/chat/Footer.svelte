<script>
	import { slide } from 'svelte/transition';
	let expanded = false;

	function toggleFooter() {
		expanded = !expanded;
	}
</script>

<footer class="fr-footer" role="contentinfo" id="footer-7361">
	<div class="fr-container">
		<div class="fr-footer__header">
			<div class="fr-footer__brand fr-enlarge-link">
				<a href="/" title="Retour à l'accueil du site" class="logo-link">
					<p class="fr-logo">DINUM</p>
				</a>
			</div>
			<button
				class="fr-btn fr-btn--secondary fr-btn--sm fr-footer__expand-btn"
				on:click={toggleFooter}
				aria-expanded={expanded}
				aria-controls="footer-content"
			>
				{#if expanded}
					Réduire les informations
				{:else}
					Plus d'informations
				{/if}
			</button>
		</div>

		{#if expanded}
			<div class="fr-footer__body" transition:slide={{ duration: 300 }} id="footer-content">
				<div class="fr-footer__content">
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

					<ul class="fr-footer__bottom-list">
						<li class="fr-footer__bottom-item">
							<a class="fr-footer__bottom-link" href="#">Plan du site</a>
						</li>
						<li class="fr-footer__bottom-item">
							<a class="fr-footer__bottom-link" href="#"
								>Accessibilité : non/partiellement/totalement conforme</a
							>
						</li>
						<li class="fr-footer__bottom-item">
							<a class="fr-footer__bottom-link" href="#">Mentions légales</a>
						</li>
						<li class="fr-footer__bottom-item">
							<a class="fr-footer__bottom-link" href="/privacy">Données personnelles</a>
						</li>
						<li class="fr-footer__bottom-item">
							<a class="fr-footer__bottom-link" href="/terms">Conditions d'utilisation</a>
						</li>
					</ul>
					<div class="fr-footer__bottom-copy">
						<p>
							Sauf mention explicite de propriété intellectuelle détenue par des tiers, les contenus
							de ce site sont proposés sous <a
								href="https://github.com/etalab/licence-ouverte/blob/master/LO.md"
								target="_blank"
								rel="noopener external"
								title="Licence etalab - nouvelle fenêtre">licence etalab-2.0</a
							>
						</p>
					</div>
				</div>
			</div>
		{/if}
	</div>
</footer>

<style>
	.fr-footer {
		padding: 0.5rem 0;
	}

	.fr-footer__header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0;
	}

	.logo-link {
		display: flex;
		align-items: center;
	}

	.fr-logo {
		margin: 0;
	}

	.fr-footer__expand-btn {
		font-size: 0.875rem;
	}

	.fr-footer__body {
		padding-top: 1rem;
		border-top: 1px solid var(--border-default-grey, #ddd);
		margin-top: 0.5rem;
	}
</style>
