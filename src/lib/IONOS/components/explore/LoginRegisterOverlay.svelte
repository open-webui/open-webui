<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { createEventDispatcher, getContext } from 'svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte';
	import Link from '$lib/IONOS/components/common/Link.svelte';
	import BulletCheckmarkOnLight from '$lib/IONOS/components/icons/BulletCheckmarkOnLight.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext<Readable<I18Next>>('i18n');

	export let show = false;
</script>

<Dialog
	hasHeader={false}
	dialogId="register-login"
	{show}
>
	<content class="block p-7 flex flex-col gap-5">
		<h1 class="text-3xl">
			{$i18n.t('Your AI Experts Are Ready', { ns: 'ionos' })}
		</h1>

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
