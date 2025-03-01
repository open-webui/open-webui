<script lang="ts">
  export let showUpdatePlanModal: boolean;
  export let userId: string; // Принимаем user id как пропс
  export let email: string; // Принимаем email как пропс

  // Функция для запроса подписи с бэкенда
  async function fetchSignature(price: string, id: string): Promise<string> {
    try {
      const response = await fetch("/api/v1/payment/generate-signature", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          price: price,
          email: email,
          cardId: id
        }),
      });

      if (!response.ok) {
        throw new Error("Ошибка при генерации подписи");
      }

      const data = await response.json();
      return data.signature;
    } catch (error) {
      console.error("Ошибка:", error);
      throw error;
    }
  }

  // Функция для генерации ссылки на оплату
  async function generatePaymentLink(price: string, id: string): Promise<string> {
    const merchantLogin = "aidachat";
    const outSum = price; // Сумма оплаты
    const invId = ""; // Номер заказа (может быть пустым)
    const description = encodeURIComponent("Оплата заказа в Тестовом магазине ROBOKASSA");
    const isTest = "1"; // Тестовый режим
    const shpUserId = `Shp_userId=${userId}`; // Передаём user id в Shp
    const shpId = `Shp_id=${id}`; // Передаём id карточки в Shp
    const userEmail= email; // Передаём email 

    // Получаем подпись с бэкенда
    const signatureValue = await fetchSignature(price, id);

    // Формируем ссылку для оплаты
    const paymentLink = `https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin=${merchantLogin}&OutSum=${outSum}&InvoiceID=${invId}&Email=${userEmail}&Description=${description}&IsTest=${isTest}&${shpId}&${shpUserId}&SignatureValue=${signatureValue}`;

    return paymentLink;
  }

  // Функция для открытия нового окна с оплатой
  async function openPaymentWindow(price: string, id: string) {
    try {
      const paymentLink = await generatePaymentLink(price, id);
      // Открываем новое окно с платежной страницей
      window.location.href = paymentLink; // Переход на страницу оплаты

    } catch (error) {
      console.error("Ошибка при генерации ссылки на оплату:", error);
      alert("Не удалось сформировать платёжную ссылку. Пожалуйста, попробуйте позже.");
    }
  }
</script>

<style>
  /* Метатег для корректного отображения на мобильных устройствах */
  /* Добавьте это в <head> вашего HTML-документа */
  /* <meta name="viewport" content="width=device-width, initial-scale=1.0"> */

  /* Стили для модального окна */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5); /* Полупрозрачный чёрный фон */
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000; /* Убедитесь, что модальное окно поверх других элементов */
    overflow: auto; /* Добавляем прокрутку, если содержимое не помещается */
    padding: 20px; /* Отступы для мобильных устройств */
  }

  .modal-content {
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    padding: 20px;
    width: 90%; /* Ширина модального окна */
    max-width: 1200px; /* Максимальная ширина */
    max-height: 90vh; /* Максимальная высота (90% высоты экрана) */
    overflow-y: auto; /* Прокрутка, если содержимое не помещается */
    z-index: 1001; /* Контент модального окна поверх оверлея */
  }

  /* Адаптивность для мобильных устройств */
  @media (max-width: 410px) {
    .modal-content {
      width: 100%; /* На мобильных устройствах занимает всю ширину */
      max-width: 98%;
      max-height: 90vh; /* Ограничиваем высоту */
      border-radius: 0; /* Убираем скругление углов */
      padding: 10px; /* Уменьшаем отступы для мобильных устройств */
    }
  }

  /* Остальные стили (карточки, кнопки и т.д.) */
  .cards-container {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    justify-content: center;
    padding: 20px;
  }

  .card {
    background: white;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    padding: 20px;
    width: 100%;
    max-width: 300px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .card:hover {
    transform: translateY(-5px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
  }

  .card h3 {
    font-size: 1.5rem;
    margin-bottom: 10px;
    color: #333;
  }

  .card p {
    font-size: 1rem;
    color: #666;
    margin-bottom: 20px;
  }

  .card .price {
    font-size: 1.75rem;
    font-weight: bold;
    color: #000;
    margin-bottom: 20px;
  }

  .card button {
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 10px 20px;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.3s;
    pointer-events: auto; /* Разрешить события указателя */
    z-index: 1002; /* Убедитесь, что кнопки поверх модального окна */
  }

  .card button:hover {
    background: #2563eb;
  }

  /* Адаптивность для карточек */
  @media (max-width: 768px) {
    .cards-container {
      flex-direction: column;
      align-items: center;
    }

    .card {
      max-width: 100%;
    }
  }
</style>


{#if showUpdatePlanModal}
  <!-- Модальное окно -->
  <div class="modal-overlay">
    <div class="modal-content">
      <h2 class="text-xl mb-4">Обновить план</h2>

      <!-- Контейнер с карточками -->
      <div class="cards-container">
        <!-- Карточка 1 -->
        <div class="card">
          <h3>Базовый план</h3>
          <p>Идеально для начинающих</p>
          <p>1 000 000 токенов</p>
          <div class="price">₽550</div>
          <button
              on:click={() => openPaymentWindow('550', '1')}
              on:touchstart|preventDefault={() => openPaymentWindow('550', '1')}
          >
              Оплатить
          </button>
        </div>

        <!-- Карточка 2 -->
        <div class="card">
          <h3>Стандартный план</h3>
          <p>Для активных пользователей</p>
          <p>2 000 000 токенов</p>
          <div class="price">₽1000</div>
          <button
              on:click={() => openPaymentWindow('1000', '2')}
              on:touchstart={() => openPaymentWindow('1000', '2')}
          >
              Оплатить
          </button>
        </div>

        <!-- Карточка 3 -->
        <div class="card">
          <h3>Премиум план</h3>
          <p>Для профессионалов</p>
          <p>5 000 000 токенов</p>
          <div class="price">₽2000</div>
          <button
              on:click={() => openPaymentWindow('2000', '3')}
              on:touchstart={() => openPaymentWindow('2000', '3')}
          >
              Оплатить
          </button>
        </div>
      </div>

      <!-- Кнопка закрытия модального окна -->
      <div class="mt-4 flex justify-end">
        <button
          class="bg-gray-500 text-white py-2 px-4 rounded-md hover:bg-gray-600 transition"
          on:click={() => showUpdatePlanModal = false}
        >
          Закрыть
        </button>
      </div>
    </div>
  </div>
{/if}
