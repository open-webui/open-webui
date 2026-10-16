import type { Socket } from 'socket.io-client';
import type { SessionUser } from '$lib/stores';
import { writable } from 'svelte/store';
import CryptoWorker from './worker?worker';

export type Identity = { channel: string; session: string; user: string; participation: string };
type Binding = { identity: Identity; key: string };
type Member = { identity: Identity; fingerprint: string; name: string };
type Message = {
	id: string;
	type?: 'joined';
	sender: string;
	user: { id: string; name: string };
	created_at: number;
	text: string;
	expected: string[];
	received: string[];
	relayed: boolean;
};
type View = {
	channel: string;
	session: string;
	host: string;
	participation?: string;
	bindings: Binding[];
	participants: { participation: string; user: string; name: string }[];
};
export type State = {
	status: 'joining' | 'active' | 'ended';
	messages: Message[];
	members: Member[];
	typing: string[];
	self: string;
	host: string;
};
type Entry = { action: 'start' } | { action: 'join'; session: string };
let entry: { channel: string; intent: Entry } | undefined;
export function enter(channel: string, intent: Entry) {
	entry = { channel, intent };
}
export function consumeEntry(channel: string) {
	const result = entry?.channel === channel ? entry.intent : undefined;
	entry = undefined;
	return result;
}
export function canUseEncryption(
	account: SessionUser | undefined,
	features: { enable_channels?: boolean; enable_encrypted_channels?: boolean } | undefined
): boolean {
	return !!(
		features?.enable_channels &&
		features?.enable_encrypted_channels &&
		(account?.role === 'admin' ||
			(account?.role === 'user' &&
				account.permissions?.features?.channels === true &&
				account.permissions?.features?.encrypted_channels === true))
	);
}
export function connected(socket: Socket | null): socket is Socket {
	return !!socket?.connected && socket.io.engine?.transport?.name === 'websocket';
}
export function request(socket: Socket, action: string, data: object): Promise<any> {
	return new Promise((resolve, reject) => {
		if (!connected(socket) || !socket.io.engine.transport.writable)
			return reject(new Error('Encrypted chat is unavailable.'));
		// Volatile sends are never put into Socket.IO's disconnected send buffer.
		socket
			.timeout(10000)
			.volatile.emit(`encryption:${action}`, data, (error: unknown, result: any) => {
				if (error || !result?.ok) reject(new Error('Encrypted chat ended.'));
				else resolve(result);
			});
	});
}

export class Conversation {
	state = writable<State>({
		status: 'joining',
		messages: [],
		members: [],
		typing: [],
		self: '',
		host: ''
	});
	private current: State = {
		status: 'joining',
		messages: [],
		members: [],
		typing: [],
		self: '',
		host: ''
	};
	private worker: Worker;
	private pending = new Map<
		number,
		{ resolve: (result: any) => void; reject: () => void; timer: ReturnType<typeof setTimeout> }
	>();
	private nextId = 0;
	private sequence = 0;
	private stopped = false;
	private chain: Promise<unknown> = Promise.resolve();
	private view?: View;
	private participation = '';
	private timer?: ReturnType<typeof setInterval>;
	private joinTimer?: ReturnType<typeof setTimeout>;
	private messageIds = new Set<string>();
	private lastTyping?: number;
	private typingTimers = new Map<string, ReturnType<typeof setTimeout>>();
	private disposers: (() => void)[] = [];

	constructor(
		private socket: Socket,
		private channel: string,
		private user: string,
		intent: Entry
	) {
		this.worker = new CryptoWorker();
		this.worker.onmessage = ({ data }) => {
			const pending = this.pending.get(data.id);
			if (!pending || this.stopped) return;
			clearTimeout(pending.timer);
			this.pending.delete(data.id);
			if (data.error) {
				pending.reject();
				this.close();
			} else pending.resolve(data.result);
		};
		this.worker.onerror = (event) => {
			event.preventDefault();
			this.close();
		};
		this.worker.onmessageerror = () => this.close();
		const receive = (event: any) => {
			if (
				event?.channel !== this.channel ||
				(event.session && event.session !== this.view?.session)
			)
				return;
			if (event.kind === 'ended') {
				this.close();
				return;
			}
			this.enqueue(() => this.receive(event));
		};
		const end = () => this.close();
		socket.on('encryption:event', receive);
		socket.on('disconnect', end);
		socket.on('access:updated', end);
		window.addEventListener('pagehide', end);
		window.addEventListener('beforeunload', end);
		document.addEventListener('freeze', end);
		this.disposers.push(() => {
			socket.off('encryption:event', receive);
			socket.off('disconnect', end);
			socket.off('access:updated', end);
			window.removeEventListener('pagehide', end);
			window.removeEventListener('beforeunload', end);
			document.removeEventListener('freeze', end);
		});
		this.joinTimer = setTimeout(end, 30000);
		this.enqueue(async () => {
			if (!window.isSecureContext || !connected(socket)) throw new Error();
			const result = await request(socket, intent.action, { channel, ...intent });
			if (this.stopped) {
				void request(socket, 'leave', {
					channel,
					session: result.session,
					participation: result.participation
				}).catch(() => {});
				return;
			}
			this.view = result;
			this.participation = result.participation;
			const identity: Identity = {
				channel,
				session: result.session,
				user,
				participation: this.participation
			};
			await this.crypto('init', JSON.stringify(identity), result.host);
			if (intent.action === 'start') await this.crypto('create');
			const key = await this.crypto('public_key');
			const packet = intent.action === 'join' ? await this.crypto('key_package') : undefined;
			this.view = await this.send('bind', { key, packet });
			this.update({ self: this.participation, host: result.host });
			if (intent.action === 'start') await this.activate();
			if (this.stopped) return;
			this.timer = setInterval(
				() =>
					this.enqueue(async () => {
						await this.send('ping', {});
					}),
				15000
			);
		});
	}

