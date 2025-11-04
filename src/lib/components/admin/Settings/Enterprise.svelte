<script lang="ts">
	import { getContext, onMount } from 'svelte';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getSystemHealth } from '$lib/apis/system';
	import { getRAGConfig } from '$lib/apis/retrieval';

	const i18n = getContext('i18n');

	let loading = true;

	type RuntimeProfile = {
		enterprise_mode: boolean;
		local_features_enabled: boolean;
		embedding_engine: string | null;
		stt_engine: string | null;
		tts_engine: string | null;
		ocr_engine: string | null;
		vector_db: string | null;
		vector_status: {
			status: string;
			detail?: string;
			code?: number;
		} | null;
	};

	let runtime: RuntimeProfile | null = null;

	let docInt = {
		endpoint: '',
		key: '',
		modelId: '',
		apiVersion: ''
	};

	let awsTextract = {
		accessKeyId: '',
		secretAccessKey: '',
		sessionToken: '',
		region: ''
	};

	const loadEnterpriseConfig = async () => {
		loading = true;

		const [health, ragConfig] = await Promise.all([
			getSystemHealth(localStorage.token).catch((err) => {
				console.error(err);
				return null;
			}),
			getRAGConfig(localStorage.token).catch((err) => {
				console.error(err);
				return null;
			})
		]);

		if (health) {
			runtime = {
				enterprise_mode: Boolean(health?.mode?.enterprise_mode),
				local_features_enabled: Boolean(health?.mode?.local_features_enabled),
				embedding_engine: health?.engines?.embeddings ?? null,
				stt_engine: health?.engines?.stt ?? null,
				tts_engine: health?.engines?.tts ?? null,
				ocr_engine: health?.engines?.ocr ?? null,
				vector_db: health?.engines?.vectordb ?? null,
				vector_status: health?.vector_db ?? null
			};
		}

		if (ragConfig) {
			docInt = {
				endpoint: ragConfig.DOCUMENT_INTELLIGENCE_ENDPOINT ?? '',
				key: ragConfig.DOCUMENT_INTELLIGENCE_KEY ?? '',
				modelId: ragConfig.DOCUMENT_INTELLIGENCE_MODEL_ID ?? '',
				apiVersion: ragConfig.DOCUMENT_INTELLIGENCE_API_VERSION ?? ''
			};

			awsTextract = {
				accessKeyId: ragConfig.AWS_TEXTRACT_ACCESS_KEY_ID ?? '',
				secretAccessKey: ragConfig.AWS_TEXTRACT_SECRET_ACCESS_KEY ?? '',
				sessionToken: ragConfig.AWS_TEXTRACT_SESSION_TOKEN ?? '',
				region: ragConfig.AWS_TEXTRACT_REGION ?? ''
			};
		}

		loading = false;
	};

	onMount(async () => {
		await loadEnterpriseConfig();
	});
</script>

