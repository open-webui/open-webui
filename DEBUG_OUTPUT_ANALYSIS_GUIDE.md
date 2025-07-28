# Debug Output Analysis Guide - Per-User Chat Encryption

## Overview
This guide helps analyze debug output from the per-user chat encryption system to verify correct operation and troubleshoot issues.

---

## 🔍 Expected Log Patterns

### 1. Successful Encryption Cycle

**When a user sends a message, look for this sequence:**

```
DEBUG: before_flush: Processing new Chat object ID <chat_id> for encryption.
DEBUG: Successfully set plaintext DEK in context for user <user_id> for chat operation.
INFO: (CHAT) BEFORE ENCRYPT: <original_message_text>...
INFO: (CHAT) AFTER ENCRYPT: Z0FBQUFBQm9o<base64_ciphertext>...
DEBUG: Cleared DEK from context variable.
```

**What this means:**
- ✅ SQLAlchemy event listener triggered correctly
- ✅ User-specific DEK retrieved and set in context
- ✅ Message content encrypted with user's DEK
- ✅ Context cleaned up after operation

### 2. Successful Decryption Cycle

**When a user loads their chat history:**

```
DEBUG: --- SQLAlchemy 'after_load' event triggered for Chat ID: <chat_id> ---
DEBUG: Successfully set plaintext DEK in context for user <user_id> for chat operation.
INFO: (CHAT) BEFORE DECRYPT: Z0FBQUFBQm9o<base64_ciphertext>...
INFO: (CHAT) AFTER DECRYPT: <original_message_text>...
DEBUG: Cleared DEK from context variable.
```

**What this means:**
- ✅ Chat loaded from database with encrypted content
- ✅ User-specific DEK retrieved for decryption
- ✅ Ciphertext successfully decrypted to original message
- ✅ Context cleaned up

### 3. Chat Branching (History) Encryption

**When chat history/branches are processed:**

```
INFO: (HISTORY) BEFORE ENCRYPT: <branch_message_text>...
INFO: (HISTORY) AFTER ENCRYPT: Z0FBQUFBQm9o<base64_ciphertext>...
INFO: (HISTORY) BEFORE DECRYPT: Z0FBQUFBQm9o<base64_ciphertext>...
INFO: (HISTORY) AFTER DECRYPT: <branch_message_text>...
```

**What this means:**
- ✅ Both main messages AND history branches are encrypted
- ✅ Chat editing/branching functionality preserved with encryption

---

## 🚨 Error Patterns to Watch For

### 1. Missing User or Encryption Keys

```
ASSERT: User not found for ID: <user_id>. Cannot set user-specific DEK. Fallback to mock key.
ASSERT: User <user_id> is missing 'user_key' or 'user_encrypted_dek' in DB. Cannot perform user-specific encryption/decryption. Fallback to mock key.
```

**Diagnosis:**
- ❌ User doesn't exist or lacks encryption fields
- ❌ Database schema missing encryption columns
- ❌ User creation process not populating encryption fields

**Fix:** Verify database schema and user creation process

### 2. DEK Decryption Failures

```
ASSERT: Failed to decrypt DEK for user <user_id>: <error>. Fallback to mock key.
```

**Diagnosis:**
- ❌ UserKey doesn't match the one used to encrypt the DEK
- ❌ Corrupted encryption data in database
- ❌ Key derivation process changed

**Fix:** Check user encryption key consistency

### 3. Message Decryption Failures

```
ERROR: DECRYPTION FAILED for chat message: <error>
ERROR: DECRYPTION FAILED for history message <msg_id>: <error>
```

**Diagnosis:**
- ❌ Message encrypted with different DEK than current user has
- ❌ Corrupted ciphertext in database
- ❌ Wrong user trying to access another user's messages

**Fix:** Verify user isolation and data integrity

### 4. Mock Key Usage Warning

```
Warning: Using MOCK_ENCRYPTION_KEY. Ensure this is intended (Phase 1 or unauthenticated context).
```

**Diagnosis:**
- ⚠️ System fell back to mock encryption key
- Could be normal for: unauthenticated users, errors, fallback scenarios
- Could be problematic if happening for authenticated users

**Action:** Investigate why user-specific DEK wasn't available

---

## 📊 Validation Checklist

### Real-Time Validation During Testing

When testing the system, verify these patterns:

**✅ Per-User Isolation:**
- [ ] Each user sees different ciphertext for same message content
- [ ] User A cannot see decrypted content from User B's messages
- [ ] Different base64 ciphertext patterns for different users

