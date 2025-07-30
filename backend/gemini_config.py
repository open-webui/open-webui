#!/usr/bin/env python3
"""
Configuração do Gemini 1.5 Flash para Alest+GOL Partnership
"""

import os

# Configuração da API do Gemini
GEMINI_API_KEY = "AIzaSyDrqEFhXHRauPLVk4qUpvS0VSQSHh4LKKI"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Modelo específico
GEMINI_MODEL = "gemini-1.5-flash"

# Definir variáveis de ambiente
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
os.environ["GEMINI_API_BASE_URL"] = GEMINI_API_BASE_URL

print(f"✅ Gemini API configurado:")
print(f"   - Modelo: {GEMINI_MODEL}")
print(f"   - Base URL: {GEMINI_API_BASE_URL}")
print(f"   - API Key: {GEMINI_API_KEY[:10]}...") 