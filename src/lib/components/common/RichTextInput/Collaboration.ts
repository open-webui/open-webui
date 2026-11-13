import * as Y from 'yjs';
import { marked } from 'marked';
import {
	ySyncPlugin,
	ySyncPluginKey,
	yCursorPlugin,
	yUndoPlugin,
	undo,
	redo,
	prosemirrorJSONToYDoc,
	relativePositionToAbsolutePosition
} from 'y-prosemirror';
import type { Socket } from 'socket.io-client';
import type { SessionUser } from '$lib/stores';
import { createNodeFromContent, Editor, Extension } from '@tiptap/core';
import { keymap } from 'prosemirror-keymap';
import { Plugin } from 'prosemirror-state';
import { tick } from 'svelte';
import tippy, { type Instance } from 'tippy.js';

const USER_COLORS = [
	'#FF6B6B',
	'#4ECDC4',
	'#45B7D1',
	'#96CEB4',
	'#FFEAA7',
	'#DDA0DD',
	'#98D8C8',
	'#F7DC6F',
	'#BB8FCE',
	'#85C1E9'
];
const generateUserColor = () => {
	return USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)];
};

export type EditorContentGetter = () => {
	md: string;
	html: string;
	json: unknown;
};

// Collaborative editing for one editor. Editors showing the same document on
// the same socket share one DocumentSession, so they edit one Y.Doc.
export class SocketIOCollaborationProvider {
	private readonly session: DocumentSession;
	private readonly awareness: EditorAwareness;
	public editor: Editor | null = null;
	public getContent: EditorContentGetter | null = null;
	private cursorTarget: any = null;

	constructor(
		documentId: string,
		socket: Socket,
		user: SessionUser,
		initialContent: unknown = null
	) {
		this.session = DocumentSession.acquire(socket, documentId, user, initialContent, this);
		this.awareness = new EditorAwareness(this.session, this);
	}

	public revealCursor(target: any) {
		this.cursorTarget = target;
		this.revealPendingCursor();
	}

	public revealPendingCursor() {
		if (!this.session.synced || !this.editor || !this.cursorTarget) return;
		const target = this.cursorTarget;
		this.cursorTarget = null;
		const editor = this.editor;
		let position = target.cursor_position ?? 0;
		try {
			const state = ySyncPluginKey.getState(editor.state);
			if (target.cursor?.head && state?.binding) {
				position =
					relativePositionToAbsolutePosition(
						this.session.doc,
						state.type,
						Y.createRelativePositionFromJSON(target.cursor.head),
						state.binding.mapping
					) ?? position;
			}
		} catch {
			// A replaced document can no longer resolve the old relative cursor.
		}
		queueMicrotask(() => {
			if (!editor.isDestroyed)
				editor.commands.focus(Math.min(position, editor.state.doc.content.size));
		});
	}

	public getEditorExtension() {
		return Extension.create({
			name: 'yjsCollaboration',

			addProseMirrorPlugins: () => {
				const yXmlFragment = this.session.doc.getXmlFragment('prosemirror');
				if (!yXmlFragment) return [];

				const plugins = [
					new Plugin({
						filterTransaction: (tr) => {
							// Wait for the saved content before accepting local edits.
							if (
								!this.session.synced &&
								this.session.isConnected &&
								tr.docChanged &&
								!tr.getMeta(ySyncPluginKey)?.isChangeOrigin
							) {
								return false;
							}
							// Preserve literal URLs received from another editor.
							if (tr.getMeta(ySyncPluginKey)?.isChangeOrigin) {
								tr.setMeta('preventAutolink', true);
							}
							return true;
						},
						view: (view) => {
							const labels = new Map<HTMLElement, Instance>();
							const update = () => {
								for (const [cursor, label] of labels) {
									if (!view.dom.contains(cursor)) {
										label.destroy();
										labels.delete(cursor);
									}
								}
								for (const cursor of view.dom.querySelectorAll<HTMLElement>(
									'.ProseMirror-yjs-cursor'
								)) {
									if (!labels.has(cursor)) {
										const label = cursor.querySelector('div');
										if (!label) continue;
										// Float above the caret without being clipped by the editor's scroll area.
										label.remove();
										label.className = 'ProseMirror-yjs-cursor-label';
										labels.set(
											cursor,
											tippy(cursor, {
												appendTo: () => document.body,
												render: () => ({ popper: label }),
												trigger: 'manual',
												showOnCreate: true,
												hideOnClick: false,
												animation: false,
												placement: 'top-start',
												offset: [0, 2],
												zIndex: 30,
												popperOptions: {
													strategy: 'fixed',
													modifiers: [{ name: 'flip', enabled: false }]
												}
											})
										);
									}
									labels.get(cursor)?.popperInstance?.forceUpdate();
								}
							};
							update();
							const resizeObserver = new ResizeObserver(update);
							resizeObserver.observe(view.dom);
							return {
								update,
								destroy: () => {
									resizeObserver.disconnect();
									labels.forEach((label) => label.destroy());
								}
							};
						}
					}),
					ySyncPlugin(yXmlFragment),
					yUndoPlugin(),
					keymap({
						'Mod-z': undo,
						'Mod-y': redo,
						'Mod-Shift-z': redo
					})
				];

				// @ts-ignore
				plugins.push(yCursorPlugin(this.awareness));

				return plugins;
			}
		});
	}

