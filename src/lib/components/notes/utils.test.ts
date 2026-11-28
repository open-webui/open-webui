import { describe, expect, it } from 'vitest';
import { canCopyNoteLink } from './utils';

describe('canCopyNoteLink', () => {
	it('returns false when note or user is missing', () => {
		expect(canCopyNoteLink(null, { id: 'u1', role: 'user' })).toBe(false);
		expect(canCopyNoteLink({ id: 'n1', user_id: 'u1' } as never, null)).toBe(false);
	});

	it('returns false for an unshared note owned by a user without notes sharing permission', () => {
		expect(
			canCopyNoteLink(
				{ user_id: 'u1', access_grants: [] },
				{ id: 'u1', role: 'user', permissions: { sharing: { notes: false } } }
			)
		).toBe(false);
		expect(canCopyNoteLink({ user_id: 'u1' }, { id: 'u1', role: 'user', permissions: {} })).toBe(
			false
		);
	});

	it('returns true when user is admin or has notes sharing permission', () => {
		expect(
			canCopyNoteLink(
				{ user_id: 'u1', access_grants: [] },
				{ id: 'u2', role: 'admin', permissions: { sharing: { notes: false } } }
			)
		).toBe(true);
		expect(
			canCopyNoteLink(
				{ user_id: 'u1', access_grants: [] },
				{ id: 'u1', role: 'user', permissions: { sharing: { notes: true } } }
			)
		).toBe(true);
	});

	it('returns true when the note was shared with the user or already has access grants', () => {
		expect(
			canCopyNoteLink(
				{ user_id: 'owner', access_grants: [] },
				{ id: 'recipient', role: 'user', permissions: { sharing: { notes: false } } }
			)
		).toBe(true);
		expect(
			canCopyNoteLink(
				{
					user_id: 'u1',
					access_grants: [{ principal_type: 'user', principal_id: 'u2', permission: 'read' }]
				},
				{ id: 'u1', role: 'user', permissions: { sharing: { notes: false } } }
			)
		).toBe(true);
	});
});
