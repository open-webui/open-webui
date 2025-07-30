# 🛡️ Segurança e Compliance - Alest × GOL Platform

## 🎯 Visão Geral de Segurança

A plataforma Alest+GOL implementa múltiplas camadas de segurança para proteger dados sensíveis, garantir privacidade e atender aos mais altos padrões de compliance do setor de aviação e tecnologia.

---

## 🔐 Autenticação e Autorização

### **Sistema de Autenticação Multi-Layer**

#### **1. Autenticação Primária**
```yaml
Métodos Suportados:
  - Email/Senha: Criptografia bcrypt
  - OAuth 2.0: Google, GitHub, Microsoft
  - LDAP: Integração empresarial
  - SSO: Single Sign-On corporativo
  - 2FA: Two-Factor Authentication (TOTP)
```

#### **2. JWT (JSON Web Tokens)**
```python
# Configuração JWT
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_IN = "7d"  # 7 dias padrão
JWT_SECRET_KEY = "cryptographically-secure-key"

# Payload exemplo
{
  "sub": "user_id",
  "email": "user@gol.com.br",
  "role": "admin",
  "permissions": ["read", "write", "admin"],
  "exp": 1703980800,
  "iat": 1703894400
}
```

#### **3. RBAC (Role-Based Access Control)**
```yaml
Roles Definidos:
  admin:
    - Acesso total ao sistema
    - Gestão de usuários
    - Configurações globais
    - Monitoramento avançado
  
  user:
    - Acesso ao chat
    - Upload de documentos
    - Histórico pessoal
    - Configurações básicas
  
  guest:
    - Acesso limitado
    - Sem persistência
    - Rate limiting restritivo
```

### **Implementação de Segurança**
```python
# Middleware de autenticação
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Verificar JWT token
    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        try:
            payload = jwt.decode(token[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.state.user = await get_user_by_id(payload["sub"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expirado")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Token inválido")
    
    response = await call_next(request)
    return response
```

---

## 🔒 Criptografia e Proteção de Dados

### **Criptografia em Trânsito**
```yaml
TLS/SSL:
  - Versão Mínima: TLS 1.3
  - Cipher Suites: ECDHE-RSA-AES256-GCM-SHA384
  - Certificados: Let's Encrypt ou comercial
  - HSTS: Strict-Transport-Security habilitado
  - Certificate Pinning: Implementado em produção
```

### **Criptografia em Repouso**
```yaml
Database:
  - Algoritmo: AES-256-GCM
  - Key Management: AWS KMS / Azure Key Vault
  - Backup Encryption: Habilitado
  - Field-Level: Dados sensíveis específicos

Files:
  - Storage: Encrypted at rest
  - Upload: Virus scanning
  - Access: Signed URLs temporárias
```

### **Gerenciamento de Chaves**
```python
# Configuração de chaves
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
DATABASE_ENCRYPTION_KEY = os.environ.get("DB_ENCRYPTION_KEY")

# Rotação automática de chaves
class KeyRotationManager:
    def rotate_keys(self):
        # Gerar nova chave
        new_key = generate_secure_key()
        # Re-encriptar dados existentes
        self.re_encrypt_data(new_key)
        # Atualizar configuração
        self.update_key_config(new_key)
```

---

## 🚨 Proteção contra Ameaças

### **OWASP Top 10 - Proteções Implementadas**

#### **1. Broken Access Control**
```python
# Verificação de permissões
def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            user = request.state.user
            if not user.has_permission(permission):
                raise HTTPException(403, "Acesso negado")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

@app.post("/api/v1/admin/users")
@require_permission("admin.users.create")
async def create_user(request: Request):
    pass
```

#### **2. Cryptographic Failures**
```python
# Hashing seguro de senhas
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

#### **3. Injection Attacks**
```python
# SQLAlchemy ORM previne SQL injection
from sqlalchemy import text

# ✅ SEGURO - Usando ORM
users = session.query(User).filter(User.email == email).all()

# ✅ SEGURO - Parâmetros bindados
result = session.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": email}
)

# ❌ INSEGURO - String concatenation (não usado)
# query = f"SELECT * FROM users WHERE email = '{email}'"
```

#### **4. Insecure Design**
```yaml
Princípios Aplicados:
  - Defense in Depth: Múltiplas camadas
  - Principle of Least Privilege: Acesso mínimo
  - Fail Secure: Falha para estado seguro
  - Zero Trust: Verificar sempre
