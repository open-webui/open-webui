import type { IndexedTx } from '@cosmjs/cosmwasm-stargate';
import type { TxStatusResponse } from './types';

/**
 * Sanitizes query results by converting BigInt to string and handling undefined values
 * @param obj Any query result object
 * @returns Sanitized object
 */
export const sanitizeQueryResult = (obj: any): any => {
	if (obj === null || obj === undefined) return obj;
	if (typeof obj === 'bigint') return obj.toString();
	if (typeof obj === 'function') return undefined;
	if (Array.isArray(obj)) return obj.map(sanitizeQueryResult);
	if (typeof obj === 'object' && obj !== null) {
		const newObj: Record<string, any> = {};
		for (const key in obj) {
			if (Object.prototype.hasOwnProperty.call(obj, key)) {
				const sanitizedValue = sanitizeQueryResult(obj[key]);
				if (sanitizedValue !== undefined) {
					newObj[key] = sanitizedValue;
				}
			}
		}
		return newObj;
	}
	return obj;
};

// Fields to extract from cyberlink event
const FIELD_NAMES = ['numeric_id', 'numeric_ids', 'formatted_id', 'formatted_ids'];

export const parseTxStatus = async (tx: IndexedTx): Promise<TxStatusResponse> => {
	const wasmEvent = tx.events.find((e) => e.type === 'wasm')?.attributes || [];

	const result: Record<string, string> = {};

	FIELD_NAMES.forEach((key) => {
		const value = wasmEvent.find((a) => a.key === key)?.value;
		if (value) {
			result[key] = value;
		}
	});

	if (tx.code === 0) {
		return {
			status: 'confirmed',
			result
		};
	}

	return {
		status: 'failed',
		error: String(tx.code) || 'Transaction failed'
	};
};
