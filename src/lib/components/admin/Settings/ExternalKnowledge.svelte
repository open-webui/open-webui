<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';

	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ExperimentalBadge from '$lib/components/common/ExperimentalBadge.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import DatabaseSettings from '$lib/components/icons/DatabaseSettings.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import {
		createExternalKnowledgeConnection,
		createExternalKnowledgeSource,
		deleteExternalKnowledgeConnection,
		getExternalKnowledgeConnections,
		searchKnowledgeBases,
		listExternalKnowledgeStores,
		testExternalKnowledgeSource,
		updateExternalKnowledgeConnection,
		updateExternalKnowledgeSource,
		updateKnowledgeAccessGrants
	} from '$lib/apis/knowledge';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	type ExternalKnowledgeConnection = {
		id: string;
		name: string;
		provider: string;
		endpoint: string;
		config?: Record<string, any>;
		capabilities?: Record<string, any>;
		enabled?: boolean;
		auth_configured?: boolean;
	};

	type ExternalKnowledgeItem = {
		id: string;
		name: string;
		description?: string;
		access_grants?: any[];
		meta?: {
			external?: {
				connection_id?: string;
				provider?: string;
				source?: {
					name?: string;
					config?: Record<string, any>;
				};
			};
		};
	};

	// Providers that search by text server-side, so sources need no field mapping.
	const TEXT_SEARCH_PROVIDERS = ['openai'];
	const DEFAULT_PROVIDER = 'openai';

	let loading = false;
	let testing = false;
	let verifying = false;
	// Stores the connection can search, offered as suggestions for the Vector Store ID.
	let storeOptions: { id: string; name: string }[] = [];
	// A text-search knowledge base can cover several stores; results are merged.
	let storeIds: string[] = [];
	let storeIdInput = '';
	// Save a connection whose stores are listed as knowledge bases, live, instead of one knowledge base.
	let listStores = false;
	let creating = false;
	let showSourceModal = false;
	let connections: ExternalKnowledgeConnection[] = [];
	let items: ExternalKnowledgeItem[] = [];
	let editingItem: ExternalKnowledgeItem | null = null;
	let editingConnection: ExternalKnowledgeConnection | null = null;
	let accessGrants: any[] = [];
	let testResult: {
		documents?: string[];
		metadatas?: Record<string, any>[];
		distances?: number[];
	} | null = null;

	let sourceForm = {
		name: '',
		description: '',
		provider: DEFAULT_PROVIDER,
		endpoint: '',
		apiKey: '',
		timeout: 30,
		dbName: '',
		sourceName: '',
		contentField: 'payload.text',
		vectorField: '',
		metadataField: 'payload.metadata',
		documentIdField: 'id',
		tableName: 'document_chunk',
		collectionField: 'collection_name',
		testQuery: ''
	};

	$: textSearch = TEXT_SEARCH_PROVIDERS.includes(sourceForm.provider);
	$: connectionMode = listStores && textSearch && !editingItem;

	// Like model_ids on provider connections: a store_ids list (empty means all) lists the stores.
	const hasStoreIds = (connection?: ExternalKnowledgeConnection) =>
		Array.isArray(connection?.config?.store_ids);

	const schemaDefaults = (provider = sourceForm.provider) => {
		if (provider === 'milvus') {
			return {
				contentField: 'data.text',
				vectorField: 'vector',
				metadataField: 'metadata',
				documentIdField: 'id',
				tableName: 'document_chunk',
				collectionField: 'collection_name'
			};
		}
		if (provider === 'pgvector') {
			return {
				contentField: 'text',
				vectorField: 'vector',
				metadataField: 'vmetadata',
				documentIdField: 'id',
				tableName: 'document_chunk',
				collectionField: 'collection_name'
			};
		}
		return {
			contentField: 'payload.text',
			vectorField: '',
			metadataField: 'payload.metadata',
			documentIdField: 'id',
			tableName: 'document_chunk',
			collectionField: 'collection_name'
		};
	};

	const resetForm = () => {
		sourceForm = {
			name: '',
			description: '',
			provider: DEFAULT_PROVIDER,
			endpoint: '',
			apiKey: '',
			timeout: 30,
			dbName: '',
			sourceName: '',
			testQuery: '',
			...schemaDefaults(DEFAULT_PROVIDER)
		};
		accessGrants = [];
		testResult = null;
		storeOptions = [];
		storeIds = [];
		storeIdInput = '';
		listStores = false;
		editingItem = null;
		editingConnection = null;
	};

	const openEditConnection = (connection: ExternalKnowledgeConnection) => {
		resetForm();
		editingConnection = connection;
		listStores = true;
		sourceForm = {
			...sourceForm,
			name: connection.name ?? '',
			provider: connection.provider,
			endpoint: connection.endpoint ?? '',
			timeout: connection.config?.timeout ?? 30
		};
		storeIds = connection.config?.store_ids ?? [];
		accessGrants = structuredClone(connection.config?.access_grants ?? []);
		showSourceModal = true;
	};

	const openCreateSource = () => {
		resetForm();
		showSourceModal = true;
	};

	const openEditSource = (item: ExternalKnowledgeItem) => {
		const connection = connectionForItem(item);
		if (!connection) {
			toast.error($i18n.t('External connection not found.'));
			return;
		}

		resetForm();
		editingItem = item;
		editingConnection = connection;

		const source = item.meta?.external?.source;
		const sourceConfig = source?.config ?? {};
		const defaults = schemaDefaults(connection.provider);
		sourceForm = {
			name: item.name ?? '',
			description: item.description ?? '',
			provider: connection.provider ?? 'qdrant',
			endpoint: connection.endpoint ?? '',
			apiKey: '',
			timeout: connection.config?.timeout ?? 30,
			dbName: connection.config?.db_name ?? '',
			sourceName: source?.name ?? '',
			testQuery: '',
			contentField: sourceConfig.content_field ?? defaults.contentField,
			vectorField: sourceConfig.vector_field ?? defaults.vectorField,
			metadataField: sourceConfig.metadata_field ?? defaults.metadataField,
			documentIdField: sourceConfig.document_id_field ?? defaults.documentIdField,
			tableName: sourceConfig.table_name ?? defaults.tableName,
			collectionField: sourceConfig.collection_field ?? defaults.collectionField
		};
		storeIds = Array.isArray(sourceConfig.vector_store_ids)
			? sourceConfig.vector_store_ids
			: (source?.name ?? '')
					.split(',')
					.map((id: string) => id.trim())
					.filter(Boolean);
		accessGrants = structuredClone(item.access_grants ?? []);
		showSourceModal = true;
	};

	const markUntested = () => {
		testResult = null;
	};

	const refresh = async () => {
		loading = true;
		const [connectionRes, knowledgeRes] = await Promise.all([
			getExternalKnowledgeConnections(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return null;
			}),
			searchKnowledgeBases(localStorage.token, null, null, 1, 'external').catch((error) => {
				toast.error(`${error}`);
				return null;
			})
		]);
		connections = connectionRes?.items ?? [];
		// Stores a connection lists are managed through that connection's row.
		items = (knowledgeRes?.items ?? []).filter(
			(item: ExternalKnowledgeItem) => !hasStoreIds(connectionForItem(item))
		);
		loading = false;
	};

	const endpointPlaceholder = () => {
		if (sourceForm.provider === 'openai') {
			return 'http://litellm:4000/v1';
		}
		if (sourceForm.provider === 'pgvector') {
			return 'postgresql://user:password@host:5432/db';
		}
		if (sourceForm.provider === 'milvus') {
			return 'http://milvus.example.com:19530';
		}
		return 'https://qdrant.example.com';
	};

	const connectionForItem = (item: ExternalKnowledgeItem) =>
		connections.find((connection) => connection.id === item?.meta?.external?.connection_id);

	const connectionPayload = () => ({
		name:
			sourceForm.name.trim() ||
			sourceForm.sourceName.trim() ||
			$i18n.t('External Knowledge Source'),
		provider: sourceForm.provider,
		endpoint: sourceForm.endpoint,
		auth_config:
			sourceForm.provider === 'pgvector'
				? {}
				: sourceForm.apiKey
					? { type: 'bearer', api_key: sourceForm.apiKey }
					: editingConnection
						? null
						: {},
		config: {
			timeout: Number(sourceForm.timeout) || 30,
			...(sourceForm.provider === 'milvus' && sourceForm.dbName
				? { db_name: sourceForm.dbName }
				: {})
		},
		capabilities: { retrieve: true },
		enabled: editingConnection?.enabled !== false
	});

	const sourcePayload = () => {
		if (textSearch) {
			return {
				type: 'collection',
				name: storeIds.join(', '),
				config: { vector_store_ids: storeIds }
			};
		}

		const config: Record<string, string> = {
			content_field: sourceForm.contentField.trim(),
			...(sourceForm.vectorField.trim() ? { vector_field: sourceForm.vectorField.trim() } : {}),
			...(sourceForm.metadataField.trim()
				? { metadata_field: sourceForm.metadataField.trim() }
				: {}),
			...(sourceForm.documentIdField.trim()
				? { document_id_field: sourceForm.documentIdField.trim() }
				: {})
		};

		if (sourceForm.provider === 'pgvector') {
			config.table_name = sourceForm.tableName.trim();
			config.collection_field = sourceForm.collectionField.trim();
		}

		return {
			type: 'collection',
			name: sourceForm.sourceName.trim(),
			config
		};
	};

	const testFormIsValid = () =>
		!!sourceForm.endpoint.trim() &&
		(textSearch ? storeIds.length > 0 : !!sourceForm.sourceName.trim()) &&
		(textSearch ||
			(!!sourceForm.contentField.trim() &&
				(sourceForm.provider === 'qdrant' || !!sourceForm.vectorField.trim()) &&
				(sourceForm.provider !== 'pgvector' ||
					(!!sourceForm.tableName.trim() && !!sourceForm.collectionField.trim())))) &&
		!!sourceForm.testQuery.trim();

	const sourceFormIsValid = () => !!sourceForm.name.trim() && testFormIsValid();

	const loadStoreOptions = async () => {
		const res = await listExternalKnowledgeStores(localStorage.token, {
			...(editingConnection?.id ? { connection_id: editingConnection.id } : {}),
			connection: connectionPayload()
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		storeOptions = res?.items ?? [];
		return !!res;
	};

	// Checks the endpoint and key by listing the stores, which then fill the Vector Store ID suggestions.
	const verifyConnection = async () => {
		if (!sourceForm.endpoint.trim()) {
			toast.error($i18n.t('Fill the required fields first.'));
			return;
		}

		verifying = true;
		if (await loadStoreOptions()) {
			toast.success($i18n.t('Loaded {{COUNT}} vector stores.', { COUNT: storeOptions.length }));
		}
		verifying = false;
	};

	const addStoreIds = (value: string) => {
		const ids = value
			.split(',')
			.map((id) => id.trim())
			.filter((id) => id && !storeIds.includes(id));
		if (ids.length) {
			storeIds = [...storeIds, ...ids];
			markUntested();
		}
		storeIdInput = '';
	};

	const removeStoreId = (id: string) => {
		storeIds = storeIds.filter((item) => item !== id);
		markUntested();
	};

	const testSource = async () => {
		addStoreIds(storeIdInput);
		if (!testFormIsValid()) {
			toast.error($i18n.t('Fill the source fields and test query first.'));
			return;
		}

		testing = true;
		testResult = null;
		const res = await testExternalKnowledgeSource(localStorage.token, {
			...(editingConnection?.id ? { connection_id: editingConnection.id } : {}),
			connection: connectionPayload(),
			source: sourcePayload(),
			query: sourceForm.testQuery,
			count: 5
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res?.documents?.length) {
			testResult = res;
			toast.success($i18n.t('Test succeeded.'));
		} else if (res) {
			toast.error($i18n.t('Test returned no results.'));
		}
		testing = false;
	};

	const createSource = async () => {
		if (!sourceFormIsValid()) {
			toast.error($i18n.t('Fill the required fields first.'));
			return;
		}

		if (!testResult?.documents?.length) {
			// Earlier wording, kept so i18n:parse does not drop its translations: $i18n.t('Test must pass before a source is created.')
			toast.error($i18n.t('Test the source before creating it.'));
			return;
		}

		creating = true;
		const res = await createExternalKnowledgeSource(localStorage.token, {
			name: sourceForm.name,
			description: sourceForm.description,
			connection: connectionPayload(),
			source: sourcePayload(),
			access_grants: accessGrants,
			test_query: sourceForm.testQuery,
			test_count: 5
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Knowledge source created.'));
			showSourceModal = false;
			resetForm();
			await refresh();
		}
		creating = false;
	};

	const updateSource = async () => {
		if (!editingItem) return;

		if (!sourceFormIsValid()) {
			toast.error($i18n.t('Fill the required fields first.'));
			return;
		}

		if (!testResult?.documents?.length) {
			toast.error($i18n.t('Test the source before saving it.'));
			return;
		}

		creating = true;
		const res = await updateExternalKnowledgeSource(localStorage.token, editingItem.id, {
			name: sourceForm.name,
			description: sourceForm.description,
			connection: connectionPayload(),
			source: sourcePayload(),
			test_query: sourceForm.testQuery,
			test_count: 5
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Knowledge source updated.'));
			showSourceModal = false;
			resetForm();
			await refresh();
		}
		creating = false;
	};

	const saveConnection = async () => {
		if (!sourceForm.name.trim() || !sourceForm.endpoint.trim()) {
			toast.error($i18n.t('Fill the required fields first.'));
			return;
		}

		creating = true;
		const payload = connectionPayload();
		const connection = {
			...payload,
			config: { ...payload.config, store_ids: storeIds, access_grants: accessGrants }
		};
		const res = await (
			editingConnection
				? updateExternalKnowledgeConnection(localStorage.token, editingConnection.id, connection)
				: createExternalKnowledgeConnection(localStorage.token, connection)
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Saved'));
			showSourceModal = false;
			resetForm();
			await refresh();
		}
		creating = false;
	};

	const deleteConnection = async () => {
		if (!editingConnection) return;

		creating = true;
		const res = await deleteExternalKnowledgeConnection(
			localStorage.token,
			editingConnection.id
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Deleted'));
			showSourceModal = false;
			resetForm();
			await refresh();
		}
		creating = false;
	};

	const submitSource = async () => {
		if (creating) return;
		addStoreIds(storeIdInput);
		if (connectionMode) {
			await saveConnection();
		} else if (editingItem) {
			await updateSource();
		} else {
			await createSource();
		}
	};

	const toggleConnection = async (connection?: ExternalKnowledgeConnection) => {
		if (!connection) return;

		const res = await updateExternalKnowledgeConnection(localStorage.token, connection.id, {
			name: connection.name,
			provider: connection.provider,
			endpoint: connection.endpoint,
			auth_config: null,
			config: connection.config ?? {},
			capabilities: connection.capabilities ?? { retrieve: true },
			enabled: !connection.enabled
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			await refresh();
		}
	};

	const updateProvider = () => {
		sourceForm = {
			...sourceForm,
			...schemaDefaults(sourceForm.provider)
		};
		storeOptions = [];
		markUntested();
	};

	onMount(refresh);
</script>

<Modal
	ariaLabel={editingItem || editingConnection
		? $i18n.t('Edit Knowledge Connection')
		: $i18n.t('Add Knowledge Connection')}
	bind:show={showSourceModal}
	size="sm"
	className="bg-base-0 dark:bg-base-900 rounded-4xl"
>
	<div>
		<div class="flex justify-between dark:text-base-100 px-4 pt-3 pb-1">
			<h1 class="text-sm font-medium self-center">
				{editingItem || editingConnection
					? $i18n.t('Edit Knowledge Connection')
					: $i18n.t('Add Knowledge Connection')}
			</h1>

			<button
				class="self-center rounded-lg py-1 text-base-500 transition hover:text-base-700 dark:text-base-400 dark:hover:text-base-200 px-0"
				aria-label={$i18n.t('Close')}
				type="button"
				on:click={() => {
					showSourceModal = false;
					resetForm();
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-base-200">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					inert={creating}
					aria-busy={creating}
					on:submit|preventDefault={submitSource}
				>
					<div class="px-1">
						<div class="flex gap-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-base-500" for="external-source-name"
										>{$i18n.t('Name')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-name"
										class="w-full flex-1 text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
										bind:value={sourceForm.name}
										on:input={markUntested}
										placeholder={$i18n.t('Research Knowledge')}
										required
									/>
								</div>
							</div>

							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-base-500" for="external-source-provider"
										>{$i18n.t('Provider')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<SettingsSelect
										id="external-source-provider"
										bind:value={sourceForm.provider}
										className="w-full"
										on:change={updateProvider}
										selectClassName="text-sm"
									>
										<option value="openai">{$i18n.t('OpenAI-compatible')}</option>
										<option value="qdrant">Qdrant</option>
										<option value="milvus">Milvus</option>
										<option value="pgvector">pgvector</option>
									</SettingsSelect>
								</div>
							</div>
						</div>

						{#if !connectionMode}
							<div class="flex flex-col w-full mt-2">
								<label class="text-xs text-base-500 mb-0.5" for="external-source-description"
									>{$i18n.t('Description')}</label
								>
								<textarea
									id="external-source-description"
									class="w-full text-sm bg-transparent outline-hidden resize-none placeholder:text-base-300 dark:placeholder:text-base-700"
									rows="2"
									bind:value={sourceForm.description}
								></textarea>
							</div>
						{/if}

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-base-500" for="external-source-endpoint"
										>{$i18n.t('Endpoint')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-endpoint"
										class="w-full flex-1 text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
										bind:value={sourceForm.endpoint}
										on:input={markUntested}
										placeholder={endpointPlaceholder()}
										required
									/>

									{#if textSearch}
										<Tooltip
											content={$i18n.t('Verify Connection')}
											className="shrink-0 flex items-center mr-1"
										>
											<button
												class="self-center p-1 bg-transparent hover:bg-base-50/70 dark:hover:bg-base-850/50 rounded-lg transition"
												type="button"
												on:click={verifyConnection}
												disabled={verifying}
												aria-label={$i18n.t('Verify Connection')}
											>
												{#if verifying}
													<Spinner />
												{:else}
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="w-4 h-4"
														aria-hidden="true"
													>
														<path
															fill-rule="evenodd"
															d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
															clip-rule="evenodd"
														/>
													</svg>
												{/if}
											</button>
										</Tooltip>
									{/if}
								</div>
							</div>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-base-500" for="external-source-timeout"
										>{$i18n.t('Timeout')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-timeout"
										class="w-full text-sm bg-transparent outline-hidden"
										type="number"
										bind:value={sourceForm.timeout}
										on:input={markUntested}
									/>
								</div>
							</div>

							{#if sourceForm.provider !== 'pgvector'}
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-api-key"
											>{$i18n.t('API Key / Token')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-api-key"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											type="password"
											bind:value={sourceForm.apiKey}
											on:input={markUntested}
											autocomplete="off"
										/>
									</div>
								</div>
							{/if}
						</div>

						{#if sourceForm.provider === 'milvus'}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-db-name"
											>{$i18n.t('Database')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-db-name"
											class="w-full text-sm bg-transparent outline-hidden"
											bind:value={sourceForm.dbName}
											on:input={markUntested}
											placeholder={$i18n.t('Default')}
										/>
									</div>
								</div>
							</div>
						{/if}

						<hr class="border-base-100/50 dark:border-base-700/10 my-2.5 w-full" />

						{#if textSearch && !editingItem}
							<div class="flex justify-between items-center mb-2">
								<label class="text-xs text-base-500" for="external-source-stores-as-knowledge-bases"
									>{$i18n.t('List stores as knowledge bases')}</label
								>
								<Switch
									id="external-source-stores-as-knowledge-bases"
									bind:state={listStores}
									disabled={!!editingConnection}
								/>
							</div>
						{/if}

						<div class="flex gap-2">
							<div class="flex flex-col w-full">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-base-500" for="external-source-collection"
										>{connectionMode
											? $i18n.t('Store IDs')
											: textSearch
												? $i18n.t('Vector Stores')
												: $i18n.t('Collection')}</label
									>
								</div>
								{#if textSearch}
									{#if storeIds.length > 0}
										<div class="flex flex-wrap gap-1 mb-1">
											{#each storeIds as id (id)}
												<div
													class="flex items-center gap-1 rounded-lg bg-base-50 dark:bg-base-850 px-2 py-0.5 text-xs"
												>
													<span class="line-clamp-1"
														>{storeOptions.find((store) => store.id === id)?.name ?? id}</span
													>
													<button
														class="text-base-400 hover:text-base-900 dark:hover:text-base-0 transition"
														type="button"
														aria-label={$i18n.t('Remove')}
														on:click={() => removeStoreId(id)}
													>
														<XMark className="size-3" />
													</button>
												</div>
											{/each}
										</div>
									{/if}
									<input
										id="external-source-collection"
										class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
										bind:value={storeIdInput}
										on:change={() => addStoreIds(storeIdInput)}
										on:keydown={(e) => {
											if (e.key === 'Enter' || e.key === ',') {
												e.preventDefault();
												addStoreIds(storeIdInput);
											}
										}}
										placeholder={connectionMode
											? $i18n.t('Leave empty to include all stores')
											: $i18n.t('Add a vector store ID')}
										list="external-source-stores"
										autocomplete="off"
									/>
									<datalist id="external-source-stores">
										{#each storeOptions.filter((store) => !storeIds.includes(store.id)) as store (store.id)}
											<option value={store.id}>{store.name}</option>
										{/each}
									</datalist>
								{:else}
									<div class="flex flex-1 items-center">
										<input
											id="external-source-collection"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											bind:value={sourceForm.sourceName}
											on:input={markUntested}
											placeholder="research-docs"
											required
										/>
									</div>
								{/if}
							</div>
						</div>

						{#if sourceForm.provider === 'pgvector'}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-table"
											>{$i18n.t('Table')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-table"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											bind:value={sourceForm.tableName}
											on:input={markUntested}
											placeholder="document_chunk"
											required
										/>
									</div>
								</div>

								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-collection-field"
											>{$i18n.t('Collection Field')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-collection-field"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											bind:value={sourceForm.collectionField}
											on:input={markUntested}
											placeholder="collection_name"
											required
										/>
									</div>
								</div>
							</div>
						{/if}

						{#if !textSearch}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-content-field"
											>{$i18n.t('Content Field')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-content-field"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											bind:value={sourceForm.contentField}
											on:input={markUntested}
											placeholder={sourceForm.provider === 'pgvector' ? 'text' : 'payload.text'}
											required
										/>
									</div>
								</div>

								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-vector-field">
											{$i18n.t('Vector Field')}
										</label>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-vector-field"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											bind:value={sourceForm.vectorField}
											on:input={markUntested}
											placeholder={sourceForm.provider === 'qdrant' ? $i18n.t('Default') : 'vector'}
											required={sourceForm.provider !== 'qdrant'}
										/>
									</div>
								</div>
							</div>

							<div class="flex gap-2 mt-2">
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-metadata-field"
											>{$i18n.t('Metadata Field')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-metadata-field"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											bind:value={sourceForm.metadataField}
											on:input={markUntested}
											placeholder={sourceForm.provider === 'pgvector'
												? 'vmetadata'
												: 'payload.metadata'}
										/>
									</div>
								</div>

								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-document-id-field"
											>{$i18n.t('Document ID Field')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-document-id-field"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											bind:value={sourceForm.documentIdField}
											on:input={markUntested}
											placeholder="id"
										/>
									</div>
								</div>
							</div>
						{/if}

						{#if connectionMode}
							<div class="text-xs text-base-500 mt-2">
								{$i18n.t(
									'Each store this connection lists appears as a knowledge base, read live from the endpoint. Access below applies to all of them.'
								)}
							</div>
						{:else}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col w-full">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-base-500" for="external-source-test-query"
											>{$i18n.t('Test Query')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-test-query"
											class="w-full flex-1 text-sm bg-transparent outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											bind:value={sourceForm.testQuery}
											on:input={markUntested}
											placeholder={$i18n.t('Ask a test question')}
											required
										/>

										<Tooltip
											content={textSearch ? $i18n.t('Test') : $i18n.t('Verify Connection')}
											className="shrink-0 flex items-center mr-1"
										>
											<button
												class="self-center p-1 bg-transparent hover:bg-base-50/70 dark:hover:bg-base-850/50 rounded-lg transition"
												type="button"
												on:click={testSource}
												disabled={testing}
												aria-label={textSearch ? $i18n.t('Test') : $i18n.t('Verify Connection')}
											>
												{#if testing}
													<Spinner />
												{:else}
													<svg
														xmlns="http://www.w3.org/2000/svg"
														viewBox="0 0 20 20"
														fill="currentColor"
														class="w-4 h-4"
														aria-hidden="true"
													>
														<path
															fill-rule="evenodd"
															d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
															clip-rule="evenodd"
														/>
													</svg>
												{/if}
											</button>
										</Tooltip>
									</div>

									{#if !textSearch}
										<div class="text-xs text-base-500 mt-1">
											<!-- LICENSE covers this Open WebUI wordmark.
										Do not alter, remove, obscure, or replace it except as LICENSE permits:
										https://docs.openwebui.com/license. -->
											{$i18n.t(
												'External vectors must be generated with the same embedding model configured in Open WebUI.'
											)}
										</div>
									{/if}
								</div>
							</div>
						{/if}

						<hr class="border-base-100/50 dark:border-base-700/10 my-2.5 w-full" />

						<AccessControl
							bind:accessGrants
							accessRoles={['read']}
							share={true}
							sharePublic={true}
							shareUsers={true}
							onChange={async (grants) => {
								if (editingItem) {
									const item = editingItem;
									creating = true;
									try {
										await updateKnowledgeAccessGrants(localStorage.token, item.id, grants);
										item.access_grants = structuredClone(grants);
										if (editingItem === item) accessGrants = item.access_grants;
										toast.success($i18n.t('Saved'));
									} catch (error) {
										if (editingItem === item)
											accessGrants = structuredClone(item.access_grants ?? []);
										toast.error(`${error}`);
									} finally {
										creating = false;
									}
								}
							}}
						/>

						<div class="flex justify-between items-center pt-3 text-sm font-normal">
							{#if connectionMode && editingConnection}
								<button
									class="text-xs text-base-500 hover:text-red-600 dark:hover:text-red-400 transition"
									type="button"
									on:click={deleteConnection}
								>
									{$i18n.t('Delete')}
								</button>
							{:else}
								<div></div>
							{/if}

							<button
								class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0 disabled:cursor-not-allowed"
								type="submit"
								disabled={creating ||
									(connectionMode
										? !sourceForm.name.trim() || !sourceForm.endpoint.trim()
										: !sourceFormIsValid() || !testResult?.documents?.length)}
							>
								{editingItem || editingConnection ? $i18n.t('Save') : $i18n.t('Create')}
								{#if creating}<Spinner className="size-3" />{/if}
							</button>
						</div>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<div class="flex w-full flex-col justify-between text-xs">
	<div class="mb-2 flex items-center justify-between">
		<div class="flex items-center gap-2 leading-none text-base-600 dark:text-base-400">
			<Tooltip
				content={$i18n.t(
					'Connect external knowledge sources. A source is created only after its test passes.'
				)}
				placement="top-start"
				className="w-fit"
			>
				<div
					class="underline decoration-dotted decoration-base-400/70 underline-offset-4 dark:decoration-base-500 cursor-help"
				>
					{$i18n.t('settings.admin.integrations.externalKnowledge.title')}
				</div>
			</Tooltip>
			<ExperimentalBadge />
		</div>

		<Tooltip content={$i18n.t('settings.admin.integrations.externalKnowledge.addConnection.label')}>
			<button
				aria-label={$i18n.t('settings.admin.integrations.externalKnowledge.addConnection.label')}
				class="flex size-6 items-center justify-center rounded-lg text-base-400 transition-colors hover:bg-base-1000/5 hover:text-base-900 dark:text-base-600 dark:hover:bg-base-0/5 dark:hover:text-base-0"
				on:click={openCreateSource}
				type="button"
			>
				<Plus />
			</button>
		</Tooltip>
	</div>

	<div class="flex flex-col gap-1.5">
		{#each connections.filter(hasStoreIds) as connection (connection.id)}
			<div class="group/setting-row flex w-full gap-2 items-center">
				<div
					class="flex-1 relative flex gap-1.5 items-center min-w-0 {connection.enabled === false
						? 'opacity-50'
						: ''}"
				>
					<Tooltip content={$i18n.t('Knowledge')}>
						<DatabaseSettings className="size-4" strokeWidth="1.5" />
					</Tooltip>
					<div class="outline-hidden w-full bg-transparent text-xs min-w-0 line-clamp-1">
						<button
							type="button"
							on:click={() => openEditConnection(connection)}
							class="text-left cursor-pointer text-base-600 dark:text-base-400 transition-colors duration-150 group-hover/setting-row:text-base-900 dark:group-hover/setting-row:text-white"
							>{connection.name}</button
						>
						{' '}
						<span class="text-base-500">
							{connection.provider} ·
							{connection.config?.store_ids?.length
								? $i18n.t('{{COUNT}} stores', { COUNT: connection.config.store_ids.length })
								: $i18n.t('All stores')}
						</span>
					</div>
				</div>

				<div class="flex gap-1 items-center">
					<Tooltip content={$i18n.t('Configure')}>
						<button
							class="self-center p-1 bg-transparent hover:bg-base-50/70 dark:hover:bg-base-850/50 rounded-lg transition"
							type="button"
							aria-label={$i18n.t('Configure')}
							on:click={() => openEditConnection(connection)}
						>
							<Cog6 />
						</button>
					</Tooltip>

					<Tooltip
						content={connection.enabled !== false ? $i18n.t('Enabled') : $i18n.t('Disabled')}
					>
						<Switch
							id={`knowledge-connection-${connection.id}-control`}
							state={connection.enabled !== false}
							on:change={() => toggleConnection(connection)}
						/>
					</Tooltip>
				</div>
			</div>
		{/each}

		{#each items as item}
			{@const connection = connectionForItem(item)}
			<div class="group/setting-row flex w-full gap-2 items-center">
				<Tooltip className="w-full relative" content={''} placement="top-start">
					<div class="flex w-full">
						<div
							class="flex-1 relative flex gap-1.5 items-center min-w-0 {connection?.enabled ===
							false
								? 'opacity-50'
								: ''}"
						>
							<Tooltip content={$i18n.t('Knowledge')}>
								<DatabaseSettings className="size-4" strokeWidth="1.5" />
							</Tooltip>

							<div class="outline-hidden w-full bg-transparent text-xs min-w-0 line-clamp-1">
								<button
									type="button"
									disabled={!connection}
									on:click={() => openEditSource(item)}
									class="text-left cursor-pointer disabled:cursor-default text-base-600 dark:text-base-400 transition-colors duration-150 group-hover/setting-row:text-base-900 group-focus-within/setting-row:text-base-900 dark:group-hover/setting-row:text-white dark:group-focus-within/setting-row:text-white"
									>{item.name}</button
								>
								{' '}
								<span class="text-base-500">
									{item?.meta?.external?.provider ?? connection?.provider}
									{item?.meta?.external?.source?.name ? `· ${item.meta.external.source.name}` : ''}
								</span>
							</div>
						</div>
					</div>
				</Tooltip>

				<div class="flex gap-1 items-center">
					<Tooltip content={$i18n.t('Configure')}>
						<button
							class="self-center p-1 bg-transparent hover:bg-base-50/70 dark:hover:bg-base-850/50 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
							type="button"
							disabled={!connection}
							aria-label={$i18n.t('Configure')}
							on:click={() => {
								openEditSource(item);
							}}
						>
							<Cog6 />
						</button>
					</Tooltip>

					<Tooltip
						content={connection?.enabled !== false ? $i18n.t('Enabled') : $i18n.t('Disabled')}
					>
						<Switch
							id={`knowledge-${item.id}-control`}
							state={connection?.enabled !== false}
							on:change={() => {
								toggleConnection(connection);
							}}
						/>
					</Tooltip>
				</div>
			</div>
		{/each}
	</div>

	{#if loading}
		<div class="py-2">
			<Spinner />
		</div>
	{:else if items.length === 0 && !connections.some(hasStoreIds)}
		<div class="text-[0.6875rem] text-base-400 dark:text-base-600">
			{$i18n.t('No external knowledge sources configured.')}
		</div>
	{/if}
</div>
