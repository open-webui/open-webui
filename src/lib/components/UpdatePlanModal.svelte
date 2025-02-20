<script lang="ts">
  export let showUpdatePlanModal: boolean;
  export let userId: string; // Принимаем user id как пропс

  // Функция для расчёта SHA-256 хэша
  async function calculateSHA256(message: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  // Функция для генерации ссылки на оплату
  async function generatePaymentLink(): Promise<string> {
    // Параметры для подписи
    const merchantLogin = 'aidachat';
    const outSum = '11'; // Сумма оплаты
    const invId = ''; // Номер заказа (может быть пустым)
    const description = encodeURIComponent('Оплата заказа в Тестовом магазине ROBOKASSA'); // Кодируем описание
    const isTest = '1'; // Тестовый режим
    const shpUserId = `Shp_userId=${userId}`; // Передаём user id в Shp

    // Пароль#1 (замените на ваш)
    const password1 = 'r8xoXYKrTcsoT11Xq02N';

    // Строка для подписи
    const signatureString = `${merchantLogin}:${outSum}:${invId}:${password1}:${shpUserId}`;

    // Рассчитываем подпись (SHA-256)
    const signatureValue = await calculateSHA256(signatureString);

    // Формируем ссылку для оплаты
    const paymentLink = `https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin=${merchantLogin}&OutSum=${outSum}&InvoiceID=${invId}&Description=${description}&IsTest=${isTest}&${shpUserId}&SignatureValue=${signatureValue}`;

    return paymentLink;
  }

  // Функция для перенаправления на страницу оплаты
  async function redirectToPayment() {
    try {
      const paymentLink = await generatePaymentLink();
      window.location.href = paymentLink; // Перенаправляем пользователя
    } catch (error) {
      console.error('Ошибка при генерации ссылки на оплату:', error);
      alert('Не удалось сформировать платёжную ссылку. Пожалуйста, попробуйте позже.');
    }
  }
</script>

{#if showUpdatePlanModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
    <div class="bg-white dark:bg-gray-850 p-6 rounded-xl shadow-xl w-96">
      <h2 class="text-xl mb-4">Обновить план</h2>
      <p>User ID: {userId}</p> <!-- Отображаем user id -->
      <p>Здесь будет контент для обновления плана...</p>

      <!-- Кнопка для перехода на страницу оплаты -->
      <div class="mt-4 flex justify-end">
        <button
          class="bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 transition"
          on:click={redirectToPayment}
        >
          Оплатить
        </button>
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
