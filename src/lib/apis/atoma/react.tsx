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

const SuiConnectButton: React.FC<SuiButtonProps, string> = ({ fn, text }) => {
	const { currentWallet, connectionStatus } = useCurrentWallet();
	const { mutate: signPersonalMessage } = useSignPersonalMessage();
	const { mutate: signAndExecuteTransaction } = useSignAndExecuteTransaction();

	useEffect(() => {
		fn(currentWallet, connectionStatus, signPersonalMessage, signAndExecuteTransaction);
	}, [currentWallet, connectionStatus, signPersonalMessage, signAndExecuteTransaction]);

	return (
		<ConnectModal
			trigger={
				<button className="flex items-center px-6 border-2 dark:border-gray-800 duration-300 dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 w-full rounded-2xl dark:text-white text-sm py-3 transition">
					<svg
						width="300"
						height="384"
						viewBox="0 0 300 384"
						className="size-6 mr-3"
						fill="none"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							fillRule="evenodd"
							clipRule="evenodd"
							d="M240.057 159.914C255.698 179.553 265.052 204.39 265.052 231.407C265.052 258.424 255.414 284.019 239.362 303.768L237.971 305.475L237.608 303.31C237.292 301.477 236.929 299.613 236.502 297.749C228.46 262.421 202.265 232.134 159.148 207.597C130.029 191.071 113.361 171.195 108.985 148.586C106.157 133.972 108.258 119.294 112.318 106.717C116.379 94.1569 122.414 83.6187 127.549 77.2831L144.328 56.7754C147.267 53.1731 152.781 53.1731 155.719 56.7754L240.073 159.914H240.057ZM266.584 139.422L154.155 1.96703C152.007 -0.655678 147.993 -0.655678 145.845 1.96703L33.4316 139.422L33.0683 139.881C12.3868 165.555 0 198.181 0 233.698C0 316.408 67.1635 383.461 150 383.461C232.837 383.461 300 316.408 300 233.698C300 198.181 287.613 165.555 266.932 139.896L266.568 139.438L266.584 139.422ZM60.3381 159.472L70.3866 147.164L70.6868 149.439C70.9237 151.24 71.2239 153.041 71.5715 154.858C78.0809 189.001 101.322 217.456 140.173 239.496C173.952 258.724 193.622 280.828 199.278 305.064C201.648 315.176 202.059 325.129 201.032 333.835L200.969 334.372L200.479 334.609C185.233 342.05 168.09 346.237 149.984 346.237C86.4546 346.237 34.9484 294.826 34.9484 231.391C34.9484 204.153 44.4439 179.142 60.3065 159.44L60.3381 159.472Z"
							fill="#4DA2FF"
						/>
					</svg>{' '}
					<span>{text}</span>
				</button>
			}
		/>
	);
};

interface SuiWrapperProps {
	children: React.ReactNode;
}

const SuiWrapper: React.FC<boolean, SuiWrapperProps> = ({ autoConnect, children }) => {
	return (
		<QueryClientProvider client={queryClient}>
			<SuiClientProvider networks={networkConfig} defaultNetwork="network">
				<WalletProvider autoConnect={autoConnect}>{children}</WalletProvider>
			</SuiClientProvider>
		</QueryClientProvider>
	);
};

export const renderSuiConnectButton = (
	target: HTMLElement | null,
	autoConnect: boolean,
	fn: FnType,
	text: string
) => {
	if (target) {
		createRoot(target).render(
			<SuiWrapper autoConnect={autoConnect}>
				<SuiConnectButton fn={fn} text={text} />
			</SuiWrapper>
		);
	}
};
