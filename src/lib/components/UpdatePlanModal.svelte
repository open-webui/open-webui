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
  async function generatePaymentLink(price: string): Promise<string> {
    // Параметры для подписи
    const merchantLogin = 'aidachat';
    const outSum = price; // Сумма оплаты
    const invId = ''; // Номер заказа (может быть пустым)
    const description = encodeURIComponent('Оплата заказа в Тестовом магазине ROBOKASSA'); // Кодируем описание
    const isTest = '1'; // Тестовый режим
    const shpUserId = `Shp_userId=${userId}`; // Передаём user id в Shp

    // Пароль#1 (замените на ваш)
    // const password1 = 'r8xoXYKrTcsoT11Xq02N';
    const password1 = process.env.ROBOKASSA_PASSWORD;
    console.log("PASS", password1)
    // Строка для подписи
    const signatureString = `${merchantLogin}:${outSum}:${invId}:${password1}:${shpUserId}`;

    // Рассчитываем подпись (SHA-256)
    const signatureValue = await calculateSHA256(signatureString);

    // Формируем ссылку для оплаты
    const paymentLink = `https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin=${merchantLogin}&OutSum=${outSum}&InvoiceID=${invId}&Description=${description}&IsTest=${isTest}&${shpUserId}&SignatureValue=${signatureValue}`;

    return paymentLink;
  }

  // Функция для открытия нового окна с оплатой
  async function openPaymentWindow(price: string) {
    try {
      const paymentLink = await generatePaymentLink(price);
      // Открываем новое окно с платежной страницей
      window.open(paymentLink, '_blank', 'width=600,height=800');
    } catch (error) {
      console.error('Ошибка при генерации ссылки на оплату:', error);
      alert('Не удалось сформировать платёжную ссылку. Пожалуйста, попробуйте позже.');
    }
  }
</script>

<style>
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
  }

  .card button:hover {
    background: #2563eb;
  }

  /* Адаптивность */
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

<div class="cards-container">
  <!-- Карточка 1 -->
  <div class="card">
    <h3>Базовый план</h3>
    <p>Идеально для начинающих. Включает основные функции.</p>
    <div class="price">$10</div>
    <button on:click={() => openPaymentWindow('10')}>Оплатить</button>
  </div>

  <!-- Карточка 2 -->
  <div class="card">
    <h3>Стандартный план</h3>
    <p>Для активных пользователей. Расширенные возможности.</p>
    <div class="price">$25</div>
    <button on:click={() => openPaymentWindow('25')}>Оплатить</button>
  </div>

  <!-- Карточка 3 -->
  <div class="card">
    <h3>Премиум план</h3>
    <p>Для профессионалов. Все функции и приоритетная поддержка.</p>
    <div class="price">$50</div>
    <button on:click={() => openPaymentWindow('50')}>Оплатить</button>
  </div>
</div>
