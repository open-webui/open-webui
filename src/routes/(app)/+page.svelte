<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';

    onMount(() => {
        const assignmentCompleted = localStorage.getItem('assignmentCompleted') === 'true';
        if (assignmentCompleted) {
            goto('/completion');
            return;
        }

        goto('/assignment-instructions');
    });

</script>

