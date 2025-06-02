<script lang="ts">
    import { createEventDispatcher } from 'svelte';
    import { mobile } from '$lib/stores';
    import '$lib/styles/pill-button.css'; // Import the shared styles
    import Carousel from '$lib/components/common/Carousel.svelte';
    import { getProductImages } from '$lib/utils/images';

    const dispatch = createEventDispatcher();



    export let products = [];

    export let product_context = { header_message: '', footer_message: '' };
    export let productSelected = null;
    export let showProductDetailsModal = false; // New state variable to manage modal

    $: _productSelected = productSelected;

    function handleViewDetailsClick(product) {
        showProductDetailsModal = true; // Show the modal
        productSelected = product;
    }

    function handleCloseClick() {
        showProductDetailsModal = false;
        productSelected = null;
    }
</script>

{#if showProductDetailsModal}
    <div class="modal">
        <div class="relative items-center justify-center h-[400px] w-[400px] border-1 rounded-lg">
            <button class="close-button px-1 py-1 rounded-lg bg-gray-50 dark:bg-gray-600 border-1 shadow-md z-10" on:click={() => handleCloseClick()} >
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
                <!-- Display image -->
                <img src={product.thumbnails[0]} alt={product.thumbnails[0]} class="grid-item-image" />

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
                        <button class="pill-button rounded-3xl px-3" on:click={() => window.open(product.product_info.url, '_blank')}>
                            {'Buy Now'}
                        </button>
                    {:else if product.experience_info}
                        <button class="pill-button rounded-3xl px-3" on:click={() => window.open(product.experience_info.url, '_blank')}>
                            {'Book Now'}
                        </button>
                    {/if}
                </div>

                {#if product.product_info}
                    <button
                    class="details-button px-1 py-1 rounded-lg bg-gray-200 border-1"
                    on:click={() => handleViewDetailsClick(product)}
                    >
                        <div class=" m-auto self-center">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" id="magnifying-glass">
                              <path fill="#333" d="M9.37395 6.4078C8.5036 6.44165 7.71765 6.75215 7.2972 7.1727C7.10195 7.368 6.78535 7.368 6.5901 7.17275C6.3948 6.97755 6.39475 6.66095 6.58995 6.46565C7.2387 5.81685 8.2944 5.44905 9.33505 5.40855C10.3825 5.3678 11.5261 5.6546 12.3269 6.4556C12.5221 6.65085 12.5221 6.96745 12.3268 7.1627C12.1316 7.35795 11.815 7.3579 11.6197 7.16265C11.0742 6.617 10.2375 6.3742 9.37395 6.4078Z"></path>
                              <path fill="#333" fill-rule="evenodd" d="M14.4678 13.692C15.4238 12.5604 16 11.0974 16 9.5C16 5.91015 13.0898 3 9.5 3C5.91015 3 3 5.91015 3 9.5C3 13.0898 5.91015 16 9.5 16C11.0974 16 12.5604 15.4238 13.692 14.4678L13.5 15.5721L17.2568 19.3289L19.3289 17.2568L15.5721 13.5L14.4678 13.692ZM9.5 14.5C12.2614 14.5 14.5 12.2614 14.5 9.5C14.5 6.73858 12.2614 4.5 9.5 4.5C6.73858 4.5 4.5 6.73858 4.5 9.5C4.5 12.2614 6.73858 14.5 9.5 14.5Z" clip-rule="evenodd"></path>
                              <path fill="#333" d="M17.9639 20.0361L20.0361 17.9639L20.7139 18.6418C21.0954 19.0233 21.0954 19.6418 20.7139 20.0233L20.0233 20.7139C19.6418 21.0954 19.0233 21.0954 18.6418 20.7139L17.9639 20.0361Z"></path>
                            </svg>
                        </div>
                    </button>
                {/if}
            </div>
        {/each}
    </div>

    {#if product_context.footer_message}
        {product_context.footer_message}
    {/if}
</div>

<style>
   .details-button {
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

    .grid-header {
        font-size: 1.2rem;
        font-weight: normal;
        margin-bottom: 1rem;
    }

    .product-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }

    .grid-item {
        position: relative;
        display: flex;
        flex-direction: column;
        text-align: left;
        border: 1px solid #ddd;
    }

    .grid-item-footer {
       margin-top: auto;
    }

    .grid-item-image {
        width: 100%;
        height: 200px;
        object-fit: cover;
        margin: 0rem 0 0.5rem 1rem;
        border-radius: 8px 8px 0 0; /* Optional: Rounded corners for the top of the image */
        margin: 0; /* Remove any margin */
    }

    .grid-item-name {
        font-size: 1rem;
        align-self: left;
        font-weight: bold;
        margin: 0.5rem 0 0.5rem 1rem;
        overflow: hidden;
        text-overflow: ellipsis;
        min-height: 2.4em; /* Ensures space for 2 lines of text */
        line-height: 1.2em; /* Adjust line height to match the text spacing */
    }

    .grid-item-price {
        font-size: 0.85rem;
        align-self: left;
        font-weight: lighter;
        margin: 0.5rem 0 0.5rem 1rem;
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

    .grid-item-description {
        font-size: 0.9rem;
        align-self: left;
        color: #555;
        margin: 0.5rem 0 0.5rem 1rem;
        display: -webkit-box;
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
        min-height: 2.4em; /* Ensures space for 2 lines of text */
        line-height: 1.2em; /* Adjust line height to match the text spacing */
    }

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

  .carousel-container {
      position: relative;
      padding: 1rem;
      border-radius: 8px;
      max-width: 90%;
      max-height: 90%;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      align-items: center;
  }

  .carousel-image {
      max-width: 100%;
      max-height: 80vh;
      margin-bottom: 1rem;
  }

  .close-button {
      position:absolute;
      display: flex;
      cursor: pointer;
      top: 0;
      right: 0;
  }
</style>