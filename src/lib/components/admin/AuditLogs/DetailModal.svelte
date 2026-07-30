<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import dayjs from 'dayjs';
	import { toast } from 'svelte-sonner';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Clipboard from '$lib/components/icons/Clipboard.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import { getAuditLogById, type AuditLogDetail } from '$lib/apis/audit-logs';

	const i18n: any = getContext('i18n');

	export let show: boolean = false;
	export let logId: string | null = null;

	let loading: boolean = false;
	let logDetail: AuditLogDetail | null = null;
	let copiedField: string | null = null;

	let expandReqBody: boolean = false;
	let expandResBody: boolean = false;

	const copyToClipboard = (text: string, fieldName: string) => {
		navigator.clipboard.writeText(text);
		copiedField = fieldName;
		toast.success($i18n.t('Copied to clipboard'));
		setTimeout(() => {
			if (copiedField === fieldName) copiedField = null;
		}, 2000);
	};

	const fetchDetail = async () => {
		if (!logId) return;
		loading = true;
		logDetail = null;
		try {
			logDetail = await getAuditLogById(localStorage.token, logId);
		} catch (err: any) {
			toast.error(`${err}`);
		} finally {
			loading = false;
		}
	};

	$: if (show && logId) {
		fetchDetail();
	}

	const statusColorClass = (code: number) => {
		if (!code) return 'bg-gray-500 text-white';
		if (code >= 200 && code < 300) return 'bg-green-500/15 text-green-700 dark:text-green-400 border-green-300 dark:border-green-800';
		if (code >= 400 && code < 500) return 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-800';
		if (code >= 500) return 'bg-red-500/15 text-red-700 dark:text-red-400 border-red-300 dark:border-red-800';
		return 'bg-gray-500/15 text-gray-700 dark:text-gray-400 border-gray-300 dark:border-gray-800';
	};

	const formatJson = (val: any) => {
		if (!val) return null;
		if (typeof val === 'string') {
			try {
				return JSON.stringify(JSON.parse(val), null, 2);
			} catch {
				return val;
			}
		}
		return JSON.stringify(val, null, 2);
	};
</script>

