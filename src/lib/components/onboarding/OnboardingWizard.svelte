<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import {
		onboardingStep,
		connectorStatus,
		recommendedSkills,
		completeOnboarding
	} from '$lib/stores/onboarding';
	import type { OnboardingStep } from '$lib/stores/onboarding';

	import ConnectorButton from './ConnectorButton.svelte';
	import SkillResults from './SkillResults.svelte';

	export let onComplete: () => void = () => {};

	const steps: { key: OnboardingStep; label: string }[] = [
		{ key: 'slack', label: 'Slack' },
		{ key: 'notion', label: 'Notion' },
		{ key: 'analyzing', label: 'Analizando' },
		{ key: 'done', label: 'Listo' }
	];

	function currentStepIndex(step: OnboardingStep): number {
		return steps.findIndex((s) => s.key === step);
	}

	function nextStep() {
		const idx = currentStepIndex($onboardingStep);
		if (idx < steps.length - 1) {
			$onboardingStep = steps[idx + 1].key;
		}

		if ($onboardingStep === 'analyzing') {
			runAnalysis();
		}
	}

	async function runAnalysis() {
		const providers: string[] = [];
		if ($connectorStatus.slack) providers.push('slack');
		if ($connectorStatus.notion) providers.push('notion');

		try {
			const res = await fetch(`${WEBUI_BASE_URL}/api/v1/clapnclaw/onboarding/run-agent`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ providers })
			});
			const data = await res.json();
			$recommendedSkills = data.skills || [];
		} catch {
			$recommendedSkills = [];
		}

		$onboardingStep = 'done';
	}

	function finish() {
		completeOnboarding();
		onComplete();
	}
</script>

<div class="fixed inset-0 z-[999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
	<div
		class="w-full max-w-lg mx-4 bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden"
	>
		<!-- Header -->
		<div class="px-6 pt-6 pb-4 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center gap-3 mb-4">
				<img
					crossorigin="anonymous"
					src="{WEBUI_BASE_URL}/static/favicon.png"
					class="size-8 rounded-full"
					alt="ClapNClaw"
				/>
				<h2 class="text-xl font-bold text-gray-900 dark:text-white">
					Configura tu workspace
				</h2>
			</div>

			<!-- Progress -->
			<div class="flex gap-1.5">
				{#each steps as step, i}
					<div
						class="h-1 flex-1 rounded-full transition-colors {i <=
						currentStepIndex($onboardingStep)
							? 'bg-claw-500'
							: 'bg-gray-200 dark:bg-gray-700'}"
					/>
				{/each}
			</div>
		</div>

		<!-- Content -->
		<div class="p-6 space-y-4">
			{#if $onboardingStep === 'slack'}
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
					Conecta Slack para buscar y enviar mensajes.
				</p>
				<ConnectorButton
					provider="slack"
					label="Slack"
					icon="S"
					bind:connected={$connectorStatus.slack}
					onConnect={nextStep}
				/>
			{:else if $onboardingStep === 'notion'}
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
					Conecta Notion para buscar en tu knowledge base.
				</p>
				<ConnectorButton
					provider="notion"
					label="Notion"
					icon="N"
					optional={true}
					bind:connected={$connectorStatus.notion}
					onConnect={nextStep}
					onSkip={nextStep}
				/>
			{:else if $onboardingStep === 'analyzing'}
				<div class="flex flex-col items-center py-8">
					<div
						class="size-12 border-4 border-claw-500 border-t-transparent rounded-full animate-spin mb-4"
					/>
					<p class="text-gray-600 dark:text-gray-400">
						Analizando tus integraciones y recomendando skills...
					</p>
				</div>
			{:else if $onboardingStep === 'done'}
				{#if $recommendedSkills.length > 0}
					<SkillResults skills={$recommendedSkills} />
				{:else}
					<p class="text-sm text-gray-600 dark:text-gray-400">
						Todo listo. Ya puedes empezar a chatear con tus herramientas conectadas.
					</p>
				{/if}

				<button
					class="w-full mt-4 px-4 py-3 rounded-xl bg-claw-500 hover:bg-claw-600 text-white font-medium transition"
					on:click={finish}
				>
					Empieza a chatear
				</button>
			{/if}
		</div>
	</div>
</div>
