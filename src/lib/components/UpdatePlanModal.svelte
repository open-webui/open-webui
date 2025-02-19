<script lang="ts">
  export let showUpdatePlanModal: boolean;
  export let userId: string; // Принимаем user id как пропс

import md5 from 'crypto-js/md5';

function calculateSignatureValue(merchantLogin: string, outSum: string, password1: string, invId: string = ''): string {
  // Формируем строку для расчета
  const baseString = invId
    ? `${merchantLogin}:${outSum}:${invId}:${password1}`
    : `${merchantLogin}:${outSum}::${password1}`;

  // Вычисляем MD5 хэш
  return md5(baseString).toString();
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

async function openRobokassaIframe() {
  try {
    // Загружаем скрипт Robokassa, если он ещё не загружен
    if (!window.Robokassa) {
      await loadRobokassaScript();
    }

    // Параметры для расчета SignatureValue
    const merchantLogin = 'aidachat';
    const outSum = '11';
    const password1 = 'YgUKSjuCRDqO01x90IX2'; // Замените на ваш Пароль#1
    const invId = ''; // Номер заказа (может быть пустым)

    // Рассчитываем SignatureValue
    const signatureValue = calculateSignatureValue(merchantLogin, outSum, password1, invId);

    // Вызываем Robokassa.Render
    Robokassa.Render({
      MerchantLogin: merchantLogin,
      OutSum: outSum,
      InvId: invId,
      Description: 'Оплата заказа в Тестовом магазине ROBOKASSA',
      Culture: 'ru',
      Encoding: 'utf-8',
      IsTest: 1,
      Shp: { userId },
      Settings: JSON.stringify({ PaymentMethods: ['BankCard', 'SBP'], Mode: 'modal' }),
      SignatureValue: signatureValue // Используем рассчитанное значение
    });
  } catch (error) {
    console.error('Ошибка при загрузке Robokassa:', error);
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
