<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores'; // Assuming WEBUI_NAME is available for the message
	import { getContext } from 'svelte';

	export let visible = false;

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	function handleAccept() {
		dispatch('accepted');
	}
</script>

{#if visible}
	<div
		class="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto"
		aria-labelledby="pre-login-notice-title"
		role="dialog"
		aria-modal="true"
	>
		<div
			class="bg-white dark:bg-gray-800 p-6 sm:p-8 rounded-xl shadow-2xl max-w-2xl w-full text-gray-900 dark:text-gray-100 max-h-[90vh] overflow-y-auto"
		>
			<h2 id="pre-login-notice-title" class="text-xl sm:text-2xl font-semibold mb-4 text-center">
				{$i18n.t('Notice on the use of the {{WEBUI_NAME}} system', { WEBUI_NAME: $WEBUI_NAME })}
			</h2>
			<p class="text-sm sm:text-base mb-3 text-gray-700 dark:text-gray-300 text-justify">
				{$i18n.t(
					'The Boti system is currently in a preliminary development and evaluation phase. It has been designed by the Faculty of Engineering of the University of Deusto as part of a research project on the application of artificial intelligence in teaching environments.'
				)}
			</p>
			<p class="text-sm sm:text-base mb-3 text-gray-700 dark:text-gray-300 text-justify">
				{$i18n.t(
					"The use of this platform is experimental in nature and is intended for academic and research purposes only. When accessing the system, the user's email address is recorded along with information relating to their activity during the session. This data will be processed in accordance with the General Data Protection Regulation (GDPR) 2016/679, and will be kept for a maximum of six months, after which it will be securely deleted. It will not be used for commercial purposes or passed on to third parties."
				)}
			</p>
			<p class="text-sm sm:text-base mb-3 text-gray-700 dark:text-gray-300 text-justify">
				{$i18n.t(
					'You can find more information about the processing of your personal data on the '
				)}
				<a
					href="https://www.deusto-publicaciones.es/deusto/pdfs/politica_privacidad.pdf"
					target="_blank"
					class="text-blue-600 hover:underline dark:text-blue-400"
				>
					{$i18n.t('Privacy Policy of the University of Deusto')}
				</a>
				{$i18n.t(' or contact the team in charge by writing to ')}

				<a
					href="mailto:ingenieria@deusto.es"
					class="text-blue-600 hover:underline dark:text-blue-400"
				>
					ingenieria@deusto.es
				</a>
			</p>
			<button
				on:click={handleAccept}
				class="w-full bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white font-medium text-sm py-3 px-4 rounded-lg transition duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
			>
				{$i18n.t('Accept and continue')}
			</button>
		</div>
	</div>
{/if}