<div class="flex flex-col h-full justify-between space-y-3 text-sm">
	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<Spinner className="size-8" />
		</div>
	{:else}
		<div class="space-y-3 overflow-y-scroll scrollbar-hidden h-full pr-1.5">
			{#if runtime}
				<div>
					<div class="mb-2.5 text-base font-medium">{$i18n.t('Runtime Profile')}</div>
					<hr class="border-gray-100 dark:border-gray-850 my-2" />
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
						<div class="flex justify-between rounded-md bg-gray-50 dark:bg-gray-900 px-3 py-2">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Enterprise Mode')}</span>
							<span class="font-medium">{runtime.enterprise_mode ? $i18n.t('Enabled') : $i18n.t('Disabled')}</span>
						</div>
						<div class="flex justify-between rounded-md bg-gray-50 dark:bg-gray-900 px-3 py-2">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Local Features')}</span>
							<span class="font-medium">{runtime.local_features_enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}</span>
						</div>
						<div class="flex justify-between rounded-md bg-gray-50 dark:bg-gray-900 px-3 py-2">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Embedding Engine')}</span>
							<span class="font-medium">{runtime.embedding_engine ?? $i18n.t('Unset')}</span>
						</div>
						<div class="flex justify-between rounded-md bg-gray-50 dark:bg-gray-900 px-3 py-2">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Vector Database')}</span>
							<span class="font-medium">{runtime.vector_db ?? $i18n.t('Unset')}</span>
						</div>
						<div class="flex justify-between rounded-md bg-gray-50 dark:bg-gray-900 px-3 py-2">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Speech-to-Text Engine')}</span>
							<span class="font-medium">{runtime.stt_engine ?? $i18n.t('Unset')}</span>
						</div>
						<div class="flex justify-between rounded-md bg-gray-50 dark:bg-gray-900 px-3 py-2">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Text-to-Speech Engine')}</span>
							<span class="font-medium">{runtime.tts_engine ?? $i18n.t('Unset')}</span>
						</div>
						<div class="flex justify-between rounded-md bg-gray-50 dark:bg-gray-900 px-3 py-2">
							<span class="text-gray-500 dark:text-gray-400">{$i18n.t('OCR Engine')}</span>
							<span class="font-medium">{runtime.ocr_engine ?? $i18n.t('Unset')}</span>
						</div>
						{#if runtime.vector_status}
							<div class="flex justify-between rounded-md bg-gray-50 dark:bg-gray-900 px-3 py-2">
								<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Vector Health')}</span>
								<span class="font-medium">
									{runtime.vector_status.status}
								</span>
							</div>
						{/if}
					</div>
					{#if runtime?.vector_status?.detail}
						<p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
							{runtime.vector_status.detail}
						</p>
					{/if}
				</div>
			{/if}

			<div>
				<div class="mb-2.5 text-base font-medium">{$i18n.t('Document Intelligence')}</div>
				<hr class="border-gray-100 dark:border-gray-850 my-2" />
				<p class="mb-2 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Manage Document Intelligence credentials in the Documents settings panel.')}
					<a class="underline" href="/admin/settings/documents">{$i18n.t('Open Documents settings')}</a>
				</p>
				<div class="flex flex-col gap-2">
					<input
						class="w-full rounded-md bg-transparent outline-hidden text-sm border border-gray-200 dark:border-gray-800 px-3 py-2"
						type="text"
						readonly
						value={docInt.endpoint}
					/>
					<SensitiveInput value={docInt.key} readOnly />
					<input
						class="w-full rounded-md bg-transparent outline-hidden text-sm border border-gray-200 dark:border-gray-800 px-3 py-2"
						type="text"
						readonly
						value={docInt.modelId}
					/>
					<input
						class="w-full rounded-md bg-transparent outline-hidden text-sm border border-gray-200 dark:border-gray-800 px-3 py-2"
						type="text"
						readonly
						value={docInt.apiVersion}
					/>
				</div>
			</div>

			<div>
				<div class="mb-2.5 text-base font-medium">{$i18n.t('AWS Textract')}</div>
				<hr class="border-gray-100 dark:border-gray-850 my-2" />
				<p class="mb-2 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Manage AWS Textract credentials in the Documents settings panel.')}
					<a class="underline" href="/admin/settings/documents">{$i18n.t('Open Documents settings')}</a>
				</p>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
					<SensitiveInput value={awsTextract.accessKeyId} readOnly />
					<SensitiveInput value={awsTextract.secretAccessKey} readOnly />
					<SensitiveInput value={awsTextract.sessionToken} readOnly />
					<input
						class="w-full rounded-md bg-transparent outline-hidden text-sm border border-gray-200 dark:border-gray-800 px-3 py-2"
						type="text"
						readonly
						value={awsTextract.region}
					/>
				</div>
			</div>
		</div>
	{/if}

	<div class="flex justify-end pt-3 text-xs text-gray-500 dark:text-gray-400">
		{$i18n.t('Enterprise mode lists effective SaaS providers; update credentials from their respective settings panels.')}
	</div>
</div>
