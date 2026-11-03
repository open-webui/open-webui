<script lang="ts">
	export let type = 'info';
	export let content = '';

	const classNames: Record<string, string> = {
		info: 'bg-blue-500/20 text-blue-700 dark:text-blue-200 ',
		success: 'bg-green-500/20 text-green-700 dark:text-green-200',
		warning: 'bg-yellow-500/20 text-yellow-700 dark:text-yellow-200',
		error: 'bg-red-500/20 text-red-700 dark:text-red-200',
		muted: 'bg-gray-500/20 text-gray-700 dark:text-gray-200',
		subtle: 'bg-gray-100/80 text-gray-500 dark:bg-gray-800/50 dark:text-gray-400'
	};
</script>

<div
	class="font-normal {classNames[type] ?? classNames['info']} w-fit px-[0.3125rem] mr-0.5 {type ===
	'subtle'
		? 'shrink-0 whitespace-nowrap rounded-md text-[0.6875rem] leading-4 normal-case'
		: 'rounded-lg text-xs uppercase line-clamp-1'}"
>
	{content}
</div>
