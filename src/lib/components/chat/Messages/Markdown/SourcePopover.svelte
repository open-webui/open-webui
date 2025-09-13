<script lang="ts">
        import Tooltip from '$lib/components/common/Tooltip.svelte';
        export let snippet = '';
</script>

<Tooltip
        content={`<div class='max-w-xs md:max-w-md whitespace-pre-line text-xs'>${snippet}</div>`}
        placement="top"
        className="inline-flex"
        interactive={true}
        allowHTML={true}
        tippyOptions={{ maxWidth: 300 }}
>
        <slot />
</Tooltip>
