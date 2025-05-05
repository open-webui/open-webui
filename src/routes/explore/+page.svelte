<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import AnimatedBackground from '$lib/IONOS/components/explore/AnimatedBackground.svelte'
	import AgentSelector from '$lib/IONOS/components/explore/AgentSelector.svelte'
	import PromptSelector from '$lib/IONOS/components/explore/PromptSelector.svelte'
	import LoginRegisterOverlay from '$lib/IONOS/components/explore/LoginRegisterOverlay.svelte';
	import Robot from '$lib/components/icons/Robot.svelte'
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte'
	import Sparkles from '$lib/IONOS/components/icons/Sparkles.svelte';
	import { user } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { init as initAgentsStore } from '$lib/IONOS/stores/agents';
	import { init as initPromptsStore } from '$lib/IONOS/stores/prompts';
	import { selectAgent } from '$lib/IONOS/services/agent';
	import { selectPrompt } from '$lib/IONOS/services/prompt';
	import { signup } from '$lib/IONOS/services/signup';

	const i18n = getContext('i18n');

	let selectedAgent: string|null = null;
	let selectedPrompt: number|null = null;

	function selectAgentInternal(agentId: string) {
		if (!$user) {
			selectedAgent = agentId;
			return;
		}

		selectAgent(agentId);
	}

	function selectPromptInternal(promptId: number) {
		if (!$user) {
			selectedPrompt = promptId;
			return;
		}

		selectPrompt(promptId);
	}

	function login() {
		if (selectedAgent !== null) {
			console.log('Continue with selected agent', selectedAgent);
			selectAgent(selectedAgent);
		} else if (selectedPrompt !== null) {
			console.log('Continue with selected prompt', selectedPrompt);
			selectPrompt(selectedPrompt);
		}
	}

	onMount(async () => {
		await initAgentsStore();
		await initPromptsStore();
	});
</script>

<svelte:head>
	<title>{$i18n.t('Welcome to IONOS GPT,', { ns: 'ionos' })} {$i18n.t('Where AI becomes your ultimate team of experts!', { ns: 'ionos' })}</title>
</svelte:head>

<AnimatedBackground />

<content class="flex flex-col items-center mx-3 text-blue-800 w-full">
		<h1 class="my-5 text-5xl leading-[56px] font-overpass text-center text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-700">
			{$i18n.t('Welcome to IONOS GPT,', { ns: 'ionos' })}
			<br>
			{$i18n.t('Where AI becomes your ultimate team of experts!', { ns: 'ionos' })}
		</h1>

	<p class="max-w-3xl mb-4 text-lg leading-[26px] text-center text-blue-800">
		{$i18n.t('From ideas to execution, our virtual team is here to help — from writing and design to coding, they handle the details so you can focus on what matters. Get to know them and see how they can support your projects.', { ns: 'ionos' })}
	</p>

	<div class="flex flex-col items-center text-sm">
		<span>{$i18n.t('Select a specialist', { ns: 'ionos' })}</span>
		<span>
			<ChevronDown />
		</span>
	</div>

	<div class="block py-5 my-2">
		<AgentSelector on:select={({ detail: id }) => selectAgentInternal(id)} />
	</div>

	<h1 class="my-4 text-center text-[32px] leading-[40px] text-blue-800">
		{$i18n.t('Bringing your ideas to life is easy with our AI specialists', { ns: 'ionos' })}
	</h1>

	<p class="max-w-2xl text-center text-lg leading-[26px] text-blue-800">
		{$i18n.t('Whether you need great content, eye-catching designs, or clean code, your virtual team is here to help every step of the way.', { ns: 'ionos' })}
	</p>

	<div class="block w-full py-5 my-8">
		<PromptSelector on:select={({ detail: id }) => selectPromptInternal(id)} />
	</div>

	<div class="my-20">
		<Sparkles  filled={false}/>
	</div>
</content>

<LoginRegisterOverlay
	on:login={login}
	on:signup={signup}
	show={selectedAgent !== null || selectedPrompt !== null}
/>

<style>
	:global(body) {
		background-color: #f9f9f9;
	}
</style>
