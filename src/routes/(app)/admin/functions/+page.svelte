<script>
	import { onMount } from 'svelte';
	import { functions } from '$lib/stores';

	import { getFunctions } from '$lib/apis/functions';
	import { getSessionUser } from '$lib/apis/auths';
	import Functions from '$lib/components/admin/Functions.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				// First attempt to load functions
				let result = await getFunctions(localStorage.token).catch(async (error) => {
					// If unauthorized, try to refresh session and retry once
					if (error?.toString().includes('401') || error?.toString().includes('Unauthorized')) {
						try {
							// Validate/refresh session
							await getSessionUser(localStorage.token);
							// Retry loading functions
							return await getFunctions(localStorage.token);
						} catch (refreshError) {
							// Session refresh failed - redirect will be handled by layout
							console.log('Session validation failed:', refreshError);
							return null;
						}
					}
					// Non-401 error or retry failed
					console.error('Failed to load functions:', error);
					return null;
				});
				functions.set(result);
			})()
		]);
	});
</script>

<Functions />
