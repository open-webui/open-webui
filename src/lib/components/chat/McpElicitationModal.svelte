<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '../common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let show = false;
	export let message = '';
	export let requestedSchema: any = null;

	export let onAccept: (content: Record<string, any>) => void = () => {};
	export let onDecline: () => void = () => {};
	export let onCancel: () => void = () => {};

	const i18n = getContext('i18n');

	let formData: Record<string, any> = {};
	let validationErrors: Record<string, string> = {};

	$: if (show && requestedSchema) {
		initFormData();
	}

	function initFormData() {
		formData = {};
		validationErrors = {};
		const properties = requestedSchema?.properties ?? {};
		for (const [key, schema] of Object.entries(properties) as [string, any][]) {
			if (schema.type === 'boolean') {
				formData[key] = schema.default ?? false;
			} else if (schema.type === 'number' || schema.type === 'integer') {
				formData[key] = schema.default ?? null;
			} else if (schema.enum) {
				formData[key] = schema.default ?? '';
			} else {
				formData[key] = schema.default ?? '';
			}
		}
	}

	function getInputType(schema: any): string {
		if (schema.type === 'boolean') return 'checkbox';
		if (schema.type === 'number' || schema.type === 'integer') return 'number';
		if (schema.type === 'string') {
			if (schema.format === 'email') return 'email';
			if (schema.format === 'uri') return 'url';
			if (schema.format === 'date') return 'date';
			if (schema.format === 'date-time') return 'datetime-local';
		}
		return 'text';
	}

	function getLabel(key: string, schema: any): string {
		return schema.title || key;
	}

	function isRequired(key: string): boolean {
		return (requestedSchema?.required ?? []).includes(key);
	}

	function validate(): boolean {
		validationErrors = {};
		const properties = requestedSchema?.properties ?? {};
		const required = requestedSchema?.required ?? [];
		let valid = true;

		for (const [key, schema] of Object.entries(properties) as [string, any][]) {
			const value = formData[key];

			if (required.includes(key)) {
				if (value === null || value === undefined || value === '') {
					validationErrors[key] = $i18n.t('This field is required');
					valid = false;
					continue;
				}
			}

			if (value !== null && value !== undefined && value !== '') {
				if (schema.type === 'string' && typeof value === 'string') {
					if (schema.minLength && value.length < schema.minLength) {
						validationErrors[key] = $i18n.t('Minimum {{count}} characters', {
							count: schema.minLength
						});
						valid = false;
					}
					if (schema.maxLength && value.length > schema.maxLength) {
						validationErrors[key] = $i18n.t('Maximum {{count}} characters', {
							count: schema.maxLength
						});
						valid = false;
					}
				}
				if (
					(schema.type === 'number' || schema.type === 'integer') &&
					typeof value === 'number'
				) {
					if (schema.minimum !== undefined && value < schema.minimum) {
						validationErrors[key] = $i18n.t('Minimum value is {{min}}', {
							min: schema.minimum
						});
						valid = false;
					}
					if (schema.maximum !== undefined && value > schema.maximum) {
						validationErrors[key] = $i18n.t('Maximum value is {{max}}', {
							max: schema.maximum
						});
						valid = false;
					}
				}
			}
		}

		return valid;
	}

	function handleAccept() {
		if (!validate()) return;

		// Build clean content object, omitting empty optional fields
		const content: Record<string, any> = {};
		const properties = requestedSchema?.properties ?? {};
		const required = requestedSchema?.required ?? [];

		for (const key of Object.keys(properties)) {
			const value = formData[key];
			if (value !== null && value !== undefined && value !== '') {
				content[key] = value;
			} else if (required.includes(key)) {
				content[key] = value;
			}
		}

		onAccept(content);
		show = false;
	}

	function handleDecline() {
		onDecline();
		show = false;
	}

	function handleCancel() {
		onCancel();
		show = false;
	}
</script>

