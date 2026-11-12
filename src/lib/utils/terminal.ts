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

// Reload direct terminals into the store, keeping system terminals (those with an `id`).
const refreshDirectTerminals = async (servers: DirectTerminal[]) => {
	const systemTerminals = (get(terminalServers) ?? []).filter((terminal) => terminal.id);
	const enabled = servers.filter((server) => server.enabled);
	if (!enabled.length) {
		terminalServers.set(systemTerminals);
		return;
	}
	const data = await getToolServersData(
		enabled.map((server) => ({
			url: server.url,
			auth_type: server.auth_type ?? 'bearer',
			key: server.key ?? '',
			path: server.path ?? '/openapi.json',
			config: { enable: true }
		}))
	);
	terminalServers.set([
		...data.flatMap((item, i) =>
			item && !item.error
				? [{ ...item, key: enabled[i].key ?? '', config: enabled[i].config ?? item.config ?? {} }]
				: []
		),
		...systemTerminals
	]);
};

// Select a chat's terminal at once, saving it to the chat in the background.
export const selectTerminal = (
	selectedTerminalId: Pick<Writable<string | null>, 'set'>,
	id: string | null,
	chatId: string | null
) => {
	selectedTerminalId.set(id);
	if (isSavedChatId(chatId))
		updateChatById(localStorage.token, chatId!, { terminal_id: id, working_directory: '' }).catch(
			(error) => toast.error(String(error))
		);

	// Direct terminals live in settings, outside the Settings type; only the selected one stays enabled.
	const current = get(settings) as Settings & { terminalServers?: DirectTerminal[] };
	const servers = current?.terminalServers ?? [];
	const isDirect = !!id && servers.some((server) => server.url === id);
	if (!isDirect && !servers.some((server) => server.enabled)) return;
	const updated = servers.map((server) => ({ ...server, enabled: isDirect && server.url === id }));
	settings.set({ ...current, terminalServers: updated } as Settings);
	void refreshDirectTerminals(updated);
};
