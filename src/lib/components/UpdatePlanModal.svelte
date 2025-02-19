<script lang="ts">
  import { onMount } from 'svelte';

  export let showUpdatePlanModal: boolean;
  export let userId: string; // Принимаем userId как пропс

  // Флаг загрузки Robokassa
  let isRobokassaLoaded = false;

  // Функция загрузки Robokassa
  async function loadRobokassaScript(): Promise<void> {
    if (isRobokassaLoaded) return;
    
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://auth.robokassa.ru/Merchant/bundle/robokassa_iframe.js';
      script.onload = () => {
        isRobokassaLoaded = true;
        resolve();
      };
      script.onerror = () => reject(new Error('Не удалось загрузить Robokassa'));
      document.head.appendChild(script);
    });
  }

  // Функция вычисления контрольной суммы (SHA-256)
  async function calculateSignatureValue(merchantLogin: string, outSum: string, password1: string, invId: string = ''): Promise<string> {
    const baseString = invId ? `${merchantLogin}:${outSum}:${invId}:${password1}` : `${merchantLogin}:${outSum}::${password1}`;
    
    const encoder = new TextEncoder();
    const data = encoder.encode(baseString);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);

    // Преобразуем результат в 16-ричную строку
    return Array.from(new Uint8Array(hashBuffer))
      .map(byte => byte.toString(16).padStart(2, '0'))
      .join('');
  }

  // Функция для открытия Robokassa
  async function openRobokassaIframe(): Promise<void> {
    try {
      await loadRobokassaScript();

      if (!window.Robokassa) {
        console.error('Ошибка: Robokassa не загружена.');
        return;
      }

      // Данные платежа
      const merchantLogin = 'aidachat';
      const outSum = '11';
      const password1 = 'YgUKSjuCRDqO01x90IX2'; // Замените на ваш Пароль#1
      const invId = ''; // Может быть пустым

      // Рассчитываем SignatureValue (SHA-256)
      const signatureValue = await calculateSignatureValue(merchantLogin, outSum, password1, invId);

      // Вызываем платежный iframe
      window.Robokassa.Render({
        MerchantLogin: merchantLogin,
        OutSum: outSum,
        InvId: invId,
        Description: 'Оплата заказа в Тестовом магазине ROBOKASSA',
        Culture: 'ru',
        Encoding: 'utf-8',
        IsTest: 1, // Убрать, если реальный платеж
        Shp: { userId }, // Передаем userId в параметры
        Settings: JSON.stringify({ PaymentMethods: ['BankCard', 'SBP'], Mode: 'modal' }),
        SignatureValue: signatureValue,
      });
    } catch (error) {
      console.error('Ошибка при загрузке Robokassa:', error);
    }
  }

  // Загружаем Robokassa при монтировании, если модальное окно открыто
  onMount(loadRobokassaScript);
</script>

{#if showUpdatePlanModal}
  <div class="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
    <div class="bg-white dark:bg-gray-850 p-6 rounded-xl shadow-xl w-96">
      <h2 class="text-xl mb-4">Обновить план</h2>
      <p>User ID: {userId}</p>
      <p>Здесь будет контент для обновления плана...</p>

      <!-- Кнопка для запуска Robokassa -->
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
