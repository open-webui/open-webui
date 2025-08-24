import { writable, derived, get } from 'svelte/store';
import type { Writable } from 'svelte/store';

export interface ToolApprovalRequest {
    approval_id: string;
    tool_id: string;
    tool_name: string;
    tool_params: Record<string, any>;
}

export interface ToolApprovalData {
    chat_id: string;
    message_id: string;
    tools: ToolApprovalRequest[];
    timestamp: number;
}

export const pendingApprovals: Writable<ToolApprovalData | null> = writable(null);

export const showApprovalModal = writable(false);

export const remainingTools = derived(
    pendingApprovals,
    $pendingApprovals => $pendingApprovals?.tools.length || 0
);

export async function setApprovalRequest(data: ToolApprovalData) {
    if (data.chat_id) {
        const autoApprove = await getBackendAutoApprove(data.chat_id);
        if (autoApprove) {
            
            import('$lib/stores').then(({ socket }) => {
                const $socket = get(socket);
                if ($socket) {
                    data.tools.forEach(tool => {
                        $socket.emit('tool:approval_response', {
                            chat_id: data.chat_id,
                            approval_id: tool.approval_id,
                            decision: 'approved'
                        });
                    });
                }
            });
            
            return;
        }
    }
    
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



export async function setBackendAutoApprove(chatId: string, enabled: boolean) {
    try {
        const { socket } = await import('$lib/stores');
        const $socket = get(socket);
        
        if ($socket) {
            const response = await $socket.emitWithAck('tool:toggle_auto_approval', {
                chat_id: chatId,
                enabled: enabled
            });
            
            return response.status === 'success';
        }
        return false;
    } catch (error) {
        return false;
    }
}

export async function getBackendAutoApprove(chatId: string): Promise<boolean> {
    try {
        const { socket } = await import('$lib/stores');
        const $socket = get(socket);
        
        if ($socket) {
            const response = await $socket.emitWithAck('tool:get_auto_approval_status', {
                chat_id: chatId
            });
            
            if (response.status === 'success') {
                return response.enabled;
            }
        }
        return false;
    } catch (error) {
        return false;
    }
}


export async function hasAutoApproval(chatId: string): Promise<boolean> {
    return await getBackendAutoApprove(chatId);
}

export async function getAutoApprovalEnabled(chatId: string): Promise<boolean> {
    return await getBackendAutoApprove(chatId);
}

export function clearAllAutoApprovals() {
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
    
    if (data.chat_id) {
        const autoApprove = await getBackendAutoApprove(data.chat_id);
        if (autoApprove) {
            
            import('$lib/stores').then(({ socket }) => {
                const $socket = get(socket);
                if ($socket) {
                    data.tools.forEach(tool => {
                        $socket.emit('tool:approval_response', {
                            chat_id: data.chat_id,
                            approval_id: tool.approval_id,
                            decision: 'approved'
                        });
                    });
                }
            });
            return;
        }
    }
    
    pendingApprovals.set({
        ...data,
        timestamp: Date.now()
    });
    showApprovalModal.set(true);
}


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