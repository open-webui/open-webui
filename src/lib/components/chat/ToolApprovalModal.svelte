<script lang="ts">
    import { onDestroy, getContext } from 'svelte';
    import { fade, fly } from 'svelte/transition';
    import { socket } from '$lib/stores';
    import { 
        pendingApprovals, 
        removeToolFromPending,
        clearApprovals,
        showApprovalModal,
        addAlwaysApproved
    } from '$lib/stores/toolApproval';
    import { approvalCoordinator } from '$lib/utils/toolApprovalChannel';
    import { toast } from 'svelte-sonner';
    
    const i18n = getContext('i18n');
    
    
    $: if ($showApprovalModal && $pendingApprovals) {
        claimApproval();
    }
    
    function claimApproval() {
        if (!$pendingApprovals) return;
        
        if (!approvalCoordinator.claimApproval()) {
            showApprovalModal.set(false);
            return;
        }
    }
    
    
    function sendApprovalResponse(approvalId: string, decision: 'approved' | 'denied') {
        if (!$pendingApprovals || !$socket) return;
        
        $socket.emit('tool:approval_response', {
            chat_id: $pendingApprovals.chat_id,
            approval_id: approvalId,
            decision: decision
        });
        
        removeToolFromPending(approvalId);
        
        if ($pendingApprovals?.tools.length === 0) {
            clearApprovals();
            approvalCoordinator.releaseApproval();
        }
    }
    
    function approveAllOnce() {
        if (!$pendingApprovals) return;
        
        const tools = [...$pendingApprovals.tools];
        tools.forEach(tool => {
            sendApprovalResponse(tool.approval_id, 'approved');
        });
    }
    
    function denyAll() {
        if (!$pendingApprovals) return;
        
        const tools = [...$pendingApprovals.tools];
        tools.forEach(tool => {
            sendApprovalResponse(tool.approval_id, 'denied');
        });
    }
    
    async function alwaysAllowFunctions() {
        if (!$pendingApprovals) return;
        
        const chatId = $pendingApprovals.chat_id;
        if (!chatId) {
            toast.error('Chat ID not found');
            return;
        }
        
        const tools = [...$pendingApprovals.tools];
        const uniqueFunctions = new Map<string, string>();
        for (const tool of tools) {
            uniqueFunctions.set(tool.tool_name, tool.parent_tool_id);
        }
        
        for (const [functionName, parentToolId] of uniqueFunctions) {
            await addAlwaysApproved(chatId, parentToolId, functionName, 'function');
        }
        
        toast.success($i18n.t('Functions always allowed for this chat'));
        
        tools.forEach(tool => {
            sendApprovalResponse(tool.approval_id, 'approved');
        });
    }
    
    async function alwaysAllowParents() {
        if (!$pendingApprovals) return;
        
        const chatId = $pendingApprovals.chat_id;
        if (!chatId) {
            toast.error('Chat ID not found');
            return;
        }
        
        const tools = [...$pendingApprovals.tools];
        const uniqueParents = new Set(tools.map(t => t.parent_tool_id));
        
        for (const parentToolId of uniqueParents) {
            await addAlwaysApproved(chatId, parentToolId, '', 'parent');
        }
        
        toast.success($i18n.t('Tools always allowed for this chat'));
        
        tools.forEach(tool => {
            sendApprovalResponse(tool.approval_id, 'approved');
        });
    }
    
    
    $: uniqueFunctionNames = $pendingApprovals
        ? [...new Set($pendingApprovals.tools.map(t => t.tool_name))].filter(Boolean)
        : [];
    
    $: uniqueParentNames = $pendingApprovals
        ? [...new Set($pendingApprovals.tools.map(t => t.parent_tool_id))].filter(id => id && id !== 'unknown')
        : [];
    
    onDestroy(() => {
        if ($pendingApprovals) {
            approvalCoordinator.notifyTabClosing(true);
        }
    });
</script>


