<script lang="ts">
  export let showUpdatePlanModal: boolean;
  export let userId: string; // Принимаем user id как пропс

  // Функция для запуска Robokassa iframe
  function openRobokassaIframe() {
    Robokassa.Render({
      MerchantLogin: 'robo-demo',
      OutSum: '11', // Сумма оплаты
      InvId: '', // Номер заказа (может быть пустым)
      Description: 'Оплата заказа в Тестовом магазине ROBOKASSA',
      Culture: 'ru',
      Encoding: 'utf-8',
      Settings: JSON.stringify({ PaymentMethods: ['BankCard', 'SBP'], Mode: 'modal' }),
      SignatureValue: '00c6675e103f387ae5a3c0ba80695b98' // Подпись (замените на вашу)
    });
  }
</script>

{#if showUpdatePlanModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
    <div class="bg-white dark:bg-gray-850 p-6 rounded-xl shadow-xl w-96">
      <h2 class="text-xl mb-4">Обновить план</h2>
      <p>User ID: {userId}</p> <!-- Отображаем user id -->
      <p>Здесь будет контент для обновления плана...</p>

      <!-- Кнопка для запуска Robokassa iframe -->
      <div class="mt-4 flex justify-end">
        <button
          class="bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 transition"
          on:click={openRobokassaIframe}
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

<!-- Подключение скрипта Robokassa -->
<script type="text/javascript" src="https://auth.robokassa.ru/Merchant/bundle/robokassa_iframe.js"></script>
