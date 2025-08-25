export type Banner = {
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export enum TTS_RESPONSE_SPLIT {
	PUNCTUATION = 'punctuation',
	PARAGRAPHS = 'paragraphs',
	NONE = 'none'
}

// Add these interfaces to your existing types

export interface ToolApprovalRequest {
    approval_id: string;
    tool_id: string;
    tool_name: string;
    tool_params: Record<string, any>;
    risk_level: 'high' | 'medium' | 'low';
}

export interface ToolApprovalData {
    session_id: string;
    chat_id: string;
    message_id: string;
    tools: ToolApprovalRequest[];
    timestamp?: number;
}

export interface ToolApprovalResponse {
    session_id: string;
    approval_id: string;
    decision: 'approved' | 'denied';
}

export interface ToolApprovalStatusEvent {
    tool_id: string;
    tool_name: string;
    status: 'approved' | 'denied';
}