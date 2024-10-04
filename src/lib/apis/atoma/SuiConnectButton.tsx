import React, { useEffect } from 'react';
import {
	ConnectModal,
	createNetworkConfig,
	SuiClientProvider,
	useCurrentWallet,
	useSignAndExecuteTransaction,
	useSignPersonalMessage,
	WalletProvider
} from '@mysten/dapp-kit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@mysten/dapp-kit/dist/index.css';
import { createRoot } from 'react-dom/client';

const queryClient = new QueryClient();
const { networkConfig } = createNetworkConfig({
	network: { url: 'http://localhost:9000' }
});

type FnType = (
	wallet: import('@mysten/wallet-standard').WalletWithRequiredFeatures | null,
	status: 'connecting' | 'disconnected' | 'connected',
	signPersonalMessage: any,
	signAndExecuteTransaction: any
) => void;

interface SuiButtonProps {
	fn: FnType;
}

const SuiConnectButton: React.FC<SuiButtonProps> = ({ fn }) => {
	const { currentWallet, connectionStatus } = useCurrentWallet();
	const { mutate: signPersonalMessage } = useSignPersonalMessage();
	const { mutate: signAndExecuteTransaction } = useSignAndExecuteTransaction();

	useEffect(() => {
		fn(currentWallet, connectionStatus, signPersonalMessage, signAndExecuteTransaction);
	}, [currentWallet, connectionStatus, signPersonalMessage, signAndExecuteTransaction]);

	return <ConnectModal trigger={<div className="py-3">Connect</div>} />;
};

const SuiButton: React.FC<SuiButtonProps> = ({ fn }) => {
	return (
		<QueryClientProvider client={queryClient}>
			<SuiClientProvider networks={networkConfig} defaultNetwork="network">
				<WalletProvider>
					<SuiConnectButton fn={fn} />
				</WalletProvider>
			</SuiClientProvider>
		</QueryClientProvider>
	);
};

export const renderSuiConnectButton = (target: HTMLElement | null, fn: FnType) => {
	if (target) {
		createRoot(target).render(<SuiButton fn={fn} />);
	}
};
