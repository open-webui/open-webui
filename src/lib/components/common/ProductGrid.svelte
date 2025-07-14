<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import '$lib/styles/pill-button.css'; // Import the shared styles
    import Carousel from '$lib/components/common/Carousel.svelte';
    import {mobile } from '$lib/stores';

    const dispatch = createEventDispatcher();


    export let products = [];
    export let chat_id = '';
    export let gift_idea_id = {id: ''};
    export let product_context = { header_message: '', footer_message: '' };

    export let productSelected = null;
    export let showProductDetailsModal = false; // New state variable to manage modal
    function handleViewDetailsClick(product) {
        showProductDetailsModal = true; // Show the modal
        productSelected = product;
    }

    function handleCloseClick() {
        showProductDetailsModal = false;
        productSelected = null;
    }

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
        const previousGiftIdeas = JSON.parse(giftRequestContent)[0].previous_gift_ideas;
        products = [];
        if (giftIdeaId === 'random') {
            if (currentGiftRequest) {
              products = currentGiftRequest.matched_products.filter((p: any) => p.reranker_score > 0.2);
            }
            if (previousGiftIdeas.length > 0) {
              // const firstIdea = previousGiftIdeas[0];
              // products = firstIdea.matched_products.filter((p: any) => p.reranker_score > 0.2);
              // Add products for all previous gift ideas to products
              products = products.concat(
                previousGiftIdeas.flatMap((idea: { type: string; matched_products: any[] }) => {
                  if (idea.type === 'product') {
                    return idea.matched_products.filter((p: { reranker_score: number }) => p.reranker_score > 0.2);
                  }
                  return [];
                })
              );
            }
            // Randomize the products
            products = products.sort(() => Math.random() - 0.5);
        }
        // Check if the gift idea ID matches currentGiftRequest.hash_id
        else if (currentGiftRequest && currentGiftRequest.hash_id == giftIdeaId) {
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

{#if showProductDetailsModal}
    <div class="modal" role="dialog" tabindex="0" aria-modal="true" on:click={() => handleCloseClick()} on:keydown={(e) => e.key === 'Escape' && handleCloseClick()} >
        <div class="relative items-center justify-center h-[400px] w-[400px] border-1 rounded-lg bg-white"
            on:click|stopPropagation tabindex="0" role="document" on:keydown={(e) => e.key === 'Escape' && handleCloseClick()}>
            <button class="close-button px-1 py-1 rounded-sm bg-gray-50 border-gray-50 text-gray-700 shadow-md z-10" on:click={() => handleCloseClick()} >
              <div class=" m-auto self-center">
                <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                    class="size-3.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M6 6l12 12M6 18L18 6"
                    />
                </svg>
              </div>
            </button>
            <Carousel imageUrls={productSelected.thumbnails} showArrows={true} duration={3000} />
        </div>
    </div>
{/if}

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
                {#if !$mobile}
                  <button class="grid-item-image relative items-center justify-center bg-white"
                  on:click={() => handleViewDetailsClick(product)}>
                    <Carousel imageUrls={product.thumbnails} showArrows={false} />
                  </button>
                {:else}
                  <button class="grid-item-image-mobile relative items-center justify-center bg-white"
                  on:click={() => handleViewDetailsClick(product)}>
                    <Carousel imageUrls={product.thumbnails} showArrows={false} />
                  </button>
                {/if}

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
    .modal {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.8);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }

    .close-button {
      position:absolute;
      display: flex;
      cursor: pointer;
      top: 0;
      right: 0;
    }

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
        height: 300px;
        object-fit: cover;
        margin: 0; /* Remove any margin */
        border-radius: 0; /* Remove rounded corners */
    }

    .grid-item-image-mobile {
        width: 100%;
        height: 360px;
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