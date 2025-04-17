<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, config, settings } from '$lib/stores';
	import Modal from './common/Modal.svelte';
	import { updateUserSettings } from '$lib/apis/users';

	const i18n = getContext('i18n');

	export let show = false;
	export let onAccept = () => {};

	let agreementAccepted = false;
</script>

<Modal bind:show size="lg">
	<div class="px-5 pt-4 dark:text-gray-300 text-gray-700">
		<div class="flex justify-between items-start">
			<div class="text-xl font-semibold">
				{$i18n.t('User Agreement')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>
	</div>

	<div class="w-full p-4 px-5 text-gray-700 dark:text-gray-100">
		<div
			class="overflow-y-scroll max-h-96 scrollbar-hidden border dark:border-gray-700 p-3 rounded"
		>
			<div class="mb-3">
				<h3 class="font-semibold mb-2">{$i18n.t('1. Introduction')}</h3>
				<p class="text-sm mb-3">
					{$i18n.t(
						'Welcome to {{WEBUI_NAME}}. By accessing and using our services, you agree to be bound by these terms.',
						{ WEBUI_NAME: $WEBUI_NAME }
					)}
				</p>

				<h3 class="font-semibold mb-2">{$i18n.t('2. User Responsibilities')}</h3>
				<p class="text-sm mb-3">
					{$i18n.t(
						'Users are responsible for maintaining the confidentiality of their account information and for all activities that occur under their account.'
					)}
				</p>

				<h3 class="font-semibold mb-2">{$i18n.t('3. Privacy Policy')}</h3>
				<p class="text-sm mb-3">
					{$i18n.t(
						'Our privacy policy describes how we handle your personal data and protect your privacy when using our services.'
					)}
				</p>

				<h3 class="font-semibold mb-2">{$i18n.t('4. Acceptable Use')}</h3>
				<p class="text-sm mb-3">
					{$i18n.t(
						'Users must not use the service for any illegal purposes or to violate the rights of others. The service must not be used to distribute harmful content.'
					)}
				</p>
			</div>
		</div>
	</div>
</Modal>
