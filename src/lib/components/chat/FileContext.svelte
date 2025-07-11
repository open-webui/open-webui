<!-- AXL:김정민 파일 컨텍스트 20250704 -->
<script lang="ts">
	import { onMount, tick, getContext, createEventDispatcher, onDestroy } from 'svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import CommandLine from '../icons/CommandLine.svelte';

	const i18n = getContext('i18n');

	export let contextFiles: {
		fileName: string;
		startLine: number;
		endLine: number;
		context: string;
	}[] = [];

	$: console.log('files:', contextFiles);
</script>

{#each contextFiles as file}
	<Tooltip
		content={`${file.fileName}${file.startLine !== undefined ? `[${file.startLine}-${file.endLine}]` : ''}`}
		placement="top"
	>
		<button
			type="button"
			class="px-2.5 py-2 pr-1 flex gap-1.5 items-center text-sm rounded-full transition-colors duration-300 focus:outline-hidden max-w-full overflow-hidden hover:bg-gray-50 dark:hover:bg-gray-800 bg-transparent text-gray-600 dark:text-gray-300"
		>
			<CommandLine className="size-4" strokeWidth="1.75" />
			<span class="@xl:block whitespace-nowrap overflow-hidden text-ellipsis leading-none">
				{`${file.fileName}${file.startLine !== undefined ? `[${file.startLine}-${file.endLine}]` : ''}`}
			</span>
		</button>
		<button
			type="button"
			class="text-red-500 hover:text-red-700 focus:outline-none"
			aria-label="Delete"
			on:click={() => (contextFiles = contextFiles.filter((f) => f !== file))}
		>
			&times;
		</button>
	</Tooltip>
{/each}
