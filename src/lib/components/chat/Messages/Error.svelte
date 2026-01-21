<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';

	export let content = '';

	const HTML_ERROR_SENTINELS = ['<!doctype', '<html', '<head', '<body', '<title'];

	const summarizeHtmlError = (message: string) => {
		const lowerMessage = message.toLowerCase();
		if (!HTML_ERROR_SENTINELS.some((tag) => lowerMessage.includes(tag))) {
			return message;
		}

		const titleMatch = message.match(/<title>(.*?)<\/title>/i);
		const title = titleMatch ? titleMatch[1].trim() : '';
		const codeMatch = message.match(/\b([45]\d{2})\b/);
		const code = codeMatch ? codeMatch[1] : '';

		if (code && title) {
			return `Upstream error ${code}. ${title}`;
		}
		if (code) {
			return `Upstream error ${code}. The proxy returned an HTML error page.`;
		}
		if (title) {
			return `Upstream error. ${title}`;
		}
		return 'Upstream error. The proxy returned an HTML error page.';
	};

	const formatError = (value: unknown) => {
		if (typeof value === 'string') {
			return summarizeHtmlError(value);
		}

		if (value && typeof value === 'object') {
			const record = value as Record<string, unknown>;
			const nestedError = record.error as Record<string, unknown> | undefined;
			const message =
				(typeof nestedError?.message === 'string' && nestedError.message) ||
				(typeof record.detail === 'string' && record.detail) ||
				(typeof record.message === 'string' && record.message);

			if (message) {
				return summarizeHtmlError(message);
			}
		}

		return JSON.stringify(value);
	};
</script>

<div class="flex my-2 gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-lg">
	<div class=" self-start mt-0.5">
		<Info className="size-5 text-red-700 dark:text-red-400" />
	</div>

	<div class=" self-center text-sm">
		{formatError(content)}
	</div>
</div>