**✅ Encryption Format:**
- [ ] Ciphertext starts with `Z0FBQUFBQm9o` (Base64 encoded Fernet tokens)
- [ ] No plaintext content visible in `(CHAT) AFTER ENCRYPT` logs
- [ ] Symmetric encrypt/decrypt cycles (same content in/out)

**✅ Context Management:**
- [ ] Every `Successfully set plaintext DEK` has matching `Cleared DEK from context`
- [ ] No DEK context leakage between users
- [ ] Context cleared even when exceptions occur

**✅ Multi-Language Support:**
- [ ] Unicode characters (emojis, accented chars, non-Latin scripts) encrypt/decrypt correctly
- [ ] No encoding issues in logs or database

---

## 🔧 Troubleshooting Guide

### Issue: No Encryption Logs Appearing

**Symptoms:**
- No `(CHAT) BEFORE ENCRYPT` / `(CHAT) AFTER ENCRYPT` logs
- Messages appear to save normally but may not be encrypted

**Debug Steps:**
1. Check if SQLAlchemy event listeners are registered:
   ```python
   python -c "from open_webui.models import db_encryption_shim; print('Shim loaded')"
   ```
2. Verify database has encryption columns:
   ```sql
   .schema user  -- Should show salt, user_encrypted_dek, etc.
   ```
3. Check if users have encryption keys populated

### Issue: Decryption Errors on Load

**Symptoms:**
- Messages show as `[DECRYPTION ERROR]` in UI
- `DECRYPTION FAILED` errors in logs

**Debug Steps:**
1. Check if user's DEK can be decrypted:
   ```python
   user = Users.get_user_by_id(user_id)
   dek = decrypt_dek(user.user_encrypted_dek, user.user_key)
   ```
2. Verify message format in database:
   ```sql
   SELECT json_extract(chat, '$.messages[0].content') FROM chat WHERE user_id = 'user_id';
   ```
3. Check for user_id mismatches

### Issue: Cross-User Data Access

**Symptoms:**
- User can see another user's decrypted messages
- Same ciphertext appearing for different users

**Debug Steps:**
1. Verify user isolation in database:
   ```sql
   SELECT DISTINCT user_encrypted_dek FROM user;  -- Should be unique per user
   ```
2. Check authentication system - ensure correct user_id in context
3. Verify DEK context is cleared between requests

### Issue: Performance Problems

**Symptoms:**
- Slow message loading
- High CPU usage during chat operations

**Debug Steps:**
1. Monitor encryption/decryption frequency in logs
2. Check for unnecessary re-encryption of already encrypted content
3. Verify database indexes on user_id and encryption fields
4. Profile SQLAlchemy query performance

---

## 📈 Performance Monitoring

### Key Metrics to Track

**Encryption Operations:**
- Count of `BEFORE ENCRYPT` vs `AFTER ENCRYPT` (should match)
- Time between encrypt start/finish (should be <10ms typically)
- Frequency of mock key fallbacks (should be minimal)

**Database Operations:**
- Query time for user encryption data retrieval
- Chat loading time with decryption
- Database connection pool usage

**Error Rates:**
- Decryption failure rate (should be <0.1%)
- Mock key usage rate for authenticated users (should be <1%)
- Context cleanup failure rate (should be 0%)

### Log Analysis Commands

```bash
# Count encryption operations
grep "BEFORE ENCRYPT" logs.txt | wc -l

# Find decryption errors
grep "DECRYPTION FAILED" logs.txt

# Check mock key usage frequency  
grep "Using MOCK_ENCRYPTION_KEY" logs.txt | wc -l

# Monitor user isolation
grep "Successfully set plaintext DEK" logs.txt | awk '{print $NF}' | sort | uniq -c
```

---

## ✅ Success Indicators

**System is working correctly when you see:**

1. **Consistent encrypt/decrypt cycles** for each user
2. **Unique ciphertext** for each user's messages  
3. **No decryption errors** during normal operation
4. **Clean context management** (all DEKs cleared after use)
5. **History/branching support** (both CHAT and HISTORY logs)
6. **Multi-language content** encrypting properly
7. **Zero cross-user data leakage**

**System is ready for production when:**

1. **All users can encrypt/decrypt their own data**
2. **No user can access another user's decrypted data**
3. **Performance meets requirements (encrypt/decrypt <10ms)**
4. **Error rates are acceptable (<0.1% decryption failures)**
5. **Audit logs show proper encryption coverage**
6. **Database storage shows encrypted format consistently**

---

This guide should help you analyze the debug output to confirm your per-user chat encryption is working correctly and troubleshoot any issues that arise.