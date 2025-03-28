<script lang="ts">
	import type { Readable } from 'svelte/store';
	import type { I18Next } from '$lib/IONOS/i18next.d.ts';
	import { createEventDispatcher, getContext } from 'svelte';
	import Dialog from '$lib/IONOS/components/common/Dialog.svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte';
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
	<content class="block p-2">
		<h1 class="text-2xl mb-5">
			{$i18n.t('Your AI Experts Are Ready', { ns: 'ionos' })}
		</h1>

		<h2 class="text-xl my-5">
			{$i18n.t('Boost productivity with AI-powered tools', { ns: 'ionos' })}
		</h2>

		<ul>
			<li class="flex items-center my-5">
				<BulletCheckmarkOnLight className="inline size-6 mr-2"/>
				{$i18n.t('Chat, write, design, and code with expert AI assistants', { ns: 'ionos' })}
			</li>
			<li class="flex items-center my-5">
				<BulletCheckmarkOnLight className="inline size-6 mr-2"/>
				{$i18n.t('Get tailored answers and generate content effortlessly', { ns: 'ionos' })}
			</li>
			<li class="flex items-center my-5">
				<BulletCheckmarkOnLight className="inline size-6 mr-2"/>
				{$i18n.t('Upload files for context-aware insights and solutions', { ns: 'ionos' })}
			</li>
		</ul>

		<div class="flex flex-row gap-4 mt-8 items-center">
			<Button
				on:click={() => dispatch('login')}
				className="px-4 py-1 flex-grow"
				type={ButtonType.primary}
			>
				{$i18n.t('Login', { ns: 'ionos' })}
			</Button>

			<span class="text-gray-500">or</span>

			<Button
				on:click={() => dispatch('signup')}
				className="px-4 py-1 flex-grow"
				type={ButtonType.secondary}
			>
				{$i18n.t('Sign Up', { ns: 'ionos' })}
			</Button>
		</div>
	</content>
</Dialog>
