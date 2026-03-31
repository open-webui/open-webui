<script lang="ts">
	import { copyToClipboard, unescapeHtml } from '$lib/utils';
	import { toast } from 'svelte-sonner';

	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let token;
	export let done = true;
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
<code
	class="codespan cursor-pointer {!done ? 'fade-in-token' : ''}"
	on:click={() => {
		copyToClipboard(unescapeHtml(token.text));
		toast.success($i18n.t('Copied to clipboard'));
	}}>{unescapeHtml(token.text)}</code
>

<style>
	@keyframes fade-in-token {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}
	.fade-in-token {
		animation: fade-in-token 100ms ease-out;
	}
</style>
