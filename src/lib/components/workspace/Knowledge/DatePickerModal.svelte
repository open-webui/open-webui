<script lang="ts">
	import CalendarSidebar from "$lib/components/calendar/CalendarSidebar.svelte";
	import Modal from "$lib/components/common/Modal.svelte";

    export let currentDate: Date = new Date();
    export let onDateSelect: (date: Date) => void = () => {};
</script>


<Modal>
    <CalendarSidebar  currentDate={currentDate} onDateSelect={onDateSelect}/>
</Modal>