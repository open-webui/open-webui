export type GovernanceCapabilities = {
	can_use_private_chat: boolean;
	can_create_workspace: boolean;
	can_access_all_workspaces: boolean;
};

export const workspaceOnlyCapabilities: GovernanceCapabilities = {
	can_use_private_chat: false,
	can_create_workspace: false,
	can_access_all_workspaces: false
};

export const fallbackGovernanceCapabilities = (
	user: { role?: string } | null | undefined
): GovernanceCapabilities => ({
	can_use_private_chat: user?.role === 'admin',
	can_create_workspace: user?.role === 'admin',
	can_access_all_workspaces: false
});

export const canUsePrivateChat = (
	user: { role?: string } | null | undefined,
	capabilities: GovernanceCapabilities | null | undefined
) => (capabilities ?? fallbackGovernanceCapabilities(user)).can_use_private_chat;

export const canCreateWorkspace = (
	user: { role?: string } | null | undefined,
	capabilities: GovernanceCapabilities | null | undefined
) => (capabilities ?? fallbackGovernanceCapabilities(user)).can_create_workspace;

export const canAccessAllWorkspaces = (
	user: { role?: string } | null | undefined,
	capabilities: GovernanceCapabilities | null | undefined
) => (capabilities ?? fallbackGovernanceCapabilities(user)).can_access_all_workspaces;

export const canWriteWorkspace = (
	workspace: { my_role?: string | null } | null | undefined,
	user: { role?: string } | null | undefined,
	capabilities: GovernanceCapabilities | null | undefined
) => canAccessAllWorkspaces(user, capabilities) || ['manager', 'member'].includes(workspace?.my_role ?? '');

export const canManageWorkspace = (
	workspace: { my_role?: string | null } | null | undefined,
	user: { role?: string } | null | undefined,
	capabilities: GovernanceCapabilities | null | undefined
) => user?.role === 'admin' || canAccessAllWorkspaces(user, capabilities) || workspace?.my_role === 'manager';
