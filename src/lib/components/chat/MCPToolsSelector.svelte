<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { createEventDispatcher, getContext } from 'svelte';

	import { tools as _tools } from '$lib/stores';
	import { getTools } from '$lib/apis/tools';

	// Import servers API to fetch server visibility
	import { mcpServersApi, type MCPServerUserResponse } from '$lib/apis/mcp_servers';

	import Tooltip from '../common/Tooltip.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let selectedToolIds: string[] = [];
	export let publicOnly: boolean = false;

	interface MCPTool {
		id: string;
		name: string;
		displayName: string;
		fullName: string;
		description: string;
		serverName: string;
		isPublic: boolean;
		scopePrefix: string;
		enabled: boolean;
		specs: any[];
		hasStructuredOutput: boolean;
		supportsJsonResponse: boolean;
		outputSchema: any;
		// Added to disambiguate servers with the same name
		serverId?: string;
		groupKey: string;
	}

	let show = false;
	let searchValue = '';
	let mcpTools: Record<string, MCPTool> = {};
	let hasMcpTools = false;
	let loading = false;

	// Cache of server visibility; prefer id, fallback to name
	let serverPublicById: Record<string, boolean> = {};
	let serverPublicByName: Record<string, boolean> = {};

	// Check if there are MCP tools available
	$: hasMcpTools = ($_tools || []).filter((tool: any) => tool.id.startsWith('mcp:')).length > 0;

	// Optimized filtering with search
	$: filteredTools = Object.entries(mcpTools).filter(([toolId, tool]) => {
		if (!searchValue.trim()) return true;
		const searchLower = searchValue.toLowerCase();
		return (
			tool.name.toLowerCase().includes(searchLower) ||
			tool.description.toLowerCase().includes(searchLower) ||
			tool.serverName.toLowerCase().includes(searchLower)
		);
	});

	// Group filtered tools by unique server group key
	$: groupedTools = filteredTools.reduce(
		(acc, [toolId, tool]) => {
			if (!acc[tool.groupKey]) {
				acc[tool.groupKey] = [];
			}
			acc[tool.groupKey].push([toolId, tool]);
			return acc;
		},
		{} as Record<string, [string, MCPTool][]>
	);

	const init = async () => {
		if ($_tools === null) {
			await _tools.set(await getTools(localStorage.token));
		}

		// Fetch servers to derive public/private per server
		try {
			const servers: MCPServerUserResponse[] = await mcpServersApi.getMCPServers(localStorage.token);
			serverPublicById = (servers || []).reduce((acc: Record<string, boolean>, s) => {
				acc[s.id] = Boolean((s as any).is_public);
				return acc;
			}, {} as Record<string, boolean>);
			serverPublicByName = (servers || []).reduce((acc: Record<string, boolean>, s) => {
				acc[s.name.replace(/^\[Global\]\s*/, '')] = Boolean((s as any).is_public);
				return acc;
			}, {} as Record<string, boolean>);
		} catch (e) {
			serverPublicById = {};
			serverPublicByName = {};
		}

		// Filter MCP tools only
		const allMcpTools = ($_tools || []).filter((tool: any) => tool.id.startsWith('mcp:'));

		// If no MCP tools, don't process further
		if (allMcpTools.length === 0) {
			return;
		}

		mcpTools = allMcpTools.reduce((acc: Record<string, MCPTool>, tool: any) => {
			// Extract server identity and tool name
			let serverName = 'Unknown Server';
			let serverId: string | undefined = undefined;
			let cleanToolName = tool.name;

			// Determine if tool is public based on server visibility; prefer id
			const manifestServerId = tool.meta?.manifest?.mcp_server_id as string | undefined;
			const manifestServerName = tool.meta?.manifest?.mcp_server_name as string | undefined;
			const normalizedServerName = manifestServerName
				? manifestServerName.replace(/^\[Global\]\s*/, '')
				: undefined;
			const isPublicByServer = manifestServerId
				? Boolean(serverPublicById[manifestServerId])
				: normalizedServerName
				? Boolean(serverPublicByName[normalizedServerName])
				: false;
			// When publicOnly is true, only include tools from public servers
			if (publicOnly && !isPublicByServer) {
				return acc;
			}
			const is_public = isPublicByServer; // Only server ACL defines public
			const scopePrefix = is_public ? '[Public]' : '[Private]';

			// Try to get server id/name from meta first (most reliable)
			if (manifestServerId) {
				serverId = manifestServerId;
			}
			if (manifestServerName) {
				serverName = manifestServerName;
			}

			// Try to get tool name from meta first (most reliable)
			if (tool.meta?.manifest?.mcp_original_name) {
				cleanToolName = tool.meta.manifest.mcp_original_name;
			} else {
				// Fallback: parse from tool name
				if (tool.name.startsWith('[MCP] ') && tool.name.includes(' - ')) {
					const nameWithoutPrefix = tool.name.substring(6); // Remove "[MCP] "
					const parts = nameWithoutPrefix.split(' - ');
					if (parts.length >= 2) {
						if (!tool.meta?.manifest?.mcp_server_name) {
							serverName = parts[0];
						}
						cleanToolName = parts.slice(1).join(' - ');
					}
				}
			}

			// Create display name with proper title casing
			const displayName = cleanToolName
				.split(/[\s_-]+/)
				.map((word: string) => {
					if (word.length <= 2) {
						return word.toUpperCase();
					}
					return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
				})
				.join(' ');

			// Unique grouping key: prefer serverId; fallback to name+scope
			const groupKey = serverId ? serverId : `${serverName}::${is_public ? 'public' : 'private'}`;

			// Internal unique key per server+tool to avoid collisions across servers with same tool id
			const toolKey = serverId ? `${tool.id}::${serverId}` : `${tool.id}::${serverName}`;

			acc[toolKey] = {
				id: tool.id,
				name: cleanToolName,
				displayName: displayName,
				fullName: tool.name,
				description:
					tool.meta?.description || tool.meta?.manifest?.description || 'No description available',
				serverName: serverName,
				isPublic: is_public,
				scopePrefix: scopePrefix,
				enabled: selectedToolIds.includes(tool.id),
				specs: tool.specs || [],
				hasStructuredOutput: tool.meta?.manifest?.has_structured_output || false,
				supportsJsonResponse: tool.meta?.manifest?.supports_json_response || false,
				outputSchema: tool.meta?.manifest?.output_schema || null,
				serverId,
				groupKey
			};
			return acc;
		}, {});
	};

	const toggleTool = (toolId: string) => {
		if (selectedToolIds.includes(toolId)) {
			selectedToolIds = selectedToolIds.filter((id) => id !== toolId);
		} else {
			selectedToolIds = [...selectedToolIds, toolId];
		}
		dispatch('change', { selectedToolIds });
	};

	const toggleAllServerTools = (groupKey: string, enable: boolean) => {
		const serverToolIds = Object.entries(mcpTools)
			.filter(([_, tool]) => tool.groupKey === groupKey)
			.map(([_, tool]) => tool.id);

		if (enable) {
			// Add all server tools to selectedToolIds
			const newToolIds = serverToolIds.filter((id) => !selectedToolIds.includes(id));
			selectedToolIds = [...selectedToolIds, ...newToolIds];
		} else {
			// Remove all server tools from selectedToolIds
			selectedToolIds = selectedToolIds.filter((id) => !serverToolIds.includes(id));
		}

		dispatch('change', { selectedToolIds });
	};

	const getServerToolsStatus = (groupKey: string) => {
		const serverToolIds = Object.entries(mcpTools)
			.filter(([_, tool]) => tool.groupKey === groupKey)
			.map(([_, tool]) => tool.id);

		if (serverToolIds.length === 0)
			return { allEnabled: false, someEnabled: false, noneEnabled: true };

		const enabledCount = serverToolIds.filter((id) => selectedToolIds.includes(id)).length;
		return {
			allEnabled: enabledCount === serverToolIds.length,
			someEnabled: enabledCount > 0 && enabledCount < serverToolIds.length,
			noneEnabled: enabledCount === 0
		};
	};

	const refreshTools = async () => {
		loading = true;
		try {
			await _tools.set(await getTools(localStorage.token));
		} finally {
			loading = false;
		}
	};

	// Handle dropdown open/close
	const handleOpenChange = (open: boolean) => {
		show = open;
		if (!open) {
			searchValue = '';
		} else {
			// Initialize tools when dropdown opens
			init();
		}
	};

	$: if (show) {
		init();
	}
