<script lang="ts">
	export let size = 'md';
</script>

<div class="w-full mt-2 mb-2">
	<div class="animate-pulse flex w-full">
		<div class="{size === 'md' ? 'space-y-2' : 'space-y-1.5'} w-full">
			<div
				class="{size === 'md' ? 'h-2' : 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm mr-14"
			/>

			<div class="grid grid-cols-3 gap-4">
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-2"
				/>
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-1"
				/>
			</div>
			<div class="grid grid-cols-4 gap-4">
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-1"
				/>
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-2"
				/>
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm col-span-1 mr-4"
				/>
			</div>

			<div class="{size === 'md' ? 'h-2' : 'h-1.5'} bg-gray-200 dark:bg-gray-600 rounded-sm" />
		</div>
	</div>
</div>
