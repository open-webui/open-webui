<script lang="ts">
	import { getContext } from 'svelte';
	import dayjs from 'dayjs';

	import { formatDate, formatMessageTimestampFull } from '$lib/utils';
	import Tooltip from './Tooltip.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	// Milliseconds since epoch
	export let timestamp: number;

	$: date = dayjs(timestamp);
	$: label = $i18n.t(formatDate(timestamp), {
		LOCALIZED_TIME: date.locale($i18n.language).format('LT'),
		LOCALIZED_DATE: date.toDate().toLocaleDateString($i18n.language, {
			weekday: 'short',
			month: 'short',
			day: 'numeric',
			...(date.isSame(dayjs(), 'year') ? {} : { year: 'numeric' })
		})
	});
</script>

<div class="flex justify-center pt-4 pb-3">
	<Tooltip content={formatMessageTimestampFull(timestamp, $i18n.language)}>
		<time
			datetime={date.toISOString()}
			class="text-xs tabular-nums text-base-500 dark:text-base-400 select-none">{label}</time
		>
	</Tooltip>
</div>
