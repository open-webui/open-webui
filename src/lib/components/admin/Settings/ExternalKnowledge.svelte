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
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import DatabaseSettings from '$lib/components/icons/DatabaseSettings.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import {
		createExternalKnowledgeSource,
		getExternalKnowledgeConnections,
		searchKnowledgeBases,
		testExternalKnowledgeSource,
		updateExternalKnowledgeConnection,
		updateExternalKnowledgeSource
	} from '$lib/apis/knowledge';

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

	let loading = false;
	let testing = false;
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
		provider: 'qdrant',
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
			provider: 'qdrant',
			endpoint: '',
			apiKey: '',
			timeout: 30,
			dbName: '',
			sourceName: '',
			testQuery: '',
			...schemaDefaults('qdrant')
		};
		accessGrants = [];
		testResult = null;
		editingItem = null;
		editingConnection = null;
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
		accessGrants = item.access_grants ?? [];
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
		items = knowledgeRes?.items ?? [];
		loading = false;
	};

	const endpointPlaceholder = () => {
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
		!!sourceForm.sourceName.trim() &&
		!!sourceForm.contentField.trim() &&
		(sourceForm.provider === 'qdrant' || !!sourceForm.vectorField.trim()) &&
		(sourceForm.provider !== 'pgvector' ||
			(!!sourceForm.tableName.trim() && !!sourceForm.collectionField.trim())) &&
		!!sourceForm.testQuery.trim();

	const sourceFormIsValid = () => !!sourceForm.name.trim() && testFormIsValid();

	const testSource = async () => {
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
			access_grants: accessGrants,
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

	const submitSource = async () => {
		if (editingItem) {
			await updateSource();
		} else {
			await createSource();
		}
	};

	const toggleSource = async (item: ExternalKnowledgeItem) => {
		const connection = connectionForItem(item);
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
		markUntested();
	};

	onMount(refresh);
</script>

<Modal bind:show={showSourceModal} size="sm">
	<div>
		<div class="flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<h1 class="text-lg font-medium self-center font-primary">
				{editingItem ? $i18n.t('Edit Knowledge Connection') : $i18n.t('Add Knowledge Connection')}
			</h1>

			<button
				class="self-center"
				aria-label={$i18n.t('Close')}
				type="button"
				on:click={() => {
					showSourceModal = false;
					resetForm();
				}}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form class="flex flex-col w-full" on:submit|preventDefault={submitSource}>
					<div class="px-1">
						<div class="flex gap-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-gray-500" for="external-source-name"
										>{$i18n.t('Name')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-name"
										class="w-full flex-1 text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
										bind:value={sourceForm.name}
										on:input={markUntested}
										placeholder={$i18n.t('Research Knowledge')}
										required
									/>
								</div>
							</div>

							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-gray-500" for="external-source-provider"
										>{$i18n.t('Provider')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<select
										id="external-source-provider"
										class="w-full text-sm bg-transparent outline-hidden"
										bind:value={sourceForm.provider}
										on:change={updateProvider}
									>
										<option value="qdrant">Qdrant</option>
										<option value="milvus">Milvus</option>
										<option value="pgvector">pgvector</option>
									</select>
								</div>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<label class="text-xs text-gray-500 mb-0.5" for="external-source-description"
								>{$i18n.t('Description')}</label
							>
							<textarea
								id="external-source-description"
								class="w-full text-sm bg-transparent outline-hidden resize-none placeholder:text-gray-300 dark:placeholder:text-gray-700"
								rows="2"
								bind:value={sourceForm.description}
							></textarea>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-gray-500" for="external-source-endpoint"
										>{$i18n.t('Endpoint')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-endpoint"
										class="w-full flex-1 text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
										bind:value={sourceForm.endpoint}
										on:input={markUntested}
										placeholder={endpointPlaceholder()}
										required
									/>
								</div>
							</div>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-gray-500" for="external-source-timeout"
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
										<label class="text-xs text-gray-500" for="external-source-api-key"
											>{$i18n.t('API Key / Token')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-api-key"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
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
										<label class="text-xs text-gray-500" for="external-source-db-name"
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

						<hr class="border-gray-100/50 dark:border-gray-700/10 my-2.5 w-full" />

						<div class="flex gap-2">
							<div class="flex flex-col w-full">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-gray-500" for="external-source-collection"
										>{$i18n.t('Collection')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-collection"
										class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
										bind:value={sourceForm.sourceName}
										on:input={markUntested}
										placeholder="research-docs"
										required
									/>
								</div>
							</div>
						</div>

						{#if sourceForm.provider === 'pgvector'}
							<div class="flex gap-2 mt-2">
								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-gray-500" for="external-source-table"
											>{$i18n.t('Table')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-table"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
											bind:value={sourceForm.tableName}
											on:input={markUntested}
											placeholder="document_chunk"
											required
										/>
									</div>
								</div>

								<div class="flex flex-col flex-1">
									<div class="flex justify-between mb-0.5">
										<label class="text-xs text-gray-500" for="external-source-collection-field"
											>{$i18n.t('Collection Field')}</label
										>
									</div>
									<div class="flex flex-1 items-center">
										<input
											id="external-source-collection-field"
											class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
											bind:value={sourceForm.collectionField}
											on:input={markUntested}
											placeholder="collection_name"
											required
										/>
									</div>
								</div>
							</div>
						{/if}

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-gray-500" for="external-source-content-field"
										>{$i18n.t('Content Field')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-content-field"
										class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
										bind:value={sourceForm.contentField}
										on:input={markUntested}
										placeholder={sourceForm.provider === 'pgvector' ? 'text' : 'payload.text'}
										required
									/>
								</div>
							</div>

							<div class="flex flex-col flex-1">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-gray-500" for="external-source-vector-field">
										{$i18n.t('Vector Field')}
									</label>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-vector-field"
										class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
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
									<label class="text-xs text-gray-500" for="external-source-metadata-field"
										>{$i18n.t('Metadata Field')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-metadata-field"
										class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
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
									<label class="text-xs text-gray-500" for="external-source-document-id-field"
										>{$i18n.t('Document ID Field')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-document-id-field"
										class="w-full text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
										bind:value={sourceForm.documentIdField}
										on:input={markUntested}
										placeholder="id"
									/>
								</div>
							</div>
						</div>

						<div class="flex gap-2 mt-2">
							<div class="flex flex-col w-full">
								<div class="flex justify-between mb-0.5">
									<label class="text-xs text-gray-500" for="external-source-test-query"
										>{$i18n.t('Test Query')}</label
									>
								</div>
								<div class="flex flex-1 items-center">
									<input
										id="external-source-test-query"
										class="w-full flex-1 text-sm bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
										bind:value={sourceForm.testQuery}
										on:input={markUntested}
										placeholder={$i18n.t('Ask a test question')}
										required
									/>

									<Tooltip
										content={$i18n.t('Verify Connection')}
										className="shrink-0 flex items-center mr-1"
									>
										<button
											class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
											type="button"
											on:click={testSource}
											disabled={testing}
											aria-label={$i18n.t('Verify Connection')}
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

								<div class="text-xs text-gray-500 mt-1">
									{$i18n.t(
										'External vectors must be generated with the same embedding model configured in Open WebUI.'
									)}
								</div>
							</div>
						</div>

						<hr class="border-gray-100/50 dark:border-gray-700/10 my-2.5 w-full" />

						<AccessControl
							bind:accessGrants
							accessRoles={['read']}
							share={true}
							sharePublic={true}
							shareUsers={true}
						/>

						<div class="flex justify-between items-center pt-3 text-sm font-medium">
							<div></div>

							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
								type="submit"
								disabled={creating || !sourceFormIsValid() || !testResult?.documents?.length}
							>
								{editingItem ? $i18n.t('Save') : $i18n.t('Create')}
								{#if creating}<Spinner />{/if}
							</button>
						</div>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<div class="mb-2.5 flex flex-col w-full justify-between text-sm">
	<div class="flex justify-between items-center mb-1">
		<div class="flex items-center gap-2">
			<div class="font-medium">{$i18n.t('External Knowledge Sources')}</div>
			<span
				class="text-[0.65rem] font-medium uppercase px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400"
				>{$i18n.t('Experimental')}</span
			>
		</div>

		<Tooltip content={$i18n.t('Add Connection')}>
			<button class="px-1" on:click={openCreateSource} type="button">
				<Plus />
			</button>
		</Tooltip>
	</div>

	<div class="flex flex-col gap-1.5">
		{#each items as item}
			{@const connection = connectionForItem(item)}
			<div class="flex w-full gap-2 items-center">
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

							<div class="outline-hidden w-full bg-transparent text-sm min-w-0 line-clamp-1">
								<span>{item.name}</span>
								{' '}
								<span class="text-gray-500">
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
							class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
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
							state={connection?.enabled !== false}
							on:change={() => {
								toggleSource(item);
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
	{:else if items.length === 0}
		<div class="text-xs text-gray-400 dark:text-gray-500">
			{$i18n.t('No external knowledge sources configured.')}
		</div>
	{/if}

	<div class="my-1.5">
		<div class="text-xs text-gray-500">
			{$i18n.t(
				'Create one read-only Knowledge source per external collection. Test must pass before the source is created.'
			)}
		</div>
	</div>
</div>
