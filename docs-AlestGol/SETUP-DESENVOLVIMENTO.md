# 🛠️ Setup de Desenvolvimento - Alest × GOL

## 🎯 Como Rodar o Projeto (Frontend + Backend Separados)

Este guia mostra exatamente como rodamos o projeto durante o desenvolvimento, com **frontend e backend separados** para facilitar o desenvolvimento e debug.

---

## 📋 Pré-requisitos

### **Software Necessário**
```bash
# Node.js (versão 18 ou superior)
node --version  # deve mostrar v18.x.x ou superior
npm --version   # deve mostrar 9.x.x ou superior

# Python (versão 3.11 ou superior)
python3 --version  # deve mostrar Python 3.11.x ou superior
pip3 --version     # deve mostrar pip 23.x.x ou superior

# Git
git --version
```

### **Instalação dos Pré-requisitos**

#### **macOS**
```bash
# Instalar Node.js via Homebrew
brew install node

# Instalar Python via Homebrew
brew install python@3.11

# Verificar instalações
node --version && python3 --version
```

#### **Ubuntu/Debian**
```bash
# Atualizar sistema
sudo apt update

# Instalar Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Instalar Python
sudo apt install python3.11 python3.11-pip python3.11-venv

# Verificar instalações
node --version && python3.11 --version
```

#### **Windows**
```bash
# Instalar via Chocolatey
choco install nodejs python311

# Ou baixar diretamente:
# Node.js: https://nodejs.org/
# Python: https://www.python.org/downloads/
```

---

## 🚀 Setup do Projeto

### **1. Clone do Repositório**
```bash
# Clone do projeto
git clone https://github.com/open-webui/open-webui.git
cd open-webui

# Checkout da branch com tema Alest+GOL
git checkout feature.alest.gol.theme

# Verificar se está na branch correta
git branch  # deve mostrar * feature.alest.gol.theme
```

### **2. Setup do Backend (Python/FastAPI)**
```bash
# Navegar para pasta do backend
cd backend

# Criar ambiente virtual Python
python3 -m venv venv

# Ativar ambiente virtual
# macOS/Linux:
source venv/bin/activate

# Windows:
# venv\Scripts\activate

# Verificar se ambiente está ativo (deve mostrar (venv) no prompt)
which python  # deve apontar para pasta venv

# Instalar dependências
pip install -r requirements.txt

# Verificar instalação
pip list | grep fastapi  # deve mostrar FastAPI instalado
```

### **3. Setup do Frontend (Node.js/SvelteKit)**
```bash
# Voltar para raiz do projeto
cd ..  # ou cd /caminho/para/open-webui

# Instalar dependências do frontend
npm install

# Verificar instalação
npm list --depth=0 | grep svelte  # deve mostrar SvelteKit
```

---

## 🔧 Configuração do Ambiente

### **1. Variáveis de Ambiente do Backend**
```bash
# Criar arquivo .env na pasta backend
cd backend
touch .env

# Adicionar configurações (usando seu editor favorito)
cat > .env << EOF
# Database
DATABASE_URL=sqlite:///./data/webui.db

# CORS para desenvolvimento
CORS_ALLOW_ORIGIN=http://localhost:5173

# Gemini API (já configurado)
GEMINI_API_KEY=AIzaSyDrqEFhXHRauPLVk4qUpvS0VSQSHh4LKKI
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta

# Ollama (se estiver rodando)
OLLAMA_BASE_URL=http://localhost:11434

# Configurações de desenvolvimento
WEBUI_NAME="Alest × GOL - AI Assistant"
DEFAULT_THEME=alest-gol
ENABLE_SIGNUP=true
EOF
```

### **2. Configuração do Frontend**
```bash
# Voltar para raiz
cd ..

# O frontend já está configurado com:
# - Tema Alest+GOL ativo por padrão
# - Proxy para backend na porta 8080
# - Configurações de desenvolvimento
```

---

## 🚀 Rodando o Projeto

### **Método 1: Usando o Script Personalizado (Recomendado)**
```bash
# Na raiz do projeto, usar o script que criamos
./start-alest-gol.sh

# Este script:
# 1. Copia todos os assets (logos, favicons)
# 2. Configura variáveis do Gemini
# 3. Inicia o backend na porta 8080
```

