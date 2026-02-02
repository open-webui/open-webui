<script lang="ts">
	export let size = 'md';
</script>

<div class="w-full mt-2 mb-2">
	<div class="animate-pulse flex w-full">
		<div class="{size === 'md' ? 'space-y-2' : 'space-y-1.5'} w-full">
			<div
				class="{size === 'md' ? 'h-2' : 'h-1.5'} rounded-sm mr-14"
				style="background: linear-gradient(90deg, #e5e7eb 0%, #f3f4f6 50%, #e5e7eb 100%); background-size: 200% 100%; animation: shimmer 2s infinite; border-radius: 6px;"
			/>

			<div class="grid grid-cols-3 gap-4">
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} rounded-sm col-span-2"
					style="background: linear-gradient(90deg, #e5e7eb 0%, #f3f4f6 50%, #e5e7eb 100%); background-size: 200% 100%; animation: shimmer 2s infinite 0.1s; border-radius: 6px;"
				/>
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} rounded-sm col-span-1"
					style="background: linear-gradient(90deg, #e5e7eb 0%, #f3f4f6 50%, #e5e7eb 100%); background-size: 200% 100%; animation: shimmer 2s infinite 0.2s; border-radius: 6px;"
				/>
			</div>
			<div class="grid grid-cols-4 gap-4">
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} rounded-sm col-span-1"
					style="background: linear-gradient(90deg, #e5e7eb 0%, #f3f4f6 50%, #e5e7eb 100%); background-size: 200% 100%; animation: shimmer 2s infinite 0.3s; border-radius: 6px;"
				/>
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} rounded-sm col-span-2"
					style="background: linear-gradient(90deg, #e5e7eb 0%, #f3f4f6 50%, #e5e7eb 100%); background-size: 200% 100%; animation: shimmer 2s infinite 0.4s; border-radius: 6px;"
				/>
				<div
					class="{size === 'md'
						? 'h-2'
						: 'h-1.5'} rounded-sm col-span-1 mr-4"
					style="background: linear-gradient(90deg, #e5e7eb 0%, #f3f4f6 50%, #e5e7eb 100%); background-size: 200% 100%; animation: shimmer 2s infinite 0.5s; border-radius: 6px;"
				/>
			</div>

			<div 
				class="{size === 'md' ? 'h-2' : 'h-1.5'} rounded-sm"
				style="background: linear-gradient(90deg, #e5e7eb 0%, #f3f4f6 50%, #e5e7eb 100%); background-size: 200% 100%; animation: shimmer 2s infinite 0.6s; border-radius: 6px;"
			/>
		</div>
	</div>
</div>

<style>
	@keyframes shimmer {
		0% {
			background-position: 200% 0;
		}
		100% {
			background-position: -200% 0;
		}
	}
	
	:global(.dark) div[style*="shimmer"] {
		background: linear-gradient(90deg, #4b5563 0%, #6b7280 50%, #4b5563 100%) !important;
		background-size: 200% 100% !important;
	}
</style>