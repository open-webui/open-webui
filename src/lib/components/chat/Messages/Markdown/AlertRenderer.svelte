<script lang="ts" context="module">
	import { marked, type Token } from 'marked';

	type AlertType = 'NOTE' | 'TIP' | 'IMPORTANT' | 'WARNING' | 'CAUTION';

	interface AlertTheme {
		border: string;
		text: string;
		icon: ComponentType;
	}

	export interface AlertData {
		type: AlertType;
		text: string;
		tokens: Token[];
	}

	const alertStyles: Record<AlertType, AlertTheme> = {
		NOTE: {
			border: 'border-sky-500',
			text: 'text-sky-500',
			icon: Info
		},
		TIP: {
			border: 'border-emerald-500',
			text: 'text-emerald-500',
			icon: LightBlub
		},
		IMPORTANT: {
			border: 'border-purple-500',
			text: 'text-purple-500',
			icon: Star
		},
		WARNING: {
			border: 'border-yellow-500',
			text: 'text-yellow-500',
			icon: ArrowRightCircle
		},
		CAUTION: {
			border: 'border-rose-500',
			text: 'text-rose-500',
			icon: Bolt
		}
	};

	export function alertComponent(token: Token): AlertData | false {
		const regExpStr = `^(?:\\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\\])\\s*?\n*`;
		const regExp = new RegExp(regExpStr);
		const matches = token.text?.match(regExp);

		if (matches && matches.length) {
			const alertType = matches[1] as AlertType;
			const newText = token.text.replace(regExp, '');
			const newTokens = marked.lexer(newText);
			return {
				type: alertType,
				text: newText,
				tokens: newTokens
			};
		}
		return false;
	}
</script>

<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';
	import Star from '$lib/components/icons/Star.svelte';
	import LightBlub from '$lib/components/icons/LightBlub.svelte';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import ArrowRightCircle from '$lib/components/icons/ArrowRightCircle.svelte';
	import MarkdownTokens from './MarkdownTokens.svelte';
	import type { ComponentType } from 'svelte';

	export let token: Token;
	export let alert: AlertData;
	export let id = '';
	export let tokenIdx = 0;
	export let onTaskClick: ((event: MouseEvent) => void) | undefined = undefined;
	export let onSourceClick: ((event: MouseEvent) => void) | undefined = undefined;
</script>

<!--

Renders the following Markdown as alerts:

> [!NOTE]
> Example note

> [!TIP]
> Example tip

> [!IMPORTANT]
> Example important

> [!CAUTION]
> Example caution

> [!WARNING]
> Example warning

-->
<div class={`border-l-4 pl-2.5 ${alertStyles[alert.type].border} my-0.5`}>
	<div class="{alertStyles[alert.type].text} items-center flex gap-1 py-1.5">
		<svelte:component this={alertStyles[alert.type].icon} className="inline-block size-4" />
		<span class=" font-medium">{alert.type}</span>
	</div>
	<div class="pb-2">
		<MarkdownTokens id={`${id}-${tokenIdx}`} tokens={alert.tokens} {onTaskClick} {onSourceClick} />
	</div>
</div>
