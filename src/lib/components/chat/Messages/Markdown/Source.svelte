<script lang="ts">
        import SourcePopover from './SourcePopover.svelte';

        export let id;
        export let token;
        export let onClick: Function = () => {};

        let attributes: Record<string, string | undefined> = {};

        function extractAttributes(input: string): Record<string, string> {
                const regex = /(\w+)="([^"]*)"/g;
                let match;
                let attrs: Record<string, string> = {};

                while ((match = regex.exec(input)) !== null) {
                        attrs[match[1]] = match[2];
                }

                return attrs;
        }

        $: attributes = extractAttributes(token.text);
</script>

{#if attributes.title !== 'N/A'}
        <SourcePopover snippet={decodeURIComponent(attributes.snippet ?? '')}>
                <button
                        class="text-xs font-medium w-fit translate-y-[2px] px-2 py-0.5 dark:bg-white/5 dark:text-white/60 dark:hover:text-white bg-gray-50 text-black/60 hover:text-black transition rounded-lg"
                        on:click={() => {
                                onClick(id, attributes.data);
                        }}
                >
                        [{attributes.data}]
                </button>
        </SourcePopover>
{/if}
