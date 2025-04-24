<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { getContext } from 'svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
 	import FilledUserAvatar from '$lib/IONOS/components/icons/FilledUserAvatar.svelte';
 	import Gear from '$lib/IONOS/components/icons/Gear.svelte';
	import General from './General.svelte';
	import Account from './Account.svelte';
	import NavItem from './NavItem.svelte';
	import { showSettings } from '$lib/stores';
	const i18n = getContext<Readable<I18Next>>('i18n');

	export let show = false;

	let section = 'general';
</script>

<Dialog
	title={$i18n.t("Settings", { ns: 'ionos' })}
	dialogId="settings"
	on:close={() => { showSettings.set(false); }}
	show={show}
>

	<div class="flex flex-row gap-4 py-5 px-2 min-h-[350px] min-w-[700px] max-w-[700px] text-blue-800">
		<nav class="w-48 flex-shrink-0">
			<ul class="flex flex-col">
				<li class="mb-3">
					<NavItem bind:group={section} value="general">
						<Gear slot="icon" className="inline s-4"/>
						<span class="ml-2">
							{$i18n.t('General', { ns: 'ionos' })}
						</span>
					</NavItem>
				</li>
				<li class="mb-3">
					<NavItem bind:group={section} value="account">
						<FilledUserAvatar slot="icon" className="inline s-4"/>
						<span class="ml-2">
							{$i18n.t('Account', { ns: 'ionos' })}
						</span>
					</NavItem>
				</li>
			</ul>
		</nav>

		<div class="flex-grow">
			{#if section === 'general'}
				<General />
			{:else if section === 'account'}
				<Account />
			{/if}
		</div>
	</div>
</Dialog>
