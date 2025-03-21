<script lang="ts">
	import { onMount } from 'svelte';
	import Button, { ButtonType } from '$lib/IONOS/components/common/Button.svelte'

	onMount(() => {
		console.log(Button.type);
	});
</script>

<div class="bg-slate-100 p-8 pb-32">

<h1>Buttons</h1>

<h2>Mono-Primary</h2>

<Button className="px-4 py-1" type={ButtonType.primary}>stateless</Button>
<Button className="px-4 py-1" type={ButtonType.primary} disabled={true}>disabled</Button>
<Button className="px-4 py-1" type={ButtonType.primary} pressed={true}>pressed</Button>
<Button className="px-4 py-1" type={ButtonType.primary} disabled={true} pressed={true}>disabled + pressed</Button>


<h2>Mono-Secondary</h2>

<Button className="px-4 py-1" type={ButtonType.secondary}>stateless</Button>
<Button className="px-4 py-1" type={ButtonType.secondary} disabled={true}>disabled</Button>
<Button className="px-4 py-1" type={ButtonType.secondary} pressed={true}>pressed</Button>
<Button className="px-4 py-1" type={ButtonType.secondary} disabled={true} pressed={true}>disabled + pressed</Button>


<h2>Mono-Tertiary</h2>

<Button className="px-4 py-1" type={ButtonType.tertiary}>stateless</Button>
<Button className="px-4 py-1" type={ButtonType.tertiary} disabled={true}>disabled</Button>
<Button className="px-4 py-1" type={ButtonType.tertiary} pressed={true}>pressed</Button>
<Button className="px-4 py-1" type={ButtonType.tertiary} disabled={true} pressed={true}>disabled + pressed</Button>


<h2>Caution</h2>

<Button className="px-4 py-1" type={ButtonType.caution}>stateless</Button>
<Button className="px-4 py-1" type={ButtonType.caution} disabled={true}>disabled</Button>
<Button className="px-4 py-1" type={ButtonType.caution} pressed={true}>pressed</Button>
<Button className="px-4 py-1" type={ButtonType.caution} disabled={true} pressed={true}>disabled + pressed</Button>


<h2>Special</h2>

<Button className="px-4 py-1" type={ButtonType.special}>stateless</Button>
<Button className="px-4 py-1" type={ButtonType.special} disabled={true}>disabled</Button>
<Button className="px-4 py-1" type={ButtonType.special} pressed={true}>pressed</Button>
<Button className="px-4 py-1" type={ButtonType.special} disabled={true} pressed={true}>disabled + pressed</Button>



</div>
