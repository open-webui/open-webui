export interface TxCyberlinkResponseResult {
	numeric_id?: string; // Created/updated cyberlink ID
	formatted_id?: string; // Created/updated formatted ID
	numeric_ids?: string[]; // Batch operation IDs
	formatted_ids?: string[]; // Batch operation formatted IDs
}

export interface TxStatusResponse {
	status: 'pending' | 'confirmed' | 'failed'; // Transaction status
	result?: TxCyberlinkResponseResult; // Optional result data
	error?: string; // Optional error message
}
