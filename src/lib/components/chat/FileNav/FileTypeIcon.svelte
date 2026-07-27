<script lang="ts">
	import Icon from './Icon.svelte';
	import { fileIconName } from './fileIcon';

	export let name = '';
	export let type = 'file';
	export let size = 14;
	export let strokeWidth = 1.4;

	$: iconName = fileIconName(name, type);
	$: tone =
		type === 'directory' ? 'text-gray-500 dark:text-gray-400' : 'text-gray-400 dark:text-gray-500';
</script>

<Icon name={iconName} {size} {strokeWidth} class={`shrink-0 ${tone}`} />
