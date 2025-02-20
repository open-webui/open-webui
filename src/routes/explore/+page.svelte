<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import AgentSelector from '$lib/IONOS/components/AgentSelector.svelte'
	import Robot from '$lib/components/icons/Robot.svelte'
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte'
	import { init as initAgentsStore } from '$lib/IONOS/stores/agents';

	const i18n = getContext('i18n');

	onMount(async () => {
		await initAgentsStore();
	});
</script>

<h1 class="my-5 text-3xl text-center text-pink-300">
	{$i18n.t('Welcome to IONOS GPT,', { ns: 'ionos' })}
	<br>
	{$i18n.t('Where AI becomes your ultimate team of experts!', { ns: 'ionos' })}
</h1>

<p class="max-w-3xl mb-4 text-sm">
	{$i18n.t('From ideas to execution, our virtual team is here to help — from writing and design to coding, they handle the details so you can focus on what matters. Get to know them and see how they can support your projects.', { ns: 'ionos' })}
</p>

<div class="flex flex-col items-center">
	<span>{$i18n.t('Select a specialist', { ns: 'ionos' })}</span>
	<span>
		<ChevronDown />
	</span>
</div>

<div class="block py-5 my-16">
	<AgentSelector />
</div>

<h1 class="text-xl my-4">
	{$i18n.t('Bringing your ideas to life is easy with our AI specialists', { ns: 'ionos' })}
</h1>

<p class="max-w-2xl text-sm">
	{$i18n.t('Whether you need great content, eye-catching designs, or clean code, your virtual team is here to help every step of the way.', { ns: 'ionos' })}
</p>

<div class="block w-full h-20 py-5 text-center my-8 bg-white">
	... Preprompts here ...
</div>

<div class="my-20">
	<Robot />
</div>

<p class="max-w-2xl my-5 text-sm text-center">
	{$i18n.t('By sending messages to IONOS GPT, you agree to our terms and conditions and confirm that you\'ve read our privacy policy.', { ns: 'ionos' })}
</p>
