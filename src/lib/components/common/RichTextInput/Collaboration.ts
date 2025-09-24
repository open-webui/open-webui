import * as Y from 'yjs';
import {
	ySyncPlugin,
	yCursorPlugin,
	yUndoPlugin,
	undo,
	redo,
	prosemirrorJSONToYDoc
} from 'y-prosemirror';
import type { Socket } from 'socket.io-client';
import type { Awareness } from 'y-protocols/awareness';
import type { SessionUser } from '$lib/stores';
import { Editor, Extension } from '@tiptap/core';
import { keymap } from 'prosemirror-keymap';
import { tick } from 'svelte';

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
	json: string;
};

// Custom Yjs Socket.IO provider
export class SocketIOCollaborationProvider {
	private readonly doc = new Y.Doc();
	private readonly awareness = new SimpleAwareness(this.doc);
	private isConnected = false;
	private synced = false;
	private editor: Editor | null = null;
	private editorContentGetter: EditorContentGetter | null = null;

	constructor(
		private readonly documentId: string,
		private readonly socket: Socket,
		private readonly user: SessionUser,
		private readonly initialContent: string | null = null
	) {
		this.setupEventListeners();
	}

	public getEditorExtension() {
		return Extension.create({
			name: 'yjsCollaboration',

			addProseMirrorPlugins: () => {
				const yXmlFragment = this.doc.getXmlFragment('prosemirror');
				if (!yXmlFragment) return [];

				const plugins = [
					ySyncPlugin(yXmlFragment),
					yUndoPlugin(),
					keymap({
						'Mod-z': undo,
						'Mod-y': redo,
						'Mod-Shift-z': redo
					})
				];

				plugins.push(yCursorPlugin(this.awareness as unknown as Awareness));

				return plugins;
			}
		});
	}

	public setEditor(editor: Editor, editorContentGetter: EditorContentGetter) {
		this.editor = editor;
		this.editorContentGetter = editorContentGetter;
	}

	private joinDocument() {
		const userColor = generateUserColor();
		this.socket.emit('ydoc:document:join', {
			document_id: this.documentId,
			user_id: this.user?.id,
			user_name: this.user?.name,
			user_color: userColor
		});

		// Set user awareness info
		if (this.user) {
			this.awareness.setLocalStateField('user', {
				name: `${this.user.name}`,
				color: userColor,
				id: this.socket.id
			});
		}
	}

	private setupEventListeners() {
		// Listen for document updates from server
		this.socket.on('ydoc:document:update', (data) => {
			if (data.document_id === this.documentId && data.socket_id !== this.socket.id) {
				try {
					const update = new Uint8Array(data.update);
					Y.applyUpdate(this.doc, update);
				} catch (error) {
					console.error('Error applying Yjs update:', error);
				}
			}
		});

		// Listen for document state from server
		this.socket.on('ydoc:document:state', async (data) => {
			if (data.document_id === this.documentId) {
				try {
					if (data.state) {
						const state = new Uint8Array(data.state);

						if (state.length === 2 && state[0] === 0 && state[1] === 0) {
							// Empty state, check if we have content to initialize
							// check if editor empty as well
							// const editor = await getEditorInstance();

							const isEmptyEditor = !this.editor?.getText().trim();
							if (isEmptyEditor && this.editor) {
								if (this.initialContent && (data?.sessions ?? ['']).length === 1) {
									const editorYdoc = prosemirrorJSONToYDoc(this.editor.schema, this.initialContent);
									if (editorYdoc) {
										Y.applyUpdate(this.doc, Y.encodeStateAsUpdate(editorYdoc));
									}
								}
							} else {
								// If the editor already has content, we don't need to send an empty state
								if (this.doc.getXmlFragment('prosemirror').length > 0) {
									this.socket.emit('ydoc:document:update', {
										document_id: this.documentId,
										user_id: this.user?.id,
										socket_id: this.socket.id,
										update: Y.encodeStateAsUpdate(this.doc)
									});
								} else {
									console.warn('Yjs document is empty, not sending state.');
								}
							}
						} else {
							Y.applyUpdate(this.doc, state, 'server');
						}
					}
					this.synced = true;
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
		this.socket.on('ydoc:awareness:update', (data) => {
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
			if (this.editor && origin !== 'server' && this.isConnected) {
				await tick(); // Ensure the DOM is updated before sending
				this.socket.emit('ydoc:document:update', {
					document_id: this.documentId,
					user_id: this.user?.id,
					socket_id: this.socket.id,
					update: Array.from(update),
					data: {
						content: this.editorContentGetter?.() ?? {
							md: '',
							html: '',
							json: ''
						}
					}
				});
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
						update: Array.from(awarenessUpdate)
					});
				}
			}
		);

		if (this.socket.connected) {
			this.isConnected = true;
			this.joinDocument();
		}
	}

	private readonly onConnect = () => {
		this.isConnected = true;
		this.joinDocument();
	};

	private readonly onDisconnect = () => {
		this.isConnected = false;
		this.synced = false;
	};

	public destroy() {
		this.socket.off('ydoc:document:update');
		this.socket.off('ydoc:document:state');
		this.socket.off('ydoc:awareness:update');
		this.socket.off('connect', this.onConnect);
		this.socket.off('disconnect', this.onDisconnect);

		if (this.isConnected) {
			this.socket.emit('ydoc:document:leave', {
				document_id: this.documentId,
				user_id: this.user?.id
			});
		}

		this.editor = null;
		this.editorContentGetter = null;
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
