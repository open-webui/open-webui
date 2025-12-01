<script lang="ts">
  export let src: string = "/static/load_animation.html";
  export let title: string = "Loading";
  export let style: string = "position:absolute;top:0;left:0;width:100%;height:100%;border:0;background:transparent";
</script>

<iframe {src} {title} {style}></iframe>
