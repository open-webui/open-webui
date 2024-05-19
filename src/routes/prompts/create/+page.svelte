<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(async () => {
		window.addEventListener('message', async (event) => {
			if (
				![
					'https://ollamahub.com',
					'https://www.ollamahub.com',
					'https://openwebui.com',
					'https://www.openwebui.com',
					'http://localhost:5173'
				].includes(event.origin)
			)
				return;
			const prompts = JSON.parse(event.data);
			sessionStorage.modelfile = JSON.stringify(prompts);

			goto('/workspace/prompts/create');
		});

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}
	});
</script>
