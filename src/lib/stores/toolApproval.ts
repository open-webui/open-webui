import { writable, derived, get } from 'svelte/store';
import type { Writable } from 'svelte/store';


export interface ToolApprovalRequest {
    approval_id: string;
    tool_id: string;
    tool_name: string;
    tool_params: Record<string, any>;
    parent_tool_id: string;
}


export interface ToolApprovalData {
    chat_id: string;
    message_id: string;
    tools: ToolApprovalRequest[];
    timestamp: number;
}

// { parent_tool_id: [function_names...] } where ["*"] means parent-level approval
export type AlwaysApprovedMap = Record<string, string[]>;


export const pendingApprovals: Writable<ToolApprovalData | null> = writable(null);
export const showApprovalModal = writable(false);

export const remainingTools = derived(
    pendingApprovals,
    $pendingApprovals => $pendingApprovals?.tools.length || 0
);


// ---- Helpers to get a socket ref ----

async function getSocket() {
    const { socket } = await import('$lib/stores');
    return get(socket);
}


// ---- Always-approved CRUD via socket ----

export async function addAlwaysApproved(
    chatId: string,
    parentToolId: string,
    functionName: string,
    level: 'function' | 'parent' = 'function'
): Promise<AlwaysApprovedMap | null> {
    try {
        const $socket = await getSocket();
        if (!$socket) return null;

        const response = await $socket.emitWithAck('tool:add_always_approved', {
            chat_id: chatId,
            parent_tool_id: parentToolId,
            function_name: functionName,
            level
        });

        if (response.status === 'success') {
            return response.always_approved;
        }
        return null;
    } catch {
        return null;
    }
}

export async function removeAlwaysApproved(
    chatId: string,
    parentToolId: string,
    functionName: string,
    level: 'function' | 'parent' = 'function'
): Promise<AlwaysApprovedMap | null> {
    try {
        const $socket = await getSocket();
        if (!$socket) return null;

        const response = await $socket.emitWithAck('tool:remove_always_approved', {
            chat_id: chatId,
            parent_tool_id: parentToolId,
            function_name: functionName,
            level
        });

        if (response.status === 'success') {
            return response.always_approved;
        }
        return null;
    } catch {
        return null;
    }
}

export async function getAlwaysApproved(chatId: string): Promise<AlwaysApprovedMap> {
    try {
        const $socket = await getSocket();
        if (!$socket) return {};

        const response = await $socket.emitWithAck('tool:get_always_approved', {
            chat_id: chatId
        });

        if (response.status === 'success') {
            return response.always_approved;
        }
        return {};
    } catch {
        return {};
    }
}

export async function clearAllAlwaysApproved(chatId: string): Promise<boolean> {
    try {
        const $socket = await getSocket();
        if (!$socket) return false;

        const response = await $socket.emitWithAck('tool:clear_always_approved', {
            chat_id: chatId
        });

        return response.status === 'success';
    } catch {
        return false;
    }
}


// ---- Approval request handling ----

/**
 * The backend now handles auto-approval checks server-side via should_auto_approve().
 * Tools that arrive here have already passed through the backend filter,
 * so they genuinely need user approval. Just show the modal.
 */
export async function setApprovalRequest(data: ToolApprovalData) {
    if (!data.tools || data.tools.length === 0) return;

    pendingApprovals.set({
        ...data,
        timestamp: Date.now()
    });
    showApprovalModal.set(true);
}


export function removeToolFromPending(approval_id: string) {
    pendingApprovals.update(data => {
        if (!data) return null;

        const filteredTools = data.tools.filter(t => t.approval_id !== approval_id);

        if (filteredTools.length === 0) {
            showApprovalModal.set(false);
            return null;
        }

        return {
            ...data,
            tools: filteredTools
        };
    });
}


export function clearApprovals() {
    pendingApprovals.set(null);
    showApprovalModal.set(false);
}