</script>

{#if hasMcpTools}
	<DropdownMenu.Root bind:open={show} onOpenChange={handleOpenChange}>
		<DropdownMenu.Trigger asChild let:builder>
			<Tooltip content="MCP Tools" placement="top">
				<button
					use:builder.action
					{...builder}
					class="flex cursor-pointer px-2 py-1 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-md hover:shadow-lg transition-all duration-200 transform hover:scale-[1.02]"
					type="button"
					aria-label="MCP Tools"
				>
					<div class="flex items-center gap-1.5">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
							/>
						</svg>
						<span class="text-xs font-medium">MCP</span>
						{#if selectedToolIds.filter((id) => id.startsWith('mcp:')).length > 0}
							<span class="bg-white/20 text-xs px-1.5 py-0.5 rounded-full">
								{selectedToolIds.filter((id) => id.startsWith('mcp:')).length}
							</span>
						{/if}
					</div>
				</button>
			</Tooltip>
		</DropdownMenu.Trigger>

		<DropdownMenu.Content
			class="w-[400px] max-h-[500px] rounded-lg px-1 py-1 border border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={8}
			side="top"
			align="start"
			transition={flyAndScale}
		>
			<!-- Header -->
			<div class="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center gap-2 text-sm font-medium text-gray-900 dark:text-white">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="size-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
						/>
					</svg>
					<span>MCP Tools</span>
					<div class="ml-auto flex items-center gap-2">
						<button
							class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
							on:click={refreshTools}
							disabled={loading}
							title="Refresh Tools"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-3 {loading ? 'animate-spin' : ''}"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
								/>
							</svg>
						</button>
					</div>
				</div>
				<!-- Warning message -->
				<div
					class="mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md"
				>
					<div class="flex items-start gap-2">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
							/>
						</svg>
						<div class="text-xs text-yellow-800 dark:text-yellow-200">
							<p class="font-medium">External Tool Warning</p>
							<p class="mt-1">
								MCP tools connect to external services and may share data. Use with caution and
								verify tool sources. More tools can be added via Workspace - MCP Servers.
							</p>
						</div>
					</div>
				</div>
			</div>

			<!-- Search -->
			<div class="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
				<input
					bind:value={searchValue}
					type="text"
					placeholder="Search tools..."
					class="w-full px-3 py-2 text-sm bg-gray-50 dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
				/>
			</div>

			<!-- Tools List -->
			{#if Object.keys(mcpTools).length === 0}
				<div class="px-3 py-4 text-center text-gray-500 dark:text-gray-400 text-sm">
					No MCP tools available
				</div>
			{:else}
				<div class="max-h-80 overflow-y-auto">
					{#each Object.entries(groupedTools) as [groupKey, tools]}
						{@const status = getServerToolsStatus(groupKey)}
						<!-- Server group header with actions -->
						<div class="flex items-center gap-2 px-3 py-1">
							<div
								class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide flex-shrink-0"
							>
								{tools[0][1].serverName}
								<span class="ml-1 text-[10px] {tools[0][1].isPublic ? 'text-blue-600 dark:text-blue-400' : 'text-green-600 dark:text-green-400'}">
									{tools[0][1].isPublic ? '[Public]' : '[Private]'}
								</span>
							</div>
							<div class="flex items-center gap-1 ml-auto">
								{#if !status.allEnabled}
									<Tooltip content="Enable All">
										<button
											class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
											on:click={() => toggleAllServerTools(groupKey, true)}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2"
												stroke="currentColor"
												class="size-3 text-green-600 dark:text-green-400"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}
								{#if status.someEnabled || status.allEnabled}
									<Tooltip content="Disable All">
										<button
											class="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
											on:click={() => toggleAllServerTools(groupKey, false)}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="2"
												stroke="currentColor"
												class="size-3 text-red-600 dark:text-red-400"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15 12H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}
							</div>
						</div>
						{#each tools as [toolId, tool]}
							<DropdownMenu.Item asChild>
								<Tooltip content={tool.description} placement="left">
									<button
										class="flex w-full justify-between gap-2 items-center px-3 py-2 text-sm cursor-pointer rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
										on:click={() => toggleTool(tool.id)}
									>
										<div class="flex-1 min-w-0">
											<div class="flex items-center gap-2 min-w-0">
												<div class="flex-shrink-0">
													<div
														class="size-2 rounded-full {selectedToolIds.includes(tool.id)
															? 'bg-green-500'
															: 'bg-gray-300 dark:bg-gray-600'}"
													></div>
												</div>
												<div class="truncate">
													<div class="font-semibold text-base">
														<span class="text-xs font-normal {tool.isPublic ? 'text-blue-600 dark:text-blue-400' : 'text-green-600 dark:text-green-400'} mr-1">{tool.isPublic ? '[Public]' : '[Private]'}</span>
														{tool.displayName.replace(/^Mcp:\s*/i, '').replace(/^Jira\s+/i, '')}
													</div>
												</div>
											</div>
											<div class="flex items-center gap-1 flex-shrink-0">
												{#if tool.hasStructuredOutput}
													<Tooltip content="Structured Output">
														<div
															class="size-4 rounded bg-blue-100 dark:bg-blue-900 flex items-center justify-center"
														>
															<svg
																xmlns="http://www.w3.org/2000/svg"
																fill="none"
																viewBox="0 0 24 24"
																stroke-width="2"
																stroke="currentColor"
																class="size-2.5 text-blue-600 dark:text-blue-400"
															>
																<path
																	stroke-linecap="round"
																	stroke-linejoin="round"
																	d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"
																/>
															</svg>
														</div>
													</Tooltip>
												{/if}
											</div>
										</button>
								</Tooltip>
							</DropdownMenu.Item>
						{/each}
					{/each}
				</div>
			{/if}
		</DropdownMenu.Content>
	</DropdownMenu.Root>
{/if}