	private update(patch: Partial<State>) {
		if (this.stopped) return;
		if (patch.messages) {
			let bytes = patch.messages.reduce(
				(n, m) => n + new TextEncoder().encode(JSON.stringify(m)).length,
				0
			);
			patch.messages = [...patch.messages];
			while (patch.messages.length > 500 || bytes > 8 * 1024 * 1024) {
				bytes -= new TextEncoder().encode(JSON.stringify(patch.messages.shift()!)).length;
			}
		}
		this.current = { ...this.current, ...patch };
		this.state.set(this.current);
	}
	private enqueue(operation: () => Promise<void>) {
		this.chain = this.chain
			.then(async () => {
				if (!this.stopped) await operation();
			})
			.catch(() => this.close());
		return this.chain;
	}
	private crypto(method: string, ...args: unknown[]): Promise<any> {
		if (this.stopped) return Promise.reject(new Error());
		return new Promise((resolve, reject) => {
			const id = ++this.nextId;
			const fail = () => reject(new Error('Encrypted chat ended.'));
			this.pending.set(id, {
				resolve,
				reject: fail,
				timer: setTimeout(() => {
					fail();
					this.close();
				}, 30000)
			});
			this.worker.postMessage({ id, method, args });
		});
	}
	private async send(action: string, data: object) {
		if (this.stopped || !this.view) throw new Error();
		const result = await request(this.socket, action, {
			...data,
			channel: this.channel,
			session: this.view.session,
			participation: this.participation
		});
		if (this.stopped) throw new Error();
		return result as View;
	}
	private async members() {
		const members: Member[] = JSON.parse(await this.crypto('members'));
		if (this.stopped) return;
		const previous = new Set(this.current.members.map((m) => m.identity.participation));
		for (const id of this.current.typing) {
			if (!members.some((m) => m.identity.participation === id)) this.removeTyping(id);
		}
		this.update({
			members: members.map((m) => ({
				...m,
				name:
					this.view?.participants.find((p) => p.participation === m.identity.participation)?.name ??
					'Participant'
			}))
		});
		if (this.current.status === 'active') {
			for (const member of this.current.members) {
				if (previous.has(member.identity.participation)) continue;
				this.append({
					id: crypto.randomUUID(),
					type: 'joined',
					sender: member.identity.participation,
					text: '',
					expected: [],
					received: [],
					relayed: true
				});
			}
		}
	}
	private async activate() {
		clearTimeout(this.joinTimer);
		await this.members();
		this.update({ status: 'active' });
	}
	private async receive(event: any) {
		if (!this.view || event.session !== this.view.session || event.sequence !== this.sequence + 1)
			throw new Error();
		this.sequence = event.sequence;
		this.view = event;
		const bindings = JSON.stringify(event.bindings);
		if (event.kind === 'candidate') {
			const added = JSON.parse(await this.crypto('add', event.packet, event.sender, bindings));
			this.view = await this.send('packet', {
				kind: 'admit',
				target: event.sender,
				packet: added.commit,
				welcome: added.welcome
			});
			await this.members();
		} else if (event.kind === 'welcome') {
			if (event.sender !== event.host || this.current.status !== 'joining') throw new Error();
			await this.crypto('join', event.packet, bindings);
			await this.activate();
		} else if (event.kind === 'departed') {
			this.removeTyping(event.participation);
			if (event.admitted && this.participation === event.host) {
				const packet = await this.crypto('remove', event.participation, bindings);
				await this.send('packet', { kind: 'mls', packet });
				await this.members();
			}
		} else if (event.kind === 'mls') {
			const result = JSON.parse(await this.crypto('process', event.packet, event.sender, bindings));
			if (result.kind === 'application') await this.application(result.sender, result.text);
			else if (result.kind === 'proposal' && this.participation === event.host) {
				const packet = await this.crypto('commit_updates');
				await this.send('packet', { kind: 'mls', packet });
				await this.members();
			} else if (result.kind === 'commit') await this.members();
		} else throw new Error();
	}
	private append(message: Omit<Message, 'user' | 'created_at'>) {
		const sender = this.current.members.find(
			(member) => member.identity.participation === message.sender
		);
		this.update({
			messages: [
				...this.current.messages,
				{
					...message,
					user: { id: sender?.identity.user ?? '', name: sender?.name ?? 'Participant' },
					created_at: Date.now() * 1000000
				}
			]
		});
	}
	private async application(sender: Identity, text: string) {
		const data = JSON.parse(text);
		if (
			data.session !== this.view?.session ||
			data.channel !== this.channel ||
			typeof data.id !== 'string' ||
			!/^[a-f0-9-]{36}$/.test(data.id)
		)
			throw new Error();
		if (data.type === 'typing') {
			if (typeof data.typing !== 'boolean') throw new Error();
			const id = sender.participation;
			if (
				id === this.participation ||
				!this.current.members.some((m) => m.identity.participation === id)
			)
				return;
			if (data.typing) {
				clearTimeout(this.typingTimers.get(id));
				this.typingTimers.set(
					id,
					setTimeout(() => this.removeTyping(id), 5000)
				);
				if (!this.current.typing.includes(id))
					this.update({ typing: [...this.current.typing, id] });
			} else this.removeTyping(id);
		} else if (data.type === 'receipt') {
			const messages = this.current.messages.map((m) =>
				m.id === data.id &&
				m.sender === this.participation &&
				m.expected.includes(sender.participation)
					? { ...m, received: [...new Set([...m.received, sender.participation])] }
					: m
			);
			this.update({ messages });
		} else if (data.type === 'text') {
			if (
				typeof data.text !== 'string' ||
				new TextEncoder().encode(data.text).length > 16384 ||
				this.messageIds.has(data.id)
			)
				throw new Error();
			this.messageIds.add(data.id);
			this.removeTyping(sender.participation);
			// MLS rejects replay; the bounded ID set additionally rejects repeated app envelopes.
			if (this.messageIds.size > 1000)
				this.messageIds.delete(this.messageIds.values().next().value!);
			this.append({
				id: data.id,
				sender: sender.participation,
				text: data.text,
				expected: [],
				received: [],
				relayed: true
			});
			const packet = await this.crypto(
				'encrypt',
				JSON.stringify({
					type: 'receipt',
					id: data.id,
					channel: this.channel,
					session: this.view!.session
				})
			);
			await this.send('packet', { kind: 'mls', packet });
		} else throw new Error();
	}
	private removeTyping(id: string) {
		clearTimeout(this.typingTimers.get(id));
		this.typingTimers.delete(id);
		if (this.current.typing.includes(id))
			this.update({ typing: this.current.typing.filter((participant) => participant !== id) });
	}
	sendTyping(typing: boolean) {
		if (this.current.status !== 'active') return;
		const now = Date.now();
		if (
			typing
				? this.lastTyping !== undefined && now - this.lastTyping < 2000
				: this.lastTyping === undefined
		)
			return;
		this.lastTyping = typing ? now : undefined;
		return this.enqueue(async () => {
			const packet = await this.crypto(
				'encrypt',
				JSON.stringify({
					type: 'typing',
					id: crypto.randomUUID(),
					typing,
					channel: this.channel,
					session: this.view!.session
				})
			);
			await this.send('packet', { kind: 'mls', packet });
		});
	}
	sendText(text: string) {
		if (
			this.current.status !== 'active' ||
			!text.trim() ||
			new TextEncoder().encode(text).length > 16384
		)
			return;
		this.sendTyping(false);
		return this.enqueue(async () => {
			const id = crypto.randomUUID();
			const expected = this.current.members
				.map((m) => m.identity.participation)
				.filter((p) => p !== this.participation);
			this.append({ id, sender: this.participation, text, expected, received: [], relayed: false });
			const packet = await this.crypto(
				'encrypt',
				JSON.stringify({
					type: 'text',
					id,
					text,
					channel: this.channel,
					session: this.view!.session
				})
			);
			await this.send('packet', { kind: 'mls', packet });
			this.update({
				messages: this.current.messages.map((m) => (m.id === id ? { ...m, relayed: true } : m))
			});
		});
	}
	updateKeys() {
		return this.enqueue(async () => {
			const packet = await this.crypto('update');
			await this.send('packet', { kind: 'mls', packet });
		});
	}
	close() {
		if (this.stopped) return;
		this.stopped = true;
		clearInterval(this.timer);
		clearTimeout(this.joinTimer);
		this.disposers.splice(0).forEach((dispose) => dispose());
		this.worker.terminate();
		for (const pending of this.pending.values()) {
			clearTimeout(pending.timer);
			pending.reject();
		}
		this.pending.clear();
		this.messageIds.clear();
		for (const timer of this.typingTimers.values()) clearTimeout(timer);
		this.typingTimers.clear();
		this.lastTyping = undefined;
		if (this.view && this.participation && connected(this.socket)) {
			void request(this.socket, 'leave', {
				channel: this.channel,
				session: this.view.session,
				participation: this.participation
			}).catch(() => {});
		}
		this.view = undefined;
		this.current = { status: 'ended', messages: [], members: [], typing: [], self: '', host: '' };
		this.state.set(this.current);
	}
}