```

#### **5. Security Misconfiguration**
```python
# Headers de segurança
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response
```

### **Rate Limiting e DDoS Protection**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Rate limits por endpoint
@app.post("/api/v1/chat")
@limiter.limit("60/minute")  # 60 requests por minuto
async def chat_endpoint(request: Request):
    pass

@app.post("/api/v1/auth/login")
@limiter.limit("5/minute")   # 5 tentativas de login por minuto
async def login_endpoint(request: Request):
    pass
```

### **Input Validation e Sanitização**
```python
from pydantic import BaseModel, validator
import bleach

class ChatMessage(BaseModel):
    content: str
    model: str
    
    @validator('content')
    def sanitize_content(cls, v):
        # Remover HTML malicioso
        clean_content = bleach.clean(v, tags=[], attributes={})
        # Validar tamanho
        if len(clean_content) > 10000:
            raise ValueError('Mensagem muito longa')
        return clean_content
    
    @validator('model')
    def validate_model(cls, v):
        allowed_models = ['gemma2:2b', 'gemini-1.5-flash']
        if v not in allowed_models:
            raise ValueError('Modelo não permitido')
        return v
```

---

## 🔍 Monitoramento e Auditoria

### **Logging de Segurança**
```python
import logging
import json
from datetime import datetime

# Logger estruturado para auditoria
security_logger = logging.getLogger("security")

def log_security_event(event_type: str, user_id: str, details: dict):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent"),
        "details": details
    }
    security_logger.info(json.dumps(log_entry))

# Exemplos de uso
log_security_event("LOGIN_SUCCESS", user.id, {"method": "oauth"})
log_security_event("LOGIN_FAILED", None, {"email": email, "reason": "invalid_password"})
log_security_event("ADMIN_ACTION", user.id, {"action": "user_created", "target": new_user.id})
```

### **Eventos Auditados**
```yaml
Autenticação:
  - login_success
  - login_failed
  - logout
  - password_change
  - 2fa_enabled
  - 2fa_disabled

Autorização:
  - access_denied
  - permission_escalation
  - role_change

Dados:
  - data_access
  - data_modification
  - data_export
  - file_upload
  - file_download

Sistema:
  - config_change
  - user_created
  - user_deleted
  - model_added
  - api_key_created
```

### **Alertas de Segurança**
```python
class SecurityAlertManager:
    def __init__(self):
        self.alert_thresholds = {
            "failed_logins": 5,      # 5 falhas em 5 minutos
            "admin_actions": 10,     # 10 ações admin em 1 hora
            "data_access": 100,      # 100 acessos em 10 minutos
        }
    
    async def check_suspicious_activity(self, event_type: str, user_id: str):
        # Verificar padrões suspeitos
        recent_events = await self.get_recent_events(event_type, user_id)
        
        if len(recent_events) > self.alert_thresholds.get(event_type, 999):
            await self.send_security_alert(
                f"Atividade suspeita detectada: {event_type}",
                {"user_id": user_id, "count": len(recent_events)}
            )
```

---

## 🏢 Compliance e Regulamentações

### **LGPD (Lei Geral de Proteção de Dados)**
```yaml
Implementações:
  Consentimento:
    - Opt-in explícito para coleta
    - Granularidade por tipo de dado
    - Revogação facilitada
  
  Direitos do Titular:
    - Acesso aos dados
    - Correção de dados
    - Exclusão (direito ao esquecimento)
    - Portabilidade
    - Informação sobre uso
  
  Minimização:
    - Coleta apenas dados necessários
    - Retenção por tempo limitado
    - Anonimização quando possível
```

### **Implementação LGPD**
```python
class LGPDManager:
    async def export_user_data(self, user_id: str) -> dict:
        """Exportar todos os dados do usuário (portabilidade)"""
        user_data = {
            "profile": await self.get_user_profile(user_id),
            "chats": await self.get_user_chats(user_id),
            "files": await self.get_user_files(user_id),
            "preferences": await self.get_user_preferences(user_id)
        }
        return user_data
    
    async def delete_user_data(self, user_id: str):
        """Exclusão completa dos dados (direito ao esquecimento)"""
        # Anonimizar mensagens em chats compartilhados
        await self.anonymize_shared_content(user_id)
        # Deletar dados pessoais
        await self.delete_personal_data(user_id)
        # Log da ação
        log_security_event("DATA_DELETION", user_id, {"reason": "user_request"})
```

