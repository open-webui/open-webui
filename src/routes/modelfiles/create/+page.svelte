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
			const model = JSON.parse(event.data);
			sessionStorage.model = JSON.stringify(model);

			goto('/workspace/models/create');
		});

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}
	});
</script>
