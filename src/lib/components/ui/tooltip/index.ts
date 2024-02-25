import { Tooltip as TooltipPrimitive } from "bits-ui";
import Content from "./tooltip-content.svelte";

const Root = TooltipPrimitive.Root;
const Trigger = TooltipPrimitive.Trigger;

export {
	Root,
	Trigger,
	Content,
	//
	Root as Tooltip,
	Content as TooltipContent,
	Trigger as TooltipTrigger,
};