{#if $showApprovalModal && $pendingApprovals}
    <div 
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
        transition:fade={{ duration: 200 }}
        on:click|self|preventDefault|stopPropagation
        on:keydown|preventDefault|stopPropagation
    >
        <div 
            class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
            transition:fly={{ y: 20, duration: 300 }}
            on:click|stopPropagation
        >
            <!-- Header -->
            <div class="px-6 py-5">
                <h2 class="text-xl font-semibold text-gray-900 dark:text-white text-center">
                    {$i18n.t('Tool Approval Required')}
                </h2>
            </div>

            <!-- Content -->
            <div class="px-6 py-4 max-h-[60vh] overflow-y-auto">
                <div class="space-y-4">
                    {#each $pendingApprovals.tools as tool (tool.approval_id)}
                        <div class="bg-gray-50 dark:bg-gray-800 rounded-xl p-4">
                            <div class="flex items-center justify-between mb-3">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                                        <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                        </svg>
                                    </div>

                                    <div>
                                        <h3 class="font-medium text-gray-900 dark:text-white text-lg">
                                            {tool.tool_name}
                                        </h3>
                                        {#if tool.parent_tool_id && tool.parent_tool_id !== 'unknown'}
                                            <p class="text-xs text-gray-500 dark:text-gray-400">
                                                {tool.parent_tool_id}
                                            </p>
                                        {/if}
                                    </div>
                                </div>
                            </div>

                            {#if !tool.parent_tool_id || tool.parent_tool_id === 'unknown'}
                                <div class="flex items-center gap-2 mb-3 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-700 dark:text-amber-400 text-xs">
                                    <svg class="size-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                                        <line x1="12" y1="9" x2="12" y2="13"/>
                                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                                    </svg>
                                    <span>{$i18n.t('Unrecognized tool call — this may fail')}</span>
                                </div>
                            {/if}

                            {#if Object.keys(tool.tool_params).length > 0}
                                <div class="bg-white dark:bg-gray-800 rounded-lg p-3 mb-4 border border-gray-100 dark:border-gray-600">
                                    <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                                        {$i18n.t('Parameters:')}
                                    </p>
                                    <pre class="text-sm text-gray-700 dark:text-gray-300 font-mono overflow-x-auto whitespace-pre-wrap">{JSON.stringify(tool.tool_params, null, 2)}</pre>
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>

                <div class="mt-6 px-6">
                    <p class="text-sm text-gray-500 dark:text-gray-400 text-center">
                        {$i18n.t('Review each action carefully before approving')}
                    </p>
                </div>
            </div>

            <!-- Footer Actions -->
            <div class="px-6 py-4">
                <div class="flex flex-col gap-2">
                    <!-- Always Approve row -->
                    <div class="flex gap-2 justify-center">
                        <button
                            on:click={alwaysAllowFunctions}
                            class="flex-1 max-w-xs px-4 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors text-sm text-center"
                        >
                            <span class="font-medium">{$i18n.t('Always Approve')}</span>
                            <br />
                            <span class="text-xs text-gray-500 dark:text-gray-400">({uniqueFunctionNames.join(', ')})</span>
                        </button>
                        {#if uniqueParentNames.length > 0}
                            <button
                                on:click={alwaysAllowParents}
                                class="flex-1 max-w-xs px-4 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors text-sm text-center"
                            >
                                <span class="font-medium">{$i18n.t('Always Approve')}</span>
                                <br />
                                <span class="text-xs text-gray-500 dark:text-gray-400">({uniqueParentNames.join(', ')})</span>
                            </button>
                        {/if}
                    </div>
                    <!-- Allow Once / Decline row -->
                    <div class="flex gap-2 justify-center">
                        <button
                            on:click={approveAllOnce}
                            class="flex-1 max-w-xs px-4 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors font-medium text-sm"
                        >
                            {$i18n.t('Allow Once')}
                        </button>
                        <button
                            on:click={denyAll}
                            class="flex-1 max-w-xs px-4 py-2.5 bg-gray-800 dark:bg-gray-600 text-white rounded-lg hover:bg-gray-900 dark:hover:bg-gray-500 transition-colors font-medium text-sm"
                        >
                            {$i18n.t('Decline')}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
{/if}
