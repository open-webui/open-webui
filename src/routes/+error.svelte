<script>
	import { page } from '$app/stores';
</script>

<main class=" bg-white dark:bg-gray-800 min-h-screen" id="main-content">
	<div class=" flex h-full">
		<h1 class="m-auto my-10 dark:text-gray-300 text-3xl font-medium">
			{$page.status}: {$page.error?.message}
		</h1>
	</div>
</main>
