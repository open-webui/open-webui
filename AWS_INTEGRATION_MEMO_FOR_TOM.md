# AWS Integration Technical Memo - Per-User Chat Encryption
## For Tom (Claude Code Session)

**Context**: The per-user chat encryption system is fully implemented and tested on the `feature/db-shim` branch. This memo provides step-by-step AWS integration instructions for Aurora database and KMS integration.

**Branch**: `feature/db-shim` (merge to `main` when ready)
**Status**: ✅ Local testing completed successfully - encryption working for all users

---

## 🎯 Current Implementation Status

### ✅ What's Already Working
- **Complete per-user encryption system** with SQLAlchemy event listeners
- **Database schema** includes all encryption fields (salt, user_encrypted_dek, user_key, kms_encrypted_dek)
- **Encryption utilities** with full PBKDF2, Fernet, and context management
- **Chat branching support** (encrypts both `chat.messages[]` and `chat.history.messages{}`)
- **Multi-user isolation** verified - users cannot decrypt each other's data
- **Fallback mechanisms** for missing keys and error handling

### 🔄 What Needs AWS Integration
- **Database**: SQLite → Aurora PostgreSQL connection (no migration needed)
- **Key Management**: Local HMAC → AWS KMS HMAC for User ID generation
- **User Keys**: Integrate with existing KMS keys for DEK encryption

---

## 📋 Infrastructure Status (Tom's Reference)

### ✅ Already Completed by You
- **Aurora DB**: Stood up in separate CDK stack
- **KMS Keys**: System-wide keys already created (including 512-bit HMAC keys)
- **Secrets Manager**: Already configured
- **ALB**: Handled in separate CDK stack
- **CI/CD Pipeline**: You're handling Docker build & push to ECR/ECS

### 🚫 Explicitly NOT Doing
- **Key Rotation**: We're not rotating user encryption keys (non-standard but intentional)
  - **Reason**: Users maintain encryption keys in client certificates across multiple devices
  - **Impact**: If we rotated DEKs, we'd have to re-encrypt ALL chat data (expensive)
  - **Design Decision**: Client cert-based keys are persistent by design
- **Data Migration**: No existing data to migrate from SQLite to Aurora
- **User Provisioning Changes**: Will be handled later with client cert integration

---

# 📋 AWS Integration Checklist for Tom

## Phase 1: Aurora PostgreSQL Connection [Priority: HIGH]

### 1.1 Database Schema Creation
**✅ GOOD NEWS**: OWUI handles schema creation automatically (same as local SQLite)
- The existing migration system will create all tables including encryption fields
- No manual schema creation needed

### 1.2 Connection Configuration

**Update**: `backend/open_webui/config.py`
```python
# Replace SQLite configuration with Aurora
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)

# Aurora-specific connection settings
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "connect_args": {
        "sslmode": "require",
        "application_name": "open-webui"
    }
}
```

**Environment Variables for Aurora:**
```bash
# Aurora PostgreSQL connection (via Secrets Manager)
DATABASE_URL=postgresql://owui_user:password@aurora-endpoint:5432/owui?sslmode=require
```

---

## Phase 2: KMS Integration with Existing Keys [Priority: HIGH]

### 2.1 KMS Key Configuration
**✅ You've already created the KMS keys** - we just need to integrate them.

**Tom**: Check your AWS KMS console for:
- **512-bit HMAC key** for User ID generation (you mentioned you created this)
- **Encryption key** for DEK encryption (system-wide key)
- **Stripe ID key** (if needed for payment integration)

### 2.2 KMS Integration Code Changes

**Update**: `backend/open_webui/utils/encryption_utils.py`

