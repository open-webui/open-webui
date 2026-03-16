<script lang="ts">
	export let data: unknown;
	export let key: string | null = null;
	export let root = true;
	export let expandDepth = 2;

	let depth = 0;
	export { depth };

	$: expanded = depth < expandDepth;

	const toggle = () => {
		expanded = !expanded;
	};

	$: type = Array.isArray(data) ? 'array' : data === null ? 'null' : typeof data;
	$: isExpandable = type === 'object' || type === 'array';
	$: entries = isExpandable && data !== null ? Object.entries(data as Record<string, unknown>) : [];
	$: bracket = type === 'array' ? ['[', ']'] : ['{', '}'];
	$: preview =
		type === 'array'
			? `[${(data as unknown[]).length}]`
			: type === 'object'
				? `{${entries.length}}`
				: '';
</script>

{#if isExpandable}
	<div class="json-node" class:json-root={root}>
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<span class="json-toggle" on:click={toggle}>
			<span class="json-arrow" class:json-expanded={expanded}>▶</span>
			{#if key !== null}<span class="json-key">{key}</span><span class="json-colon">: </span>{/if}
			{#if !expanded}<span class="json-preview">{bracket[0]} {preview} {bracket[1]}</span>{/if}
			{#if expanded}<span class="json-bracket">{bracket[0]}</span>{/if}
		</span>
		{#if expanded}
			<div class="json-children">
				{#each entries as [k, v], i}
					<div class="json-entry">
						<svelte:self
							data={v}
							key={type === 'array' ? null : k}
							root={false}
							depth={depth + 1}
							{expandDepth}
						/>
						{#if i < entries.length - 1}<span class="json-comma">,</span>{/if}
					</div>
				{/each}
			</div>
			<span class="json-bracket">{bracket[1]}</span>
		{/if}
	</div>
{:else}
	<span class="json-leaf">
		{#if key !== null}<span class="json-key">{key}</span><span class="json-colon">: </span>{/if}
		{#if type === 'string'}
			<span class="json-string">"{data}"</span>
		{:else if type === 'number'}
			<span class="json-number">{data}</span>
		{:else if type === 'boolean'}
			<span class="json-boolean">{data}</span>
		{:else if type === 'null'}
			<span class="json-null">null</span>
		{:else}
			<span>{String(data)}</span>
		{/if}
	</span>
{/if}

<style>
	.json-root {
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		font-size: 0.75rem;
		line-height: 1.6;
		padding: 0.75rem 1rem;
	}
	.json-node {
		/* keep structure visible */
	}
	.json-toggle {
		cursor: pointer;
		user-select: none;
	}
	.json-toggle:hover {
		opacity: 0.7;
	}
	.json-arrow {
		display: inline-block;
		width: 1em;
		font-size: 0.55em;
		transition: transform 0.15s ease;
		color: #9ca3af;
		vertical-align: middle;
	}
	.json-expanded {
		transform: rotate(90deg);
	}
	.json-children {
		padding-left: 1.25em;
		border-left: 1px solid rgba(128, 128, 128, 0.15);
		margin-left: 0.35em;
	}
	.json-entry {
		/* one entry per line */
	}
	.json-key {
		color: #0550ae;
	}
	:global(.dark) .json-key {
		color: #79c0ff;
	}
	.json-colon {
		color: #6b7280;
	}
	.json-string {
		color: #0a3069;
	}
	:global(.dark) .json-string {
		color: #a5d6ff;
	}
	.json-number {
		color: #0550ae;
	}
	:global(.dark) .json-number {
		color: #79c0ff;
	}
	.json-boolean {
		color: #cf222e;
	}
	:global(.dark) .json-boolean {
		color: #ff7b72;
	}
	.json-null {
		color: #6b7280;
		font-style: italic;
	}
	.json-bracket {
		color: #6b7280;
	}
	.json-comma {
		color: #6b7280;
	}
	.json-preview {
		color: #9ca3af;
		font-size: 0.85em;
	}
	:global(.dark) .json-preview {
		color: #6b7280;
	}
</style>
