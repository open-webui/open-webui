<script lang="ts">
	export let className = '';
	export let style = '';
</script>

<div
	class={`rounded-xl! p-0.5! border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg ${className} [&_button:hover]:bg-transparent! [&_a:hover]:bg-transparent! [&_button:hover]:text-gray-900 dark:[&_button:hover]:text-gray-100 [&_a:hover]:text-gray-900 dark:[&_a:hover]:text-gray-100 [&>button]:flex [&>button]:w-full [&>button]:h-[1.6875rem]! [&>button]:items-center [&>button]:gap-2! [&>button]:rounded-xl! [&>button]:bg-transparent [&>button]:px-2! [&>button]:text-[13px]! [&>button]:font-normal! [&>a]:flex [&>a]:w-full [&>a]:h-[1.6875rem]! [&>a]:items-center [&>a]:gap-2! [&>a]:rounded-xl! [&>a]:bg-transparent [&>a]:px-2! [&>a]:text-[13px]! [&>a]:font-normal! [&_button_svg]:size-3.5! [&_a_svg]:size-3.5! [&>hr]:my-0.5 [&>hr]:mx-1`}
	{style}
>
	<slot />
</div>
