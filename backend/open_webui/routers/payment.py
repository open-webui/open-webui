# backend/open_webui/routers/payment.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import hashlib
import os

router = APIRouter()

# Модель для запроса
class SignatureRequest(BaseModel):
    user_id: str
    price: str

# Пароль#1 (замените на ваш реальный пароль)
ROBOKASSA_PASSWORD = os.getenv("ROBOKASSA_PASSWORD", "r8xoXYKrTcsoT11Xq02N")

@router.post("/generate-signature")
async def generate_signature(request: SignatureRequest):
    merchant_login = "aidachat"
    out_sum = request.price  # Сумма оплаты
    inv_id = ""  # Номер заказа (может быть пустым)
    shp_user_id = f"Shp_userId={request.user_id}"  # Передаём user id в Shp
    shp_email = f"Shp_email={request.email}"  # Передаём user id в Shp

    # Строка для подписи
    signature_string = f"{merchant_login}:{out_sum}:{inv_id}:{ROBOKASSA_PASSWORD}:{shp_email}:{shp_user_id}"

    # Рассчитываем SHA-256 хэш
    signature_value = hashlib.sha256(signature_string.encode()).hexdigest()

    return {"signature": signature_value}
