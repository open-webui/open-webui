/**
 * Vitest setup file for Mermaid tests
 * 
 * Sets up browser environment mocks for IndexedDB, BroadcastChannel, and other browser APIs
 */

import { beforeEach, afterEach, vi } from 'vitest';

// Mock IndexedDB
class MockIDBDatabase {
	objectStoreNames = {
		contains: vi.fn(() => false),
		length: 0
	};
	transaction = vi.fn(() => ({
		objectStore: vi.fn(() => ({
			get: vi.fn(() => ({
				onsuccess: null,
				onerror: null,
				result: null
			})),
			put: vi.fn(() => ({
				onsuccess: null,
				onerror: null
			})),
			delete: vi.fn(() => ({
				onsuccess: null,
				onerror: null
			})),
			clear: vi.fn(() => ({
				onsuccess: null,
				onerror: null
			})),
			index: vi.fn(() => ({
				openCursor: vi.fn(() => ({
					onsuccess: null,
					onerror: null
				}))
			}))
		}))
	}));
	close = vi.fn();
}

class MockIDBRequest {
	result: any = null;
	error: any = null;
	onsuccess: ((event: Event) => void) | null = null;
	onerror: ((event: Event) => void) | null = null;
	onupgradeneeded: ((event: Event) => void) | null = null;
}

const mockIndexedDB = {
	open: vi.fn((name: string, version?: number) => {
		const request = new MockIDBRequest();
		setTimeout(() => {
			if (request.onsuccess) {
				request.result = new MockIDBDatabase();
				request.onsuccess({} as Event);
			}
		}, 0);
		return request;
	}),
	deleteDatabase: vi.fn(() => ({
		onsuccess: null,
		onerror: null
	}))
};

// Mock BroadcastChannel
class MockBroadcastChannel {
	name: string;
	onmessage: ((event: MessageEvent) => void) | null = null;
	onerror: ((event: Event) => void) | null = null;
	private static channels = new Map<string, MockBroadcastChannel[]>();

	constructor(name: string) {
		this.name = name;
		if (!MockBroadcastChannel.channels.has(name)) {
			MockBroadcastChannel.channels.set(name, []);
		}
		MockBroadcastChannel.channels.get(name)!.push(this);
	}

	postMessage(message: any) {
		const channels = MockBroadcastChannel.channels.get(this.name) || [];
		channels.forEach((channel: MockBroadcastChannel) => {
			if (channel !== this && channel.onmessage) {
				setTimeout(() => {
					channel.onmessage!({
						data: message,
						origin: 'test',
						source: null
					} as MessageEvent);
				}, 0);
			}
		});
	}

	close() {
		const channels = MockBroadcastChannel.channels.get(this.name) || [];
		const index = channels.indexOf(this);
		if (index > -1) {
			channels.splice(index, 1);
		}
	}

	static clear() {
		MockBroadcastChannel.channels.clear();
	}
}

// Mock IntersectionObserver
class MockIntersectionObserver implements IntersectionObserver {
	readonly root: Element | null = null;
	readonly rootMargin: string = '';
	readonly thresholds: ReadonlyArray<number> = [];
	callback: IntersectionObserverCallback;
	options?: IntersectionObserverInit;
	observedElements: Element[] = [];

	constructor(callback: IntersectionObserverCallback, options?: IntersectionObserverInit) {
		this.callback = callback;
		this.options = options;
	}

	observe(element: Element): void {
		this.observedElements.push(element);
		// Simulate immediate intersection
		setTimeout(() => {
			this.callback(
				[
					{
						target: element,
						isIntersecting: true,
						intersectionRatio: 1,
						boundingClientRect: {} as DOMRectReadOnly,
						intersectionRect: {} as DOMRectReadOnly,
						rootBounds: null,
						time: Date.now()
					}
				],
				this
			);
		}, 0);
	}

	unobserve(element: Element): void {
		const index = this.observedElements.indexOf(element);
		if (index > -1) {
			this.observedElements.splice(index, 1);
		}
	}

	disconnect(): void {
		this.observedElements = [];
	}

	takeRecords(): IntersectionObserverEntry[] {
		return [];
	}
}

// Setup global mocks
beforeEach(() => {
	// Mock browser environment
	(globalThis as any).window = (globalThis as any).window || {};
	(globalThis as any).document = (globalThis as any).document || {
		documentElement: {
			classList: {
				contains: vi.fn(() => false),
				add: vi.fn(),
				remove: vi.fn()
			}
		},
		createElement: vi.fn(() => ({
			classList: { add: vi.fn(), remove: vi.fn() },
			innerHTML: '',
			textContent: ''
		})),
		querySelector: vi.fn(),
		querySelectorAll: vi.fn(() => []),
		getElementById: vi.fn()
	} as any;

	// Mock IndexedDB
	(globalThis as any).indexedDB = mockIndexedDB as any;

	// Mock BroadcastChannel
	(globalThis as any).BroadcastChannel = MockBroadcastChannel as any;

	// Mock IntersectionObserver
	(globalThis as any).IntersectionObserver = MockIntersectionObserver as any;

	// Mock performance API
	(globalThis as any).performance = {
		now: vi.fn(() => Date.now())
	} as any;

	// Mock console methods to reduce noise in tests
	(globalThis as any).console = {
		...console,
		log: vi.fn(),
		warn: vi.fn(),
		error: vi.fn()
	};
});

afterEach(() => {
	MockBroadcastChannel.clear();
	vi.clearAllMocks();
});

