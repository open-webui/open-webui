<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';

	export let content = '';
</script>

<div class="flex my-2 gap-2.5 border px-4 py-3 border-red-800 bg-red-800/30 font-medium rounded-lg">
	<div class=" self-start mt-0.5">
		<Info className="size-5" />
	</div>

	<div class=" self-center text-sm">
		{content}
	</div>
</div>