	public setEditor(editor: Editor, getContent: EditorContentGetter) {
		this.editor = editor;
		this.getContent = getContent;
		this.session.editorReady();
	}

	public flush() {
		return this.session.flush(this);
	}

	public destroy() {
		this.session.release(this);
		this.editor = null;
		this.getContent = null;
	}
}

// One Y.Doc and room membership per socket and document. The server tracks
// room membership per socket, so this joins once for every editor showing the
// document, and leaves only when the last of them closes.
class DocumentSession {
	private static readonly sessions = new WeakMap<Socket, Map<string, DocumentSession>>();

	public static acquire(
		socket: Socket,
		documentId: string,
		user: SessionUser,
		initialContent: unknown,
		provider: SocketIOCollaborationProvider
	) {
		let bySocket = DocumentSession.sessions.get(socket);
		if (!bySocket) DocumentSession.sessions.set(socket, (bySocket = new Map()));
		let session = bySocket.get(documentId);
		if (!session) {
			session = new DocumentSession(documentId, socket, user, initialContent);
			bySocket.set(documentId, session);
		}
		session.providers.add(provider);
		return session;
	}

	public readonly doc = new Y.Doc();
	public readonly awareness = new SimpleAwareness(this.doc);
	public isConnected: boolean;
	public synced = false;
	public cursorOwner: SocketIOCollaborationProvider | null = null;
	private joined = false;
	private readonly providers = new Set<SocketIOCollaborationProvider>();
	private listeners: Array<[string, (...args: any[]) => void]> = [];
	private contentSnapshotTimer: ReturnType<typeof setTimeout> | null = null;

	private constructor(
		private readonly documentId: string,
		private readonly socket: Socket,
		private readonly user: SessionUser,
		private readonly initialContent: unknown
	) {
		this.isConnected = socket.connected;
		this.setupEventListeners();
	}

	// Every editor renders the same Y.Doc, so any of them can supply the content.
	private get primary() {
		for (const provider of this.providers) if (provider.editor) return provider;
		return null;
	}

	public editorReady() {
		this.isConnected ||= this.socket.connected;
		if (this.isConnected && !this.joined) this.join();
	}

	public release(provider: SocketIOCollaborationProvider) {
		if (!this.providers.has(provider)) return;
		// Close while the last editor is still attached so its final snapshot is sent.
		if (this.providers.size === 1) this.close();
		else this.providers.delete(provider);
	}

	private markSynced() {
		this.synced = true;
		for (const provider of this.providers) provider.revealPendingCursor();
	}

	private initializeContent(content = this.initialContent) {
		const editor = this.primary?.editor;
		if (!editor) return;

		if (typeof content === 'string') {
			content = createNodeFromContent(content, editor.schema, { slice: false }).toJSON();
		}

		const doc = prosemirrorJSONToYDoc(editor.schema, content);
		const update = Array.from(Y.encodeStateAsUpdate(doc));
		doc.destroy();
		this.socket.emit(
			'ydoc:document:update',
			{ document_id: this.documentId, update, initialize: true },
			(state: number[] | null) => {
				if (!state || !this.primary) return;
				Y.applyUpdate(this.doc, new Uint8Array(state), 'server');
				this.markSynced();
				if (!this.contentSnapshotTimer) this.sendContentSnapshot();
			}
		);
	}

	// Send the merged content; the remote sender had not seen our edits yet.
	private sendContentSnapshot() {
		this.contentSnapshotTimer = null;
		const getContent = this.primary?.getContent;
		if (!this.isConnected || !getContent) return;

		this.socket.emit('ydoc:document:update', {
			document_id: this.documentId,
			data: { content: getContent() }
		});
	}

	private join() {
		if (!this.primary) return;

		const userColor = generateUserColor();
		this.socket.emit('ydoc:document:join', {
			document_id: this.documentId,
			user_id: this.user?.id,
			user_name: this.user?.name,
			user_color: userColor
		});
		this.joined = true;

		// Set user awareness info
		if (this.user) {
			this.awareness.setLocalStateField('user', {
				name: `${this.user.name}`,
				color: userColor,
				id: this.socket.id
			});
		}
	}

