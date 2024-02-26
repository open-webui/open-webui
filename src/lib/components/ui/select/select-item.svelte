<script lang="ts">
	import { cn } from "$lib/shadcn";
	import { Select as SelectPrimitive } from "bits-ui";
	import Check from "svelte-radix/Check.svelte";

	type $$Props = SelectPrimitive.ItemProps;
	type $$Events = Required<SelectPrimitive.ItemEvents>;

	let className: $$Props["class"] = undefined;
	export let value: $$Props["value"];
	export let label: $$Props["label"] = undefined;
	export let disabled: $$Props["disabled"] = undefined;
	export { className as class };
</script>

<SelectPrimitive.Item
	{value}
	{disabled}
	{label}
	class={cn(
		"relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-2 pr-8 text-sm outline-none data-[disabled]:pointer-events-none data-[highlighted]:bg-accent data-[highlighted]:text-accent-foreground data-[disabled]:opacity-50",
		className
	)}
	{...$$restProps}
	on:click
	on:pointermove
	on:focusin
>
	<span class="absolute right-2 flex h-3.5 w-3.5 items-center justify-center">
		<SelectPrimitive.ItemIndicator>
			<Check class="h-4 w-4" />
		</SelectPrimitive.ItemIndicator>
	</span>
	<slot>
		{label ? label : value}
	</slot>
</SelectPrimitive.Item>
