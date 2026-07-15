<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';

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
	class="my-2 flex w-full items-center gap-3 rounded-3xl bg-gray-100 px-4 py-3 text-gray-800 dark:bg-gray-800 dark:text-gray-100"
>
	<Info className="size-5 shrink-0" strokeWidth="2" />

	<div class="min-w-0 self-center break-words text-sm">
		{message}
	</div>
</div>
