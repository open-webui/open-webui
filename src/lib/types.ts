export interface Chat {
    id: string;
    title: string;
    time_range?: string;
    created_at?: number;
    updated_at?: number;
    folder_id?: string | null;
    pinned?: boolean;
    archived?: boolean;
    tags?: string[];
} 