**Add KMS integration functions:**
```python
import boto3
from botocore.exceptions import ClientError
import os

# AWS KMS client
kms_client = boto3.client('kms', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# KMS Key IDs from environment (Tom: use your actual key IDs)
HMAC_KEY_ID = os.getenv('KMS_HMAC_KEY_ID')  # Your 512-bit HMAC key
APPLICATION_CMK_ID = os.getenv('KMS_APPLICATION_CMK_ID')  # Your system-wide encryption key

def generate_user_id_kms(email: str, hmac_key_id: str = None) -> str:
    """
    Generate User ID using AWS KMS GenerateMac operation.
    Replaces the local HMAC implementation.
    """
    if not hmac_key_id:
        hmac_key_id = HMAC_KEY_ID
    
    if not hmac_key_id:
        raise ValueError("KMS HMAC Key ID not configured")
    
    try:
        response = kms_client.generate_mac(
            KeyId=hmac_key_id,
            Message=email.lower().encode('utf-8'),
            MacAlgorithm='HMAC_SHA_256'
        )
        # Return hex digest like the original implementation
        return response['Mac'].hex()
    except ClientError as e:
        raise Exception(f"KMS GenerateMac failed: {e}")

def encrypt_dek_kms(dek: bytes, cmk_id: str = None) -> bytes:
    """
    Encrypt DEK using AWS KMS.
    This populates the kms_encrypted_dek field for disaster recovery.
    """
    if not cmk_id:
        cmk_id = APPLICATION_CMK_ID
    
    if not cmk_id:
        raise ValueError("KMS Application CMK ID not configured")
    
    try:
        response = kms_client.encrypt(
            KeyId=cmk_id,
            Plaintext=dek,
            EncryptionContext={
                'purpose': 'user-dek-encryption',
                'application': 'open-webui'
            }
        )
        return response['CiphertextBlob']
    except ClientError as e:
        raise Exception(f"KMS Encrypt failed: {e}")

def decrypt_dek_kms(kms_encrypted_dek: bytes) -> bytes:
    """
    Decrypt DEK using AWS KMS.
    Used for disaster recovery when user_key is lost.
    """
    try:
        response = kms_client.decrypt(
            CiphertextBlob=kms_encrypted_dek,
            EncryptionContext={
                'purpose': 'user-dek-encryption', 
                'application': 'open-webui'
            }
        )
        return response['Plaintext']
    except ClientError as e:
        raise Exception(f"KMS Decrypt failed: {e}")

# Update existing functions to populate kms_encrypted_dek field
def setup_user_encryption(user_id: str, email: str) -> dict:
    """
    Complete user encryption setup with both local and KMS encryption.
    Call this when creating new users.
    """
    # Generate salt and DEK
    salt = generate_salt()
    dek_plaintext = generate_dek()
    
    # Derive UserKey from UserID (replace with client cert in production)
    user_key = derive_key_from_user_id(user_id, salt)
    
    # Encrypt DEK with UserKey (normal operation)
    user_encrypted_dek = encrypt_dek(dek_plaintext, user_key)
    
    # ALSO encrypt DEK with KMS (disaster recovery)
    kms_encrypted_dek = encrypt_dek_kms(dek_plaintext)
    
    return {
        'salt': salt,
        'user_key': user_key,  # TEMPORARY - remove when client certs implemented
        'user_encrypted_dek': user_encrypted_dek,
        'kms_encrypted_dek': kms_encrypted_dek
    }
```

**Environment Variables for KMS:**
```bash
# AWS KMS Configuration (Tom: use your actual key ARNs)
AWS_REGION=us-east-1
KMS_HMAC_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/your-512bit-hmac-key-id
KMS_APPLICATION_CMK_ID=arn:aws:kms:us-east-1:123456789012:key/your-system-wide-key-id
```

### 2.3 User Creation Integration

**Update**: `backend/open_webui/models/users.py`

**Modify user creation to use KMS and populate kms_encrypted_dek:**
```python
from open_webui.utils.encryption_utils import generate_user_id_kms, setup_user_encryption

class Users:
    @staticmethod
    def insert_new_user(email: str, name: str, password: str, role: str = "pending") -> Optional[UserModel]:
        # Generate User ID using KMS HMAC (replaces local HMAC)
        user_id = generate_user_id_kms(email)
        
        # For now, hash password with KDF until client cert integration
        # Tom: This is temporary until we implement client cert provisioning
        password_hash = hash_password(password)  # Use existing password hashing
        
        # Setup complete encryption for the user
        encryption_data = setup_user_encryption(user_id, email)
        
        user = UserForm(**{
            "id": user_id,
            "name": name,
            "email": email, 
            "password": password_hash,  # Temporary until client certs
            "role": role,
            "profile_image_url": "/user.png",
            "salt": encryption_data['salt'],
            "user_key": encryption_data['user_key'],  # TEMPORARY
            "user_encrypted_dek": encryption_data['user_encrypted_dek'],
            "kms_encrypted_dek": encryption_data['kms_encrypted_dek']  # NEW - KMS backup
        })
        
        # Insert user with all encryption fields populated
        try:
            with get_db() as db:
                result = Users.insert_user(db, user)
                if result:
                    return Users.get_user_by_id(result.id)
                else:
                    return None
        except Exception as e:
            log.exception(f"Failed to create user {email}: {e}")
            return None
```

---

## Phase 3: ECS Deployment Configuration [Priority: MEDIUM]

### 3.1 IAM Permissions for ECS Task

**ECS Task Role** needs these KMS permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "KMSAccess",
      "Effect": "Allow",
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt", 
        "kms:GenerateMac",
        "kms:DescribeKey"
      ],
      "Resource": [
        "arn:aws:kms:us-east-1:ACCOUNT:key/YOUR-HMAC-KEY-ID",
        "arn:aws:kms:us-east-1:ACCOUNT:key/YOUR-SYSTEM-WIDE-KEY-ID"
      ]
    },
    {
      "Sid": "SecretsManagerAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:owui/*"
      ]
    }
  ]
}
```

### 3.2 Environment Variables via Secrets Manager

**Tom**: Store these in your existing Secrets Manager setup:
```bash
# Add KMS configuration to existing secrets
aws secretsmanager create-secret \
  --name "owui/kms-hmac-key-id" \
  --description "KMS HMAC Key ID for User ID generation" \
  --secret-string "arn:aws:kms:us-east-1:123456789012:key/YOUR-ACTUAL-HMAC-KEY-ID"

