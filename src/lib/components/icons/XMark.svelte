<script lang="ts">
  interface Props {
    className?: string;
    strokeWidth?: string;
  }

  let { className = 'size-3.5', strokeWidth = '2' }: Props = $props();
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
    d="M6 18 18 6M6 6l12 12"
    stroke-linecap="round"
    stroke-linejoin="round"
  />
</svg>
