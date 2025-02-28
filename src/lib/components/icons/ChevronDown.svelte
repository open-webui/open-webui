<script lang="ts">
  interface Props {
    className?: string;
    strokeWidth?: string;
  }

  let { className = 'w-4 h-4', strokeWidth = '1.5' }: Props = $props();
</script>

<svg
  class={className}
  fill="none"
  stroke="currentColor"
  stroke-width={strokeWidth}
  viewBox="0 0 24 24"
  xmlns="http://www.w3.org/2000/svg"
>
  <path
    d="m19.5 8.25-7.5 7.5-7.5-7.5"
    stroke-linecap="round"
    stroke-linejoin="round"
  />
</svg>
