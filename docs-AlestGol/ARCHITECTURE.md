# 🏗️ Arquitetura Técnica - Alest × GOL Platform

## 📋 Visão Geral da Arquitetura

A plataforma Alest+GOL é construída sobre uma arquitetura moderna, escalável e segura, baseada em microsserviços e tecnologias de ponta para oferecer uma experiência de IA conversacional robusta para o setor de aviação.

---

## 🎨 Arquitetura Frontend

### **SvelteKit + TypeScript**
```
src/
├── lib/
│   ├── components/          # Componentes modulares
│   │   ├── chat/           # Interface de chat
│   │   ├── layout/         # Layout e navegação
│   │   ├── admin/          # Painel administrativo
│   │   └── common/         # Componentes reutilizáveis
│   ├── stores/             # Estado global (Svelte stores)
│   ├── apis/               # Cliente HTTP para backend
│   └── utils/              # Utilitários e helpers
├── routes/                 # Roteamento SvelteKit
└── static/                 # Assets estáticos
    ├── themes/
    │   └── alest-gol.css   # Tema personalizado
    ├── Logo-Alest-Branco-240x104-1-1.png
    └── logo-gol.svg
```

### **Características Técnicas**
- **Framework**: SvelteKit 2.0+ com TypeScript
- **Styling**: TailwindCSS + CSS customizado
- **Estado**: Svelte Stores para gerenciamento reativo
- **Build**: Vite com otimizações de produção
- **PWA**: Service Worker e manifest configurados
- **Responsivo**: Mobile-first design

### **Tema Alest+GOL**
```css
/* Cores principais */
:root {
  --alest-primary: #ff6b35;    /* Laranja Alest */
  --gol-primary: #ff6b35;      /* Laranja GOL */
  --background: #0f0f0f;       /* Fundo escuro */
  --text-primary: #ffffff;     /* Texto branco */
  --text-secondary: #a1a1aa;   /* Texto cinza */
}
```

---

## ⚙️ Arquitetura Backend

### **FastAPI + Python**
```
backend/open_webui/
├── main.py                 # Aplicação principal
├── config.py               # Configurações globais
├── routers/                # 25+ routers modulares
│   ├── auths.py           # Autenticação
│   ├── chats.py           # Gerenciamento de chats
│   ├── users.py           # Gestão de usuários
│   ├── models.py          # Modelos de IA
│   ├── ollama.py          # Proxy Ollama
│   ├── openai.py          # Proxy OpenAI/Gemini
│   └── admin.py           # Endpoints administrativos
├── models/                 # Modelos SQLAlchemy
├── utils/                  # Utilitários backend
└── static/                 # Assets servidos
```

### **Características Técnicas**
- **Framework**: FastAPI 0.104+ com Python 3.11+
- **ASGI**: Uvicorn para alta performance
- **ORM**: SQLAlchemy 2.0 com Alembic migrations
- **Validação**: Pydantic models
- **Documentação**: OpenAPI/Swagger automática
- **WebSocket**: Suporte para real-time

### **Configuração de Produção**
```python
# Configurações específicas Alest+GOL
GEMINI_API_KEY = "AIzaSyDrqEFhXHRauPLVk4qUpvS0VSQSHh4LKKI"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

# Prompts personalizados GOL
default_prompt_suggestions = [
    {
        "title": "Planejar minha viagem",
        "content": "com a GOL Linhas Aéreas"
    },
    {
        "title": "Procedimentos de segurança", 
        "content": "em voos comerciais"
    },
    {
        "title": "Destinos GOL",
        "content": "mais procurados e rotas"
    },
    {
        "title": "Curiosidades sobre aviação",
        "content": "e a história da GOL"
    }
]
```

---

## 💾 Arquitetura de Dados

### **Banco de Dados Principal**
```sql
-- Principais tabelas
users                    # Usuários do sistema
chats                    # Conversas
messages                 # Mensagens individuais
models                   # Configurações de modelos IA
prompts                  # Templates de prompts
functions                # Funções customizadas
files                    # Arquivos uploadados
tags                     # Sistema de tags
groups                   # Grupos de usuários
```

### **Suporte Multi-Database**
- **Desenvolvimento**: SQLite (padrão)
- **Produção**: PostgreSQL recomendado
- **Alternativas**: MySQL, MariaDB
- **Migrations**: Alembic para versionamento

### **Vector Databases (RAG)**
```yaml
Suportados:
  - ChromaDB: Padrão, local
  - Qdrant: Cloud/self-hosted
  - Pinecone: Cloud comercial
  - Weaviate: Open source
  - Milvus: Escalável
  - PGVector: PostgreSQL extension
  - OpenSearch: Elasticsearch-based
  - Chroma: Local development
```

---

## 🤖 Arquitetura de IA

### **Modelos Suportados**

#### **1. Ollama (Local)**
```yaml
Instalado:
  - gemma2:2b: Modelo compacto (1.6GB)
  - Configuração: localhost:11434
  - Performance: CPU/GPU otimizado
  - Privacy: Dados não saem do servidor
```