### **Certificações e Standards**
```yaml
ISO 27001:
  - Information Security Management System
  - Risk assessment framework
  - Continuous improvement process

SOC 2 Type II:
  - Security controls
  - Availability monitoring  
  - Processing integrity
  - Confidentiality measures

GDPR Compliance:
  - Data protection by design
  - Privacy impact assessments
  - Data breach notification
```

---

## 🔧 Configurações de Segurança

### **Ambiente de Produção**
```bash
# Variáveis críticas de segurança
JWT_SECRET=<256-bit-cryptographically-secure-key>
DATABASE_ENCRYPTION_KEY=<aes-256-key>
SESSION_SECRET=<secure-session-key>

# HTTPS obrigatório
FORCE_HTTPS=true
SECURE_COOKIES=true

# Rate limiting
RATE_LIMIT_ENABLED=true
MAX_REQUESTS_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
SECURITY_LOG_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=365
```

### **Hardening de Sistema**
```yaml
Server Hardening:
  - Disable root login
  - SSH key-only authentication
  - Fail2ban para proteção SSH
  - Firewall rules restritivas
  - Regular security updates

Container Security:
  - Non-root user
  - Read-only filesystem
  - Minimal base images
  - Security scanning
  - Resource limits
```

### **Backup e Recovery Seguro**
```python
class SecureBackupManager:
    def __init__(self):
        self.encryption_key = os.environ.get("BACKUP_ENCRYPTION_KEY")
    
    async def create_encrypted_backup(self):
        # Criar backup dos dados
        backup_data = await self.export_all_data()
        
        # Criptografar backup
        encrypted_backup = self.encrypt_data(backup_data, self.encryption_key)
        
        # Upload seguro para storage
        backup_url = await self.upload_to_secure_storage(encrypted_backup)
        
        # Log da operação
        log_security_event("BACKUP_CREATED", "system", {
            "backup_id": backup_url,
            "size": len(encrypted_backup)
        })
```

---

## 🚨 Incident Response

### **Plano de Resposta a Incidentes**
```yaml
Detecção:
  - Monitoring automatizado
  - Alertas em tempo real
  - Análise de logs de segurança
  - Relatórios de usuários

Contenção:
  - Isolamento de sistemas afetados
  - Revogação de credenciais comprometidas
  - Bloqueio de IPs maliciosos
  - Ativação de modo de emergência

Erradicação:
  - Remoção de malware/ameaças
  - Patch de vulnerabilidades
  - Atualização de credenciais
  - Reforço de controles

Recuperação:
  - Restauração de serviços
  - Validação de integridade
  - Monitoramento intensivo
  - Comunicação com stakeholders
```

### **Contatos de Emergência**
```yaml
Equipe de Segurança:
  - Security Lead: security@alest-gol.ai
  - DevOps Lead: devops@alest-gol.ai
  - CTO Alest: cto@alest.com
  - IT Director GOL: it-director@gol.com.br

Canais de Comunicação:
  - Slack: #security-incidents
  - WhatsApp: Grupo de emergência
  - Email: security-team@alest-gol.ai
  - Phone: +55 11 99999-9999
```

---

## 📋 Checklist de Segurança

### **Pré-Deploy**
- [ ] Todos os secrets em variáveis de ambiente
- [ ] TLS/SSL configurado corretamente
- [ ] Rate limiting implementado
- [ ] Headers de segurança configurados
- [ ] Input validation em todos endpoints
- [ ] Logging de auditoria ativo
- [ ] Backup automatizado configurado
- [ ] Monitoramento de segurança ativo

### **Pós-Deploy**
- [ ] Penetration testing executado
- [ ] Vulnerability scanning completo
- [ ] Logs de segurança funcionando
- [ ] Alertas testados
- [ ] Incident response plan validado
- [ ] Team treinado em procedimentos
- [ ] Documentação atualizada
- [ ] Compliance verificado

---

## 📊 Métricas de Segurança

### **KPIs de Segurança**
```yaml
Disponibilidade:
  - Uptime: 99.9%
  - MTTR: <30 minutos
  - RTO: <1 hora
  - RPO: <15 minutos

Segurança:
  - Zero data breaches
  - <0.1% failed authentications
  - 100% encrypted communications
  - <24h vulnerability patching

Compliance:
  - 100% LGPD compliance
  - Annual security audits
  - Quarterly penetration tests
  - Monthly vulnerability scans
```

---

**🛡️ Segurança de nível empresarial para proteger dados críticos da aviação**

*Implementada com os mais altos padrões para a parceria Alest × GOL* ✈️