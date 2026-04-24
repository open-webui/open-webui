import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type OnboardingStep = 'slack' | 'notion' | 'analyzing' | 'done';

export interface ConnectorStatus {
	slack: boolean;
	notion: boolean;
}

export interface SkillRecommendation {
	id: string;
	name: string;
	description: string;
	icon: string;
}

const defaultConnectors: ConnectorStatus = {
	slack: false,
	notion: false
};

export const onboardingStep = writable<OnboardingStep>('slack');
export const connectorStatus = writable<ConnectorStatus>({ ...defaultConnectors });
export const recommendedSkills = writable<SkillRecommendation[]>([]);

export const isOnboardingCompleted = writable<boolean>(
	browser ? localStorage.getItem('onboarding_completed') === 'true' : false
);

export function completeOnboarding() {
	isOnboardingCompleted.set(true);
	if (browser) {
		localStorage.setItem('onboarding_completed', 'true');
	}
}
