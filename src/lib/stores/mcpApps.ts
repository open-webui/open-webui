/**
 * MCP Apps State Store.
 *
 * Manages active MCP App instances and their state.
 */

import { writable, derived, type Writable } from 'svelte/store';
import type { MCPAppInstance, MCPAppDisplayMode, MCPAppState } from '$lib/types/mcpApps';

/**
 * Store for MCP App instances.
 * Key: instanceId, Value: MCPAppInstance
 */
export const mcpApps: Writable<Map<string, MCPAppInstance>> = writable(new Map());

/**
 * Derived store: currently fullscreen app (only one allowed).
 */
export const fullscreenApp = derived(mcpApps, ($apps) => {
	for (const app of $apps.values()) {
		if (app.displayMode === 'fullscreen') {
			return app;
		}
	}
	return null;
});

/**
 * Derived store: apps in PiP mode.
 */
export const pipApps = derived(mcpApps, ($apps) => {
	return Array.from($apps.values()).filter((app) => app.displayMode === 'pip');
});

/**
 * Derived store: count of active apps (not closed/error).
 */
export const activeAppCount = derived(mcpApps, ($apps) => {
	return Array.from($apps.values()).filter(
		(app) => app.state !== 'closed' && app.state !== 'error'
	).length;
});

/**
 * Generate unique instance ID.
 */
export function generateInstanceId(): string {
	return `mcp-app-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Create a new MCP App instance.
 */
export function createAppInstance(
	params: Pick<MCPAppInstance, 'serverId' | 'toolName' | 'resource' | 'toolCallId'>
): MCPAppInstance {
	return {
		instanceId: generateInstanceId(),
		serverId: params.serverId,
		toolName: params.toolName,
		resource: params.resource,
		state: 'loading',
		displayMode: 'inline',
		height: 400,
		title: params.toolName,
		toolCallId: params.toolCallId,
		createdAt: Date.now()
	};
}

/**
 * Add a new app instance to the store.
 */
export function addApp(app: MCPAppInstance): void {
	mcpApps.update((apps) => {
		apps.set(app.instanceId, app);
		return apps;
	});
}

/**
 * Update an app instance in the store.
 */
export function updateApp(instanceId: string, updates: Partial<MCPAppInstance>): void {
	mcpApps.update((apps) => {
		const app = apps.get(instanceId);
		if (app) {
			apps.set(instanceId, { ...app, ...updates });
		}
		return apps;
	});
}

/**
 * Update app state.
 */
export function updateAppState(instanceId: string, state: MCPAppState, error?: string): void {
	updateApp(instanceId, { state, error });
}

/**
 * Update app display mode.
 */
export function updateAppDisplayMode(instanceId: string, displayMode: MCPAppDisplayMode): void {
	mcpApps.update((apps) => {
		// If setting fullscreen, clear any other fullscreen app
		if (displayMode === 'fullscreen') {
			for (const [id, app] of apps) {
				if (app.displayMode === 'fullscreen' && id !== instanceId) {
					apps.set(id, { ...app, displayMode: 'inline' });
				}
			}
		}

		const app = apps.get(instanceId);
		if (app) {
			apps.set(instanceId, { ...app, displayMode });
		}
		return apps;
	});
}

/**
 * Update app height (from size change notifications).
 */
export function updateAppHeight(instanceId: string, height: number): void {
	updateApp(instanceId, { height });
}

/**
 * Update app title.
 */
export function updateAppTitle(instanceId: string, title: string): void {
	updateApp(instanceId, { title });
}

/**
 * Remove an app instance from the store.
 */
export function removeApp(instanceId: string): void {
	mcpApps.update((apps) => {
		apps.delete(instanceId);
		return apps;
	});
}

/**
 * Close an app (mark as closed, then remove).
 */
export function closeApp(instanceId: string): void {
	updateAppState(instanceId, 'closed');
	// Optionally remove after a delay to allow cleanup
	setTimeout(() => removeApp(instanceId), 100);
}

/**
 * Get an app instance by ID.
 */
export function getApp(instanceId: string): MCPAppInstance | undefined {
	let result: MCPAppInstance | undefined;
	mcpApps.subscribe((apps) => {
		result = apps.get(instanceId);
	})();
	return result;
}

/**
 * Clear all app instances.
 */
export function clearApps(): void {
	mcpApps.set(new Map());
}
