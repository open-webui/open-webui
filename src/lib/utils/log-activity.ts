// src/lib/utils/log-activity.ts
export function logActivity(log_message: string, user_id: string | undefined) {
    const timestamp = new Date().toISOString();
    fetch('/api/log_activity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            log_message: `[${timestamp}] ${log_message}`,
            user_id
        })
    });
}
