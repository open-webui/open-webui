<script context="module">
	import { ButtonType } from './buttons';
	export { ButtonType };
</script>

<script lang="ts">
	import { stateClassBuilder } from './buttons';

	export let className = '';
	export let id = '';
	export let name = '';
	export let label = '';
	export let type: ButtonType = ButtonType.primary;
	export let disabled = false;
	export let pressed = false;
	export let pressable = false;
	export let iconOnly = false;

	const baseClasses = 'select-none outline-offset-2';

	$: classes = `${className} ${iconOnly ? 'p-1.5' : 'px-4 py-1'} ${baseClasses} ${stateClassBuilder(type, disabled, pressed)}`;
</script>

<button
	on:click
	{id}
	{name}
	data-button-type={type}
	aria-pressed={pressable && pressed ? 'true' : (pressable ? 'false' : undefined)}
	aria-label={label}
	{disabled}
	class={classes}
>
	<slot />
</button>
