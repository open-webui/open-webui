<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';
	import Markdown from './Markdown.svelte';

	export let content: unknown = '';

	const getErrorMessage = (value: unknown): string => {
		if (typeof value === 'string') {
			return value;
		}

		if (typeof value === 'object' && value !== null) {
			const error = 'error' in value ? value.error : null;

			if (
				typeof error === 'object' &&
				error !== null &&
				'message' in error &&
				typeof error.message === 'string'
			) {
				return error.message;
			}

			if ('detail' in value && typeof value.detail === 'string') {
				return value.detail;
			}

			if ('message' in value && typeof value.message === 'string') {
				return value.message;
			}

			return JSON.stringify(value) ?? String(value);
		}

		return JSON.stringify(value) ?? String(value);
	};

	$: message = getErrorMessage(content) || 'Error submitting message';
</script>

<div
	class="my-1.5 flex w-full items-start gap-2 rounded-2xl bg-base-1000/[0.03] px-3 py-2 text-base-500 dark:bg-base-0/[0.04] dark:text-base-400"
>
	<Info className="mt-0.5 size-4 shrink-0 text-base-400 dark:text-base-500" strokeWidth="1.8" />

	<div
		class="markdown-prose min-w-0 text-[0.8125rem]! leading-5! text-base-500! dark:text-base-400! [&_p]:leading-5!"
	>
		<Markdown content={message} allowRemoteContent={false} editCodeBlock={false} />
	</div>
</div>
