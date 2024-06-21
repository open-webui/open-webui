<script>
	import { showSidebar } from '$lib/stores';

	import Playground from '$lib/components/workspace/Playground.svelte';
</script>

<div
	class=" flex flex-col w-full min-h-screen max-h-screen {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''}"
>
	<div class=" py-4 px-5 flex-1 max-h-full overflow-y-auto">
		<Playground />
	</div>
</div>