	private listen(event: string, handler: (...args: any[]) => void) {
		this.listeners.push([event, handler]);
		this.socket.on(event, handler);
	}

	public async flush(provider: SocketIOCollaborationProvider) {
		await tick();
		const getContent = provider.getContent;
		if (!this.isConnected || !this.synced || !getContent) {
			throw new Error('Tab is not connected. Reconnect before leaving this tab.');
		}
		if (this.contentSnapshotTimer) {
			clearTimeout(this.contentSnapshotTimer);
			this.contentSnapshotTimer = null;
		}
		const result = await this.socket.timeout(10000).emitWithAck('ydoc:document:update', {
			document_id: this.documentId,
			flush: true,
			data: { content: getContent() }
		});
		if (!result?.ok) throw new Error(result?.error || 'Failed to save page');
	}

	private setupEventListeners() {
		// Listen for document updates from server
		this.listen('ydoc:document:update', (data) => {
			if (data.document_id === this.documentId && data.socket_id !== this.socket.id) {
				try {
					const update = new Uint8Array(data.update);
					// 'server' stops the local update listener sending this straight back out
					Y.applyUpdate(this.doc, update, 'server');

					if (this.contentSnapshotTimer) {
						clearTimeout(this.contentSnapshotTimer);
					}
					this.contentSnapshotTimer = setTimeout(() => this.sendContentSnapshot(), 500);
				} catch (error) {
					console.error('Error applying Yjs update:', error);
				}
			}
		});

		// Listen for document state from server
		this.listen('ydoc:document:state', async (data) => {
			if (data.document_id === this.documentId) {
				try {
					if (data.state) {
						const state = new Uint8Array(data.state);

						if (state.length === 2 && state[0] === 0 && state[1] === 0) {
							const editor = this.primary?.editor;
							if (
								editor &&
								!editor.getText().trim() &&
								this.doc.getXmlFragment('prosemirror').length === 0
							) {
								if (data.content || this.initialContent) {
									// The HTTP snapshot may predate the last socket save.
									this.initializeContent(
										data.content
											? data.content.json ||
													data.content.html ||
													marked.parse(data.content.md ?? '', { async: false })
											: this.initialContent
									);
									return;
								}
							} else {
								// If the editor already has content, we don't need to send an empty state
								if (this.doc.getXmlFragment('prosemirror').length > 0) {
									this.socket.emit('ydoc:document:update', {
										document_id: this.documentId,
										user_id: this.user?.id,
										socket_id: this.socket.id,
										update: Array.from(Y.encodeStateAsUpdate(this.doc))
									});
								} else {
									console.warn('Yjs document is empty, not sending state.');
								}
							}
						} else {
							Y.applyUpdate(this.doc, state, 'server');
						}
					}
					this.markSynced();
				} catch (error) {
					console.error('Error applying Yjs state:', error);

					this.synced = false;
					this.socket.emit('ydoc:document:state', {
						document_id: this.documentId
					});
				}
			}
		});

		// Listen for awareness updates
		this.listen('ydoc:awareness:update', (data) => {
			if (data.document_id === this.documentId) {
				try {
					const awarenessUpdate = new Uint8Array(data.update);
					this.awareness.applyUpdate(awarenessUpdate, 'server');
				} catch (error) {
					console.error('Error applying awareness update:', error);
				}
			}
		});

		// Handle connection events
		this.socket.on('connect', this.onConnect);
		this.socket.on('disconnect', this.onDisconnect);

		// Listen for document updates from Yjs
		this.doc.on('update', async (update, origin) => {
			if (this.primary && origin !== 'server' && this.isConnected) {
				await tick(); // Ensure the DOM is updated before sending
				const getContent = this.primary?.getContent;
				if (!getContent || !this.isConnected) return;
				this.socket.emit('ydoc:document:update', {
					document_id: this.documentId,
					user_id: this.user?.id,
					socket_id: this.socket.id,
					update: Array.from(update),
					data: { content: getContent() }
				});

				if (this.contentSnapshotTimer) {
					clearTimeout(this.contentSnapshotTimer);
					this.contentSnapshotTimer = null;
				}
			}
		});

		// Listen for awareness updates from Yjs
		this.awareness.on(
			'change',
			(
				{ added, updated, removed }: { added: number[]; updated: number[]; removed: number[] },
				origin: string
			) => {
				if (origin !== 'server' && this.isConnected) {
					const changedClients = added.concat(updated).concat(removed);
					const awarenessUpdate = this.awareness.encodeUpdate(changedClients);
					this.socket.emit('ydoc:awareness:update', {
						document_id: this.documentId,
						user_id: this.socket.id,
						update: Array.from(awarenessUpdate),
						cursor: this.awareness.getLocalState()?.cursor,
						cursor_position: (this.cursorOwner ?? this.primary)?.editor?.state.selection.head
					});
				}
			}
		);
	}

