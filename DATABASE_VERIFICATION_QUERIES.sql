-- Database Verification Queries for Per-User Chat Encryption
-- Use these queries to verify encrypted storage and unique user keys

-- =============================================================================
-- USER ENCRYPTION FIELDS VERIFICATION
-- =============================================================================

-- Check all users and their encryption key status
.headers on
.mode column
SELECT 
    id,
    email,
    name,
    user_key IS NOT NULL as has_user_key,
    user_encrypted_dek IS NOT NULL as has_encrypted_dek,
    salt IS NOT NULL as has_salt,
    kms_encrypted_dek IS NOT NULL as has_kms_dek,
    LENGTH(user_key) as user_key_length,
    LENGTH(user_encrypted_dek) as encrypted_dek_length,
    LENGTH(salt) as salt_length
FROM user
ORDER BY created_at;

-- Verify unique encryption keys per user
SELECT 
    'Unique user_key count:' as verification,
    COUNT(DISTINCT user_key) as count
FROM user 
WHERE user_key IS NOT NULL;

SELECT 
    'Unique user_encrypted_dek count:' as verification,
    COUNT(DISTINCT user_encrypted_dek) as count
FROM user 
WHERE user_encrypted_dek IS NOT NULL;

SELECT 
    'Unique salt count:' as verification,
    COUNT(DISTINCT salt) as count
FROM user 
WHERE salt IS NOT NULL;

-- =============================================================================
-- CHAT ENCRYPTION VERIFICATION
-- =============================================================================

-- Overview of chat data and encryption status
SELECT 
    id,
    user_id,
    title,
    LENGTH(chat) as chat_size,
    created_at,
    updated_at
FROM chat
ORDER BY updated_at DESC
LIMIT 10;

-- Check for encrypted message format in recent chats
SELECT 
    c.id,
    c.user_id,
    u.email,
    c.title,
    -- Extract first message content to check format
    json_extract(c.chat, '$.messages[0].content') as first_message_content,
    -- Check if it's encrypted format
    json_extract(c.chat, '$.messages[0].content.is_encrypted') as is_first_msg_encrypted,
    -- Extract ciphertext preview
    substr(json_extract(c.chat, '$.messages[0].content.ciphertext'), 1, 50) as ciphertext_preview
FROM chat c
JOIN user u ON c.user_id = u.id
WHERE json_extract(c.chat, '$.messages') IS NOT NULL
ORDER BY c.updated_at DESC
LIMIT 5;

-- Check for encrypted history messages
SELECT 
    c.id,
    c.user_id,
    u.email,
    -- Count total history messages
    json_extract(c.chat, '$.history.messages') IS NOT NULL as has_history,
    -- Sample a history message if it exists
    json_type(json_extract(c.chat, '$.history.messages')) as history_type
FROM chat c
JOIN user u ON c.user_id = u.id
WHERE json_extract(c.chat, '$.history.messages') IS NOT NULL
LIMIT 5;

-- =============================================================================
-- DETAILED ENCRYPTION FORMAT ANALYSIS
-- =============================================================================

-- Examine the structure of encrypted messages
SELECT 
    'Message Structure Analysis' as analysis_type,
    c.id as chat_id,
    u.email,
    json_extract(c.chat, '$.messages[0].role') as message_role,
    json_type(json_extract(c.chat, '$.messages[0].content')) as content_type,
    CASE 
        WHEN json_extract(c.chat, '$.messages[0].content.is_encrypted') = 1 THEN 'ENCRYPTED'
        WHEN json_type(json_extract(c.chat, '$.messages[0].content')) = 'text' THEN 'PLAINTEXT'
        ELSE 'UNKNOWN'
    END as encryption_status,
    LENGTH(json_extract(c.chat, '$.messages[0].content.ciphertext')) as ciphertext_length
FROM chat c
JOIN user u ON c.user_id = u.id
WHERE json_extract(c.chat, '$.messages[0]') IS NOT NULL
ORDER BY c.updated_at DESC
LIMIT 10;

-- Check for mixed encrypted/unencrypted content (should not exist)
SELECT 
    'Mixed Encryption Check' as check_type,
    c.id,
    u.email,
    COUNT(*) as total_messages,
    SUM(
        CASE 
            WHEN json_extract(value, '$.content.is_encrypted') = 1 THEN 1 
            ELSE 0 
        END
    ) as encrypted_messages,
    SUM(
        CASE 
            WHEN json_type(json_extract(value, '$.content')) = 'text' THEN 1 
            ELSE 0 
        END
    ) as plaintext_messages
FROM chat c
JOIN user u ON c.user_id = u.id,
json_each(c.chat, '$.messages')
GROUP BY c.id, u.email
HAVING encrypted_messages > 0 AND plaintext_messages > 0;

