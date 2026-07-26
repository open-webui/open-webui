import { describe, expect, it } from 'vitest';

import { shouldShowUserDisclaimer } from './disclaimer';

const configured = (ui = {}) => ({
	ui: {
		user_disclaimer_content: 'You agree to the acceptable use policy.',
		...ui
	}
});

describe('shouldShowUserDisclaimer', () => {
	describe('when no disclaimer is configured', () => {
		it('stays hidden without any config', () => {
			expect(shouldShowUserDisclaimer(undefined, {})).toBe(false);
			expect(shouldShowUserDisclaimer(null, {})).toBe(false);
			expect(shouldShowUserDisclaimer({}, {})).toBe(false);
		});

		it('stays hidden when the content is empty', () => {
			expect(shouldShowUserDisclaimer({ ui: { user_disclaimer_content: '' } }, {})).toBe(false);
		});

		it('stays hidden when the content is only whitespace', () => {
			expect(shouldShowUserDisclaimer({ ui: { user_disclaimer_content: '  \n\t ' } }, {})).toBe(
				false
			);
		});

		it('stays hidden even if a version is set but there is nothing to show', () => {
			expect(shouldShowUserDisclaimer({ ui: { user_disclaimer_version: 'v2' } }, {})).toBe(false);
		});
	});

	describe('on first login', () => {
		it('shows for a user who has never acknowledged anything', () => {
			expect(shouldShowUserDisclaimer(configured(), {})).toBe(true);
		});

		it('shows when the user has no settings at all', () => {
			expect(shouldShowUserDisclaimer(configured(), undefined)).toBe(true);
			expect(shouldShowUserDisclaimer(configured(), null)).toBe(true);
		});

		it('shows when other settings exist but no acknowledgement does', () => {
			expect(shouldShowUserDisclaimer(configured(), { userDisclaimerAcknowledgedAt: null })).toBe(
				true
			);
		});
	});

	describe('once acknowledged', () => {
		it('hides for a user who accepted the default (unversioned) disclaimer', () => {
			expect(shouldShowUserDisclaimer(configured(), { userDisclaimerVersion: '' })).toBe(false);
		});

		it('hides for a user who accepted the current version', () => {
			expect(
				shouldShowUserDisclaimer(configured({ user_disclaimer_version: 'v2' }), {
					userDisclaimerVersion: 'v2'
				})
			).toBe(false);
		});

		it('distinguishes never-acknowledged from accepting the empty version', () => {
			// The nullish default must not collapse these two states into one.
			expect(shouldShowUserDisclaimer(configured(), {})).toBe(true);
			expect(shouldShowUserDisclaimer(configured(), { userDisclaimerVersion: '' })).toBe(false);
		});

		it('ignores the recorded timestamp when deciding', () => {
			expect(
				shouldShowUserDisclaimer(configured(), {
					userDisclaimerVersion: '',
					userDisclaimerAcknowledgedAt: 1750000000
				})
			).toBe(false);
		});
	});

	describe('when the disclaimer text changes', () => {
		it('re-prompts everyone after the version is bumped', () => {
			expect(
				shouldShowUserDisclaimer(configured({ user_disclaimer_version: 'v2' }), {
					userDisclaimerVersion: ''
				})
			).toBe(true);
		});

		it('re-prompts a user still on an older version', () => {
			expect(
				shouldShowUserDisclaimer(configured({ user_disclaimer_version: 'v3' }), {
					userDisclaimerVersion: 'v2'
				})
			).toBe(true);
		});

		it('re-prompts if the version is cleared again', () => {
			expect(shouldShowUserDisclaimer(configured(), { userDisclaimerVersion: 'v2' })).toBe(true);
		});

		it('does not re-prompt merely because the title changed', () => {
			expect(
				shouldShowUserDisclaimer(configured({ user_disclaimer_title: 'Updated heading' }), {
					userDisclaimerVersion: ''
				})
			).toBe(false);
		});
	});
});
