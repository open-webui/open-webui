<script lang="ts">
  interface Props {
    className?: string;
    strokeWidth?: string;
  }

  let { className = 'size-4', strokeWidth = '2' }: Props = $props();
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
    d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
    stroke-linecap="round"
    stroke-linejoin="round"
  />
</svg>