<Modal bind:show size="lg" className="bg-white dark:bg-gray-900 rounded-2xl max-h-[90vh] flex flex-col">
	<div class="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-850">
		<div class="flex items-center gap-2">
			<h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">
				{$i18n.t('Audit Log Details')}
			</h3>
			{#if logDetail?.id}
				<span class="font-mono text-xs text-gray-400 dark:text-gray-500 truncate max-w-48">
					{logDetail.id}
				</span>
			{/if}
		</div>
		<button
			type="button"
			class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
			on:click={() => (show = false)}
			aria-label={$i18n.t('Close')}
		>
			<XMark className="size-4" />
		</button>
	</div>

	<div class="flex-1 overflow-y-auto p-5 space-y-6 text-xs text-gray-800 dark:text-gray-200">
		{#if loading}
			<div class="flex justify-center items-center py-16">
				<Spinner className="size-6" />
			</div>
		{:else if !logDetail}
			<div class="text-center py-12 text-gray-400">
				{$i18n.t('Unable to load audit log details')}
			</div>
		{:else}
			<!-- Section 1: Request Metadata -->
			<div class="space-y-3">
				<div class="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-1.5">
					<h4 class="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
						{$i18n.t('Request Details')}
					</h4>
					<span class="px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
						Level: {logDetail.audit_level || 'REQUEST'}
					</span>
				</div>

				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
					<div>
						<span class="text-gray-400 block mb-0.5">{$i18n.t('Time')}</span>
						<span class="font-mono font-medium">
							{dayjs(logDetail.created_at).format('YYYY-MM-DD HH:mm:ss.SSS')}
						</span>
					</div>

					<div>
						<span class="text-gray-400 block mb-0.5">{$i18n.t('User')}</span>
						<span class="font-medium">
							{logDetail.user?.name || logDetail.user_snapshot?.name || $i18n.t('Anonymous')}
						</span>
						{#if logDetail.user?.email || logDetail.user_snapshot?.email}
							<span class="text-gray-400 text-[11px] block">
								({logDetail.user?.email || logDetail.user_snapshot?.email})
							</span>
						{/if}
					</div>

					<div>
						<span class="text-gray-400 block mb-0.5">{$i18n.t('Method & Path')}</span>
						<span class="inline-flex items-center gap-1.5 font-mono">
							<span class="px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-[10px] font-bold text-gray-700 dark:text-gray-300">
								{logDetail.verb}
							</span>
							<span class="truncate">{logDetail.request_path}</span>
						</span>
					</div>

					<div>
						<span class="text-gray-400 block mb-0.5">{$i18n.t('Source IP')}</span>
						<span class="font-mono">{logDetail.source_ip || '-'}</span>
					</div>

					<div class="sm:col-span-2">
						<span class="text-gray-400 block mb-0.5">{$i18n.t('Request URI')}</span>
						<div class="flex items-center gap-1">
							<span class="font-mono truncate text-[11px] bg-gray-50 dark:bg-gray-850 px-2 py-0.5 rounded border border-gray-200 dark:border-gray-800 flex-1">
								{logDetail.request_uri || logDetail.request_path}
							</span>
							{#if logDetail.request_uri}
								<button
									class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
									on:click={() => copyToClipboard(logDetail?.request_uri || '', 'uri')}
								>
									{#if copiedField === 'uri'}
										<Check className="size-3 text-green-500" />
									{:else}
										<Clipboard className="size-3" />
									{/if}
								</button>
							{/if}
						</div>
					</div>
				</div>

				{#if logDetail.user_agent}
					<div>
						<span class="text-gray-400 block mb-0.5">{$i18n.t('User Agent')}</span>
						<span class="font-mono text-[11px] text-gray-600 dark:text-gray-400 break-all bg-gray-50 dark:bg-gray-850 p-1.5 rounded block border border-gray-200 dark:border-gray-800">
							{logDetail.user_agent}
						</span>
					</div>
				{/if}

				<!-- Parsed Split Request Fields -->
				{#if logDetail.request_model || logDetail.request_skill_ids?.length || logDetail.request_user_messages?.length}
					<div class="p-2.5 rounded-lg bg-gray-50/70 dark:bg-gray-850/40 border border-gray-200/80 dark:border-gray-800/80 space-y-2 mt-2">
						<span class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider block">
							{$i18n.t('Parsed Request Metadata')}
						</span>
						<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
							{#if logDetail.request_model}
								<div>
									<span class="text-gray-400">Request Model:</span>
									<span class="font-mono font-medium ml-1">{logDetail.request_model}</span>
								</div>
							{/if}
							{#if logDetail.request_skill_ids && logDetail.request_skill_ids.length > 0}
								<div>
									<span class="text-gray-400">Skills:</span>
									<span class="font-mono font-medium ml-1">{logDetail.request_skill_ids.join(', ')}</span>
								</div>
							{/if}
							{#if logDetail.request_tool_ids && logDetail.request_tool_ids.length > 0}
								<div>
									<span class="text-gray-400">Tools:</span>
									<span class="font-mono font-medium ml-1">{logDetail.request_tool_ids.join(', ')}</span>
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>

			<!-- Section 2: Response Metadata -->
			<div class="space-y-3">
				<div class="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 pb-1.5">
					<h4 class="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
						{$i18n.t('Response Details')}
					</h4>
				</div>

				<div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
					<div>
						<span class="text-gray-400 block mb-0.5">{$i18n.t('HTTP Status')}</span>
						<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border {statusColorClass(logDetail.response_status_code)}">
							<span class="size-1.5 rounded-full bg-current"></span>
							{logDetail.response_status_code || $i18n.t('No response')}
						</span>
					</div>

					<div>
						<span class="text-gray-400 block mb-0.5">{$i18n.t('Response Model')}</span>
						<span class="font-mono font-medium">{logDetail.response_model || '-'}</span>
					</div>

					<div>
						<span class="text-gray-400 block mb-0.5">{$i18n.t('Finish Reasons')}</span>
						<span class="font-mono font-medium">
							{logDetail.response_finish_reasons?.join(', ') || '-'}
						</span>
					</div>
				</div>
			</div>

			<!-- Section 3: Captured Content Payloads -->
			<div class="space-y-4">
				<div class="border-b border-gray-100 dark:border-gray-800 pb-1.5">
					<h4 class="text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
						{$i18n.t('Captured Content')}
					</h4>
					<p class="text-[11px] text-gray-400 mt-0.5">
						{$i18n.t('Payload contents are sanitized and shown in plain text.')}
					</p>
				</div>

				<!-- Request Body Box -->
				<div class="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-gray-50/50 dark:bg-gray-950/40">
					<div class="flex items-center justify-between px-3 py-2 bg-gray-100/70 dark:bg-gray-850/70 border-b border-gray-200 dark:border-gray-800">
						<div class="flex items-center gap-2">
							<span class="font-semibold text-gray-700 dark:text-gray-300">{$i18n.t('Request Body')}</span>
							{#if logDetail.request_captured}
								<span class="px-2 py-0.2 rounded text-[10px] font-medium bg-green-100 dark:bg-green-950/60 text-green-700 dark:text-green-300">
									{$i18n.t('Captured')}
								</span>
							{:else}
								<span class="px-2 py-0.2 rounded text-[10px] font-medium bg-gray-200 dark:bg-gray-800 text-gray-500">
									{$i18n.t('Not Captured')}
								</span>
							{/if}
							{#if logDetail.request_truncated}
								<span class="px-2 py-0.2 rounded text-[10px] font-medium bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300">
									{$i18n.t('Truncated')}
								</span>
							{/if}
						</div>

						{#if logDetail.request_object}
							<div class="flex items-center gap-1">
								<button
									class="p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
									on:click={() => copyToClipboard(logDetail?.request_object || '', 'req_body')}
									title={$i18n.t('Copy request body')}
								>
									{#if copiedField === 'req_body'}
										<Check className="size-3.5 text-green-500" />
									{:else}
										<Clipboard className="size-3.5" />
									{/if}
								</button>
								<button
									class="p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
									on:click={() => (expandReqBody = !expandReqBody)}
								>
									{#if expandReqBody}
										<ChevronUp className="size-3.5" />
									{:else}
										<ChevronDown className="size-3.5" />
									{/if}
								</button>
							</div>
						{/if}
					</div>

					<div class="p-3">
						{#if logDetail.request_object}
							<pre
								class="font-mono text-[11px] leading-relaxed text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all overflow-y-auto transition-all duration-200 {expandReqBody
									? 'max-h-96'
									: 'max-h-44'}"
							>{formatJson(logDetail.request_object)}</pre>
							{#if logDetail.request_truncated}
								<div class="mt-2 text-[10px] italic text-amber-600 dark:text-amber-400 border-t border-dashed border-amber-300 dark:border-amber-800/60 pt-1">
									⚠️ {$i18n.t('Captured content was truncated by body size limit.')}
								</div>
							{/if}
						{:else}
							<div class="text-gray-400 text-center py-4 italic">
								{$i18n.t('No request body captured for this audit level.')}
							</div>
						{/if}
					</div>
				</div>

				<!-- Response Body Box -->
				<div class="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-gray-50/50 dark:bg-gray-950/40">
					<div class="flex items-center justify-between px-3 py-2 bg-gray-100/70 dark:bg-gray-850/70 border-b border-gray-200 dark:border-gray-800">
						<div class="flex items-center gap-2">
							<span class="font-semibold text-gray-700 dark:text-gray-300">{$i18n.t('Response Body')}</span>
							{#if logDetail.response_captured}
								<span class="px-2 py-0.2 rounded text-[10px] font-medium bg-green-100 dark:bg-green-950/60 text-green-700 dark:text-green-300">
									{$i18n.t('Captured')}
								</span>
							{:else}
								<span class="px-2 py-0.2 rounded text-[10px] font-medium bg-gray-200 dark:bg-gray-800 text-gray-500">
									{$i18n.t('Not Captured')}
								</span>
							{/if}
							{#if logDetail.response_truncated}
								<span class="px-2 py-0.2 rounded text-[10px] font-medium bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300">
									{$i18n.t('Truncated')}
								</span>
							{/if}
						</div>

						{#if logDetail.response_object}
							<div class="flex items-center gap-1">
								<button
									class="p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
									on:click={() => copyToClipboard(logDetail?.response_object || '', 'res_body')}
									title={$i18n.t('Copy response body')}
								>
									{#if copiedField === 'res_body'}
										<Check className="size-3.5 text-green-500" />
									{:else}
										<Clipboard className="size-3.5" />
									{/if}
								</button>
								<button
									class="p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition"
									on:click={() => (expandResBody = !expandResBody)}
								>
									{#if expandResBody}
										<ChevronUp className="size-3.5" />
									{:else}
										<ChevronDown className="size-3.5" />
									{/if}
								</button>
							</div>
						{/if}
					</div>

					<div class="p-3">
						{#if logDetail.response_object}
							<pre
								class="font-mono text-[11px] leading-relaxed text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all overflow-y-auto transition-all duration-200 {expandResBody
									? 'max-h-96'
									: 'max-h-44'}"
							>{formatJson(logDetail.response_object)}</pre>
							{#if logDetail.response_truncated}
								<div class="mt-2 text-[10px] italic text-amber-600 dark:text-amber-400 border-t border-dashed border-amber-300 dark:border-amber-800/60 pt-1">
									⚠️ {$i18n.t('Captured content was truncated by body size limit.')}
								</div>
							{/if}
						{:else}
							<div class="text-gray-400 text-center py-4 italic">
								{$i18n.t('No response body captured for this audit level.')}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="px-5 py-3 border-t border-gray-100 dark:border-gray-850 flex justify-end bg-gray-50/50 dark:bg-gray-900/50 rounded-b-2xl">
		<button
			type="button"
			class="px-4 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-xs text-gray-800 dark:text-gray-200 font-medium transition"
			on:click={() => (show = false)}
		>
			{$i18n.t('Close')}
		</button>
	</div>
</Modal>
