<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	let activeTab = 'files';

	function navigateTo(tab) {
		activeTab = tab;
		if (tab === 'files') {
			goto(`/workspace/knowledge/${$page.params.id}`);
		} else {
			goto(`/workspace/knowledge/${$page.params.id}/${tab}`);
		}
	}

	$: {
		const path = $page.url.pathname;
		if (path.endsWith('/chunks')) activeTab = 'chunks';
		else if (path.endsWith('/processing')) activeTab = 'processing';
		else if (path.endsWith('/evaluate')) activeTab = 'evaluate';
		else if (path.endsWith('/snapshots')) activeTab = 'snapshots';
		else activeTab = 'files';
	}
</script>

<div class="flex flex-col h-full">
	<!-- Tab Navigation -->
	<div class="flex items-center gap-1 px-4 pt-3 pb-0 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-950">
		<button
			on:click={() => navigateTo('files')}
			class="px-4 py-2 text-sm font-medium rounded-t-lg transition {activeTab === 'files'
				? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 border-b-2 border-blue-600'
				: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
		>
			📁 Files
		</button>
		<button
			on:click={() => navigateTo('chunks')}
			class="px-4 py-2 text-sm font-medium rounded-t-lg transition {activeTab === 'chunks'
				? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 border-b-2 border-blue-600'
				: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
		>
			🧩 Chunks
		</button>
		<button
			on:click={() => navigateTo('processing')}
			class="px-4 py-2 text-sm font-medium rounded-t-lg transition {activeTab === 'processing'
				? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 border-b-2 border-blue-600'
				: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
		>
			⏳ Processing
		</button>
		<button
			on:click={() => navigateTo('evaluate')}
			class="px-4 py-2 text-sm font-medium rounded-t-lg transition {activeTab === 'evaluate'
				? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 border-b-2 border-blue-600'
				: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
		>
			📊 Evaluate
		</button>
		<button
			on:click={() => navigateTo('snapshots')}
			class="px-4 py-2 text-sm font-medium rounded-t-lg transition {activeTab === 'snapshots'
				? 'bg-white dark:bg-gray-900 text-blue-600 dark:text-blue-400 border-b-2 border-blue-600'
				: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}"
		>
			📸 Snapshots
		</button>
	</div>

	<!-- Page Content -->
	<div class="flex-1 overflow-hidden">
		<slot />
	</div>
</div>
