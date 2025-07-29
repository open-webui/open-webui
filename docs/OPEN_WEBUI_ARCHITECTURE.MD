# 🏗️ **OPEN WEBUI - ARQUITETURA TÉCNICA**
## **DOCUMENTAÇÃO COMPLETA PARA DESENVOLVIMENTO**

---

## 📊 **VISÃO GERAL DA ARQUITETURA**

### **🎯 STACK TECNOLÓGICO ATUAL**
- **Frontend**: SvelteKit + TypeScript + TailwindCSS
- **Backend**: FastAPI + Python + SQLAlchemy
- **Database**: SQLite (default) / PostgreSQL / MySQL
- **AI Engine**: Ollama + Multi-provider support
- **Containerização**: Docker + Compose
- **Build**: Vite + SvelteKit Adapter

---

## 📁 **ESTRUTURA DE DIRETÓRIOS**

```
open-webui/
├── 📁 src/                          # 🎯 FRONTEND (FOCO MODIFICAÇÃO)
│   ├── 📁 lib/
│   │   ├── 📁 apis/                 # Clientes API
│   │   ├── 📁 components/           # Componentes Svelte
│   │   │   ├── 📁 admin/           # Admin components
│   │   │   ├── 📁 chat/            # Chat interface
│   │   │   ├── 📁 common/          # Componentes reutilizáveis
│   │   │   ├── 📁 icons/           # Ícones SVG
│   │   │   ├── 📁 layout/          # Layout components
│   │   │   └── 📁 workspace/       # Workspace components
│   │   ├── 📁 stores/              # Estado global Svelte
│   │   ├── 📁 utils/               # Utilitários frontend
│   │   └── 📁 constants/           # Constantes
│   ├── 📁 routes/                  # Páginas SvelteKit
│   ├── 📁 styles/                  # CSS global
│   ├── app.html                    # Template HTML base
│   └── app.d.ts                    # Tipos TypeScript
├── 📁 backend/                      # API FastAPI
│   ├── 📁 open_webui/
│   │   ├── 📁 routers/             # Endpoints API
│   │   ├── 📁 models/              # Models SQLAlchemy
│   │   ├── 📁 utils/               # Utilitários backend
│   │   └── main.py                 # Entrada principal
│   └── requirements.txt            # Dependências Python
├── 📁 static/                      # Assets estáticos
├── 📁 kubernetes/                  # Manifests K8s
├── 📁 docker/                      # Configurações Docker
├── package.json                    # Dependências Node.js
├── vite.config.ts                  # Configuração Vite
├── svelte.config.js                # Configuração Svelte
├── tailwind.config.js              # Configuração Tailwind
└── tsconfig.json                   # Configuração TypeScript
```

---

## 🎨 **FRONTEND - COMPONENTES PRINCIPAIS**

### **📱 LAYOUT HIERARCHY**
```
App
├── Header/Navbar                   # 🎯 ALVO: Branding Alest+GOL
├── Sidebar                         # 🎯 ALVO: Navegação personalizada
├── Main Content
│   ├── Chat Interface              # 🎯 ALVO: UI conversacional
│   ├── Settings Panel             # 🎯 ALVO: Configurações
│   ├── Model Selector              # 🎯 ALVO: Seleção de modelos
│   └── Workspace                   # 🎯 ALVO: Área de trabalho
└── Footer                          # 🎯 ALVO: Rodapé branded
```

### **🎨 COMPONENTES DE UI CRÍTICOS**

#### **📍 src/lib/components/layout/**
```
layout/
├── Navbar.svelte                   # ⭐ PRIORIDADE 1: Header principal
├── Sidebar.svelte                  # ⭐ PRIORIDADE 1: Menu lateral
├── Footer.svelte                   # ⭐ PRIORIDADE 2: Rodapé
└── TopBar.svelte                   # ⭐ PRIORIDADE 2: Barra superior
```

#### **📍 src/lib/components/chat/**
```
chat/
├── Messages.svelte                 # ⭐ PRIORIDADE 1: Área de mensagens
├── MessageInput.svelte             # ⭐ PRIORIDADE 1: Input de chat
├── MessageBubble.svelte            # ⭐ PRIORIDADE 2: Bolhas de mensagem
└── ChatControls.svelte             # ⭐ PRIORIDADE 2: Controles do chat
```

#### **📍 src/lib/components/common/**
```
common/
├── Button.svelte                   # ⭐ PRIORIDADE 1: Botões
├── Modal.svelte                    # ⭐ PRIORIDADE 2: Modais
├── Card.svelte                     # ⭐ PRIORIDADE 2: Cards
├── Input.svelte                    # ⭐ PRIORIDADE 2: Inputs
└── Dropdown.svelte                 # ⭐ PRIORIDADE 3: Dropdowns
```

