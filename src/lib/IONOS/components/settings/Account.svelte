<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Confirm from '$lib/IONOS/components/common/Confirm.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte'
	import { user } from '$lib/stores';
	import { resetPassword } from '$lib/IONOS/services/account';
	const i18n = getContext<Readable<I18Next>>('i18n');
</script>

<div class="flex flex-col gap-5">
	<div class="flex flex-row items-center h-10">
		<div class="flex-grow">
			{$i18n.t('Email', { ns: 'ionos' })}
		</div>
		<div>
			{$user.email}
		</div>
	</div>
	<div class="flex flex-row items-center h-10">
		<div class="flex-grow">
			{$i18n.t('Reset password', { ns: 'ionos' })}
		</div>
		<div>
			<Button
				on:click={() => resetPassword()}
				type={ButtonType.secondary}>
				{$i18n.t('Reset password', { ns: 'ionos' })}
			</Button>
		</div>
	</div>
</div>
