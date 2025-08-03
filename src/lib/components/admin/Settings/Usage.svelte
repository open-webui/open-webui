<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import MyOrganizationUsage from './MyOrganizationUsage.svelte';

	const i18n = getContext('i18n');
</script>

<MyOrganizationUsage />