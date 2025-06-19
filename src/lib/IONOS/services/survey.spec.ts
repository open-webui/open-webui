import { describe, beforeEach, expect, it, vi } from 'vitest';
import type { SessionUser, Config } from '$lib/stores';
import { buildSurveyUrl } from '$lib/IONOS/services/survey';

const mocks = vi.hoisted(() => {
	return {
		stores: {
			config: {
				subscribe: vi.fn(),
			},
		},
	};
});

vi.mock('$lib/stores', async () => {
	return mocks.stores;
});

type ConfigSubscriberCallback = (value: Partial<Config>) => void;

describe('suvey', () => {
	describe('buildSurveyUrl()', () => {
		const userId = 'pseudonymized-user-id-47';

		const user: SessionUser = Object.freeze({
			id: 'foo-id-123',
			email: 'foo@localhost',
			name: 'foo',
			role: 'user',
			profile_image_url: '',
			created_at: 0,
			pseudonymized_user_id: userId,
		});

		let surveyUrl;

		beforeEach(() => {
			surveyUrl = 'https://acmesurvey.com/foo47';

			mocks.stores.config.subscribe.mockImplementation((fn: ConfigSubscriberCallback) => {
				fn({
					// @ts-expect-error Argument of type 'Partial<SessionUser>' is not assignable to parameter of type 'SessionUser'.
					features: {
						ionos_survey_new_users_url: surveyUrl
					}
				});

				return () => { /* unsubscriber */ };
			});
		});

		it('should build a survey URL with the pseudynimized user ID', async () => {
			expect(buildSurveyUrl(user)).toBe(`${surveyUrl}?urlVar01=DE&urlVar02=${userId}&urlVar03=Product`);
		});

		it('should return null if the survey URL is null', async () => {
			surveyUrl = null;
			expect(buildSurveyUrl(user)).toBe(null);
		});
	});
});
