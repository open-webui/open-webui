<script lang="ts">
  export let showUpdatePlanModal: boolean;
  export let userId: string;

  // Функция для запроса подписи с бэкенда
  async function fetchSignature(price: string): Promise<string> {
    try {
      const response = await fetch("/api/v1/payment/generate-signature", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          price: price,
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
  async function generatePaymentLink(price: string): Promise<string> {
    const merchantLogin = "aidachat";
    const outSum = price; // Сумма оплаты
    const invId = ""; // Номер заказа (может быть пустым)
    const description = encodeURIComponent("Оплата заказа в Тестовом магазине ROBOKASSA");
    const isTest = "1"; // Тестовый режим
    const shpUserId = `Shp_userId=${userId}`; // Передаём user id в Shp

    // Получаем подпись с бэкенда
    const signatureValue = await fetchSignature(price);

    // Формируем ссылку для оплаты
    const paymentLink = `https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin=${merchantLogin}&OutSum=${outSum}&InvoiceID=${invId}&Description=${description}&IsTest=${isTest}&${shpUserId}&SignatureValue=${signatureValue}`;

    return paymentLink;
  }

  // Функция для открытия нового окна с оплатой
  async function openPaymentWindow(price: string) {
    try {
      const paymentLink = await generatePaymentLink(price);
      // Открываем новое окно с платежной страницей
      window.open(paymentLink, "_blank", "width=600,height=800");
    } catch (error) {
      console.error("Ошибка при генерации ссылки на оплату:", error);
      alert("Не удалось сформировать платёжную ссылку. Пожалуйста, попробуйте позже.");
    }
  }
</script>
