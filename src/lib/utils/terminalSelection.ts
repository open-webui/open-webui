import { get, type Writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { settings, terminalServers } from '$lib/stores';
import { getToolServersData } from '$lib/apis';
import { updateChatById } from '$lib/apis/chats';
import { isSavedChatId } from '$lib/utils/chatId';

type Settings = Parameters<typeof settings.set>[0];
type DirectTerminal = {
	url: string;
	key?: string;
	auth_type?: string;
	path?: string;
	enabled?: boolean;
	config?: unknown;
};

// Rebuild the direct entries of the terminal store; system terminals (with an `id`) are kept.
const refreshDirectTerminals = async (servers: DirectTerminal[]) => {
	const system = (get(terminalServers) ?? []).filter((terminal) => terminal.id);
	const active = servers.filter((server) => server.enabled);
	if (!active.length) {
		terminalServers.set(system);
		return;
	}
	const data = await getToolServersData(
		active.map((terminal) => ({
			url: terminal.url,
			auth_type: terminal.auth_type ?? 'bearer',
			key: terminal.key ?? '',
			path: terminal.path ?? '/openapi.json',
			config: { enable: true }
		}))
	);
	terminalServers.set([
		...data
			.map((item, index) => ({ item, server: active[index] }))
			.filter(({ item }) => item && !item.error)
			.map(({ item, server }) => ({
				...item,
				key: server?.key ?? '',
				config: server?.config ?? item?.config ?? {}
			})),
		...system
	]);
};

/**
 * Make `id` the chat's terminal: persist it on a saved chat, then enable only the matching
 * direct terminal. `isCurrent` lets the caller drop a selection that outlived its chat.
 */
export const selectChatTerminal = async (
	id: string | null,
	chatId: string | null,
	selectedTerminalId: Pick<Writable<string | null>, 'set'>,
	isCurrent: () => boolean = () => true
) => {
	if (isSavedChatId(chatId)) {
		try {
			await updateChatById(localStorage.token, chatId!, {
				terminal_id: id,
				working_directory: ''
			});
		} catch (error) {
			toast.error(String(error));
			return false;
		}
	}
	if (!isCurrent()) return false;
	selectedTerminalId.set(id);

	// Direct terminals live in user settings but are not part of the Settings type.
	const current = get(settings) as Settings & { terminalServers?: DirectTerminal[] };
	const servers = current?.terminalServers ?? [];
	const direct = !!id && servers.some((server) => server.url === id);
	// A system terminal only needs the direct ones switched off when any were on.
	if (!direct && !servers.some((server) => server.enabled)) return true;
	const updated = servers.map((server) => ({ ...server, enabled: direct && server.url === id }));
	settings.set({ ...current, terminalServers: updated } as Settings);
	await refreshDirectTerminals(updated);
	return true;
};
