<script lang="ts">
	import { Select as SelectPrimitive } from "bits-ui";
	import { cn, flyAndScale } from "$lib/shadcn";
	import { scale } from "svelte/transition";

	type $$Props = SelectPrimitive.ContentProps;

	let className: $$Props["class"] = undefined;
	export let sideOffset: $$Props["sideOffset"] = 4;
	export let inTransition: $$Props["inTransition"] = flyAndScale;
	export let inTransitionConfig: $$Props["inTransitionConfig"] = undefined;
	export let outTransition: $$Props["outTransition"] = scale;
	export let outTransitionConfig: $$Props["outTransitionConfig"] = {
		start: 0.95,
		opacity: 0,
		duration: 50,
	};
	export { className as class };
</script>

<SelectPrimitive.Content
	{inTransition}
	{inTransitionConfig}
	{outTransition}
	{outTransitionConfig}
	{sideOffset}
	class={cn(
		"relative z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md focus:outline-none",
		className
	)}
	{...$$restProps}
>
	<div class="w-full p-1">
		<slot />
	</div>
</SelectPrimitive.Content>