aws secretsmanager create-secret \
  --name "owui/kms-application-key-id" \
  --description "KMS system-wide key for DEK encryption" \
  --secret-string "arn:aws:kms:us-east-1:123456789012:key/YOUR-ACTUAL-SYSTEM-KEY-ID"
```

---

## Phase 4: Testing & Validation [Priority: HIGH]

### 4.1 Test User Creation with KMS Integration
**Use existing OWUI username/password authentication:**
```bash
# Create test user via OWUI signup
curl -X POST https://your-domain/api/v1/auths/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password", "name": "Test User"}'
```

### 4.2 Database Verification (Aurora Access)
**Tom**: Since you have an airgapped system, you'll need to access Aurora from within the VPC.

**Options for Aurora access:**
1. **EC2 Jumpbox** in the DB private subnet (recommended)
2. **ECS Exec** into running container
3. **AWS Systems Manager Session Manager** with VPC endpoints

**Create EC2 jumpbox with psql:**
```bash
# Launch EC2 instance in DB subnet with security group allowing Aurora access
# Install psql client:
sudo yum update -y
sudo yum install -y postgresql15

# Test Aurora connection
psql -h your-aurora-endpoint.cluster-xxxxx.us-east-1.rds.amazonaws.com -U owui_user -d owui
```

**Verification queries to run:**
```sql
-- Check KMS encryption fields are populated for new users
SELECT 
    email, 
    kms_encrypted_dek IS NOT NULL as has_kms_backup,
    user_encrypted_dek IS NOT NULL as has_user_dek
FROM "user" 
WHERE email = 'test@example.com';

-- Verify all users have unique encryption keys
SELECT 
    COUNT(DISTINCT user_encrypted_dek) as unique_user_deks,
    COUNT(DISTINCT kms_encrypted_dek) as unique_kms_deks,
    COUNT(*) as total_users
FROM "user" 
WHERE user_encrypted_dek IS NOT NULL;
```

---

## 🚨 Critical Items for Tom

### 1. **KMS Key Discovery**
**Action Required**: Check your AWS KMS console and identify:
- The 512-bit HMAC key you created (for User ID generation)
- The system-wide encryption key (for DEK encryption/disaster recovery)
- Update the environment variables with actual ARNs

### 2. **Disaster Recovery is Critical**
- The KMS system-wide key is critical for disaster recovery
- If users lose client certificates, KMS decrypt is the only way to recover their data
- Monitor KMS API calls via CloudTrail
- Test KMS decrypt functionality before production

### 3. **Client Certificate Integration (Future)**
- Current implementation stores `user_key` in database (temporary)
- After client cert integration, remove `user_key` from database entirely
- UserKeys will be delivered via mTLS client certificates
- KMS `kms_encrypted_dek` becomes the primary disaster recovery mechanism

### 4. **Aurora Schema Validation**
- OWUI should auto-create tables including encryption fields
- Verify the migration system creates: `salt`, `user_encrypted_dek`, `user_key`, `kms_encrypted_dek` columns
- If schema creation fails, check Aurora permissions and connection string

---

## ✅ Success Criteria for Tom

**Phase 1 Complete When:**
- ✅ Aurora connection working (OWUI starts without database errors)
- ✅ Schema auto-created with all encryption fields
- ✅ Can create test user via OWUI signup

**Phase 2 Complete When:**
- ✅ KMS HMAC working for User ID generation  
- ✅ New users have `kms_encrypted_dek` populated
- ✅ Chat encryption still working end-to-end
- ✅ Can query Aurora from jumpbox/container

**Ready for Production When:**
- ✅ All KMS operations working reliably
- ✅ Disaster recovery tested (KMS decrypt works)
- ✅ Performance benchmarks meet requirements
- ✅ Monitoring/alerting configured for KMS operations

---

## 🔄 Implementation Priority Order

1. **HIGH**: Aurora connection configuration
2. **HIGH**: KMS key integration (HMAC for User ID, encryption for DEK backup)
3. **MEDIUM**: ECS task permissions and environment variables
4. **HIGH**: Testing with jumpbox Aurora access
5. **LOW**: Performance optimization and monitoring

---

**Questions for Tom?**
- What are the actual KMS key ARNs you created?
- Do you prefer EC2 jumpbox or ECS exec for Aurora testing?
- Is the Aurora endpoint already configured in your Secrets Manager?

---

*This focused memo addresses your specific AWS integration needs without unnecessary complexity. The local encryption system is fully tested and ready for Aurora/KMS integration.*