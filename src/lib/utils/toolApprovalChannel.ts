export class ToolApprovalCoordinator {
    private channel: BroadcastChannel;
    private isHandlingApproval = false;
    private tabId: string;
    
    constructor() {
        this.tabId = Math.random().toString(36).substring(7);
        this.channel = new BroadcastChannel('tool-approval-channel');
        
        this.channel.onmessage = (event) => {
            this.handleMessage(event.data);
        };
    }
    
    private handleMessage(data: unknown) {
        if (!data || typeof data !== 'object' || !('type' in data)) return;
        
        const msg = data as { type: string; tabId?: string; hasApprovals?: boolean };
        
        switch (msg.type) {
            case 'APPROVAL_CLAIMED':
                if (msg.tabId !== this.tabId) {
                    // Another tab is handling it
                    this.isHandlingApproval = false;
                }
                break;
                
            case 'APPROVAL_COMPLETED':
                // Clear any pending state
                this.isHandlingApproval = false;
                break;
                
            case 'TAB_CLOSING':
                // Tab is closing with pending approvals
                if (msg.hasApprovals && !this.isHandlingApproval) {
                    // Could take over, but we'll let it timeout per requirements
                }
                break;
        }
    }
    
    claimApproval(): boolean {
        if (this.isHandlingApproval) return true;
        
        // Try to claim the approval handling
        this.channel.postMessage({
            type: 'APPROVAL_CLAIMED',
            tabId: this.tabId,
            timestamp: Date.now()
        });
        
        this.isHandlingApproval = true;
        return true;
    }
    
    releaseApproval() {
        this.isHandlingApproval = false;
        this.channel.postMessage({
            type: 'APPROVAL_COMPLETED',
            tabId: this.tabId,
            timestamp: Date.now()
        });
    }
    
    notifyTabClosing(hasApprovals: boolean) {
        this.channel.postMessage({
            type: 'TAB_CLOSING',
            tabId: this.tabId,
            hasApprovals,
            timestamp: Date.now()
        });
    }
    
    destroy() {
        this.channel.close();
    }
}

// Export singleton instance
export const approvalCoordinator = new ToolApprovalCoordinator();