export function checkPendingApprovals(chatId: string) {
    if (!chatId) return;

    import('$lib/stores').then(({ socket }) => {
        const $socket = get(socket);
        if ($socket) {
            $socket.emit('tool:check_pending', {
                chat_id: chatId
            });
        }
    });
}


export async function handlePendingFound(data: ToolApprovalData) {
    if (!data.tools || data.tools.length === 0) return;

    pendingApprovals.set({
        ...data,
        timestamp: Date.now()
    });
    showApprovalModal.set(true);
}


// ---- YOLO mode via socket ----

export interface YoloStatus {
    yolo_all: boolean;
    yolo_functions: Record<string, string[]>;
}

export async function setYolo(
    chatId: string,
    level: 'all' | 'parent' | 'function',
    enabled: boolean,
    parentToolId: string = '',
    functionName: string = ''
): Promise<YoloStatus | null> {
    try {
        const $socket = await getSocket();
        if (!$socket) return null;

        const response = await $socket.emitWithAck('tool:set_yolo', {
            chat_id: chatId,
            level,
            enabled,
            parent_tool_id: parentToolId,
            function_name: functionName
        });

        if (response.status === 'success') {
            return response.yolo;
        }
        return null;
    } catch {
        return null;
    }
}

export async function getYoloStatus(chatId: string): Promise<YoloStatus> {
    try {
        const $socket = await getSocket();
        if (!$socket) return { yolo_all: false, yolo_functions: {} };

        const response = await $socket.emitWithAck('tool:get_yolo', {
            chat_id: chatId
        });

        if (response.status === 'success') {
            return response.yolo;
        }
        return { yolo_all: false, yolo_functions: {} };
    } catch {
        return { yolo_all: false, yolo_functions: {} };
    }
}

export async function clearYolo(chatId: string): Promise<boolean> {
    try {
        const $socket = await getSocket();
        if (!$socket) return false;

        const response = await $socket.emitWithAck('tool:clear_yolo', {
            chat_id: chatId
        });

        return response.status === 'success';
    } catch {
        return false;
    }
}


// ---- Pending YOLO for new chats (no chatId yet) ----

export interface PendingYoloState {
    yolo_all: boolean;
    yolo_parents: string[];
}

export const pendingYolo: Writable<PendingYoloState> = writable({ yolo_all: false, yolo_parents: [] });

export function setPendingYolo(level: 'all' | 'parent', enabled: boolean, parentToolId: string = '') {
    pendingYolo.update(state => {
        if (level === 'all') {
            return { ...state, yolo_all: enabled };
        } else {
            const parents = new Set(state.yolo_parents);
            if (enabled) {
                parents.add(parentToolId);
            } else {
                parents.delete(parentToolId);
            }
            return { ...state, yolo_parents: [...parents] };
        }
    });
}

export function getPendingYoloAsStatus(): YoloStatus {
    const state = get(pendingYolo);
    const yolo_functions: Record<string, string[]> = {};
    for (const parentId of state.yolo_parents) {
        yolo_functions[parentId] = ['*'];
    }
    return { yolo_all: state.yolo_all, yolo_functions };
}

export async function flushPendingYolo(chatId: string): Promise<void> {
    const state = get(pendingYolo);
    if (!state.yolo_all && state.yolo_parents.length === 0) return;

    if (state.yolo_all) {
        await setYolo(chatId, 'all', true);
    } else {
        for (const parentId of state.yolo_parents) {
            await setYolo(chatId, 'parent', true, parentId);
        }
    }

    pendingYolo.set({ yolo_all: false, yolo_parents: [] });
}


// ---- Socket listener for pending_found ----

if (typeof window !== 'undefined') {
    import('$lib/stores').then(({ socket }) => {
        socket.subscribe(($socket) => {
            if ($socket) {
                $socket.off('tool:pending_found');
                $socket.on('tool:pending_found', handlePendingFound);
            }
        });
    });
}
