import { Select as SelectPrimitive } from "bits-ui";

import Label from "./select-label.svelte";
import Item from "./select-item.svelte";
import Content from "./select-content.svelte";
import Trigger from "./select-trigger.svelte";
import Separator from "./select-separator.svelte";

const Root = SelectPrimitive.Root;
const Group = SelectPrimitive.Group;
const Input = SelectPrimitive.Input;
const Value = SelectPrimitive.Value;

export {
	Root,
	Item,
	Group,
	Input,
	Label,
	Value,
	Content,
	Trigger,
	Separator,
	//
	Root as Select,
	Item as SelectItem,
	Group as SelectGroup,
	Input as SelectInput,
	Label as SelectLabel,
	Value as SelectValue,
	Content as SelectContent,
	Trigger as SelectTrigger,
	Separator as SelectSeparator,
};
