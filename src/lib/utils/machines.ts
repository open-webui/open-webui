import type { Writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { updateChatById } from '$lib/apis/chats';
import { isSavedChatId } from '$lib/utils/chatId';

// Select a chat's machine at once, saving it to the chat in the background.
export const selectMachine = (
	selectedMachineId: Pick<Writable<string | null>, 'set'>,
	id: string | null,
	chatId: string | null
) => {
	selectedMachineId.set(id);
	// New chats start on the last pick.
	if (id) localStorage.selectedMachineId = id;
	else delete localStorage.selectedMachineId;
	if (isSavedChatId(chatId))
		updateChatById(localStorage.token, chatId!, { machine_id: id, working_directory: '' }).catch(
			(error) => toast.error(String(error))
		);
};

// Machines were called terminals, and saved data and older servers can still use the old names.
// Write the new names and read both:
//   machine_id / machineId    ← terminal_id / terminalId
//   owned_by / skill source   'machine' ← 'terminal'
//   skill and tool ids        'machine:' ← 'terminal:'
//   automation data.machine   ← data.terminal
//   settings machineFileDisplay, machinePreviewAllowSameOrigin ← terminal*
//   events 'machine:*' ← 'terminal:*'

type Dict = Record<string, any> | null | undefined;

/** A present current key wins, even when empty, so clearing a machine is not undone by a stale old key. */
export const machineIdOf = (data: Dict): string | undefined =>
	(data ? ('machine_id' in data ? data.machine_id : data.terminal_id) : undefined) || undefined;

export const metaMachineIdOf = (meta: Dict): string | undefined =>
	(meta ? ('machineId' in meta ? meta.machineId : meta.terminalId) : undefined) || undefined;

export const isMachine = (value: unknown): boolean => value === 'machine' || value === 'terminal';

export const isMachineRef = (id: unknown): id is string =>
	typeof id === 'string' && (id.startsWith('machine:') || id.startsWith('terminal:'));

export const automationMachineOf = (data: Dict): { server_id?: string; cwd?: string } | undefined =>
	data?.machine ?? data?.terminal ?? undefined;

/** Returns the object with a former terminalId moved onto machineId (saved panel tabs). */
export const normalizeMetaMachineId = <T extends Dict>(data: T): T => {
	if (data && 'terminalId' in data) {
		const { terminalId, ...rest } = data as Record<string, any>;
		return { machineId: terminalId, ...rest } as unknown as T;
	}
	return data;
};

/** Saved chat views name the selected machine selectedTerminalId. */
export const normalizeViewMachineId = <T extends Dict>(state: T): T => {
	if (state && 'selectedTerminalId' in state) {
		const { selectedTerminalId, ...rest } = state as Record<string, any>;
		return { selectedMachineId: selectedTerminalId, ...rest } as unknown as T;
	}
	return state;
};

/** Machine events were sent as terminal:*. Returns the event name without either prefix. */
export const machineEventName = (type: string): string | null =>
	isMachineRef(type) ? type.slice(type.indexOf(':') + 1) : null;