### **Método 2: Rodando Separadamente (Para Debug)**

#### **Terminal 1 - Backend**
```bash
# Navegar para backend
cd backend

# Ativar ambiente virtual
source venv/bin/activate  # macOS/Linux
# ou venv\Scripts\activate  # Windows

# Rodar backend
python -m uvicorn open_webui.main:app --port 8080 --host 0.0.0.0 --reload

# Deve mostrar:
# INFO: Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
# INFO: Started reloader process
```

#### **Terminal 2 - Frontend**
```bash
# Na raiz do projeto (novo terminal)
npm run dev

# Deve mostrar:
# VITE ready in Xms
# Local:   http://localhost:5173/
# Network: http://192.168.x.x:5173/
```

#### **Terminal 3 - Ollama (Opcional)**
```bash
# Se quiser rodar Ollama local
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Baixar modelo
docker exec -it ollama ollama pull gemma2:2b
```

---

## 🔍 Verificação do Setup

### **1. Verificar Backend**
```bash
# Testar se backend está funcionando
curl http://localhost:8080/health

# Deve retornar:
# {"status":"ok"}

# Testar API
curl http://localhost:8080/api/v1/configs

# Deve retornar JSON com configurações
```

### **2. Verificar Frontend**
```bash
# Abrir no navegador
open http://localhost:5173  # macOS
# ou apenas acessar http://localhost:5173

# Deve mostrar:
# ✅ Tela de login com logos Alest+GOL
# ✅ Tema personalizado ativo
# ✅ Interface funcionando
```

### **3. Verificar Assets**
```bash
# Verificar se logos estão disponíveis
curl -I http://localhost:8080/static/logo-gol.svg
curl -I http://localhost:8080/static/Logo-Alest-Branco-240x104-1-1.png

# Ambos devem retornar: HTTP/1.1 200 OK
```

---

## 📁 Estrutura de Desenvolvimento

### **Portas Usadas**
```
Frontend (SvelteKit): http://localhost:5173
Backend (FastAPI):    http://localhost:8080
Ollama (opcional):    http://localhost:11434
```

### **Arquivos Importantes**
```
open-webui/
├── backend/
│   ├── .env                    # Variáveis de ambiente
│   ├── requirements.txt        # Dependências Python
│   ├── open_webui/
│   │   ├── main.py            # Aplicação principal
│   │   ├── config.py          # Configurações (Gemini, prompts GOL)
│   │   └── static/            # Assets servidos pelo backend
│   └── venv/                  # Ambiente virtual Python
├── src/
│   ├── lib/components/        # Componentes Svelte
│   ├── routes/               # Páginas da aplicação
│   └── app.html              # Template principal
├── static/
│   ├── themes/
│   │   └── alest-gol.css     # Tema personalizado
│   ├── logo-gol.svg          # Logo GOL
│   └── Logo-Alest-Branco-240x104-1-1.png  # Logo Alest
├── package.json              # Dependências Node.js
└── start-alest-gol.sh       # Script de inicialização
```

---

## 🐛 Troubleshooting

### **Problemas Comuns**

#### **"Backend não inicia"**
```bash
# Verificar se ambiente virtual está ativo
which python  # deve apontar para venv

# Verificar dependências
pip install -r requirements.txt

# Verificar porta
lsof -i :8080  # ver se porta está ocupada

# Logs detalhados
python -m uvicorn open_webui.main:app --port 8080 --log-level debug
```

#### **"Frontend não conecta com backend"**
```bash
# Verificar se backend está rodando
curl http://localhost:8080/health

# Verificar CORS no backend/.env
grep CORS backend/.env
# Deve ter: CORS_ALLOW_ORIGIN=http://localhost:5173

# Verificar proxy no vite.config.ts
grep -A 10 "proxy" vite.config.ts
```

#### **"Logos não aparecem"**
```bash
# Verificar se assets foram copiados
ls -la backend/open_webui/static/

# Copiar manualmente se necessário
cp static/logo-gol.svg backend/open_webui/static/
cp static/Logo-Alest-Branco-240x104-1-1.png backend/open_webui/static/
```

