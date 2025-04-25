import { writable, type Writable } from 'svelte/store';
import { browser } from '$app/environment';
import { SigningCosmWasmClient, CosmWasmClient } from '@cosmjs/cosmwasm-stargate';
import type { ExecuteResult } from '@cosmjs/cosmwasm-stargate';
import { GasPrice } from '@cosmjs/stargate';
import type { TxStatusResponse } from './types';
import { parseTxStatus } from './utils';

// Chain Configuration
const CHAIN_CONFIG = {
	CONTRACT_ADDRESS: 'wasm1nc5tatafv6eyq7llkr2gv50ff9e22mnf70qgjlv737ktmt4eswrqr5j2ht',
	CHAIN_ID: 'test-chain',
	DENOM: 'stake',
	NODE_URL: 'http://localhost:26657',
	RPC_TIMEOUT: 60000,
	GAS_PRICE_AMOUNT: '0.025'
} as const;

interface SignDoc {
	chain_id: string;
	account_number: string;
	sequence: string;
	fee: {
		amount: { amount: string; denom: string }[];
		gas: string;
	};
	msgs: unknown[];
	memo: string;
}

interface KeplerWalletState {
	isConnected: boolean;
	address: string | null;
}

interface KeplerWalletContext {
	connect: () => Promise<void>;
	disconnect: () => Promise<void>;
	signTransaction: (signDoc: SignDoc) => Promise<ExecuteResult>;
	executeContract: (contractMsg: Record<string, unknown>) => Promise<ExecuteResult>;
	getTx: (transactionHash: string) => Promise<TxStatusResponse | null>;
	state: Writable<KeplerWalletState>;
	config: typeof CHAIN_CONFIG;
	client: CosmWasmClient | null;
}

const STORAGE_KEY = 'kepler_wallet_state';

function createKeplerWalletContext(): KeplerWalletContext {
	// Initialize state from localStorage if available
	const initialState: KeplerWalletState = browser
		? JSON.parse(localStorage.getItem(STORAGE_KEY) || '{"isConnected": false, "address": null}')
		: { isConnected: false, address: null };

	const state = writable<KeplerWalletState>(initialState);
	let cosmWasmClient: CosmWasmClient | null = null;

	// Subscribe to state changes and save to localStorage
	if (browser) {
		state.subscribe((value) => {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
		});

		// Initialize CosmWasmClient immediately
		CosmWasmClient.connect(CHAIN_CONFIG.NODE_URL)
			.then((client) => {
				cosmWasmClient = client;
			})
			.catch(console.error);
	}

	const connect = async () => {
		try {
			if (!window.keplr) {
				throw new Error('Keplr extension not installed');
			}

			// Enable access to chain
			await window.keplr.enable(CHAIN_CONFIG.CHAIN_ID);

			// Get the offline signer
			const offlineSigner = window.keplr.getOfflineSigner(CHAIN_CONFIG.CHAIN_ID);

			// Get user's Kepler account
			const accounts = await offlineSigner.getAccounts();
			const address = accounts[0].address;

			state.update((s) => ({ ...s, isConnected: true, address }));
		} catch (error) {
			console.error('Failed to connect Kepler wallet:', error);
			throw error;
		}
	};

	const disconnect = async () => {
		state.update((s) => ({ ...s, isConnected: false, address: null }));
	};

	const signTransaction = async (signDoc: SignDoc) => {
		try {
			if (!window.keplr) {
				throw new Error('Keplr extension not installed');
			}

			const offlineSigner = window.keplr.getOfflineSigner(CHAIN_CONFIG.CHAIN_ID);
			const accounts = await offlineSigner.getAccounts();

			// Ensure the signDoc uses our chain configuration
			signDoc.chain_id = CHAIN_CONFIG.CHAIN_ID;
			if (signDoc.fee.amount.length > 0) {
				signDoc.fee.amount[0].denom = CHAIN_CONFIG.DENOM;
			}

			return await offlineSigner.signAmino(accounts[0].address, signDoc);
		} catch (error) {
			console.error('Failed to sign transaction:', error);
			throw error;
		}
	};

	const getTx = async (transactionHash: string): Promise<TxStatusResponse | null> => {
		if (!cosmWasmClient) {
			throw new Error('CosmWasm client not initialized');
		}
		const tx = await cosmWasmClient.getTx(transactionHash);

		if (!tx) {
			return null;
		}

		return parseTxStatus(tx || {});
	};

	const waitForTransaction = async (
		txHash: string,
		timeoutMs: number = 30000,
		pollIntervalMs: number = 1000
	) => {
		const startTime = Date.now();

		while (Date.now() - startTime < timeoutMs) {
			try {
				const result = await getTx(txHash);

				return result;
			} catch (error) {
				console.error(`Error while polling transaction ${txHash}:`, error);
				// Continue polling if transaction not found
			}
			await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
		}

		throw new Error(`Transaction confirmation timed out after ${timeoutMs}ms`);
	};

	const executeContract = async (contractMsg: Record<string, unknown>) => {
		try {
			if (!window.keplr) {
				throw new Error('Keplr extension not installed');
			}

			// Get the offline signer
			const offlineSigner = window.keplr.getOfflineSigner(CHAIN_CONFIG.CHAIN_ID);
			const accounts = await offlineSigner.getAccounts();
			const sender = accounts[0];

			// Create signing client
			const gasPrice = GasPrice.fromString(`${CHAIN_CONFIG.GAS_PRICE_AMOUNT}${CHAIN_CONFIG.DENOM}`);
			const signingClient = await SigningCosmWasmClient.connectWithSigner(
				CHAIN_CONFIG.NODE_URL,
				offlineSigner,
				{ gasPrice }
			);

			// Execute contract
			const result = await signingClient.execute(
				sender.address,
				CHAIN_CONFIG.CONTRACT_ADDRESS,
				contractMsg,
				'auto'
			);

			return result;
		} catch (error) {
			console.error('Failed to execute contract:', error);
			throw error;
		}
	};

	return {
		connect,
		disconnect,
		signTransaction,
		executeContract,
		getTx: waitForTransaction,
		state: {
			...state,
			subscribe: state.subscribe
		},
		config: CHAIN_CONFIG,
		get client() {
			return cosmWasmClient;
		}
	};
}

export const keplerWallet = createKeplerWalletContext();
