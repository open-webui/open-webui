# Heroku Postgres Backup Setup

## Current Configuration

**App Name:** `contextquiz-openwebui-kidsgpt`  
**Database:** `postgresql-opaque-40379`  
**Plan:** `essential-0`  
**Backup Schedule:** Daily at 02:00 America/Los_Angeles  
**Status:** ✅ Active

## Scheduled Commands

### View Current Backup Schedule
```bash
heroku pg:backups:schedules --app contextquiz-openwebui-kidsgpt
```

### View All Backups
```bash
heroku pg:backups --app contextquiz-openwebui-kidsgpt
```

### Create Manual Backup
```bash
heroku pg:backups:capture --app contextquiz-openwebui-kidsgpt
```

### Download Backup
```bash
heroku pg:backups:download --app contextquiz-openwebui-kidsgpt
```

### Restore from Backup
```bash
heroku pg:backups:restore BACKUP_ID postgresql-opaque-40379 --app contextquiz-openwebui-kidsgpt
```

## Important Notes

### Plan Limitations (Essential-0)
- **No Automated Backups**: The `essential-0` plan does not support automatic daily backups
- **Manual Backups Only**: Only manual backups can be created and scheduled
- **No Continuous Protection**: Point-in-time recovery is not available
- **Backup Retention**: Manually created backups must be managed by you

### Upgrade Path for Automated Backups

To enable true automated daily backups, consider upgrading to:
- **Standard-0**: Includes daily automated backups with 7-day retention
- **Premium-0**: Includes daily automated backups with 30-day retention + continuous protection

Current backup schedule was set, but **will not run automatically** on the `essential-0` plan.

### Recommended Backup Strategy

Since the current plan doesn't support automated backups, consider:

1. **Manual Backup Daily**: Create a manual backup script that runs daily via Heroku Scheduler
2. **Upgrade Plan**: Move to at least `standard-0` for automated backup support
3. **External Backup**: Use a third-party backup service or cron job to download backups regularly

### Checking Backup Status

Monitor your backups regularly:
```bash
# View recent backups
heroku pg:backups --app contextquiz-openwebui-kidsgpt

# Get detailed info about a specific backup
heroku pg:backups:info BACKUP_ID --app contextquiz-openwebui-kidsgpt
```

### Verifying Backup Works

To verify your backup system works correctly:

1. **Create a test backup**:
   ```bash
   heroku pg:backups:capture --app contextquiz-openwebui-kidsgpt
   ```

2. **Check backup status**:
   ```bash
   heroku pg:backups --app contextquiz-openwebui-kidsgpt
   ```
   Look for "Completed" status and note the backup ID (e.g., `b002`)

3. **Get detailed backup info**:
   ```bash
   heroku pg:backups:info BACKUP_ID --app contextquiz-openwebui-kidsgpt
   ```
   Verify:
   - Status: `Completed`
   - Type: `Manual` or `Scheduled`
   - Original DB Size: Should match your database size
   - Backup Size: Should be compressed (usually 99%+ compression)

4. **Test download** (optional):
   ```bash
   heroku pg:backups:download BACKUP_ID --app contextquiz-openwebui-kidsgpt
   ```
   This downloads a `.dump` file you can inspect locally

**Expected Results**:
- ✅ Backup completes in under 1 minute (for small databases)
- ✅ Status shows "Completed" 
- ✅ All tables are backed up (see backup logs)
- ✅ Backup size is significantly compressed
- ✅ Backup ID is listed in backup history

## Next Steps

1. **Verify Current Setup**: Run `heroku pg:backups:schedules` to confirm schedule
2. **Consider Upgrade**: If automated backups are critical, upgrade to `standard-0` or higher
3. **Implement Manual Schedule**: Set up Heroku Scheduler or external cron to trigger daily backups
4. **Monitor Backups**: Check backup creation and status regularly

## References

- [Heroku Postgres Backups Documentation](https://devcenter.heroku.com/articles/heroku-postgres-backups)
- [Heroku Scheduler](https://devcenter.heroku.com/articles/scheduler)
- [Heroku Postgres Plans](https://devcenter.heroku.com/articles/heroku-postgres-plans)

