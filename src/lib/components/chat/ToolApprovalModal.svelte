<script lang="ts">
    import { onMount, onDestroy, getContext } from 'svelte';
    import { fade, fly } from 'svelte/transition';
    import { socket } from '$lib/stores';
    import { 
        pendingApprovals, 
        removeToolFromPending,
        clearApprovals,
        showApprovalModal,
        setBackendAutoApprove
    } from '$lib/stores/toolApproval';
    import { approvalCoordinator } from '$lib/utils/toolApprovalChannel';
    import { toast } from 'svelte-sonner';
    
    const i18n = getContext('i18n');
    
    
    $: if ($showApprovalModal && $pendingApprovals) {
        claimApproval();
    }
    
    function claimApproval() {
        if (!$pendingApprovals) return;
        
        // Claim this approval across tabs
        if (!approvalCoordinator.claimApproval()) {
            // Another tab is handling it
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
        
        // Remove from pending list
        removeToolFromPending(approvalId);
        
        // Check if all tools are handled
        if ($pendingApprovals?.tools.length === 0) {
            clearApprovals();
            approvalCoordinator.releaseApproval();
        }
    }
    
    function approveAll() {
        if (!$pendingApprovals) return;
        
        const tools = [...$pendingApprovals.tools];
        tools.forEach(tool => {
            sendApprovalResponse(tool.approval_id, 'approved');
        });
        
        toast.success('All tools approved');
    }
    
    function denyAll() {
        if (!$pendingApprovals) return;
        
        const tools = [...$pendingApprovals.tools];
        tools.forEach(tool => {
            sendApprovalResponse(tool.approval_id, 'denied');
        });
        
        toast.info('All tools denied');
    }
    
    async function approveAllFuture() {
        if (!$pendingApprovals) return;
        
        // Enable auto-approval for THIS SPECIFIC CHAT only
        const chatId = $pendingApprovals.chat_id;
        if (chatId) {
            const success = await setBackendAutoApprove(chatId, true);
            if (success) {
                toast.success('Auto-approval enabled for this chat');
                
                // Trigger a refresh of auto-approval status in MessageInput
                window.dispatchEvent(new CustomEvent('autoApprovalChanged', { 
                    detail: { chatId, enabled: true } 
                }));
            } else {
                toast.error('Failed to enable auto-approval');
                return;
            }
        } else {
            toast.error('Chat ID not found');
            return;
        }
        
        // Approve all current tools
        const tools = [...$pendingApprovals.tools];
        tools.forEach(tool => {
            sendApprovalResponse(tool.approval_id, 'approved');
        });
        
        // Toast already handled by the auto-approval success response
    }
    
    
    
    // Handle tab close
    onDestroy(() => {
        if ($pendingApprovals) {
            approvalCoordinator.notifyTabClosing(true);
            // Close modal without response
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
                <!-- Tools List -->
                <div class="space-y-4">
                    {#each $pendingApprovals.tools as tool (tool.approval_id)}
                        <div class="bg-gray-50 dark:bg-gray-800 rounded-xl p-4">
                            <!-- Tool Header -->
                            <div class="flex items-center justify-between mb-3">
                                <div class="flex items-center gap-3">
                                    <!-- Tool Icon -->
                                    <div class="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                                        <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                        </svg>
                                    </div>


                                    <!-- Tool Info -->
                                    <div>
                                        <h3 class="font-medium text-gray-900 dark:text-white text-lg">
                                            {tool.tool_name}
                                        </h3>
                                    </div>
                                </div>
                            </div>


                            <!-- Parameters -->
                            {#if Object.keys(tool.tool_params).length > 0}
                                <div class="bg-white dark:bg-gray-800 rounded-lg p-3 mb-4 border border-gray-100 dark:border-gray-600">
                                    <p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                                        {$i18n.t('Parameters:')}
                                    </p>
                                    <pre class="text-sm text-gray-700 dark:text-gray-300 font-mono overflow-x-auto whitespace-pre-wrap">
{JSON.stringify(tool.tool_params, null, 2)}</pre>
                                </div>
                            {/if}
                        </div>
                    {/each}
                </div>


                <!-- Warning Text -->
                <div class="mt-6 px-6">
                    <p class="text-sm text-gray-500 dark:text-gray-400 text-center">
                        {$i18n.t('Review each action carefully before approving')}
                    </p>
                </div>
            </div>


            <!-- Footer Actions -->
            <div class="px-6 py-4">
                <div class="flex gap-2 justify-between">
                    <!-- Left side - Approve buttons -->
                    <div class="flex gap-2">
                        <!-- Always Allow Button -->
                        <button
                            on:click={approveAllFuture}
                            class="w-40 px-4 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors font-medium text-sm"
                        >
                            {$i18n.t('Allow Always')}
                        </button>


                        <!-- Allow Once Button -->
                        <button
                            on:click={() => {
              if (!$pendingApprovals) return;
              const tools = [...$pendingApprovals.tools];
              tools.forEach(tool => {
                  sendApprovalResponse(tool.approval_id, 'approved');
              })
          }}
                            class="w-40 px-4 py-2.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors font-medium text-sm"
                        >
                            {$i18n.t('Allow Once')}
                        </button>
                    </div>


                    <!-- Right side - Decline button -->
                    <button
                        on:click={() => {
          if (!$pendingApprovals) return;
          const tools = [...$pendingApprovals.tools];
          tools.forEach(tool => {
              sendApprovalResponse(tool.approval_id, 'denied');
          });
      }}
                        class="px-4 py-2.5 bg-gray-800 dark:bg-gray-600 text-white rounded-lg hover:bg-gray-900 dark:hover:bg-gray-500 transition-colors font-medium text-sm"
                    >
                        {$i18n.t('Decline')}
                    </button>
                </div>
            </div>
            </div>
    </div>
{/if}