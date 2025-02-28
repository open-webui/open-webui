<script lang="ts">
  interface Props {
    className?: string;
    strokeWidth?: string;
  }

  let { className = 'size-4', strokeWidth = '1.5' }: Props = $props();
</script>

<svg
  class={className}
  aria-hidden="true"
  fill="none"
  height="24"
  stroke="currentColor"
  stroke-width={strokeWidth}
  viewBox="0 0 22 22"
  width="24"
  xmlns="http://www.w3.org/2000/svg"
>
  <path
    d="m4 12 8-8 8 8M6 10.5V19a1 1 0 0 0 1 1h3v-3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v3h3a1 1 0 0 0 1-1v-8.5"
    stroke="currentColor"
    stroke-linecap="round"
    stroke-linejoin="round"
  />
</svg>
