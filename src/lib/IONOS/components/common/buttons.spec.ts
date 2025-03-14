import { describe, expect, it } from 'vitest';
import { stateClassBuilder as build, ButtonType } from './buttons';

describe('buttons', () => {
	// Bare minimum sanity tests, it makes no sense to duplicate styles here
	describe('stateClassBuilder', () => {
		// To test that there's at least some mapping
		it('should not throw', () => {
			expect(() => build(ButtonType.primary, false, false)).not.toThrow();
			expect(() => build(ButtonType.secondary, false, false)).not.toThrow();
			expect(() => build(ButtonType.tertiary, false, false)).not.toThrow();
			expect(() => build(ButtonType.caution, false, false)).not.toThrow();
			expect(() => build(ButtonType.special, false, false)).not.toThrow();
		});

		it('should not include hover states for disabled buttons', () => {
			expect(build(ButtonType.primary, true, false)).not.toContain('hover:');
			expect(build(ButtonType.secondary, true, false)).not.toContain('hover:');
			expect(build(ButtonType.tertiary, true, false)).not.toContain('hover:');
			expect(build(ButtonType.caution, true, false)).not.toContain('hover:');
			expect(build(ButtonType.special, true, false)).not.toContain('hover:');
		});

		it('should not include active states for disabled buttons', () => {
			expect(build(ButtonType.primary, true, false)).not.toContain('active:');
			expect(build(ButtonType.secondary, true, false)).not.toContain('active:');
			expect(build(ButtonType.tertiary, true, false)).not.toContain('active:');
			expect(build(ButtonType.caution, true, false)).not.toContain('active:');
			expect(build(ButtonType.special, true, false)).not.toContain('active:');
		});

		it('should not include hover states for disabled and pressed buttons', () => {
			expect(build(ButtonType.primary, true, true)).not.toContain('hover:');
			expect(build(ButtonType.secondary, true, true)).not.toContain('hover:');
			expect(build(ButtonType.tertiary, true, true)).not.toContain('hover:');
			expect(build(ButtonType.caution, true, true)).not.toContain('hover:');
			expect(build(ButtonType.special, true, true)).not.toContain('hover:');
		});

		it('should not include active states for disabled and pressed buttons', () => {
			expect(build(ButtonType.primary, true, true)).not.toContain('active:');
			expect(build(ButtonType.secondary, true, true)).not.toContain('active:');
			expect(build(ButtonType.tertiary, true, true)).not.toContain('active:');
			expect(build(ButtonType.caution, true, true)).not.toContain('active:');
			expect(build(ButtonType.special, true, true)).not.toContain('active:');
		});

		it('should have cursor-default for disabled and pressed + disabled', () => {
			expect(build(ButtonType.primary, true, false)).toContain('cursor-default');
			expect(build(ButtonType.secondary, true, true)).toContain('cursor-default');
			expect(build(ButtonType.tertiary, true, true)).toContain('cursor-default');
			expect(build(ButtonType.caution, true, true)).toContain('cursor-default');
			expect(build(ButtonType.special, true, true)).toContain('cursor-default');
		});
	});
});
