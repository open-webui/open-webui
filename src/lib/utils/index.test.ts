import { describe, it, expect } from 'vitest';
import { checkAccess } from './index';

describe('checkAccess', () => {
  describe('Basic access control', () => {
    it('should deny access when no user ID is provided', () => {
      expect(checkAccess(undefined, [], null, 'read')).toBe(false);
      expect(checkAccess('', [], null, 'read')).toBe(false);
    });

    it('should grant read access when accessControl is null (public)', () => {
      expect(checkAccess('user1', [], null, 'read')).toBe(true);
    });

    it('should deny write access when accessControl is null (public)', () => {
      expect(checkAccess('user1', [], null, 'write')).toBe(false);
    });

    it('should grant read access when accessControl is undefined (public)', () => {
      expect(checkAccess('user1', [], undefined, 'read')).toBe(true);
    });

    it('should deny write access when accessControl is undefined (public)', () => {
      expect(checkAccess('user1', [], undefined, 'write')).toBe(false);
    });
  });

  describe('Admin user access', () => {
    it('should grant full access to admin users regardless of access control', () => {
      const restrictiveAccessControl = {
        read: { user_ids: ['other_user'], group_ids: [] },
        write: { user_ids: ['other_user'], group_ids: [] }
      };

      expect(checkAccess('admin_user', [], restrictiveAccessControl, 'read', 'admin')).toBe(true);
      expect(checkAccess('admin_user', [], restrictiveAccessControl, 'write', 'admin')).toBe(true);
    });

    it('should grant admin access even with null access control', () => {
      expect(checkAccess('admin_user', [], null, 'read', 'admin')).toBe(true);
      expect(checkAccess('admin_user', [], null, 'write', 'admin')).toBe(true);
    });

    it('should grant admin access even without user groups', () => {
      const accessControl = {
        read: { user_ids: [], group_ids: ['special_group'] },
        write: { user_ids: [], group_ids: ['special_group'] }
      };

      expect(checkAccess('admin_user', [], accessControl, 'read', 'admin')).toBe(true);
      expect(checkAccess('admin_user', [], accessControl, 'write', 'admin')).toBe(true);
    });
  });

  describe('User ID based access control', () => {
    it('should grant access when user is in permitted user IDs', () => {
      const accessControl = {
        read: { user_ids: ['user1', 'user2'], group_ids: [] },
        write: { user_ids: ['user1'], group_ids: [] }
      };

      expect(checkAccess('user1', [], accessControl, 'read')).toBe(true);
      expect(checkAccess('user1', [], accessControl, 'write')).toBe(true);
      expect(checkAccess('user2', [], accessControl, 'read')).toBe(true);
      expect(checkAccess('user2', [], accessControl, 'write')).toBe(false);
    });

    it('should deny access when user is not in permitted user IDs', () => {
      const accessControl = {
        read: { user_ids: ['user1'], group_ids: [] },
        write: { user_ids: [], group_ids: [] }
      };

      expect(checkAccess('user2', [], accessControl, 'read')).toBe(false);
      expect(checkAccess('user1', [], accessControl, 'write')).toBe(false);
    });
  });

  describe('Group based access control', () => {
    it('should grant access when user is in permitted groups', () => {
      const userGroups = [{ id: 'group1' }, { id: 'group2' }];
      const accessControl = {
        read: { user_ids: [], group_ids: ['group1', 'group3'] },
        write: { user_ids: [], group_ids: ['group2'] }
      };

      expect(checkAccess('user1', userGroups, accessControl, 'read')).toBe(true);
      expect(checkAccess('user1', userGroups, accessControl, 'write')).toBe(true);
    });

    it('should deny access when user is not in any permitted groups', () => {
      const userGroups = [{ id: 'group1' }];
      const accessControl = {
        read: { user_ids: [], group_ids: ['group2'] },
        write: { user_ids: [], group_ids: ['group3'] }
      };

      expect(checkAccess('user1', userGroups, accessControl, 'read')).toBe(false);
      expect(checkAccess('user1', userGroups, accessControl, 'write')).toBe(false);
    });

    it('should handle undefined or empty user groups', () => {
      const accessControl = {
        read: { user_ids: [], group_ids: ['group1'] },
        write: { user_ids: [], group_ids: ['group1'] }
      };

      expect(checkAccess('user1', undefined, accessControl, 'read')).toBe(false);
      expect(checkAccess('user1', [], accessControl, 'read')).toBe(false);
    });
  });

  describe('Combined user ID and group access control', () => {
    it('should grant access when user matches either user ID or group', () => {
      const userGroups = [{ id: 'group1' }];
      const accessControl = {
        read: { user_ids: ['user2'], group_ids: ['group1'] },
        write: { user_ids: ['user1'], group_ids: ['group2'] }
      };

      // User1 in permitted user_ids for write, in permitted group for read
      expect(checkAccess('user1', userGroups, accessControl, 'read')).toBe(true);
      expect(checkAccess('user1', userGroups, accessControl, 'write')).toBe(true);
    });

    it('should deny access when user matches neither user ID nor group', () => {
      const userGroups = [{ id: 'group1' }];
      const accessControl = {
        read: { user_ids: ['user2'], group_ids: ['group2'] },
        write: { user_ids: ['user2'], group_ids: ['group2'] }
      };

      expect(checkAccess('user1', userGroups, accessControl, 'read')).toBe(false);
      expect(checkAccess('user1', userGroups, accessControl, 'write')).toBe(false);
    });
  });

  describe('Missing permission configurations', () => {
    it('should deny access when requested permission type is missing', () => {
      const accessControl = {
        read: { user_ids: ['user1'], group_ids: [] }
        // write permission is missing
      };

      expect(checkAccess('user1', [], accessControl, 'read')).toBe(true);
      expect(checkAccess('user1', [], accessControl, 'write')).toBe(false);
    });

    it('should handle missing user_ids and group_ids arrays', () => {
      const accessControl = {
        read: {}, // Missing user_ids and group_ids
        write: { user_ids: ['user1'] } // Missing group_ids
      };

      expect(checkAccess('user1', [], accessControl, 'read')).toBe(false);
      expect(checkAccess('user1', [], accessControl, 'write')).toBe(true);
    });
  });

  describe('Default parameter values', () => {
    it('should default to read access when type is not specified', () => {
      const accessControl = {
        read: { user_ids: ['user1'], group_ids: [] },
        write: { user_ids: [], group_ids: [] }
      };

      // Should check read access by default
      expect(checkAccess('user1', [], accessControl)).toBe(true);
      expect(checkAccess('user2', [], accessControl)).toBe(false);
    });
  });

  describe('Edge cases', () => {
    it('should handle empty access control object', () => {
      expect(checkAccess('user1', [], {}, 'read')).toBe(false);
      expect(checkAccess('user1', [], {}, 'write')).toBe(false);
    });

    it('should handle multiple groups with overlapping permissions', () => {
      const userGroups = [{ id: 'group1' }, { id: 'group2' }, { id: 'group3' }];
      const accessControl = {
        read: { user_ids: [], group_ids: ['group1', 'group2', 'group4'] },
        write: { user_ids: [], group_ids: ['group2', 'group3'] }
      };

      expect(checkAccess('user1', userGroups, accessControl, 'read')).toBe(true); // group1 or group2 match
      expect(checkAccess('user1', userGroups, accessControl, 'write')).toBe(true); // group2 or group3 match
    });

    it('should handle admin role with non-admin access patterns', () => {
      const userGroups = [{ id: 'regular_group' }];
      const accessControl = {
        read: { user_ids: ['other_user'], group_ids: ['other_group'] },
        write: { user_ids: ['other_user'], group_ids: ['other_group'] }
      };

      // Admin should bypass all restrictions
      expect(checkAccess('regular_user', userGroups, accessControl, 'read', 'admin')).toBe(true);
      expect(checkAccess('regular_user', userGroups, accessControl, 'write', 'admin')).toBe(true);
    });

    it('should handle non-admin roles normally', () => {
      const userGroups = [{ id: 'group1' }];
      const accessControl = {
        read: { user_ids: ['user1'], group_ids: [] },
        write: { user_ids: [], group_ids: ['group1'] }
      };

      // User role should not get special privileges
      expect(checkAccess('user1', userGroups, accessControl, 'read', 'user')).toBe(true);
      expect(checkAccess('user2', userGroups, accessControl, 'read', 'user')).toBe(false);
      expect(checkAccess('user1', userGroups, accessControl, 'write', 'user')).toBe(true);
    });
  });
});