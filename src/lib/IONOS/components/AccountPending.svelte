<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Link from '$lib/IONOS/components/common/Link.svelte';
	import { signout } from '$lib/services/auths';

	const i18n = getContext<Readable<I18Next>>('i18n');
</script>

<div class="fixed w-full h-full flex z-[999]">
	<div
		class="absolute w-full h-full bg-white dark:bg-gray-900/50 flex justify-center"
	>
		<div class="m-auto pb-10 flex flex-col justify-center">
			<div class="max-w-md">
				<div class="text-center dark:text-white text-2xl font-medium z-50">
					{$i18n.t('Your account is currently unavailable', { ns: 'ionos' })}<br />
				</div>

				<div class=" mt-4 text-center text-sm dark:text-gray-200 w-full">
					{$i18n.t('For more information, please visit our FAQ or contact support.', { ns: 'ionos' })}
				</div>

				<div class=" mt-4 text-center">
					<Link
						on:click={() => signout()}
					>
						{$i18n.t('Sign Out')}
					</Link>
				</div>
			</div>
		</div>
	</div>
</div>