#### **2. Gemini 1.5 Flash (Cloud)**
```yaml
Configuração:
  - API Key: Pré-configurada
  - Base URL: generativelanguage.googleapis.com
  - Modelo: gemini-1.5-flash
  - Rate Limit: Configurável
  - Context: 1M tokens
```

#### **3. OpenAI Compatible**
```yaml
Suporte:
  - GPT-3.5/4: Via OpenAI API
  - Claude: Via proxy
  - Mistral: Via API
  - Anthropic: Compatível
```

### **RAG (Retrieval Augmented Generation)**
```python
# Pipeline RAG
Document Upload → 
Text Extraction → 
Chunking → 
Embedding Generation → 
Vector Storage → 
Semantic Search → 
Context Injection → 
LLM Response
```

---

## 🌐 Arquitetura de Rede

### **Fluxo de Requisições**
```mermaid
graph LR
    Client[Cliente] --> Nginx[Nginx/Traefik]
    Nginx --> Frontend[Frontend:3000]
    Nginx --> Backend[Backend:8080]
    Backend --> Ollama[Ollama:11434]
    Backend --> External[APIs Externas]
    Backend --> DB[(Database)]
    Backend --> Vector[(Vector DB)]
```

### **Endpoints Principais**
```yaml
Frontend:
  - /: Interface principal
  - /admin: Painel administrativo
  - /api/v1/*: Proxy para backend

Backend:
  - /api/v1/chats: Gerenciamento de chats
  - /api/v1/users: Gestão de usuários
  - /api/v1/models: Configuração de modelos
  - /ollama/*: Proxy para Ollama
  - /openai/*: Proxy para OpenAI/Gemini
  - /static/*: Assets estáticos
```

---

## 🔄 Arquitetura de Deploy

### **Docker Multi-Stage**
```dockerfile
# Estágio 1: Build Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Estágio 2: Build Backend
FROM python:3.11-slim AS backend-builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Estágio 3: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=frontend-builder /app/build ./static
COPY backend/ .
EXPOSE 8080
CMD ["uvicorn", "open_webui.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### **Kubernetes Ready**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alest-gol-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: alest-gol
  template:
    spec:
      containers:
      - name: alest-gol
        image: alest-gol:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

---

## 📊 Arquitetura de Monitoramento

### **Observabilidade**
```yaml
Logs:
  - Formato: JSON estruturado
  - Níveis: DEBUG, INFO, WARN, ERROR
  - Correlação: Request IDs
  - Destino: stdout/files/ELK

Métricas:
  - Prometheus: Coleta
  - Grafana: Visualização
  - AlertManager: Alertas
  - Custom: Métricas de negócio

Traces:
  - OpenTelemetry: Padrão
  - Jaeger: Distributed tracing
  - Performance: Request tracking
```

### **Health Checks**
```python
# Endpoints de saúde
GET /health          # Status geral
GET /health/db       # Status database
GET /health/ollama   # Status Ollama
GET /health/external # Status APIs externas
```

---

## 🔧 Arquitetura de Configuração

### **Variáveis de Ambiente**
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379

# IA Services
OLLAMA_BASE_URL=http://localhost:11434
GEMINI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-...

# Security
JWT_SECRET=your-secret-key
CORS_ALLOW_ORIGIN=https://yourdomain.com

# Features
ENABLE_SIGNUP=true
ENABLE_ADMIN=true
ENABLE_RAG=true
```

### **Configuração Dinâmica**
```python
# Configurações persistentes no banco
class PersistentConfig:
    WEBUI_NAME = "Alest × GOL - AI Assistant"
    DEFAULT_THEME = "alest-gol"
    ENABLE_COMMUNITY_SHARING = False
    ENABLE_MESSAGE_RATING = True
```

---

## 📈 Arquitetura de Escalabilidade

### **Horizontal Scaling**
- **Load Balancer**: Nginx/HAProxy
- **Multiple Instances**: Stateless design
- **Database**: Connection pooling
- **Cache**: Redis para sessões
- **CDN**: Assets estáticos

### **Performance Otimizations**
- **Frontend**: Code splitting, lazy loading
- **Backend**: Async/await, connection pooling
- **Database**: Índices otimizados, queries eficientes
- **Cache**: Redis, in-memory caching
- **Compression**: Gzip, Brotli

### **Resource Management**
```yaml
Limites Recomendados:
  CPU: 2-4 cores por instância
  Memory: 4-8GB por instância
  Storage: 100GB+ para dados
  Network: 1Gbps mínimo
```

---

## 🎯 Arquitetura Específica GOL

### **Customizações**
- **Branding**: Logos e cores integradas
- **Prompts**: Conteúdo específico de aviação
- **Knowledge Base**: Dados GOL integrados
- **Workflows**: Processos específicos

### **Integrações Futuras**
- **GOL APIs**: Reservas, voos, status
- **CRM Integration**: Dados de clientes
- **Analytics**: Métricas específicas
- **Mobile App**: Aplicativo nativo

---

**🏗️ Arquitetura projetada para alta disponibilidade, escalabilidade e performance**

*Desenvolvida especificamente para as necessidades da parceria Alest × GOL* ✈️