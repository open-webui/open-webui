<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { createNewKnowledge, getKnowledgeBases } from '$lib/apis/knowledge';
	import { uploadFile } from '$lib/apis/files';
	import { v4 as uuidv4 } from 'uuid';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import KnowledgeSelector from '$lib/components/workspace/Models/Knowledge/KnowledgeSelector.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	type Client = {
		user_id: string;
		email: string;
		name: string;
		fixed_model_id: string;
		fixed_system_prompt: string;
		assigned_kb_ids: string[];
		kb_rag_query: string;
		monthly_limit_usd: number;
	};

	let loading = false;
	let showModal = false;
	let isEdit = false;
	let tempPassword: string | null = null;
	let clients: Client[] = [];
	let editClientId: string | null = null;

	// Form fields
	let clientEmail = '';
	let clientName = '';
	let fixedModel = 'gpt-4o-mini';
	let systemPrompt = '';
	let monthlyLimit = 20;
	let selectedKbItems: any[] = [];
	let ragQuery = '';
	let profileImageUrl = `${WEBUI_BASE_URL}/static/favicon.png`;

	// Inline KB creation
	let showKbCreator = false;
	let newKbName = '';
	let newKbDescription = '';
	let kbCreating = false;

	// Image upload
	let filesInputElement: HTMLInputElement | null = null;
	let inputFiles: FileList | null = null;

	// File → RAG upload
	let ragFilesInputElement: HTMLInputElement | null = null;
	let ragInputFiles: FileList | null = null;
	let uploadingFiles = new Set<string>();

	let allKnowledgeItems: any[] = [];

	const MODEL_OPTIONS = [
		{ group: 'GPT-5 Series (Latest - Aug 2025)', options: [
			{ value: 'gpt-5', label: 'gpt-5 (Latest flagship, best overall - Aug 2025)' },
			{ value: 'gpt-5-2025-08-07', label: 'gpt-5-2025-08-07 (Pinned stable version)' },
			{ value: 'gpt-5.5', label: 'gpt-5.5 (Frontier model, complex professional work)' },
			{ value: 'gpt-5.2', label: 'gpt-5.2 (Balanced performance & price)' },
			{ value: 'gpt-5.1', label: 'gpt-5.1 (Efficient, cost-effective)' },
			{ value: 'gpt-5-mini', label: 'gpt-5-mini (Fast, cheapest in GPT-5 series)' },
		]},
		{ group: 'Reasoning Models (o-series)', options: [
			{ value: 'o3', label: 'o3 (Best reasoning, STEM tasks)' },
			{ value: 'o3-mini', label: 'o3-mini (Fast reasoning, cost-effective)' },
			{ value: 'o1', label: 'o1 (Advanced reasoning)' },
			{ value: 'o1-pro', label: 'o1-pro (Premium reasoning quality)' },
			{ value: 'o1-mini', label: 'o1-mini (Quick reasoning)' },
		]},
		{ group: 'GPT-4.5 & GPT-4o Series', options: [
			{ value: 'gpt-4.5-preview', label: 'gpt-4.5-preview (Pre-GPT-5 flagship)' },
			{ value: 'gpt-4o', label: 'gpt-4o (Best all-around multimodal)' },
			{ value: 'gpt-4o-2024-11-20', label: 'gpt-4o-2024-11-20 (Stable version)' },
			{ value: 'gpt-4o-mini', label: 'gpt-4o-mini (Fast, cheap, capable)' },
			{ value: 'gpt-4o-realtime-preview', label: 'gpt-4o-realtime-preview (Realtime audio/chat)' },
		]},
		{ group: 'GPT-4.1 Series (April 2025)', options: [
			{ value: 'gpt-4.1', label: 'gpt-4.1 (Major release)' },
			{ value: 'gpt-4.1-mini', label: 'gpt-4.1-mini (Fast & efficient)' },
			{ value: 'gpt-4.1-nano', label: 'gpt-4.1-nano (Ultra fast, cheapest)' },
		]},
		{ group: 'Specialized Models', options: [
			{ value: 'gpt-4o-audio-preview', label: 'gpt-4o-audio-preview (Audio I/O)' },
			{ value: 'gpt-4o-mini-audio-preview', label: 'gpt-4o-mini-audio-preview (Audio, mini)' },
			{ value: 'gpt-4o-search-preview', label: 'gpt-4o-search-preview (With web search)' },
			{ value: 'whisper-1', label: 'whisper-1 (Speech-to-text)' },
			{ value: 'tts-1', label: 'tts-1 (Text-to-speech)' },
		]},
		{ group: 'Legacy Models', options: [
			{ value: 'gpt-4-turbo', label: 'gpt-4-turbo' },
			{ value: 'gpt-4', label: 'gpt-4' },
			{ value: 'gpt-3.5-turbo', label: 'gpt-3.5-turbo' },
		]},
	];

	async function fetchClients() {
		try {
			const res = await fetch('/api/v1/spending/clients', {
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				clients = await res.json();
			} else {
				console.error('fetchClients failed:', res.status, await res.text().catch(() => ''));
			}
		} catch (e) {
			console.error('fetchClients error:', e);
		}
	}

	async function fetchKnowledgeBases() {
		try {
			const res = await getKnowledgeBases(localStorage.token);
			if (res) {
				allKnowledgeItems = res.items || [];
			}
		} catch (e) {
			console.error('Failed to fetch knowledge bases:', e);
		}
	}

	function resetForm() {
		clientEmail = '';
		clientName = '';
		fixedModel = 'gpt-4o-mini';
		systemPrompt = '';
		ragQuery = '';
		monthlyLimit = 20;
		selectedKbItems = [];
		profileImageUrl = `${WEBUI_BASE_URL}/static/favicon.png`;
		showKbCreator = false;
		newKbName = '';
		newKbDescription = '';
	}

	function openCreate() {
		resetForm();
		isEdit = false;
		tempPassword = null;
		showModal = true;
	}

	function openEdit(client: Client) {
		editClientId = client.user_id;
		clientName = client.name;
		clientEmail = client.email;
		fixedModel = client.fixed_model_id;
		systemPrompt = client.fixed_system_prompt;
		ragQuery = client.kb_rag_query;
		monthlyLimit = client.monthly_limit_usd;
		profileImageUrl = `${WEBUI_BASE_URL}/static/favicon.png`;

		selectedKbItems = (client.assigned_kb_ids || []).map(id => {
			const kb = allKnowledgeItems.find(k => k.id === id);
			return kb ? { id: kb.id, name: kb.name || kb.title || 'Unnamed', type: 'collection' } : { id, name: 'Unknown', type: 'collection' };
		});

		isEdit = true;
		tempPassword = null;
		showModal = true;
	}

	async function createClient() {
		if (!clientEmail.trim() || !clientName.trim() || !fixedModel) {
			toast.error('Email, name and model are required');
			return;
		}
		loading = true;
		try {
			const payload = {
				email: clientEmail.trim(),
				name: clientName.trim(),
				fixed_model_id: fixedModel,
				fixed_system_prompt: systemPrompt,
				assigned_kb_ids: selectedKbItems.map(k => k.id),
				kb_rag_query: ragQuery,
				monthly_limit_usd: monthlyLimit
			};
			console.log('createClient payload:', payload);
			const res = await fetch('/api/v1/spending/clients', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(payload)
			});
			console.log('createClient response status:', res.status);
			if (!res.ok) {
				let errDetail = 'Unknown error';
				try {
					const errJson = await res.clone().json();
					errDetail = errJson.detail || JSON.stringify(errJson);
				} catch {
					errDetail = (await res.text()).slice(0, 200);
				}
				console.error('createClient error body:', errDetail);
				throw new Error(errDetail || 'Failed to create client');
			}
			const data = await res.json();
			tempPassword = data.temp_password;
			toast.success('Client created successfully');
			showModal = false;
			await fetchClients();
		} catch (e: any) {
			console.error('createClient exception:', e);
			toast.error(e.message || 'Failed to create client');
		} finally {
			loading = false;
		}
	}

	async function updateClient() {
		if (!editClientId) return;
		loading = true;
		try {
			const payload = {
				name: clientName.trim(),
				fixed_model_id: fixedModel,
				fixed_system_prompt: systemPrompt,
				assigned_kb_ids: selectedKbItems.map(k => k.id),
				kb_rag_query: ragQuery,
				monthly_limit_usd: monthlyLimit
			};
			console.log('updateClient payload:', payload);
			const res = await fetch(`/api/v1/spending/clients/${editClientId}`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(payload)
			});
			console.log('updateClient response status:', res.status);
			if (!res.ok) {
				let errDetail = 'Unknown error';
				try {
					const errJson = await res.clone().json();
					errDetail = errJson.detail || JSON.stringify(errJson);
				} catch {
					errDetail = (await res.text()).slice(0, 200);
				}
				console.error('updateClient error body:', errDetail);
				throw new Error(errDetail || 'Failed to update client');
			}
			toast.success('Client updated');
			showModal = false;
			editClientId = null;
			await fetchClients();
		} catch (e: any) {
			console.error('updateClient exception:', e);
			toast.error(e.message || 'Failed to update client');
		} finally {
			loading = false;
		}
	}

	async function deleteClient(client: Client) {
		if (!confirm(`Delete client "${client.name}" (${client.email})? This cannot be undone.`)) return;
		try {
			const res = await fetch(`/api/v1/spending/clients/${client.user_id}`, {
				method: 'DELETE',
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
				throw new Error(err.detail || 'Failed to delete');
			}
			toast.success(`Client "${client.name}" deleted`);
			await fetchClients();
		} catch (e: any) {
			toast.error(e.message || 'Failed to delete client');
		}
	}

	async function resetPassword(client: Client) {
		if (!confirm(`Reset password for "${client.name}"?`)) return;
		try {
			const res = await fetch(`/api/v1/spending/clients/${client.user_id}/reset-password`, {
				method: 'POST',
				headers: { Authorization: `Bearer ${localStorage.token}` }
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
				throw new Error(err.detail || 'Failed to reset');
			}
			const data = await res.json();
			tempPassword = data.temp_password;
			toast.success(data.message);
		} catch (e: any) {
			toast.error(e.message || 'Failed to reset password');
		}
	}

	async function createKnowledgeBaseInline() {
		if (!newKbName.trim() || !newKbDescription.trim()) {
			toast.error('Please fill in KB name and description');
			return;
		}
		kbCreating = true;
		try {
			const res = await createNewKnowledge(localStorage.token, newKbName.trim(), newKbDescription.trim(), []);
			if (res) {
				toast.success('Knowledge base created');
				await fetchKnowledgeBases();
				selectedKbItems = [...selectedKbItems, { id: res.id, name: res.name || newKbName.trim(), type: 'collection' }];
				newKbName = '';
				newKbDescription = '';
				showKbCreator = false;
			}
		} catch (e: any) {
			toast.error(e.message || 'Failed to create knowledge base');
		} finally {
			kbCreating = false;
		}
	}

	function handleImageUpload() {
		if (!inputFiles || inputFiles.length === 0) return;
		const file = inputFiles[0];
		const validTypes = ['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/svg+xml'];
		if (!validTypes.includes(file.type)) {
			toast.error('Unsupported file type. Please upload an image.');
			inputFiles = null;
			return;
		}

		const reader = new FileReader();
		reader.onload = (event) => {
			const originalImageUrl = event.target?.result as string;
			if (file.type === 'image/gif' || file.type === 'image/webp') {
				profileImageUrl = originalImageUrl;
				inputFiles = null;
				if (filesInputElement) filesInputElement.value = '';
				return;
			}

			const img = new Image();
			img.src = originalImageUrl;
			img.onload = function () {
				const canvas = document.createElement('canvas');
				const ctx = canvas.getContext('2d');
				const aspectRatio = img.width / img.height;
				let newWidth, newHeight;
				if (aspectRatio > 1) {
					newWidth = 250 * aspectRatio;
					newHeight = 250;
				} else {
					newWidth = 250;
					newHeight = 250 / aspectRatio;
				}
				canvas.width = 250;
				canvas.height = 250;
				const offsetX = (250 - newWidth) / 2;
				const offsetY = (250 - newHeight) / 2;
				ctx?.drawImage(img, offsetX, offsetY, newWidth, newHeight);
				const compressedSrc = canvas.toDataURL('image/webp', 0.8);
				profileImageUrl = compressedSrc;
				inputFiles = null;
				if (filesInputElement) filesInputElement.value = '';
			};
		};
		reader.readAsDataURL(file);
	}

	async function uploadFileToRag(file: File) {
		const tempItemId = uuidv4();
		uploadingFiles.add(tempItemId);
		uploadingFiles = uploadingFiles;

		// Add a placeholder pill
		selectedKbItems = [...selectedKbItems, {
			id: tempItemId,
			name: file.name,
			type: 'file',
			status: 'uploading'
		}];

		try {
			console.log('[uploadFileToRag] starting for', file.name);
			// 1. Create a knowledge base entry so the backend has a valid KB ID.
			const newKb = await createNewKnowledge(
				localStorage.token,
				file.name,
				'Auto-created from file upload',
				[]
			);

			console.log('[uploadFileToRag] KB created:', newKb?.id);
			if (!newKb || !newKb.id) {
				throw new Error('Failed to create knowledge base for uploaded file');
			}

			// 2. Upload the file with knowledge_id metadata.
			//    The backend auto-links the file to the KB and creates the RAG collection.
			const uploadedFile = await uploadFile(
				localStorage.token,
				file,
				{ knowledge_id: newKb.id }
			);
			console.log('[uploadFileToRag] file upload result:', uploadedFile?.id, 'error:', uploadedFile?.error);

			if (uploadedFile) {
				if (uploadedFile.error) {
					toast.warning(uploadedFile.error);
				}

				// Refresh the KB list so the new KB appears in the selector
				await fetchKnowledgeBases();

				// Replace the placeholder with the real KB item
				selectedKbItems = selectedKbItems.map(k =>
					k.id === tempItemId
						? { id: newKb.id, name: file.name, type: 'collection', file: uploadedFile, status: 'uploaded' }
						: k
				);
			} else {
				selectedKbItems = selectedKbItems.filter(k => k.id !== tempItemId);
				toast.error('File upload failed');
			}
		} catch (e) {
			console.error('[uploadFileToRag] caught error:', e);
			toast.error(`${e}`);
			selectedKbItems = selectedKbItems.filter(k => k.id !== tempItemId);
		} finally {
			uploadingFiles.delete(tempItemId);
			uploadingFiles = uploadingFiles;
			if (ragFilesInputElement) ragFilesInputElement.value = '';
		}
	}

	function handleRagFileUpload() {
		if (!ragInputFiles || ragInputFiles.length === 0) return;
		for (const file of Array.from(ragInputFiles)) {
			if (file.size === 0) {
				toast.error('You cannot upload an empty file.');
				continue;
			}
			uploadFileToRag(file);
		}
		ragInputFiles = null;
	}

	onMount(() => {
		fetchKnowledgeBases();
		fetchClients();
	});
</script>

<div class="flex flex-col w-full h-full px-4 py-4 overflow-y-auto">
	<div class="flex items-center justify-between mb-4">
		<h1 class="text-xl font-semibold dark:text-white">Client Management</h1>
		<button
			on:click={openCreate}
			class="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition"
		>
			+ New Client
		</button>
	</div>

	<!-- Temp password banner -->
	{#if tempPassword}
		<div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4 mb-4">
			<div class="text-green-800 dark:text-green-300 font-medium mb-2">Temporary Password — Share Securely</div>
			<div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700 font-mono text-sm select-all break-all">
				{tempPassword}
			</div>
			<button
				on:click={() => { tempPassword = null; }}
				class="mt-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
			>
				Dismiss
			</button>
		</div>
	{/if}

	<!-- Clients table -->
	<div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden mb-6">
		<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 font-medium dark:text-white">
			Clients ({clients.length})
		</div>
		<div class="overflow-x-auto">
			<table class="w-full text-sm">
				<thead>
					<tr class="bg-gray-50 dark:bg-gray-700/50 text-left">
						<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Name / Email</th>
						<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Model</th>
						<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">KBs</th>
						<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Limit</th>
						<th class="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each clients as client}
						<tr class="border-t border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
							<td class="px-4 py-2">
								<div class="font-medium dark:text-gray-200">{client.name}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{client.email}</div>
							</td>
							<td class="px-4 py-2">
								<span class="text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded font-mono">
									{client.fixed_model_id}
								</span>
							</td>
							<td class="px-4 py-2 dark:text-gray-200">
								{client.assigned_kb_ids?.length || 0} KB{(client.assigned_kb_ids?.length || 0) !== 1 ? 's' : ''}
							</td>
							<td class="px-4 py-2 dark:text-gray-200">${client.monthly_limit_usd}/mo</td>
							<td class="px-4 py-2">
								<div class="flex gap-2 flex-wrap">
									<button
										on:click={() => openEdit(client)}
										class="text-blue-600 dark:text-blue-400 text-xs hover:underline"
									>Edit</button>
									<button
										on:click={() => resetPassword(client)}
										class="text-amber-600 dark:text-amber-400 text-xs hover:underline"
									>Reset PW</button>
									<button
										on:click={() => deleteClient(client)}
										class="text-red-600 dark:text-red-400 text-xs hover:underline"
									>Delete</button>
								</div>
							</td>
						</tr>
					{:else}
						<tr>
							<td colspan="5" class="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
								No clients yet. Click "+ New Client" to create one.
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>

	<!-- Create / Edit Modal -->
	{#if showModal}
		<div class="fixed inset-0 z-50 flex items-start justify-center bg-black/50 backdrop-blur-sm pt-10 pb-10 overflow-y-auto">
			<div class="bg-white dark:bg-gray-850 rounded-2xl shadow-2xl w-full max-w-3xl mx-4 mb-10 border border-gray-200 dark:border-gray-700">
				<div class="px-6 py-4 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
					<h2 class="text-lg font-medium dark:text-white">
						{isEdit ? 'Edit Client' : 'Create New Client'}
					</h2>
					<button
						on:click={() => { showModal = false; editClientId = null; }}
						class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				<div class="p-6 space-y-5">

				<!-- Profile + Identity row -->
				<div class="flex flex-row gap-5">
					<!-- Profile image -->
					<div class="shrink-0 flex flex-col items-center">
						<input
							bind:this={filesInputElement}
							bind:files={inputFiles}
							type="file"
							hidden
							accept="image/*"
							on:change={handleImageUpload}
						/>
						<button
							type="button"
							class="rounded-2xl flex shrink-0 items-center shadow-xl group relative"
							on:click={() => filesInputElement?.click()}
						>
							<img
								src={profileImageUrl}
								alt="client profile"
								class="rounded-xl size-28 md:size-32 object-cover shrink-0"
							/>
							<div class="absolute bottom-0 right-0 z-10">
								<div class="m-1.5 shadow-xl p-1 rounded-full border-2 border-white bg-gray-800 text-white group-hover:bg-gray-600 transition dark:border-black dark:bg-white dark:group-hover:bg-gray-200 dark:text-black">
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
										<path fill-rule="evenodd" d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm10.5 5.707a.5.5 0 0 0-.146-.353l-1-1a.5.5 0 0 0-.708 0L9.354 9.646a.5.5 0 0 1-.708 0L6.354 7.354a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0-.146.353V12a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V9.707ZM12 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z" clip-rule="evenodd" />
									</svg>
								</div>
							</div>
							<div class="absolute top-0 bottom-0 left-0 right-0 bg-white dark:bg-black rounded-lg opacity-0 group-hover:opacity-20 transition"></div>
						</button>
						<button
							class="px-2 py-1 text-gray-500 rounded-lg text-xs mt-1 hover:text-gray-700 dark:hover:text-gray-300"
							on:click={() => { profileImageUrl = `${WEBUI_BASE_URL}/static/favicon.png`; }}
							type="button"
						>
							Reset
						</button>
					</div>

					<!-- Identity fields -->
					<div class="flex flex-col w-full flex-1 space-y-3">
						<div>
							<div class="text-xs font-medium text-gray-500 mb-1">Name *</div>
							<input
								class="text-2xl w-full bg-transparent outline-hidden dark:text-white placeholder-gray-400"
								placeholder="Client Name"
								bind:value={clientName}
							/>
						</div>

						{#if !isEdit}
							<div>
								<div class="text-xs font-medium text-gray-500 mb-1">Email *</div>
								<input
									type="email"
									class="text-sm w-full bg-transparent outline-hidden dark:text-white placeholder-gray-500"
									placeholder="client@example.com"
									bind:value={clientEmail}
								/>
							</div>
						{/if}

						<div>
							<div class="text-xs font-medium text-gray-500 mb-1">Fixed Model *</div>
							<select
								class="text-sm w-full bg-transparent outline-hidden dark:text-white dark:bg-gray-850"
								bind:value={fixedModel}
							>
								{#each MODEL_OPTIONS as group}
									<optgroup label={group.group}>
										{#each group.options as opt}
											<option value={opt.value}>{opt.label}</option>
										{/each}
									</optgroup>
								{/each}
							</select>
						</div>
					</div>
				</div>

				<hr class="border-gray-100 dark:border-gray-800" />

				<!-- System Prompt -->
				<div>
					<div class="text-xs font-medium text-gray-500 mb-1">Fixed System Prompt</div>
					<Textarea
						className="text-sm w-full bg-transparent outline-hidden resize-none overflow-y-hidden dark:text-white placeholder-gray-500"
						rows={3}
						placeholder="You are a helpful assistant for [Company]..."
						bind:value={systemPrompt}
					/>
					<p class="text-xs text-gray-500 mt-1">Injected as system message into every chat for this client</p>
				</div>

				<!-- Knowledge Bases -->
				<div>
					<div class="flex items-center justify-between mb-2">
						<div class="text-xs font-medium text-gray-500">Assigned Knowledge Bases</div>
						<button
							class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
							on:click={() => { showKbCreator = !showKbCreator; }}
						>
							{showKbCreator ? 'Hide Creator' : '+ New Knowledge Base'}
						</button>
					</div>

					{#if selectedKbItems.length > 0}
						<div class="flex flex-wrap items-center gap-2 mb-2.5">
							{#each selectedKbItems as kb, kbIdx}
								<div class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-sm">
									{#if kb.type === 'file'}
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5 text-gray-400 dark:text-gray-500">
											<path d="M5.5 7a.5.5 0 0 0 0 1h5a.5.5 0 0 0 0-1h-5z"/>
											<path d="M2 2a2 2 0 0 1 2-2h4.586a1.5 1.5 0 0 1 1.06.44l3.914 3.914a1.5 1.5 0 0 1 .44 1.06V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2zM3 2v12h10V7.414L8.586 3H3z"/>
										</svg>
									{:else}
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3.5 text-gray-400 dark:text-gray-500">
											<path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2ZM3 5a2 2 0 0 1 2-2 1 1 0 0 0 0-2 4 4 0 0 0-4 4v8a4 4 0 0 0 4 4h8a4 4 0 0 0 4-4V9a4 4 0 0 0-4-4 1 1 0 0 0 0 2 2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5Z"/>
										</svg>
									{/if}
									<span class="dark:text-gray-200">{kb.name}</span>
									{#if kb.status === 'uploading'}
										<Spinner className="size-3" />
									{/if}
									<button
										type="button"
										class="text-gray-400 hover:text-red-500 transition"
										on:click={() => { selectedKbItems = selectedKbItems.filter((_, i) => i !== kbIdx); }}
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="size-3.5">
											<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								</div>
							{/each}
						</div>
					{/if}

					<div class="flex flex-wrap gap-2">
						<KnowledgeSelector
							on:select={(e) => {
								const item = e.detail;
								if (!selectedKbItems.find(k => k.id === item.id)) {
									selectedKbItems = [...selectedKbItems, {
										id: item.id,
										name: item.name || item.title || 'Unnamed',
										type: item.type || 'collection'
									}];
								}
							}}
						>
							<div class="px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-850 rounded-3xl text-sm cursor-pointer dark:text-white">
								Select Knowledge
							</div>
						</KnowledgeSelector>

						<!-- File → RAG upload -->
						<input
							bind:this={ragFilesInputElement}
							bind:files={ragInputFiles}
							type="file"
							hidden
							multiple
							on:change={handleRagFileUpload}
						/>
						<button
							type="button"
							class="px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-850 rounded-3xl text-sm cursor-pointer dark:text-white flex items-center gap-1.5"
							on:click={() => ragFilesInputElement?.click()}
						>
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-4">
								<path d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"/>
							</svg>
							Upload File
						</button>
					</div>

					<!-- Inline KB Creator -->
					{#if showKbCreator}
						<div class="mt-3 p-4 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
							<div class="text-sm font-medium mb-2 dark:text-white">Create Knowledge Base</div>
							<div class="space-y-2">
								<input
									class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-white text-sm outline-hidden"
									bind:value={newKbName}
									placeholder="Name your knowledge base"
								/>
								<Textarea
									className="text-sm w-full bg-transparent outline-hidden resize-none dark:text-white placeholder-gray-500"
									rows={2}
									placeholder="Describe your knowledge base and objectives"
									bind:value={newKbDescription}
								/>
								<div class="flex justify-end">
									<button
										class="px-3 py-1.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 text-sm rounded-lg hover:opacity-90 transition disabled:opacity-50"
										on:click={createKnowledgeBaseInline}
										disabled={kbCreating}
									>
										{#if kbCreating}
											<span class="flex items-center gap-1.5">
												<Spinner className="size-3.5" />
												Creating...
											</span>
										{:else}
											Create & Select
										{/if}
									</button>
								</div>
							</div>
						</div>
					{/if}
				</div>

				<!-- RAG Query -->
				<div>
					<div class="text-xs font-medium text-gray-500 mb-1">Knowledge Base RAG Query</div>
					<input
						type="text"
						class="w-full text-sm bg-transparent outline-hidden dark:text-white placeholder-gray-500"
						bind:value={ragQuery}
						placeholder="e.g., company policies, product documentation, pricing..."
					/>
					<p class="text-xs text-gray-500 mt-1">Prepended to every KB search query — improves retrieval relevance for this client's context</p>
				</div>

				<!-- Monthly Limit -->
				<div>
					<div class="text-xs font-medium text-gray-500 mb-1">Monthly Limit (USD)</div>
					<input
						type="number"
						class="w-full text-sm bg-transparent outline-hidden dark:text-white"
						bind:value={monthlyLimit}
						min="0"
						step="1"
					/>
				</div>
			</div>

			<!-- Footer -->
			<div class="px-6 py-4 border-t border-gray-100 dark:border-gray-800 flex justify-end gap-2">
				<button
					on:click={() => { showModal = false; editClientId = null; }}
					class="px-4 py-2 text-sm rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-white transition"
				>
					Cancel
				</button>
				{#if isEdit}
					<button
						on:click={updateClient}
						disabled={loading}
						class="px-4 py-2 bg-black dark:bg-white text-white dark:text-black text-sm rounded-lg hover:opacity-90 disabled:opacity-50 transition flex items-center gap-2"
					>
						{#if loading}
							<Spinner className="size-4" />
						{/if}
						Save Changes
					</button>
				{:else}
					<button
						on:click={createClient}
						disabled={loading}
						class="px-4 py-2 bg-black dark:bg-white text-white dark:text-black text-sm rounded-lg hover:opacity-90 disabled:opacity-50 transition flex items-center gap-2"
					>
						{#if loading}
							<Spinner className="size-4" />
						{/if}
						Create Client
					</button>
				{/if}
			</div>
		</div>
	</div>
	{/if}

	<!-- Info box -->
	<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
		<div class="text-blue-800 dark:text-blue-300 font-medium mb-1">About Client Users</div>
		<ul class="text-sm text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
			<li>Clients are locked to a single model — they cannot change it</li>
			<li>Fixed system prompt is injected automatically into every chat</li>
			<li>Clients only see their assigned knowledge bases</li>
			<li>KB RAG Query improves knowledge base retrieval for the client's use case</li>
			<li>Model selector, Controls panel, Workspace, and Admin Panel are hidden from clients</li>
		</ul>
	</div>
</div>