---

## 🎨 **SISTEMA DE ESTILOS ATUAL**

### **🎨 TAILWIND CONFIGURATION**
```javascript
// tailwind.config.js - ATUAL
module.exports = {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        // Colors atuais para modificar
        primary: colors.blue,
        gray: colors.zinc,
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
}
```

### **🎨 CSS VARIABLES ATUAIS**
```css
/* src/styles/tailwind.css - ATUAL */
:root {
  --primary-50: 239 246 255;    /* Para modificar */
  --primary-100: 219 234 254;   /* Para modificar */
  --primary-500: 59 130 246;    /* Para modificar */
  --primary-600: 37 99 235;     /* Para modificar */
  --primary-700: 29 78 216;     /* Para modificar */
  
  /* Dark mode variants */
  --primary-dark-50: 30 58 138;
  --primary-dark-100: 30 64 175;
}
```

---

## 🛠️ **STORES (ESTADO GLOBAL)**

### **📊 PRINCIPAIS STORES SVELTE**
```typescript
// src/lib/stores/index.ts
export const user = writable(null);           # Estado do usuário
export const settings = writable({});         # Configurações globais
export const models = writable([]);           # Modelos disponíveis
export const chats = writable([]);            # Conversas
export const theme = writable('dark');        # 🎯 TEMA ATUAL
export const sidebar = writable(true);        # Estado da sidebar
```

### **🎨 THEME STORE - ALVO PRINCIPAL**
```typescript
// src/lib/stores/theme.js - MODIFICAR
import { writable } from 'svelte/store';

export const theme = writable('default'); // Modificar para 'alest-gol'

export const themes = {
  default: {
    name: 'Default',
    colors: { /* cores atuais */ }
  },
  // 🎯 ADICIONAR TEMA ALEST-GOL
  'alest-gol': {
    name: 'Alest + GOL',
    colors: {
      primary: '#FF6B00',
      secondary: '#003366',
      accent: '#2C2C2C'
    }
  }
};
```

---

## 🌐 **PÁGINAS E ROTAS**

### **📍 ESTRUTURA DE ROTAS ATUAIS**
```
src/routes/
├── +layout.svelte                  # 🎯 Layout global - MODIFICAR
├── +page.svelte                    # Homepage/Dashboard
├── c/                              # Chat routes
│   ├── [id]/
│   │   └── +page.svelte           # Chat específico
├── admin/                          # Admin panel
│   ├── +layout.svelte             # Layout admin
│   └── +page.svelte               # Dashboard admin
├── settings/                       # Configurações
│   └── +page.svelte              # Página settings
└── auth/                          # Autenticação
    ├── signin/
    └── signup/
```

### **🎯 LAYOUT PRINCIPAL PARA MODIFICAR**
```svelte
<!-- src/routes/+layout.svelte - TARGET -->
<script lang="ts">
  import '../styles/tailwind.css';  // 🎯 Estilos globais
  import Navbar from '$lib/components/layout/Navbar.svelte';
  import Sidebar from '$lib/components/layout/Sidebar.svelte';
  
  // 🎯 Imports para adicionar tema Alest-GOL
</script>

<!-- 🎯 Estrutura HTML para personalizar -->
<div class="app">
  <Navbar />
  <div class="main-container">
    <Sidebar />
    <main class="content">
      <slot />
    </main>
  </div>
</div>
```

---

## 🔧 **CONFIGURAÇÕES DE BUILD**

### **⚙️ VITE CONFIG ATUAL**
```typescript
// vite.config.ts
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  define: {
    APP_VERSION: JSON.stringify(process.env.npm_package_version),
  },
  server: {
    port: 5173,  // Dev server
    proxy: {
      '/api': 'http://localhost:8080'  // Backend proxy
    }
  }
});
```

### **⚙️ SVELTE CONFIG ATUAL**
```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/kit/vite';

export default {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter(),
    files: {
      assets: 'static'
    }
  }
};
```

---

## 🎨 **PLANO DE MODIFICAÇÃO FRONTEND**

### **🎯 FASE 1: SETUP DO TEMA**
1. **Modificar `tailwind.config.js`**
   - Adicionar cores Alest-GOL
   - Configurar paleta expandida
   - Setup de dark/light modes

2. **Atualizar CSS Variables**
   - Definir custom properties
   - Criar sistema de tokens
   - Configurar transições de tema

3. **Criar Theme Store**
   - Implementar store de tema
   - Sistema de toggle de temas
   - Persistência local

### **🎯 FASE 2: COMPONENTES BASE**
1. **Layout Components**
   - `Navbar.svelte` - Header com branding
   - `Sidebar.svelte` - Menu lateral personalizado
   - `Footer.svelte` - Rodapé com logos

