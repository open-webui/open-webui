import { writable } from "svelte/store";
import type { WalletClient, PublicActions } from "viem";

export const walletClient = writable<WalletClient & PublicActions>();
