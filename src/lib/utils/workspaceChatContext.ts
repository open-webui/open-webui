type FolderContext = {
	id?: string | null;
	workspace_id?: string | null;
};

type ChatContext = {
	folder_id?: string | null;
	workspace_id?: string | null;
};

export const resolveChatFolderId = ({
	workspaceId,
	selectedFolder,
	currentChat
}: {
	workspaceId?: string | null;
	selectedFolder?: FolderContext | null;
	currentChat?: ChatContext | null;
}) => {
	if (workspaceId) {
		if (selectedFolder?.id && selectedFolder.workspace_id === workspaceId) {
			return selectedFolder.id;
		}

		if (currentChat?.folder_id && currentChat.workspace_id === workspaceId) {
			return currentChat.folder_id;
		}

		return null;
	}

	return selectedFolder?.id && !selectedFolder.workspace_id ? selectedFolder.id : null;
};

export const resolveNewChatPath = (pathname: string, workspaceId?: string | null) => {
	if (!pathname.includes('/c/')) {
		return pathname;
	}

	return workspaceId ? `/workspaces/${workspaceId}` : '/';
};
