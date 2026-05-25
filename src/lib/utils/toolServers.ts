import { get } from 'svelte/store';

import { getToolServersData } from '$lib/apis';
import { settings, toolServers, toolServersLoaded, user } from '$lib/stores';

type LoadToolServersOptions = {
	force?: boolean;
	useCache?: boolean;
	onError?: (data: any) => void;
};

let loadPromise: Promise<any[]> | null = null;
let loadSequence = 0;

export const hasEnabledToolServers = (servers: any[] = []) =>
	servers.some((server) => server?.config?.enable);

const getToolServersLoadKey = (servers: any[] = [], userId: string | null = null) =>
	JSON.stringify({
		userId,
		servers: servers
			.filter((server) => server?.config?.enable)
			.map((server) => ({
				id: server?.id ?? '',
				url: server?.url ?? '',
				path: server?.path ?? '',
				spec_type: server?.spec_type ?? 'url',
				spec: server?.spec_type === 'json' ? (server?.spec ?? '') : '',
				auth_type: server?.auth_type ?? 'bearer',
				has_key: Boolean(server?.key)
			}))
	});

let loadPromiseKey = '';

export const loadToolServers = async ({
	force = false,
	useCache = true,
	onError
}: LoadToolServersOptions = {}) => {
	const servers = get(settings)?.toolServers ?? [];
	const userId = get(user)?.id ?? null;
	const loadKey = getToolServersLoadKey(servers, userId);

	if (!hasEnabledToolServers(servers)) {
		toolServers.set([]);
		toolServersLoaded.set(true);
		return [];
	}

	if (loadPromise && loadPromiseKey === loadKey && !force) {
		return loadPromise;
	}

	const sequence = ++loadSequence;
	loadPromiseKey = loadKey;
	toolServersLoaded.set(false);

	const promise = (async () => {
		try {
			const toolServersData = await getToolServersData(servers, {
				cacheUserId: userId,
				force,
				useCache
			});

			const availableToolServers = toolServersData.filter((data) => {
				if (!data || data.error) {
					onError?.(data);
					return false;
				}

				return true;
			});

			if (sequence === loadSequence) {
				toolServers.set(availableToolServers);
				toolServersLoaded.set(true);
			}

			return availableToolServers;
		} catch (e) {
			if (sequence === loadSequence) {
				toolServersLoaded.set(true);
			}
			throw e;
		}
	})();
	loadPromise = promise;

	try {
		return await promise;
	} finally {
		if (loadPromise === promise) {
			loadPromise = null;
		}
	}
};
