<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import '$lib/styles/pill-button.css'; // Import the shared styles
    import Carousel from '$lib/components/common/Carousel.svelte';

    const dispatch = createEventDispatcher();


    export let products = [];
    export let chat_id = '';
    export let gift_idea_id = {id: ''};

    export let product_context = { header_message: '', footer_message: '' };

    function mapExperienceToProduct(experience: any) {
        return {experience_info: {
                name: experience.name,
                display_name: experience.name,
                description: 'description' in experience ? experience.description : null,
                price: 'price' in experience ? experience.price : null,
                rating: 'rating' in experience ? experience.rating : null,
                city: 'location' in experience ? experience.location.city : null,
                state: 'location' in experience ? experience.location.state : null,
                country: 'location' in experience ? experience.location.country : null,
                zipcode: 'location' in experience ? experience.location.zip_code : null,
                phone: 'phone' in experience ? experience.phone : null,
                image_urls: experience.image_url,
                image_url: experience.image_url,
                url: ('attributes' in experience && 'business_url' in experience.attributes)
                    ? experience.attributes.business_url
                    : ('url' in experience ? experience.url : null),
            },
            thumbnails: experience.thumbnails
        };
    }

    async function buildProductListFromGiftRequestFile(chat_id: string, gift_idea_id: { id: string }) {
        const response = await fetch(`/api/gift_requests/${chat_id}`);
        if (!response.ok) {
          console.error("File not found");
          return;
        }
        const giftIdeaId = gift_idea_id.id;
        const giftRequestContent = await response.text();
        const currentGiftRequest = JSON.parse(giftRequestContent)[0].current_gift_idea;
        // Check if the gift idea ID matches currentGiftRequest.hash_id
        if (currentGiftRequest && currentGiftRequest.hash_id == giftIdeaId) {
            const gift_type = currentGiftRequest.type;
            if (gift_type === 'product') {
                products = currentGiftRequest.matched_products;
            } else if (gift_type === 'experience') {
                products = currentGiftRequest.matched_experiences.map(mapExperienceToProduct);
            } else {
                console.error("Unknown gift type:", gift_type);
            }
        } else {
            // iterate thought previous gift ideas to find the matching one
            const previousGiftIdeas = JSON.parse(giftRequestContent)[0].previous_gift_ideas;
            const matchingGiftIdea = previousGiftIdeas.find(idea => idea.hash_id === giftIdeaId);
            if (matchingGiftIdea) {
                const gift_type = matchingGiftIdea.type;
                if (gift_type === 'product') {
                    products = matchingGiftIdea.matched_products;
                } else if (gift_type === 'experience') {
                    products = matchingGiftIdea.matched_experiences.map(mapExperienceToProduct);
                } else {
                    console.error("Unknown gift type:", gift_type);
                }
            } else {
                console.error("No matching gift idea found for ID:", giftIdeaId);
            }
        }
    }

    buildProductListFromGiftRequestFile(chat_id, gift_idea_id);

    function handleExperienceBuyNowClick(url: string, chat_id: string) {
        console.log('Buy Now clicked', url, chat_id);
        fetch('/api/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ log_message: `Buy Now clicked: ${url}, chat_id: ${chat_id}` })
        });
        window.open(url, '_blank');
    }
</script>

<div class="product-grid-container">
    <!-- Add text on top -->
    {#if product_context.header_message}
        {product_context.header_message}
    {/if}

    <div class="product-grid">
        {#each products as product}
            <div class="grid-item dark:bg-gray-800 dark:text-gray-200 dark:shadow-gray-400 bg-gray-100 text-gray-800 shadow-md rounded-lg">
<!--                &lt;!&ndash; Display image &ndash;&gt;-->
<!--                <img src={product.thumbnails[0]} alt={product.thumbnails[0]} class="grid-item-image" />-->
								<div class="grid-item-image relative items-center justify-center bg-white">
									<Carousel imageUrls={product.thumbnails} showArrows={false} />
								</div>

                <!-- Display name -->
                {#if product.product_info}
                    <h3 class="grid-item-name">{product.product_info.display_name}</h3>
                    <p class="grid-item-price">{product.product_info.price ?? ''}</p>
                {:else if product.experience_info}
                    <h3 class="grid-item-name">{product.experience_info.display_name}</h3>
                    <p class="grid-item-location">
                        {product.experience_info.city ?? ''}{product.experience_info.city && product.experience_info.state ? ', ' : ''}{product.experience_info.state ?? ''}
                        <br>
                        {product.experience_info.price ?? ''}
                    </p>
                {/if}


                <!-- Buy now button -->
                <div class="grid-item-footer w-full flex justify-center py-1">
                    {#if product.product_info}
                        <button class="pill-button " on:click={() => handleExperienceBuyNowClick(product.product_info.url, chat_id)}>
                            {'Buy Now'}
                        </button>
                    {:else if product.experience_info}
                        <button class="pill-button " on:click={() => handleExperienceBuyNowClick(product.experience_info.url, chat_id)}>
                            {'Book Now'}
                        </button>
                    {/if}
                </div>
            </div>
        {/each}
    </div>

    {#if product_context.footer_message}
        {product_context.footer_message}
    {/if}
</div>

<style>
    .product-grid-container {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 0rem;
    }

    .grid-item {
        position: relative;
        display: flex;
        flex-direction: column;
        text-align: left;
        margin: 0; /* Remove any margin */
        border-radius: 0; /* Remove rounded corners */
        border: 1px solid #ddd;
    }

    .grid-item-footer {
       margin-top: auto;
    }

    .grid-item-image {
        width: 100%;
        height: 200px;
        object-fit: cover;
        margin: 0; /* Remove any margin */
        border-radius: 0; /* Remove rounded corners */
    }

    .grid-item-name {
        font-size: 1rem;
        align-self: left;
        font-weight: bold;
        margin: 0.25rem 0 0.1rem 1rem;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2em; /* Adjust line height to match the text spacing */
    }

    .grid-item-price {
        font-size: 0.85rem;
        align-self: left;
        font-weight: lighter;
        margin: 0rem 0 0.1rem 1rem;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2em; /* Adjust line height to match the text spacing */
    }

    .grid-item-location {
        font-size: 0.85rem;
        align-self: left;
        font-weight: normal;
        margin: 0.5rem 0 0.5rem 1rem;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2em; /* Adjust line height to match the text spacing */
    }
</style>