<Modal
	bind:show
	size="sm"
	on:close={() => {
		handleCancel();
	}}
>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-0.5">
			<div class="text-lg font-medium self-center flex items-center gap-2">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-5"
				>
					<path
						fill-rule="evenodd"
						d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
						clip-rule="evenodd"
					/>
				</svg>
				{$i18n.t('Information Requested')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					handleCancel();
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="px-5 pt-3 pb-5">
			{#if message}
				<p class="text-sm dark:text-gray-300 mb-4">{message}</p>
			{/if}

			{#if requestedSchema?.properties}
				<form
					on:submit|preventDefault={handleAccept}
					class="flex flex-col gap-3"
				>
					{#each Object.entries(requestedSchema.properties) as [key, schema]}
						{@const fieldSchema = /** @type {any} */ (schema)}
						<div class="flex flex-col gap-1">
							<label for="elicit-{key}" class="text-sm font-medium dark:text-gray-200">
								{getLabel(key, fieldSchema)}
								{#if isRequired(key)}
									<span class="text-red-500">*</span>
								{/if}
							</label>

							{#if fieldSchema.description}
								<p class="text-xs text-gray-500 dark:text-gray-400">
									{fieldSchema.description}
								</p>
							{/if}

							{#if fieldSchema.type === 'boolean'}
								<label class="flex items-center gap-2 cursor-pointer">
									<input
										id="elicit-{key}"
										type="checkbox"
										bind:checked={formData[key]}
										class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
									/>
									<span class="text-sm dark:text-gray-300">
										{fieldSchema.title || key}
									</span>
								</label>
							{:else if fieldSchema.enum}
								<select
									id="elicit-{key}"
									bind:value={formData[key]}
									class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-850 px-3 py-2 text-sm dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
								>
									<option value="">{$i18n.t('Select an option')}</option>
									{#each fieldSchema.enum as option, idx}
										<option value={option}>
											{fieldSchema.enumNames?.[idx] ?? option}
										</option>
									{/each}
								</select>
							{:else if fieldSchema.type === 'number' || fieldSchema.type === 'integer'}
								<input
									id="elicit-{key}"
									type="number"
									bind:value={formData[key]}
									min={fieldSchema.minimum}
									max={fieldSchema.maximum}
									step={fieldSchema.type === 'integer' ? 1 : 'any'}
									placeholder={fieldSchema.description || ''}
									class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-850 px-3 py-2 text-sm dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
								/>
							{:else}
								<input
									id="elicit-{key}"
									type={getInputType(fieldSchema)}
									bind:value={formData[key]}
									minlength={fieldSchema.minLength}
									maxlength={fieldSchema.maxLength}
									placeholder={fieldSchema.description || ''}
									class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-850 px-3 py-2 text-sm dark:text-gray-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
								/>
							{/if}

							{#if validationErrors[key]}
								<p class="text-xs text-red-500">{validationErrors[key]}</p>
							{/if}
						</div>
					{/each}

					<div class="flex justify-end gap-2 mt-3">
						<button
							type="button"
							class="px-3.5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-gray-200 dark:hover:bg-gray-800 transition rounded-full"
							on:click={handleDecline}
						>
							{$i18n.t('Decline')}
						</button>
						<button
							type="submit"
							class="px-3.5 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						>
							{$i18n.t('Submit')}
						</button>
					</div>
				</form>
			{:else}
				<p class="text-sm dark:text-gray-300 mb-4">
					{$i18n.t('The MCP server is requesting information but did not provide a form schema.')}
				</p>
				<div class="flex justify-end gap-2 mt-3">
					<button
						type="button"
						class="px-3.5 py-2 text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:text-gray-200 dark:hover:bg-gray-800 transition rounded-full"
						on:click={handleDecline}
					>
						{$i18n.t('Decline')}
					</button>
				</div>
			{/if}
		</div>
	</div>
</Modal>
