<script lang="ts">
  interface Props {
    className?: string;
    strokeWidth?: string;
  }

  let { className = 'size-4', strokeWidth = '1.5' }: Props = $props();
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
    d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
    stroke-linecap="round"
    stroke-linejoin="round"
  />
</svg>
