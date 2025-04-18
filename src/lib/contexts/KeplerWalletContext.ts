import { writable, type Writable } from 'svelte/store';
import { browser } from '$app/environment';

// Chain Configuration
const CHAIN_CONFIG = {
  CONTRACT_ADDRESS: 'wasm1nc5tatafv6eyq7llkr2gv50ff9e22mnf70qgjlv737ktmt4eswrqr5j2ht',
  CHAIN_ID: 'test-chain',
  DENOM: 'stake',
  NODE_URL: 'http://localhost:26657',
  RPC_TIMEOUT: 60000
} as const;

interface KeplrAccount {
  address: string;
  pubkey: Uint8Array;
}

interface SignDoc {
  chain_id: string;
  account_number: string;
  sequence: string;
  fee: {
    amount: { amount: string; denom: string }[];
    gas: string;
  };
  msgs: any[];
  memo: string;
}

interface KeplerWalletState {
  isConnected: boolean;
  address: string | null;
}

interface KeplerWalletContext {
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  signTransaction: (signDoc: SignDoc) => Promise<any>;
  state: Writable<KeplerWalletState>;
  config: typeof CHAIN_CONFIG;
}

const STORAGE_KEY = 'kepler_wallet_state';

function createKeplerWalletContext(): KeplerWalletContext {
  // Initialize state from localStorage if available
  const initialState: KeplerWalletState = browser
    ? JSON.parse(localStorage.getItem(STORAGE_KEY) || '{"isConnected": false, "address": null}')
    : { isConnected: false, address: null };

  const state = writable<KeplerWalletState>(initialState);

  // Subscribe to state changes and save to localStorage
  if (browser) {
    state.subscribe((value) => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    });
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

  return {
    connect,
    disconnect,
    signTransaction,
    state: {
      ...state,
      subscribe: state.subscribe
    },
    config: CHAIN_CONFIG
  };
}

export const keplerWallet = createKeplerWalletContext(); 