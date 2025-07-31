<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');
</script>

<div id="splash-screen" class="login">
	<div class="relative w-full h-full flex flex-col">
		<div class="splash-content">
			<div class="logo-container">
				<img src="/GovGPT.gif" alt="GovGPT Logo" class="logo-image" />
			</div>
			<div class="title-container">
				<h1 class="govgpt-title">{$i18n.t('GovGPT')}</h1>
			</div>
			<div class="tagline-container">
				<p class="tagline">{$i18n.t('Amplifying Government Potential')}</p>
			</div>
			<slot />
		</div>
		<img src="/GovGPT-background.gif" alt="GovGPT Logo" class="logo-image-bottom" />
	</div>
</div>
