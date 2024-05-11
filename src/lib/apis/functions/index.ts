import { browser } from '$app/environment';
import { OLLAMA_API_BASE_URL } from '$lib/constants';
import { get, writable } from 'svelte/store';

export type StringToType<T extends string> = T extends 'number'
	? number
	: T extends 'string'
	? string
	: T extends 'boolean'
	? boolean
	: T extends 'bigint'
	? bigint
	: T extends 'symbol'
	? symbol
	: T extends 'undefined'
	? undefined
	: T extends 'object'
	? object
	: never;

export interface FunctionSchema {
	[key: string]: {
		description: string;
		params: {
			[key: string]: {
				description: string;
				type: 'number' | 'string' | 'boolean' | 'bigint' | 'symbol' | 'undefined' | 'object';
				required: boolean;
				createdAt: number;
			};
		};
		requiredPhrases?: string[];
	};
}

export class FunctionCaller<T extends FunctionSchema> {
	constructor(
		private schema: T,
		private fnMap: {
			[K in keyof T]: {
				fn: string;
				icon?: string;
				enabled?: boolean;
				createdAt: number;
			};
		}
	) {
		if (!browser) return;
		// convert everything in fnMap to strings
		const fnMapString = {} as any;
		for (const key in fnMap) {
			fnMapString[key] = fnMap[key].toString();
		}
	}
	async getFunction(query: string, history: any[], model: string, token: string) {
		const date = new Date();
		const day = date.toLocaleString('en-GB', { weekday: 'long' });
		const time = date.toLocaleString('en-GB', { hour: 'numeric', minute: 'numeric' });
		const enabledFns = Object.keys(this.fnMap).filter((fn) =>
			typeof this.fnMap[fn].enabled === 'undefined' ? true : this.fnMap[fn].enabled
		);
		const enabledSchema = Object.fromEntries(
			Object.entries(this.schema).filter(([key]) => enabledFns.includes(key))
		);
		const res = await fetch(`${OLLAMA_API_BASE_URL}/api/chat`, {
			method: 'POST',
			headers: {
				Authorization: `Bearer ${token}`,
				Accept: 'application/json',
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				model,
				messages: [
					{
						role: 'system',
						content: `Functions: ${JSON.stringify(enabledSchema)}\nSchema: ${JSON.stringify({
							function: {
								type: Object.keys(enabledSchema).join(' | '),
								required: false
							},
							params: {
								type: 'Map<string, any>',
								required: false
							}
						})}\n\nIf a function doesn't match the query, return exact string { function: null }. Else, pick a function, fill in the parameters from the function's schema, and return it in the format { function: "functionName", params: { key: value } }. Only pick a function if the user asks.`
					},
					{
						role: 'user',
						content: `History: \n${history
							.slice(Math.max(history.length - 4, 0))
							.slice(0, -1)
							.map((h) => `${h.role}: ${h.content}`)
							.join(
								'\n'
							)}\n\nQuery: ${query}\n\nCurrent date (DD/MM/YYYY): ${day} ${date.toLocaleDateString()}`
					}
				],
				stream: false,
				format: 'json'
			})
		});
		const response = await res.json();
		console.log(response.message.content);
		try {
			const message = JSON.parse(
				response.message.content.startsWith('null') || response.message.content.startsWith('{}')
					? '{}'
					: response.message.content.replaceAll('`', '')
			);
			return message as {
				function: keyof T;
				params: {
					[key: string]: string;
				};
			};
		} catch (e) {
			return {} as {
				function: keyof T;
				params: {
					[key: string]: string;
				};
			};
		}
	}

	async callFunction({
		function: fn,
		params
	}: {
		function: keyof T;
		params: { [key: string]: string };
	}) {
		const schema = this.schema[fn];
		if (!schema) return '';
		console.log(`A function call was requested: ${String(fn)} (${schema.description})`);
		const fnParams: {
			[key: string]: StringToType<T[keyof T]['params'][keyof T[keyof T]['params']]['type']>;
		} = {};
		for (const key in schema.params) {
			fnParams[key] = params[key] as any;
		}
		const typescript = await import('typescript');
		const transpiled = typescript.transpile(this.fnMap[fn]?.fn || 'function() { return null; }', {
			lib: ['es2022'],
			target: typescript.ScriptTarget.ES2017
		});

		return eval(transpiled)?.(fnParams as any);
	}

	getIcon(fn: keyof T) {
		return this.fnMap[fn]?.icon;
	}

	isInFunctions(fn: string) {
		return !!this.schema[fn];
	}

	setFunctions(
		schema: T,
		fnMap: {
			[K in keyof T]: {
				fn: string;
				icon?: string;
				enabled?: boolean;
				createdAt: number;
			};
		}
	) {
		this.schema = schema;
		this.fnMap = fnMap;
	}
}

export const fnStore = writable<{
	schema: FunctionSchema;
	fns: {
		[key: string]: {
			fn: string;
			icon?: string;
			enabled?: boolean;
			createdAt: number;
		};
	};
}>({
	schema: {},
	fns: {}
});

export const fnCaller = new FunctionCaller(get(fnStore).schema, get(fnStore).fns);
