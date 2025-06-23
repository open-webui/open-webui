<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import TermsMenu from './TermsMenu.svelte';

	const i18n = getContext<Readable<I18Next>>('i18n');
	let showTerms: boolean = false;
</script>

<div class="flex flex-col items-center">
	<div class="flex mb-7 max-w-2xl text-gray-400 text-xs text-center gap-[3px]">
		<p>
			{$i18n.t('IONOS GPT can make mistakes.', { ns: 'ionos' })}
		</p>
		<TermsMenu
			show={showTerms}
			className="text-blue-700"
		>
			<div class="font-semibold underline">
				{$i18n.t('Check important info.', { ns: 'ionos' })}
			</div>
		</TermsMenu>
	</div>
</div>
