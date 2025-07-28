# Per-User Chat Encryption - Docker Build & Testing Instructions

## Phase 1: Docker Build & Local Testing

### 1. Build Docker Image

```bash
cd /Users/hero/Documents/TPAI/Product/owui

# Build the Docker image using docker-compose.dev.yml
docker-compose -f docker-compose.dev.yml build

# Start the container with debug capabilities
docker-compose -f docker-compose.dev.yml up -d
```

**Expected Output to Verify:**
- Container `owui-dev` starts successfully
- Debug port 5678 is mapped for VSCode debugging
- Port 8080 is accessible for web interface
- SQLite database is mounted at `./backend/data`

### 2. Verify Encryption Shim Loads Correctly

**Monitor the container logs for encryption shim initialization:**
```bash
docker-compose -f docker-compose.dev.yml logs -f
```

**Key Log Patterns to Look For:**
- `DEBUG_USER_KEYS=True` environment variable set
- Encryption utilities module loaded successfully
- SQLAlchemy event listeners registered
- No import errors from `db_encryption_shim.py` or `encryption_utils.py`

**Troubleshooting:**
If encryption shim fails to load:
```bash
# Check container internals
docker exec -it owui-dev bash
cd /app/backend
python -c "from open_webui.models import db_encryption_shim; print('Shim loaded successfully')"
python -c "from open_webui.utils import encryption_utils; print('Encryption utils loaded successfully')"
```

### 3. Environment Variables Verification

**Check that all required environment variables are properly configured:**
```bash
docker exec -it owui-dev env | grep -E "(DEBUG_USER_KEYS|DATABASE_URL|WEBUI_SECRET_KEY|ENABLE_SIGNUP)"
```

**Expected Values:**
- `DEBUG_USER_KEYS=True`
- `DATABASE_URL=sqlite:///data/db.sqlite`
- `WEBUI_SECRET_KEY=a_secure_random_string_for_local_dev`
- `ENABLE_SIGNUP=True`

## Phase 2: Multi-User Encryption Validation

### 1. Access the Web Interface

Open browser to: http://localhost:8080

### 2. Test with Existing Users

**The database already contains 3 users with encryption keys:**

| User ID | Email | Name | Has Encryption Keys |
|---------|-------|------|-------------------|
| c32ec6965882aa92ab44af0d9ea106c45ac5101e8cdac8847247f4ac21947c64 | rcastillo23@gmail.com | RobRob | ✅ |
| 3768f6629272f49a7da246ca73e2e2910fe56b35a1eaff7060bf1465ba76f4e1 | rcastillo@clavesecurity.com | Clave | ✅ |
| 6f3e485355fa8a93392424cc0088685ab53047b96724c3612c54319841a30fc7 | rcastillo@totallyprivate.ai | TPAI | ✅ |

### 3. Multi-User Test Procedure

**For each user:**
1. **Login** with their email (you may need to set/reset passwords)
2. **Send test messages** like "Test message from user X - secret content"
3. **Monitor encryption logs** in real-time
4. **Verify database encryption** after each message

**Expected Encryption Log Patterns:**
```
DEBUG: before_flush: Processing new Chat object ID <chat_id> for encryption.
DEBUG: Successfully set plaintext DEK in context for user <user_id> for chat operation.
INFO: (CHAT) BEFORE ENCRYPT: Test message from user X - secret content...
INFO: (CHAT) AFTER ENCRYPT: gAAAAABh...
DEBUG: Cleared DEK from context variable.
```

**Expected Decryption Log Patterns:**
```
DEBUG: --- SQLAlchemy 'after_load' event triggered for Chat ID: <chat_id> ---
DEBUG: Successfully set plaintext DEK in context for user <user_id> for chat operation.
INFO: (CHAT) BEFORE DECRYPT: gAAAAABh...
INFO: (CHAT) AFTER DECRYPT: Test message from user X - secret content...
DEBUG: Cleared DEK from context variable.
```

### 4. Cross-User Isolation Verification

**Test that users cannot decrypt each other's messages:**
1. Login as User A, send a message
2. Note the chat ID from logs
3. Login as User B
4. Attempt to view User A's chat (should show decryption errors if implemented correctly)

## Phase 3: Database Verification

### 1. Direct Database Queries

```bash
# Access the SQLite database directly
docker exec -it owui-dev sqlite3 /app/backend/data/db.sqlite

# Verify user encryption fields
.headers on
SELECT id, email, name, 
       user_key IS NOT NULL as has_user_key, 
       user_encrypted_dek IS NOT NULL as has_encrypted_dek, 
       salt IS NOT NULL as has_salt 
FROM user;

# Check encrypted chat storage
SELECT id, user_id, LENGTH(chat) as chat_size, 
       substr(chat, 1, 100) as chat_preview 
FROM chat 
ORDER BY created_at DESC 
LIMIT 5;

# Exit SQLite
.quit
```

### 2. Test Encryption Utilities from Command Line

```bash
# Access container shell
docker exec -it owui-dev bash
cd /app/backend

# Run the encryption utilities test suite
python open_webui/utils/encryption_utils.py
```

**Expected Test Output:**
- User ID generation tests pass
- Salt and DEK generation tests pass
- UserKey derivation tests pass
- DEK encryption/decryption cycle tests pass
- Message encryption with user-specific DEK tests pass
- Fallback to mock key tests pass
- All assertions pass without errors

### 3. Verify Encrypted Storage Format

**Check that messages are stored in the expected encrypted format:**
```sql
-- Look for encrypted message structure
SELECT json_extract(chat, '$.messages[0].content') as message_content 
FROM chat 
WHERE json_extract(chat, '$.messages[0].content.is_encrypted') = 1 
LIMIT 3;
```

**Expected Format:**
```json
{
  "ciphertext": "gAAAAABh...",
  "is_encrypted": true
}
```

## Phase 4: Testing Cleanup

```bash
# Stop and remove containers
docker-compose -f docker-compose.dev.yml down

# Optional: Remove images to rebuild from scratch
docker-compose -f docker-compose.dev.yml down --rmi all
```

## Troubleshooting Common Issues

### Container Won't Start
- Check if ports 8080 or 5678 are already in use
- Verify Docker daemon is running
- Check file permissions on mounted volumes

### Encryption Shim Not Loading
- Verify all Python dependencies are installed
- Check for import errors in container logs
- Ensure SQLAlchemy version compatibility

### Database Issues
- Verify SQLite file exists and is writable
- Check database schema includes encryption fields
- Ensure volume mount is correct

### Debug Mode Issues
- Confirm `DEBUGGER=True` environment variable
- Check debugpy is listening on 0.0.0.0:5678
- Verify VSCode debug configuration if using IDE debugging

## Success Criteria

✅ **Container starts successfully with all services**
✅ **Encryption shim loads without errors**
✅ **All 3 existing users can login and send messages**
✅ **Messages are encrypted with user-specific DEKs**
✅ **Users cannot decrypt each other's messages**
✅ **Database shows encrypted storage format**
✅ **Encryption utilities pass all tests**
✅ **Logs show proper encryption/decryption cycles**