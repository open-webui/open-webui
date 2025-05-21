<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { createEventDispatcher, getContext } from 'svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte';
	import Link from '$lib/IONOS/components/common/Link.svelte';
	import BulletCheckmarkOnLight from '$lib/IONOS/components/icons/BulletCheckmarkOnLight.svelte';
	import XMark from '$lib/IONOS/components/icons/XMark.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext<Readable<I18Next>>('i18n');

	export let show = false;
</script>

<Dialog
	dialogId="register-login"
	{show}
>
	<div class="flex justify-between" slot="header">
		<h1 class="text-[28px] leading-9 font-overpass p-2.5 text-blue-800">
			{$i18n.t('Your AI Experts Are Ready', { ns: 'ionos' })}
		</h1>
		<button class="justify-self-end" on:click={() => dispatch('close')}>
			<XMark />
		</button>
	</div>
	<content slot="content" class="p-2.5 block flex flex-col gap-5">

		<ul>
			<li class="flex items-center my-4">
				<BulletCheckmarkOnLight className="inline size-6 mr-2"/>
				{$i18n.t('Chat, write, design, and code with expert AI assistants', { ns: 'ionos' })}
			</li>
			<li class="flex items-center my-4">
				<BulletCheckmarkOnLight className="inline size-6 mr-2"/>
				{$i18n.t('Get tailored answers and generate content effortlessly', { ns: 'ionos' })}
			</li>
			<li class="flex items-center my-4">
				<BulletCheckmarkOnLight className="inline size-6 mr-2"/>
				{$i18n.t('Upload files for context-aware insights and solutions', { ns: 'ionos' })}
			</li>
		</ul>

		<div>
			<h3 class="font-semibold">
				{$i18n.t('Customer ID, email address or domain', { ns: 'ionos' })}
			</h3>

			<Button
				on:click={() => dispatch('login')}
				className="px-4 py-1 my-3 flex-grow w-full"
				type={ButtonType.primary}
			>
				{$i18n.t('Continue', { ns: 'ionos' })}
			</Button>
		</div>

		<div>
			<h3 class="font-semibold text-gray-500">
				{$i18n.t('Not an IONOS customer yet?', { ns: 'ionos' })}
			</h3>

			<Link
				on:click={() => dispatch('signup')}
				className="inline-block mt-3"
			>
				{$i18n.t('Sign up now for FREE to start creating with AI', { ns: 'ionos' })}
			</Link>
		</div>
	</content>
</Dialog>
