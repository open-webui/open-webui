import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveChatFolderId, resolveNewChatPath } from '../src/lib/utils/workspaceChatContext.ts';

test('workspace root chat creation uses null folder_id', () => {
	assert.equal(
		resolveChatFolderId({
			workspaceId: 'workspace-1',
			selectedFolder: null,
			currentChat: null
		}),
		null
	);
});

test('workspace folder chat creation uses the selected folder id', () => {
	assert.equal(
		resolveChatFolderId({
			workspaceId: 'workspace-1',
			activeWorkspaceFolderId: null,
			selectedFolder: { id: 'folder-yh', workspace_id: 'workspace-1' },
			currentChat: null
		}),
		'folder-yh'
	);
});

test('workspace folder chat creation uses active folder id when folder object is stale', () => {
	assert.equal(
		resolveChatFolderId({
			workspaceId: 'workspace-1',
			activeWorkspaceFolderId: 'folder-yh',
			selectedFolder: null,
			currentChat: null
		}),
		'folder-yh'
	);
});

test('second workspace chat keeps the same selected folder id', () => {
	assert.equal(
		resolveChatFolderId({
			workspaceId: 'workspace-1',
			activeWorkspaceFolderId: 'folder-yh',
			selectedFolder: { id: 'folder-yh', workspace_id: 'workspace-1' },
			currentChat: { id: 'chat-1', workspace_id: 'workspace-1', folder_id: 'folder-yh' }
		}),
		'folder-yh'
	);
});

test('opening a workspace folder chat restores folder context from the chat', () => {
	assert.equal(
		resolveChatFolderId({
			workspaceId: 'workspace-1',
			activeWorkspaceFolderId: null,
			selectedFolder: null,
			currentChat: { id: 'chat-1', workspace_id: 'workspace-1', folder_id: 'folder-yh' }
		}),
		'folder-yh'
	);
});

test('private chat creation ignores workspace folder metadata', () => {
	assert.equal(
		resolveChatFolderId({
			workspaceId: null,
			activeWorkspaceFolderId: 'folder-yh',
			selectedFolder: { id: 'folder-yh', workspace_id: 'workspace-1' },
			currentChat: { id: 'chat-1', workspace_id: 'workspace-1', folder_id: 'folder-yh' }
		}),
		null
	);
});

test('workspace chat new-chat navigation stays inside the workspace route', () => {
	assert.equal(
		resolveNewChatPath('/workspaces/workspace-1/c/chat-1', 'workspace-1'),
		'/workspaces/workspace-1'
	);
});

test('private chat new-chat navigation stays private', () => {
	assert.equal(resolveNewChatPath('/c/chat-1', null), '/');
});