#### **"Tema não está ativo"**
```bash
# Verificar se tema está sendo carregado
curl http://localhost:5173/themes/alest-gol.css

# Verificar configuração no app.html
grep "alest-gol" src/app.html

# Limpar cache do navegador
# Ctrl+Shift+F5 ou Cmd+Shift+R
```

---

## 🔄 Workflow de Desenvolvimento

### **Desenvolvimento Típico**
```bash
# 1. Ativar ambiente
cd backend && source venv/bin/activate

# 2. Rodar backend (terminal 1)
python -m uvicorn open_webui.main:app --port 8080 --reload

# 3. Rodar frontend (terminal 2, na raiz)
npm run dev

# 4. Desenvolver
# - Modificar arquivos .svelte (frontend)
# - Modificar arquivos .py (backend)
# - Hot reload automático em ambos

# 5. Testar
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8080/docs
```

### **Comandos Úteis**
```bash
# Ver logs do backend
tail -f backend/logs/app.log

# Reinstalar dependências frontend
rm -rf node_modules package-lock.json
npm install

# Resetar ambiente Python
rm -rf backend/venv
cd backend && python3 -m venv venv
source venv/bin/activate && pip install -r requirements.txt

# Build de produção (teste)
npm run build

# Verificar sintaxe Python
cd backend && python -m py_compile open_webui/main.py
```

---

## 📊 Monitoramento Durante Desenvolvimento

### **Logs Importantes**
```bash
# Backend logs
tail -f backend/logs/uvicorn.log

# Frontend logs (no terminal onde rodou npm run dev)
# Erros aparecem automaticamente

# Browser DevTools
# F12 -> Console (para erros JavaScript)
# F12 -> Network (para requisições HTTP)
```

### **Endpoints de Debug**
```bash
# Health check
curl http://localhost:8080/health

# Configurações
curl http://localhost:8080/api/v1/configs

# Usuários (se autenticado)
curl -H "Authorization: Bearer TOKEN" http://localhost:8080/api/v1/users

# Documentação interativa
open http://localhost:8080/docs
```

---

## 🚀 Deploy para Testes

### **Build de Produção Local**
```bash
# Build do frontend
npm run build

# Testar build
npm run preview  # roda na porta 4173

# Build do backend (opcional)
cd backend
pip install build
python -m build
```

### **Docker (Opcional)**
```bash
# Build da imagem
docker build -t alest-gol-platform .

# Rodar container
docker run -p 3000:8080 alest-gol-platform
```

---

## 📞 Suporte para Equipe

### **Contatos**
```
🐛 Problemas técnicos: dev-team@alest.com
📚 Dúvidas de código: code-review@alest.com
🚀 Deploy e infra: devops@alest.com
```

### **Recursos**
- **Slack**: #alest-gol-dev
- **Documentação**: Esta pasta docs-AlestGol/
- **Issues**: GitHub repository
- **Wiki**: Confluence interno

---

## 📋 Checklist para Novos Desenvolvedores

### **Setup Inicial**
- [ ] Node.js 18+ instalado
- [ ] Python 3.11+ instalado
- [ ] Git configurado
- [ ] Repositório clonado
- [ ] Branch feature.alest.gol.theme ativa
- [ ] Dependências backend instaladas
- [ ] Dependências frontend instaladas
- [ ] Arquivo .env criado no backend

### **Teste do Ambiente**
- [ ] Backend roda na porta 8080
- [ ] Frontend roda na porta 5173
- [ ] Health check do backend retorna OK
- [ ] Interface carrega com tema Alest+GOL
- [ ] Logos aparecem corretamente
- [ ] Chat básico funciona
- [ ] Gemini API responde

### **Desenvolvimento**
- [ ] Hot reload funciona (backend e frontend)
- [ ] Console sem erros críticos
- [ ] Consegue fazer login/registro
- [ ] Pode criar e usar chats
- [ ] Upload de arquivos funciona

**🎯 Ambiente pronto para desenvolvimento!** 🚀

---

**💡 Dica**: Mantenha sempre 2 terminais abertos - um para backend, outro para frontend. Isso facilita muito o debug!