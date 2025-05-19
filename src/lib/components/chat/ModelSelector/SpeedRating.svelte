<script lang="ts">
	export let rating: number = 0;
	export let max: number = 5;

	$: fullStars = Math.floor(rating);
	$: hasPartial = rating % 1 !== 0;
	$: partialFill = (rating % 1) * 100;
</script>

<div class="flex items-center gap-2.5">
    <div class="flex gap-1">
        {#each Array(fullStars) as _, i}
            <svg class="star filled text-lightGray-100 dark:text-white" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                    d="M3.3404 6.77561H4.7309V10.0156C4.7309 10.7716 5.1404 10.9246 5.6399 10.3576L9.0464 6.48761C9.4649 6.01511 9.2894 5.62361 8.6549 5.62361H7.2644V2.38361C7.2644 1.62761 6.8549 1.47461 6.3554 2.04161L2.9489 5.91161C2.5349 6.38861 2.7104 6.77561 3.3404 6.77561Z"
                    fill="currentColor"
                    stroke="currentColor"
                    stroke-width="0.96"
                    stroke-miterlimit="10"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                />
            </svg>
        {/each}

        {#if hasPartial}
            <div class="star partial-wrapper text-lightGray-100 dark:text-white" style="--fill: {partialFill}%">
                <svg class="star" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path
                        d="M3.3404 6.77561H4.7309V10.0156C4.7309 10.7716 5.1404 10.9246 5.6399 10.3576L9.0464 6.48761C9.4649 6.01511 9.2894 5.62361 8.6549 5.62361H7.2644V2.38361C7.2644 1.62761 6.8549 1.47461 6.3554 2.04161L2.9489 5.91161C2.5349 6.38861 2.7104 6.77561 3.3404 6.77561Z"
                        stroke="currentColor"
                        stroke-width="0.96"
                        stroke-miterlimit="10"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                    />
                </svg>

                <svg
                    class="star partial-fill text-lightGray-100 dark:text-white"
                    viewBox="0 0 12 12"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <path
                        d="M3.3404 6.77561H4.7309V10.0156C4.7309 10.7716 5.1404 10.9246 5.6399 10.3576L9.0464 6.48761C9.4649 6.01511 9.2894 5.62361 8.6549 5.62361H7.2644V2.38361C7.2644 1.62761 6.8549 1.47461 6.3554 2.04161L2.9489 5.91161C2.5349 6.38861 2.7104 6.77561 3.3404 6.77561Z"
                        stroke="currentColor"
                        fill="currentColor"
                        stroke-width="0.96"
                        stroke-miterlimit="10"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                    />
                </svg>
            </div>
        {/if}

        {#each Array(max - fullStars - (hasPartial ? 1 : 0)) as _, i}
            <svg class="star text-lightGray-100 dark:text-white" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path
                    d="M3.3404 6.77561H4.7309V10.0156C4.7309 10.7716 5.1404 10.9246 5.6399 10.3576L9.0464 6.48761C9.4649 6.01511 9.2894 5.62361 8.6549 5.62361H7.2644V2.38361C7.2644 1.62761 6.8549 1.47461 6.3554 2.04161L2.9489 5.91161C2.5349 6.38861 2.7104 6.77561 3.3404 6.77561Z"
                    stroke="currentColor"
                    stroke-width="0.96"
                    stroke-miterlimit="10"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                />
            </svg>
        {/each}
    </div>
    <p class="text-xs text-lightGray-100 dark:text-white">
        {rating.toFixed(1)}
    </p>
</div>

<style>
	.star {
		width: 1rem;
		height: 1rem;
	}

	.filled {
		/* color: #ffffff; */
	}

	.partial-wrapper {
		position: relative;
	}

	.partial-fill {
		position: absolute;
		top: 0;
		left: 0;
		/* color: #ffffff; */
		clip-path: inset(0 calc(100% - var(--fill, 0%)) 0 0);
		pointer-events: none;
	}
</style>
