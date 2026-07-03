import type { executeToolServer as executeToolServerApi } from '$lib/apis';

type ExecuteToolServer = typeof executeToolServerApi;
type ToolServerData = Parameters<ExecuteToolServer>[4];

type ToolServer = {
	url: string;
};

type ResolvedToolServer = {
	toolServer?: ToolServer | null;
	toolServerData?: ToolServerData;
	token?: string | null | undefined;
};

type Logger = {
	log?: (...args: unknown[]) => void;
	error?: (...args: unknown[]) => void;
};

type ExecuteToolRequestParams = {
	data: {
		name?: string;
		params?: Parameters<ExecuteToolServer>[3];
		server?: {
			url?: string;
		};
	};
	chatId?: string;
	resolved: ResolvedToolServer;
	executeToolServer: ExecuteToolServer;
	cb?: (result: unknown) => void;
	onDisplayFile?: (path: string, result: unknown) => void;
	onWriteFile?: (path: string) => void;
	logger?: Logger;
};

const getErrorMessage = (error: unknown) => {
	if (error instanceof Error && error.message) {
		return error.message;
	}

	if (
		error &&
		typeof error === 'object' &&
		'message' in error &&
		typeof (error as { message?: unknown }).message === 'string'
	) {
		return (error as { message: string }).message;
	}

	return 'Tool execution failed';
};

export const executeToolRequest = async ({
	data,
	chatId,
	resolved,
	executeToolServer,
	cb,
	onDisplayFile,
	onWriteFile,
	logger = console
}: ExecuteToolRequestParams) => {
	try {
		const { toolServer, toolServerData, token } = resolved;

		if (!toolServer) {
			cb?.({ error: 'Tool Server Not Found' });
			return;
		}

		const res = await executeToolServer(
			token ?? '',
			toolServer.url,
			data?.name ?? '',
			data?.params ?? {},
			toolServerData as ToolServerData,
			chatId
		);

		logger.log?.('executeToolServer', res);

		if (data?.name === 'display_file' && typeof data?.params?.path === 'string') {
			const result = res as { exists?: boolean };
			if (result?.exists !== false) {
				onDisplayFile?.(data.params.path, res);
			}
		}

		if (data?.name === 'write_file' && typeof data?.params?.path === 'string') {
			const result = res as { path?: string };
			onWriteFile?.(result?.path ?? data.params.path);
		}

		cb?.(structuredClone(res));
	} catch (error) {
		logger.error?.('executeTool error:', error);
		cb?.({ error: getErrorMessage(error) });
	}
};
