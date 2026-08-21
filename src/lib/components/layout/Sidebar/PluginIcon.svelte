<script lang="ts">
	import CodeIcon from '$lib/components/icons/Code.svelte';

	export let icon: string | null = null;
	export let className = 'size-4 shrink-0';
	export let strokeWidth = '1.5';

	type IconComponent = typeof CodeIcon;
	const iconModules = import.meta.glob('../../icons/*.svelte');
	let Icon: IconComponent = CodeIcon;
	let requestId = 0;

	// Manifest identifiers are normalized from kebab_case, snake_case, or camelCase
	// to the component basename: "chart-bar" and "chart_bar" both resolve ChartBar.
	const componentName = (value: string) =>
		value
			.replace(/([a-z0-9])([A-Z])/g, '$1 $2')
			.split(/[-_\s]+/)
			.filter(Boolean)
			.map((part) => part[0].toUpperCase() + part.slice(1).toLowerCase())
			.join('');

	$: void loadIcon(icon);

	async function loadIcon(value: string | null) {
		const currentRequest = ++requestId;
		Icon = CodeIcon;
		if (!value) return;

		const loader = iconModules[`../../icons/${componentName(value)}.svelte`];
		if (!loader) return;
		try {
			const module = (await loader()) as { default: IconComponent };
			if (currentRequest === requestId) Icon = module.default;
		} catch {
			// A missing or invalid icon is intentionally rendered as the Code fallback.
		}
	}
</script>

<svelte:component this={Icon} {className} {strokeWidth} />
