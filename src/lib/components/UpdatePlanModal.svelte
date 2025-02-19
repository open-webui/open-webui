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

  // Функция для загрузки скрипта Robokassa
  function loadRobokassaScript() {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://auth.robokassa.ru/Merchant/bundle/robokassa_iframe.js';
      script.onload = () => resolve(true);
      script.onerror = () => reject(new Error('Не удалось загрузить скрипт Robokassa'));
      document.head.appendChild(script);
    });
  }

  // Функция для запуска Robokassa iframe
  async function openRobokassaIframe() {
    try {
      // Загружаем скрипт Robokassa, если он ещё не загружен
      if (!window.Robokassa) {
        await loadRobokassaScript();
      }

      // Параметры для подписи
      const merchantLogin = 'aidachat';
      const outSum = '11'; // Сумма оплаты
      const invId = ''; // Номер заказа (может быть пустым)
      const description = 'Оплата заказа в Тестовом магазине ROBOKASSA';
      const culture = 'ru';
      const encoding = 'utf-8';
      const isTest = 1;
      const shpUserId = userId; // Передаём user id в Shp
      const paymentMethods = JSON.stringify({ PaymentMethods: ['BankCard', 'SBP'], Mode: 'modal' });

      // Секретный ключ (замените на ваш)
      const secretKey = 'YgUKSjuCRDqO01x90IX2';

      // Строка для подписи
      const signatureString = `${merchantLogin}:${outSum}:${invId}:${secretKey}:Shp_login=${shpUserId}`;
       console.log("Sig1", signatureString)
      // Рассчитываем подпись (SHA-256)
      const signatureValue = await calculateSHA256(signatureString);
      console.log("Sig2", signatureValue)
      // Вызываем Robokassa.Render
      Robokassa.Render({
        MerchantLogin: merchantLogin,
        OutSum: outSum,
        InvId: invId,
        Description: description,
        Culture: culture,
        Encoding: encoding,
        IsTest: isTest,
        Shp: { userId: shpUserId },
        Settings: paymentMethods,
        SignatureValue: signatureValue
      });
    } catch (error) {
      console.error('Ошибка при загрузке Robokassa:', error);
      alert('Не удалось загрузить платёжную систему. Пожалуйста, попробуйте позже.');
    }
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