2. **UI Components**
   - `Button.svelte` - Botões com cores da marca
   - `Card.svelte` - Cards com design system
   - `Modal.svelte` - Modais branded

### **🎯 FASE 3: CHAT INTERFACE**
1. **Chat Components**
   - `Messages.svelte` - Interface de conversação
   - `MessageInput.svelte` - Input personalizado
   - `MessageBubble.svelte` - Bolhas com cores da marca

2. **Interactive Elements**
   - Loading states personalizados
   - Animations e micro-interactions
   - Feedback visual aprimorado

### **🎯 FASE 4: ASSETS E BRANDING**
1. **Visual Assets**
   - Logos Alest + GOL
   - Ícones personalizados
   - Patterns e backgrounds

2. **Typography**
   - Fontes corporativas
   - Hierarquia tipográfica
   - Responsive typography

---

## 📊 **APIS E INTEGRAÇÕES**

### **🔌 CLIENT APIs (src/lib/apis/)**
```
apis/
├── ollama.js                       # Cliente Ollama
├── openai.js                       # Cliente OpenAI
├── chats.js                        # API de conversas
├── users.js                        # API de usuários
├── models.js                       # API de modelos
└── configs.js                      # API de configurações
```

### **🤖 INTEGRAÇÃO COM OLLAMA**
```typescript
// src/lib/apis/ollama.js - NÃO MODIFICAR FUNCIONALIDADE
export const getModels = async () => {
  // Mantém lógica existente
  // Apenas modifica UI de apresentação
};

export const chat = async (messages) => {
  // Mantém integração com Ollama
  // UI do chat é que será personalizada
};
```

---

## 🚀 **COMANDOS DE DESENVOLVIMENTO**

### **💻 FRONTEND DEVELOPMENT**
```bash
# Instalar dependências
npm install

# Modo desenvolvimento (SvelteKit)
npm run dev                         # Porta 5173

# Build para produção
npm run build

# Preview da build
npm run preview

# Linting e formatação
npm run lint
npm run format
```

### **🐳 DOCKER DEVELOPMENT**
```bash
# Containers atuais funcionando
docker ps                          # Ver status

# Open WebUI (porta 3000)
docker logs open-webui             # Ver logs

# Ollama (porta 11434)  
docker logs ollama                 # Ver logs Ollama

# Restart containers se necessário
docker restart open-webui ollama
```

### **🧪 TESTING**
```bash
# Testes unitários (se configurados)
npm run test

# Testes E2E (se configurados)
npm run test:e2e

# Coverage
npm run test:coverage
```

---

## 🎯 **PONTOS DE MODIFICAÇÃO PRIORITÁRIOS**

### **🎨 HIGH PRIORITY (Modificar primeiro)**
1. **`tailwind.config.js`** - Cores e tema base
2. **`src/routes/+layout.svelte`** - Layout global  
3. **`src/lib/components/layout/Navbar.svelte`** - Header
4. **`src/lib/components/layout/Sidebar.svelte`** - Menu lateral
5. **`src/lib/stores/theme.js`** - Sistema de temas

### **🎨 MEDIUM PRIORITY (Segunda fase)**
1. **`src/lib/components/chat/Messages.svelte`** - Interface chat
2. **`src/lib/components/common/Button.svelte`** - Botões
3. **`src/lib/components/common/Card.svelte`** - Cards
4. **`src/styles/tailwind.css`** - CSS global customizado

### **🎨 LOW PRIORITY (Refinamentos)**
1. **`src/lib/components/icons/*`** - Ícones personalizados
2. **`static/*`** - Assets estáticos (logos, imagens)
3. **Animações e micro-interactions**
4. **Mobile optimizations**

---

## ⚠️ **CUIDADOS E RESTRIÇÕES**

### **❌ NÃO MODIFICAR**
- **`backend/`** - Lógica do servidor
- **`src/lib/apis/`** - Clientes API (apenas UI)
- **Funcionalidades de chat e IA**
- **Sistema de autenticação**
- **Configurações do Ollama**

### **✅ PODE MODIFICAR LIVREMENTE**
- **Todos os `.svelte` components**
- **CSS e estilos (`.css`, `.scss`)**
- **`tailwind.config.js`**
- **Assets em `static/`**
- **Stores de UI (tema, layout)**

### **⚠️ MODIFICAR COM CUIDADO**
- **`src/routes/+layout.svelte`** - Manter funcionalidade
- **Stores globais** - Não quebrar estado da app
- **TypeScript types** - Manter tipagem

---

**📅 DOCUMENTO CRIADO**: Dezembro 2024
**🎯 STATUS**: Arquitetura mapeada - Pronto para desenvolvimento
**👥 TARGET**: Frontend Team - Customização Alest+GOL
**🔄 VERSÃO**: Open WebUI v0.6.18 