<script lang="ts">
	import { getContext } from 'svelte';
	import Modal from '../common/Modal.svelte';
	import XMark from '../icons/XMark.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	export let data;
	export let onResponse: (value: any) => void;

	let show = true;
	const fields: [string, any][] = Object.entries(data.requestedSchema?.properties ?? {});
	let values = Object.fromEntries(fields.map(([name, field]) => [name, field.default]));
	let error = '';
	$: if (!show) onResponse({ action: 'cancel' });

	const options = (field: any): { const: string; title?: string }[] =>
		field.enum?.map((value: string, index: number) => ({
			const: value,
			title: field.enumNames?.[index] ?? value
		})) ??
		field.oneOf ??
		field.anyOf ??
		[];
	const supported = fields.every(([, field]) =>
		field.type === 'array'
			? options(field.items ?? {}).length > 0
			: ['string', 'number', 'integer', 'boolean'].includes(field.type)
	);

	const submit = () => {
		for (const [name, field] of fields) {
			if (field.type === 'array' && values[name] !== undefined) {
				const count = values[name]?.length ?? 0;
				if (count < (field.minItems ?? 0) || count > (field.maxItems ?? Infinity)) {
					error = `${field.title ?? name}: ${$i18n.t('Invalid value')}`;
					return;
				}
			}
		}
		onResponse({
			action: 'accept',
			content: Object.fromEntries(Object.entries(values).filter(([, value]) => value !== undefined))
		});
	};
</script>

<Modal bind:show size="sm">
	<div class="flex justify-between dark:text-gray-300 px-4 pt-3 pb-1">
		<div class="text-sm font-medium self-center">{data.server_name}</div>
		<button
			type="button"
			aria-label={$i18n.t('Close')}
			class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
			on:click={() => (show = false)}
		>
			<XMark className="size-4" />
		</button>
	</div>
	<form class="flex flex-col gap-3 px-4 pb-4 dark:text-gray-200" on:submit|preventDefault={submit}>
		<p class="text-sm whitespace-pre-wrap break-words">{data.message}</p>

		{#if data.mode === 'url'}
			<p class="text-sm text-gray-500">{$i18n.t('Open this link to continue:')}</p>
			<a
				href={data.url}
				target="_blank"
				rel="noopener noreferrer"
				class="text-sm underline break-all"
				on:click={() => onResponse({ action: 'accept' })}>{data.url}</a
			>
		{:else if supported}
			{#each fields as [name, field], index}
				{@const id = `elicitation-${index}`}
				{@const required = data.requestedSchema.required?.includes(name) ?? false}
				<div class="flex flex-col gap-1.5 text-sm">
					<label for={id} class="text-xs font-normal">
						{field.title ?? name}
						{#if required}<span class="ml-1 text-gray-500">* {$i18n.t('required')}</span>{/if}
					</label>
					{#if field.description}
						<p id={`${id}-description`} class="text-xs text-gray-500 whitespace-pre-wrap">
							{field.description}
						</p>
					{/if}
					{#if field.type === 'array'}
						<select
							{id}
							multiple
							{required}
							aria-describedby={field.description ? `${id}-description` : undefined}
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
							bind:value={values[name]}
						>
							{#each options(field.items ?? {}) as option}
								<option value={option.const}>{option.title ?? option.const}</option>
							{/each}
						</select>
					{:else if field.type === 'boolean' || options(field).length}
						<select
							{id}
							{required}
							aria-describedby={field.description ? `${id}-description` : undefined}
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
							bind:value={values[name]}
						>
							<option value={undefined}>{$i18n.t('Select an option')}</option>
							{#if field.type === 'boolean'}
								<option value={true}>{$i18n.t('Yes')}</option>
								<option value={false}>{$i18n.t('No')}</option>
							{:else}
								{#each options(field) as option}
									<option value={option.const}>{option.title ?? option.const}</option>
								{/each}
							{/if}
						</select>
					{:else if field.type === 'number' || field.type === 'integer'}
						<input
							{id}
							type="number"
							{required}
							aria-describedby={field.description ? `${id}-description` : undefined}
							min={field.minimum}
							max={field.maximum}
							step={field.type === 'integer' ? 1 : 'any'}
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
							bind:value={values[name]}
						/>
					{:else}
						<input
							{id}
							type={['email', 'date'].includes(field.format)
								? field.format
								: field.format === 'uri'
									? 'url'
									: 'text'}
							placeholder={field.format === 'date-time' ? 'YYYY-MM-DDTHH:mm:ssZ' : undefined}
							{required}
							aria-describedby={field.description ? `${id}-description` : undefined}
							minlength={field.minLength}
							maxlength={field.maxLength}
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-hidden border border-gray-100/30 dark:border-gray-850/30"
							bind:value={values[name]}
						/>
					{/if}
				</div>
			{/each}
		{:else}
			<p role="alert">{$i18n.t('Unsupported input format')}</p>
		{/if}
		{#if error}<p role="alert" class="text-sm text-red-500">{error}</p>{/if}
		<div class="flex justify-end gap-1.5 pt-3 text-sm font-normal">
			<button
				type="button"
				class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition disabled:opacity-60 bg-white hover:bg-gray-100 text-black dark:bg-black dark:text-white dark:hover:bg-gray-900"
				on:click={() => onResponse({ action: 'cancel' })}>{$i18n.t('Cancel')}</button
			>
			<button
				type="button"
				class="flex h-7 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition disabled:opacity-60 bg-gray-100 hover:bg-gray-100/70 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-850/60 dark:text-white"
				on:click={() => onResponse({ action: 'decline' })}>{$i18n.t('Decline')}</button
			>
			{#if data.mode !== 'url' && supported}
				<button
					type="submit"
					class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
					>{$i18n.t('Submit')}</button
				>
			{/if}
		</div>
	</form>
</Modal>
