<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { page } from '$app/stores';

	$: error = $page.url.searchParams.get('error');
	$: if (error) toast.error(error);
</script>
