<script lang="ts">
	export let className = 'w-[38px] h-[38px]';
    export let disabled = false;
</script>

{#if disabled}
<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38" fill="none">
<rect y="0.71875" width="36" height="36" rx="18" fill="#D5DBE6"/>
<g opacity="0.7" filter="url(#filter0_d_2059_18167)">
<path d="M17.3733 26.6381V13.175L13.3077 17.2279L12.4375 16.3577L17.9983 10.7969L23.5592 16.3577L22.689 17.2487L18.6233 13.1829V26.6381H17.3733Z" fill="#F3F9FF"/>
</g>
<defs>
<filter id="filter0_d_2059_18167" x="10.4375" y="5.79688" width="27.1211" height="31.8398" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
<feFlood flood-opacity="0" result="BackgroundImageFix"/>
<feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
<feOffset dx="6" dy="3"/>
<feGaussianBlur stdDeviation="4"/>
<feComposite in2="hardAlpha" operator="out"/>
<feColorMatrix type="matrix" values="0 0 0 0 0.403333 0 0 0 0 0.484378 0 0 0 0 0.630258 0 0 0 0.3 0"/>
<feBlend mode="normal" in2="BackgroundImageFix" result="effect1_dropShadow_2059_18167"/>
<feBlend mode="normal" in="SourceGraphic" in2="effect1_dropShadow_2059_18167" result="shape"/>
</filter>
</defs>
</svg>
{:else}
<svg xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 52 52" fill="none">
<g filter="url(#filter0_d_2059_10458)">
<rect x="2" y="5" width="36" height="36" rx="18" fill="#004280" shape-rendering="crispEdges"/>
<g filter="url(#filter1_f_2059_10458)">
<circle cx="20" cy="23" r="14" fill="url(#paint0_linear_2059_10458)"/>
</g>
<path d="M19.3733 30.9155V17.4523L15.3077 21.5053L14.4375 20.6351L19.9983 15.0742L25.5592 20.6351L24.689 21.5261L20.6233 17.4603V30.9155H19.3733Z" fill="#F3F9FF"/>
</g>
<defs>
<filter id="filter0_d_2059_10458" x="0" y="0" width="52" height="52" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
<feFlood flood-opacity="0" result="BackgroundImageFix"/>
<feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
<feOffset dx="6" dy="3"/>
<feGaussianBlur stdDeviation="4"/>
<feComposite in2="hardAlpha" operator="out"/>
<feColorMatrix type="matrix" values="0 0 0 0 0.403333 0 0 0 0 0.484378 0 0 0 0 0.630258 0 0 0 0.3 0"/>
<feBlend mode="normal" in2="BackgroundImageFix" result="effect1_dropShadow_2059_10458"/>
<feBlend mode="normal" in="SourceGraphic" in2="effect1_dropShadow_2059_10458" result="shape"/>
</filter>
<filter id="filter1_f_2059_10458" x="2" y="5" width="36" height="36" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
<feFlood flood-opacity="0" result="BackgroundImageFix"/>
<feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape"/>
<feGaussianBlur stdDeviation="2" result="effect1_foregroundBlur_2059_10458"/>
</filter>
<linearGradient id="paint0_linear_2059_10458" x1="9.36" y1="14.04" x2="30.64" y2="32.52" gradientUnits="userSpaceOnUse">
<stop stop-color="#215A9E"/>
<stop offset="0.639423" stop-color="#004280"/>
</linearGradient>
</defs>
</svg>

{/if}