	private readonly onConnect = () => {
		this.isConnected = true;
		this.join();
	};

	private readonly onDisconnect = () => {
		this.isConnected = false;
		this.synced = false;
		this.joined = false;
	};

	private close() {
		for (const [event, handler] of this.listeners) this.socket.off(event, handler);
		this.listeners = [];
		this.socket.off('connect', this.onConnect);
		this.socket.off('disconnect', this.onDisconnect);

		if (this.contentSnapshotTimer) {
			clearTimeout(this.contentSnapshotTimer);
			this.sendContentSnapshot();
		}

		if (this.isConnected) {
			this.socket.emit('ydoc:document:leave', {
				document_id: this.documentId,
				user_id: this.user?.id
			});
		}

		DocumentSession.sessions.get(this.socket)?.delete(this.documentId);
		this.providers.clear();
		this.isConnected = false;
		this.doc.destroy();
	}
}

// One editor's view of the shared awareness. y-prosemirror clears the cursor
// whenever an unfocused editor updates, which would erase the cursor of the
// focused editor sharing this document, so only the editor that set it may clear it.
class EditorAwareness {
	constructor(
		private readonly session: DocumentSession,
		private readonly provider: SocketIOCollaborationProvider
	) {}

	get clientID() {
		return this.session.awareness.clientID;
	}

	get doc() {
		return this.session.doc;
	}

	on(event: string, handler: any) {
		this.session.awareness.on(event, handler);
	}

	off(event: string, handler: any) {
		this.session.awareness.off(event, handler);
	}

	getStates() {
		return this.session.awareness.getStates();
	}

	getLocalState() {
		return this.session.awareness.getLocalState();
	}

	setLocalStateField(field: string, value: any) {
		if (field === 'cursor') {
			if (value === null && this.session.cursorOwner !== this.provider) return;
			this.session.cursorOwner = value === null ? null : this.provider;
		}
		this.session.awareness.setLocalStateField(field, value);
	}
}

// Simple awareness implementation
class SimpleAwareness {
	public readonly clientID: number;
	private readonly _states: Map<number, any>;
	private readonly _updateHandlers: any[];
	private readonly _localState: any;

	public constructor(public readonly doc: Y.Doc) {
		// Yjs awareness expects clientID (not clientId) property
		this.clientID = doc.clientID ? doc.clientID : Math.floor(Math.random() * 0xffffffff);
		// Map from clientID (number) to state (object)
		this._states = new Map(); // _states, not states; will make getStates() for compat
		this._updateHandlers = [];
		this._localState = {};
		// As in Yjs Awareness, add our local state to the states map from the start:
		this._states.set(this.clientID, this._localState);
	}

	public on(event: string, handler: any) {
		if (event === 'change') this._updateHandlers.push(handler);
	}

	public off(event: string, handler: any) {
		if (event === 'change') {
			const i = this._updateHandlers.indexOf(handler);
			if (i !== -1) this._updateHandlers.splice(i, 1);
		}
	}

	public getLocalState() {
		return this._states.get(this.clientID) || null;
	}

	public getStates() {
		// Yjs returns a Map (clientID->state)
		return this._states;
	}

	public setLocalStateField(field: string, value: any) {
		let localState = this._states.get(this.clientID);
		if (!localState) {
			localState = {};
			this._states.set(this.clientID, localState);
		}
		localState[field] = value;
		// After updating, fire 'update' event to all handlers
		for (const cb of this._updateHandlers) {
			// Follows Yjs Awareness ({ added, updated, removed }, origin)
			cb({ added: [], updated: [this.clientID], removed: [] }, 'local');
		}
	}

	public applyUpdate(update: Uint8Array, origin: string) {
		// Very simple: Accepts a serialized JSON state for now as Uint8Array
		try {
			const str = new TextDecoder().decode(update);
			const obj = JSON.parse(str);
			// Should be a plain object: { clientID: state, ... }
			for (const [k, v] of Object.entries(obj)) {
				this._states.set(+k, v);
			}
			for (const cb of this._updateHandlers) {
				cb({ added: [], updated: Array.from(Object.keys(obj)).map(Number), removed: [] }, origin);
			}
		} catch (e) {
			console.warn('SimpleAwareness: Could not decode update:', e);
		}
	}

	public encodeUpdate(clients: number[]) {
		// Encodes the states for the given clientIDs as Uint8Array (JSON)
		const obj: Record<number, any> = {};
		for (const id of clients || Array.from(this._states.keys())) {
			const st = this._states.get(id);
			if (st) obj[id] = st;
		}
		const json = JSON.stringify(obj);
		return new TextEncoder().encode(json);
	}
}
