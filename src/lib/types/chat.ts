export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: number;
    parentId: string | null;
    childrenIds: string[];
    metadata?: {
        citations?: any[];
        codeExecutions?: any[];
    };
}

export interface ChatHistory {
    messages: { [key: string]: Message };
    currentId: string;
}