-- =============================================================================
-- USER ISOLATION VERIFICATION
-- =============================================================================

-- Verify users have different encryption artifacts
WITH user_encryption AS (
    SELECT 
        id,
        email,
        hex(user_key) as user_key_hex,
        hex(user_encrypted_dek) as encrypted_dek_hex,
        hex(salt) as salt_hex
    FROM user 
    WHERE user_key IS NOT NULL
)
SELECT 
    u1.email as user1,
    u2.email as user2,
    CASE WHEN u1.user_key_hex = u2.user_key_hex THEN 'SAME' ELSE 'DIFFERENT' END as user_key_comparison,
    CASE WHEN u1.encrypted_dek_hex = u2.encrypted_dek_hex THEN 'SAME' ELSE 'DIFFERENT' END as encrypted_dek_comparison,
    CASE WHEN u1.salt_hex = u2.salt_hex THEN 'SAME' ELSE 'DIFFERENT' END as salt_comparison
FROM user_encryption u1
CROSS JOIN user_encryption u2
WHERE u1.id < u2.id;

-- =============================================================================
-- PERFORMANCE AND STORAGE ANALYSIS
-- =============================================================================

-- Analyze storage overhead of encryption
SELECT 
    'Storage Analysis' as analysis,
    AVG(LENGTH(chat)) as avg_chat_size,
    MIN(LENGTH(chat)) as min_chat_size,
    MAX(LENGTH(chat)) as max_chat_size,
    COUNT(*) as total_chats
FROM chat;

-- Message count analysis
WITH message_counts AS (
    SELECT 
        c.id,
        c.user_id,
        json_array_length(c.chat, '$.messages') as message_count,
        COALESCE(json_type(json_extract(c.chat, '$.history.messages')), 'null') as has_history
    FROM chat c
)
SELECT 
    'Message Count Analysis' as analysis,
    AVG(message_count) as avg_messages_per_chat,
    MAX(message_count) as max_messages_per_chat,
    COUNT(*) as total_chats,
    SUM(CASE WHEN has_history != 'null' THEN 1 ELSE 0 END) as chats_with_history
FROM message_counts;

-- =============================================================================
-- SECURITY VALIDATION QUERIES
-- =============================================================================

-- Check for any unencrypted sensitive patterns
SELECT 
    'Security Scan' as scan_type,
    c.id,
    u.email,
    'Found potential plaintext sensitive data' as finding
FROM chat c
JOIN user u ON c.user_id = u.id
WHERE 
    -- Look for plaintext content that might contain sensitive patterns
    json_type(json_extract(c.chat, '$.messages[0].content')) = 'text'
    AND (
        json_extract(c.chat, '$.messages[0].content') LIKE '%password%'
        OR json_extract(c.chat, '$.messages[0].content') LIKE '%secret%'
        OR json_extract(c.chat, '$.messages[0].content') LIKE '%key%'
        OR json_extract(c.chat, '$.messages[0].content') LIKE '%token%'
    );

-- Verify no user keys are stored as plaintext in chat content
SELECT 
    'User Key Leak Check' as check_type,
    'No user keys found in chat content' as result
WHERE NOT EXISTS (
    SELECT 1 
    FROM chat c
    JOIN user u ON c.user_id = u.id
    WHERE c.chat LIKE '%' || hex(u.user_key) || '%'
);

-- =============================================================================
-- VALIDATION SUMMARY
-- =============================================================================

-- Final validation summary
SELECT 'VALIDATION SUMMARY' as section, '==================' as separator;

SELECT 
    'Total users with encryption keys:' as metric,
    COUNT(*) as value
FROM user 
WHERE user_key IS NOT NULL AND user_encrypted_dek IS NOT NULL AND salt IS NOT NULL;

SELECT 
    'Total encrypted chats:' as metric,
    COUNT(*) as value
FROM chat c
WHERE json_extract(c.chat, '$.messages[0].content.is_encrypted') = 1;

SELECT 
    'Users with unique encryption keys:' as metric,
    COUNT(DISTINCT user_key) as value
FROM user 
WHERE user_key IS NOT NULL;

SELECT 
    'Chats with history branches:' as metric,
    COUNT(*) as value
FROM chat c
WHERE json_extract(c.chat, '$.history.messages') IS NOT NULL;

-- Expected results for a properly configured system:
-- 1. All users should have unique encryption keys (user_key, user_encrypted_dek, salt)
-- 2. All chat messages should be in encrypted format with is_encrypted=1
-- 3. No user should have the same encryption artifacts as another
-- 4. No plaintext sensitive data should be found in chat content
-- 5. No user keys should be leaked in chat content