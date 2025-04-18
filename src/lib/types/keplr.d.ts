interface KeplrAccount {
  address: string;
  pubkey: Uint8Array;
}

interface OfflineSigner {
  getAccounts(): Promise<KeplrAccount[]>;
  signAmino(signerAddress: string, signDoc: any): Promise<any>;
}

interface Keplr {
  enable(chainId: string): Promise<void>;
  getOfflineSigner(chainId: string): OfflineSigner;
}

declare global {
  interface Window {
    keplr?: Keplr;
  }
} 