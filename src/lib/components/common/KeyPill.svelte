<script lang="ts">
	export let text: string;
	export let className = '';
</script>

<span
	class="inline-flex min-h-[1.125rem] shrink-0 items-center justify-center rounded-full bg-gray-100 px-[0.3125rem] py-0.5 text-[0.625rem] font-medium leading-none text-gray-500 dark:bg-white/6 dark:text-gray-400 {className}"
	>{text}</span
>
